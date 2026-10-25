"""Optional all-frame LK fallback with a reviewed mask, fixed lens and heldout gate.

Run long solves through scripts/jobs.py. This measures image tracks, not semantic
depth; even a passed heldout check does not establish physical or metric depth.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from fractions import Fraction
import json
import math
from pathlib import Path
import re
import sqlite3
import struct
import subprocess
import sys

from colmap_ae import binary, capture, fresh, load, save, tool_env
from geometry import pinhole, read_model

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = np = None


def prepared(path):
    manifest = load(path)
    if manifest.get("schema") != "aftereffect-colmap.frames.v1":
        raise ValueError("Use a manifest.json made by colmap_ae.py prepare")
    width, height = manifest["width"], manifest["height"]
    if not isinstance(width, int) or not isinstance(height, int) or min(width, height) <= 21:
        raise ValueError("Invalid prepared image dimensions")
    frames = manifest["frames"]
    if len(frames) < 3 or [f["frame"] for f in frames] != list(range(len(frames))):
        raise ValueError("Prepared frames must be complete, contiguous and zero-based")
    names = [f["name"] for f in frames]
    if names != [f"f{i:06d}.png" for i in range(len(names))]:
        raise ValueError("Use the complete generated f000000.png sequence")
    fps = Fraction(manifest["fps_num"], manifest["fps_den"])
    if fps <= 0 or any(Fraction(f["time_seconds"]) != Fraction(i, 1)/fps for i, f in enumerate(frames)):
        raise ValueError("Prepared frame timing must be exact CFR")
    images = Path(manifest["images_dir"]).expanduser()
    if not images.is_absolute():
        images = path.parent/images
    images = images.resolve()
    if any(not (images/name).is_file() for name in names):
        raise ValueError("Prepared images missing; no frame may be skipped")
    return manifest, names, images


def read_mask(path, width, height):
    """Allow-mask in prepared OpenCV pixel coordinates: x right, y down from 0."""
    from PIL import Image
    if path.suffix.lower() == ".png":
        with Image.open(path) as image:
            if image.size != (width, height) or image.mode not in {"1", "L"}:
                raise ValueError("Mask PNG must be same-size grayscale, without alpha")
            mask = np.asarray(image.convert("L"), dtype=np.uint8).copy()
        if not np.isin(mask, [0, 255]).all():
            raise ValueError("Mask PNG must contain only black 0 and white 255")
    elif path.suffix.lower() == ".json":
        data = load(path)
        if data.get("width") != width or data.get("height") != height:
            raise ValueError("Mask width/height must match the prepared images; never auto-scale")
        mask = np.zeros((height, width), np.uint8)
        for key, value in (("polygons", 255), ("exclude_polygons", 0)):
            polygons = data.get(key, [])
            if not isinstance(polygons, list):
                raise ValueError(f"{key} must be a list of polygons")
            for polygon in polygons:
                points = np.asarray(polygon, dtype=np.float64)
                if (points.ndim != 2 or points.shape[1] != 2 or len(points) < 3
                        or not np.isfinite(points).all()
                        or (points < 0).any() or (points[:, 0] > width-1).any()
                        or (points[:, 1] > height-1).any()):
                    raise ValueError("Each mask polygon needs >=3 finite [x,y] points inside prepared pixels")
                cv2.fillPoly(mask, [np.rint(points).astype(np.int32)], value)
    else:
        raise ValueError("Use a reviewed .json polygon allow-mask or black/white .png")
    if not np.any(mask):
        raise ValueError("Mask allows no pixels")
    return mask


def read_gray(path, width, height):
    # imread does not support every Unicode path on Windows; imdecode does.
    image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    if image is None or image.shape != (height, width):
        raise ValueError(f"Prepared frame cannot be decoded at manifest size: {path.name}")
    return image


def measure_tracks(images, names, width, height, mask, max_corners):
    previous = read_gray(images/names[0], width, height)
    corners = cv2.goodFeaturesToTrack(previous, max_corners, .015, 12, mask=mask, blockSize=7)
    if corners is None:
        raise ValueError("Reviewed mask contains no trackable corners")
    points = corners[:, 0]
    alive = np.ones(len(points), dtype=bool)
    tracks, surviving = [points.copy()], [len(points)]
    options = dict(winSize=(21, 21), maxLevel=3,
                   criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, .01))
    for name in names[1:]:
        current = read_gray(images/name, width, height)
        ids = np.flatnonzero(alive)
        if not len(ids):
            raise ValueError(f"No corner survived to {name}; no reseeding or invented observations")
        p = points[ids].reshape(-1, 1, 2)
        q, ok, error = cv2.calcOpticalFlowPyrLK(previous, current, p, None, **options)
        if q is None or ok is None or error is None:
            raise ValueError(f"Forward LK failed at {name}")
        q = q[:, 0]
        good = ((ok[:, 0] > 0) & (error[:, 0] < 15) & np.isfinite(q).all(axis=1)
                & (q[:, 0] > 10) & (q[:, 0] < width-10)
                & (q[:, 1] > 10) & (q[:, 1] < height-10))
        candidate = np.flatnonzero(good)
        if len(candidate):
            back, ok_back, _ = cv2.calcOpticalFlowPyrLK(
                current, previous, q[candidate].reshape(-1, 1, 2), None, **options)
            if back is None or ok_back is None:
                good[:] = False
            else:
                good[candidate] &= ((ok_back[:, 0] > 0) & np.isfinite(back[:, 0]).all(axis=1)
                                    & (np.linalg.norm(back[:, 0]-p[candidate, 0], axis=1) < .75))
        alive[ids] = good
        points = np.full_like(points, np.nan)
        points[ids[good]] = q[good]
        tracks.append(points.copy())
        surviving.append(int(alive.sum()))
        previous = current
    return np.stack(tracks)[:, alive], surviving


def split_tracks(tracks):
    """Reserve every fifth complete track before any feature or match import."""
    ids = np.arange(tracks.shape[1])
    heldout_ids, train_ids = ids[ids % 5 == 0], ids[ids % 5 != 0]
    return tracks[:, train_ids], tracks[:, heldout_ids], train_ids, heldout_ids


def intrinsics(width, height, focal):
    if not math.isfinite(focal) or focal <= 0:
        raise ValueError("--focal-px must be a positive finite focal length at prepared image size")
    return np.array([[focal, 0, width/2], [0, focal, height/2], [0, 0, 1]], dtype=np.float64)


def check_calibration(cameras, images, names, width, height, focal):
    used = {images[name]["camera_id"] for name in names}
    if len(used) != 1:
        raise ValueError("Temporal fallback requires one shared fixed camera")
    camera = cameras[used.pop()]
    fx, fy, cx, cy = pinhole(camera)
    if ((camera["width"], camera["height"]) != (width, height)
            or not np.allclose([fx, fy, cx, cy], [focal, focal, width/2, height/2], rtol=1e-8, atol=1e-8)):
        raise ValueError("Solved intrinsics changed from the supplied fixed pinhole assumption")
    return intrinsics(width, height, focal)


def heldout_report(heldout, images, names, k):
    projections = [k @ np.column_stack((images[name]["rotation"], images[name]["translation"])) for name in names]
    homogeneous = cv2.triangulatePoints(projections[0], projections[-1], heldout[0].T, heldout[-1].T)
    valid = np.isfinite(homogeneous).all(axis=0) & (np.abs(homogeneous[3]) > 1e-12)
    xyz = np.full((heldout.shape[1], 3), np.nan)
    xyz[valid] = (homogeneous[:3, valid]/homogeneous[3, valid]).T
    positive = valid.copy()
    residuals = []
    with np.errstate(invalid="ignore", divide="ignore"):
        for i, name in enumerate(names):
            camera = xyz @ np.asarray(images[name]["rotation"]).T + images[name]["translation"]
            positive &= camera[:, 2] > 1e-8
            uv = camera @ k.T
            residuals.append(np.linalg.norm(uv[:, :2]/uv[:, 2:3]-heldout[i], axis=1))
    errors = np.asarray(residuals)
    finite = bool(np.isfinite(errors).all())
    report = {"schema": "aftereffect-colmap.heldout.v1", "unused_tracks": int(heldout.shape[1]),
              "finite": finite, "positive_depth_fraction": float(positive.mean()),
              "median_error_px": float(np.median(errors)) if finite else None,
              "p95_error_px": float(np.percentile(errors, 95)) if finite else None,
              "max_error_px": float(np.max(errors)) if finite else None,
              "per_frame_p95_px": [float(np.percentile(row, 95)) if np.isfinite(row).all() else None for row in errors],
              "thresholds": {"median_error_px_max": 1.5, "p95_error_px_max": 3.0, "positive_depth_fraction_min": .95},
              "method": "Unused first/last tracks triangulated once; reprojected through every measured camera",
              "note": "Heldout image fit under an assumed lens is not physical/metric depth or native AE attachment proof."}
    report["passed"] = bool(heldout.shape[1] >= 20 and finite and report["positive_depth_fraction"] >= .95
                            and report["median_error_px"] <= 1.5 and report["p95_error_px"] <= 3)
    return report


def feature_files(folder, names, train):
    folder.mkdir()
    zeros = " 0"*128
    for i, name in enumerate(names):
        with (folder/(name+".txt")).open("x", encoding="ascii") as stream:
            stream.write(f"{train.shape[1]} 128\n")
            for x, y in train[i]:
                stream.write(f"{x:.8f} {y:.8f} 1 0{zeros}\n")


def raw_matches(path, names, count):
    gaps, gap = {len(names)-1}, 1
    while gap < len(names):
        gaps.add(gap)
        gap *= 2
    with path.open("x", encoding="ascii") as stream:
        for i, name in enumerate(names):
            for gap in sorted(gaps):
                if i+gap < len(names):
                    stream.write(f"{name} {names[i+gap]}\n")
                    stream.writelines(f"{k} {k}\n" for k in range(count))
                    stream.write("\n")


def imported_images(database, names, count, width, height, focal):
    # Native database_creator + feature_importer own schema, rigs and frames.
    # Read only the shared stable columns; never clone a previous shot's DB.
    with sqlite3.connect(database.as_uri()+"?mode=ro", uri=True) as db:
        byname = {name: ident for ident, name in db.execute("SELECT image_id,name FROM images")}
        counts = dict(db.execute("SELECT image_id,rows FROM keypoints"))
        cameras = list(db.execute("SELECT model,width,height,params FROM cameras"))
    if set(byname) != set(names) or any(counts.get(byname[name]) != count for name in names):
        raise ValueError("Native feature import did not preserve every training observation")
    if len(cameras) != 1 or cameras[0][:3] != (0, width, height):
        raise ValueError("Native feature import did not create one shared SIMPLE_PINHOLE camera")
    if not np.allclose(struct.unpack("<3d", cameras[0][3]), [focal, width/2, height/2]):
        raise ValueError("Native feature import changed the fixed camera parameters")
    return byname


def option(help_text, *names):
    for name in names:
        if re.search(r"--"+re.escape(name)+r"\s", help_text):
            return "--"+name
    raise ValueError(f"Unsupported COLMAP CLI options: {names}")


def solve(args):
    if cv2 is None or np is None:
        raise ValueError("Install optional requirements-tracking.txt in the project venv first")
    if not 0 < args.min_angle <= args.init_min_angle < 180:
        raise ValueError("Require 0 < --min-angle <= --init-min-angle < 180 degrees")
    if not 125 <= args.max_corners <= 10000:
        raise ValueError("--max-corners must be 125..10000")
    path = args.manifest.expanduser().resolve()
    manifest, names, images = prepared(path)
    width, height = manifest["width"], manifest["height"]
    k = intrinsics(width, height, args.focal_px)
    mask_path = args.mask.expanduser().resolve()
    mask = read_mask(mask_path, width, height)
    exe = binary("colmap", args.colmap)
    matching = capture([exe, "matches_importer", "-h"])
    mgpu = option(matching, "FeatureMatching.use_gpu", "SiftMatching.use_gpu")
    mthreads = option(matching, "FeatureMatching.num_threads", "SiftMatching.num_threads")
    guided = option(matching, "FeatureMatching.guided_matching", "SiftMatching.guided_matching")
    local_angle = option(capture([exe, "mapper", "-h"]),
                         "Mapper.ba_local_min_tri_angle", "Mapper.local_ba_min_tri_angle")
    out = fresh(args.out)
    weak = args.min_angle < 1.5 or args.init_min_angle < 16
    solution = {"schema": "aftereffect-colmap.solution.v1", "method": "temporal_lk", "manifest": str(path),
                "colmap": next((line.strip() for line in matching.splitlines() if "COLMAP" in line), "unknown"),
                "models": {}, "total_frames": len(names), "registered": 0, "points": 0,
                "missing_frames": names, "ready_for_export": False, "heldout_passed": False,
                "heldout_report": str(out/"heldout-report.json"), "visual_attachment": "not_reviewed",
                "lens_assumption": {"model": "SIMPLE_PINHOLE", "focal_px": args.focal_px,
                                    "cx": width/2, "cy": height/2, "calibrated": False},
                "min_angle_degrees": args.min_angle, "init_min_angle_degrees": args.init_min_angle,
                "weak_depth": weak, "note": "Fixed lens assumption; scale and physical depth unverified. Review in AE is still required."}
    save(out/"solution.json", solution)
    events = []
    def step(stage, argv):
        event = {"stage": stage, "started_at": datetime.now(timezone.utc).isoformat(), "command": [exe, *argv]}
        events.append(event)
        save(out/"stages.json", events)
        print(json.dumps({"stage": stage, "log": str(out/(stage+".log"))}), flush=True)
        with (out/(stage+".log")).open("x", encoding="utf-8") as log:
            process = subprocess.run([exe, *argv], stdout=log, stderr=subprocess.STDOUT, env=tool_env(exe))
        event.update(exit_code=process.returncode, ended_at=datetime.now(timezone.utc).isoformat())
        save(out/"stages.json", events)
        if process.returncode:
            raise ValueError(f"COLMAP {stage} failed with {process.returncode}; read {out/(stage+'.log')}")
    try:
        from PIL import Image
        cv2.setNumThreads(args.threads)
        Image.fromarray(mask).save(out/"allow-mask.png")
        tracks, surviving = measure_tracks(images, names, width, height, mask, args.max_corners)
        # OpenCV pixel centers start at (0,0); COLMAP's start at (.5,.5).
        train, heldout, train_ids, heldout_ids = split_tracks(tracks.astype(np.float64)+.5)
        save(out/"tracking-report.json", {"frames": len(names), "all_frame_tracks": int(tracks.shape[1]),
             "train_tracks": int(train.shape[1]), "heldout_tracks": int(heldout.shape[1]),
             "surviving_per_frame": surviving, "mask": str(mask_path), "mask_scope": "first-frame seed regions only",
             "used_mask": str(out/"allow-mask.png"), "opencv": cv2.__version__, "numpy": np.__version__,
             "coordinates": "COLMAP pixel centers; OpenCV measured xy + 0.5 in measured-tracks.npz",
             "method": "Sequential LK, forward/backward <0.75px, LK error <15; no reseeding; every fifth complete track held out",
             "first_last_displacement_median_px": float(np.median(np.linalg.norm(tracks[-1]-tracks[0], axis=1))) if tracks.shape[1] else None})
        if train.shape[1] < 100 or heldout.shape[1] < 20:
            raise ValueError(f"Only {train.shape[1]} train/{heldout.shape[1]} heldout all-frame tracks; need >=100/20. Review the shot/mask.")
        np.savez_compressed(out/"measured-tracks.npz", train=train, heldout=heldout, train_ids=train_ids, heldout_ids=heldout_ids)
        features = out/"features"
        feature_files(features, names, train)
        image_list = out/"image-list.txt"
        image_list.write_text("\n".join(names)+"\n", encoding="ascii")
        database = out/"database.db"
        step("database", ["database_creator", "--database_path", str(database)])
        step("features", ["feature_importer", "--database_path", str(database), "--image_path", str(images),
             "--import_path", str(features), "--image_list_path", str(image_list), "--ImageReader.single_camera", "1",
             "--ImageReader.camera_model", "SIMPLE_PINHOLE", "--ImageReader.camera_params", f"{args.focal_px},{width/2},{height/2}"])
        byname = imported_images(database, names, train.shape[1], width, height, args.focal_px)
        matches = out/"raw-matches.txt"
        raw_matches(matches, names, train.shape[1])
        step("verify-tracks", ["matches_importer", "--database_path", str(database), "--match_list_path", str(matches),
             "--match_type", "raw", mgpu, "0", mthreads, str(args.threads), guided, "0", "--TwoViewGeometry.max_error", "2"])
        sparse = out/"sparse"
        sparse.mkdir()
        step("mapping", ["mapper", "--database_path", str(database), "--image_path", str(images), "--output_path", str(sparse),
             "--Mapper.num_threads", str(args.threads), "--Mapper.multiple_models", "0",
             "--Mapper.ba_refine_focal_length", "0", "--Mapper.ba_refine_principal_point", "0", "--Mapper.ba_refine_extra_params", "0",
             "--Mapper.init_image_id1", str(byname[names[0]]), "--Mapper.init_image_id2", str(byname[names[-1]]),
             "--Mapper.init_min_tri_angle", str(args.init_min_angle), "--Mapper.tri_min_angle", str(args.min_angle),
             "--Mapper.filter_min_tri_angle", str(args.min_angle), local_angle, str(args.min_angle),
             "--Mapper.init_max_error", "2", "--Mapper.abs_pose_max_error", "3", "--Mapper.abs_pose_min_inlier_ratio", "0.5",
             "--Mapper.filter_max_reproj_error", "3"])
        for model in sorted(sparse.iterdir()):
            if (model/"images.bin").is_file():
                with (model/"images.bin").open("rb") as stream:
                    solution["models"][model.name] = struct.unpack("<Q", stream.read(8))[0]
        if not solution["models"]:
            raise ValueError("COLMAP registered no model; inspect logs, lens assumption and shot")
        selected = max(solution["models"], key=lambda name: solution["models"][name])
        raw = out/"raw-text"
        raw.mkdir()
        step("raw-text", ["model_converter", "--input_path", str(sparse/selected), "--output_path", str(raw), "--output_type", "TXT"])
        cameras, registered, points = read_model(raw)
        missing = [name for name in names if name not in registered]
        solution.update(selected_model=selected, registered=len(registered), points=len(points), missing_frames=missing)
        if missing or len(registered) != len(names):
            raise ValueError(f"Registered {len(registered)}/{len(names)} prepared frames; export blocked")
        k = check_calibration(cameras, registered, names, width, height, args.focal_px)
        report = heldout_report(heldout, registered, names, k)
        save(out/"heldout-report.json", report)
        if not report["passed"]:
            raise ValueError("Unused-track image fit failed; export blocked. Read heldout-report.json")
        undistorted, text_model = out/"undistorted", out/"text"
        step("undistort", ["image_undistorter", "--image_path", str(images), "--input_path", str(sparse/selected),
             "--output_path", str(undistorted), "--output_type", "COLMAP"])
        text_model.mkdir()
        step("text", ["model_converter", "--input_path", str(undistorted/"sparse"), "--output_path", str(text_model), "--output_type", "TXT"])
        final_cameras, final_images, _ = read_model(text_model)
        if set(final_images) != set(names) or any(not (undistorted/"images"/name).is_file() for name in names):
            raise ValueError("Undistorted output lost prepared frames; export blocked")
        check_calibration(final_cameras, final_images, names, width, height, args.focal_px)
        solution.update(text_model=str(text_model), images_dir=str(undistorted/"images"), heldout_passed=True, ready_for_export=True)
        save(out/"solution.json", solution)
        print(json.dumps({"solution": str(out/"solution.json"), "frames": len(names), "heldout_passed": True, "weak_depth": weak}), flush=True)
    except Exception as exc:
        solution.update(ready_for_export=False, failure_reason=str(exc))
        save(out/"solution.json", solution)
        raise


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--manifest", type=Path, required=True, help="complete prepared manifest.json")
    result.add_argument("--mask", type=Path, required=True, help="reviewed first-frame static-region JSON or binary grayscale PNG")
    result.add_argument("--focal-px", type=float, required=True, help="assumed fixed focal length at prepared image size")
    result.add_argument("--min-angle", type=float, required=True, help="triangulation/filter/local BA minimum degrees; normal COLMAP floor 1.5")
    result.add_argument("--init-min-angle", type=float, default=16, help="initial pair minimum degrees (COLMAP default 16); lower only with shot evidence")
    result.add_argument("--out", type=Path, required=True, help="new output directory; never reused")
    result.add_argument("--colmap", help="actual colmap executable, not a Windows .bat/.cmd")
    result.add_argument("--threads", type=int, choices=range(1, 17), default=4)
    result.add_argument("--max-corners", type=int, default=900, help="first-frame corner cap, 125..10000 (default 900)")
    return result


def main():
    try:
        solve(parser().parse_args())
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
