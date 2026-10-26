"""Teaching starter: video -> CPU COLMAP -> reviewable AE JSX. No AE MCP."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import statistics
import struct
import subprocess
import sys

from geometry import (ae_poses, centered_plate, cloud_glyphs, pinhole, plane_transform, project,
                      read_model, select_points, world_position)

ROOT = Path(__file__).resolve().parents[1]


def save(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def fresh(path):
    path = Path(path).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=False)
    return path


def binary(name, configured=None):
    candidate = configured or os.environ.get(name.upper()+"_BINARY")
    if not candidate and (ROOT/"tools.local.json").is_file():
        local = load(ROOT/"tools.local.json")
        if not isinstance(local, dict):
            raise ValueError("tools.local.json must map tool names to executable paths")
        candidate = local.get(name)
        if candidate:
            if not isinstance(candidate, str):
                raise ValueError(f"tools.local.json {name} must be an executable path")
            candidate = str(ROOT/Path(candidate).expanduser())
    candidate = candidate or shutil.which(name)
    if not candidate:
        raise ValueError(f"{name} not found. Read docs/setup-{('windows' if os.name == 'nt' else 'macos')}.md")
    path = Path(candidate).expanduser().resolve()
    if not path.is_file() or path.suffix.lower() in {".bat", ".cmd"}:
        raise ValueError(f"Use the actual {name} executable (Windows: bin/colmap.exe), not a batch file: {path}")
    return str(path)


def tool_env(exe):
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["OMP_NUM_THREADS"] = "4"
    if os.name == "nt":
        p = Path(exe).parent
        env["PATH"] = str(p)+os.pathsep+env.get("PATH", "")
        for q in (p.parent/"plugins", p/"plugins"):
            if q.is_dir():
                env["QT_PLUGIN_PATH"] = str(q); break
    return env


def capture(command, timeout=60):
    r = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       encoding="utf-8", errors="replace", timeout=timeout,
                       env=tool_env(command[0]), check=True)
    return r.stdout+r.stderr


def doctor(args):
    result = {"os": platform.platform(), "python": sys.version.split()[0], "tools": {},
              "colmap_weights_required": False, "ae_mcp_required": False}
    for name in ("colmap", "ffmpeg", "ffprobe"):
        try:
            exe = binary(name, getattr(args, name, None))
            text = capture([exe, "-h" if name == "colmap" else "-version"])
            result["tools"][name] = {"path": exe, "version": next((x for x in text.splitlines() if name.lower() in x.lower()), text.splitlines()[0])}
        except (ValueError, OSError, subprocess.SubprocessError) as exc:
            result["tools"][name] = {"error": str(exc)}
    try:
        import PIL
        result["pillow"] = PIL.__version__
    except ImportError:
        result["pillow"] = "missing: install requirements.txt in your venv"
    result["ready"] = all("error" not in x for x in result["tools"].values()) and not result["pillow"].startswith("missing")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 1


def prepare(args):
    from PIL import Image
    video = args.video.expanduser().resolve()
    if not video.is_file():
        raise ValueError("Video not found")
    ffmpeg, ffprobe = binary("ffmpeg"), binary("ffprobe")
    probe = json.loads(capture([ffprobe, "-v", "error", "-select_streams", "v:0",
        "-show_streams", "-show_frames", "-show_entries",
        "stream=width,height,avg_frame_rate,sample_aspect_ratio:frame=best_effort_timestamp_time",
        "-of", "json", str(video)], timeout=120))
    streams = probe.get("streams", [])
    if len(streams) != 1:
        raise ValueError("Expected one selected video stream")
    stream = streams[0]
    fps = Fraction(stream["avg_frame_rate"])
    if fps <= 0 or fps > 120 or stream.get("sample_aspect_ratio", "1:1") not in {"1:1", "N/A"}:
        raise ValueError("Use a square-pixel CFR teaching clip at <=120 fps")
    times = [Fraction(f["best_effort_timestamp_time"]) for f in probe.get("frames", []) if "best_effort_timestamp_time" in f]
    if not 3 <= len(times) <= args.max_frames:
        raise ValueError(f"Clip has {len(times)} frames; choose 3..{args.max_frames} frames or explicitly increase --max-frames. No silent sampling/trimming.")
    if any(abs(float(t-times[0]-Fraction(i, 1)/fps)) > 0.001/float(fps) for i, t in enumerate(times)):
        raise ValueError("Variable frame timing detected. Make an explicit CFR working copy first; preserve the original.")
    out = fresh(args.out); images = out/"images"; images.mkdir()
    command = [ffmpeg, "-nostdin", "-v", "error", "-n", "-i", str(video), "-map", "0:v:0",
        "-vf", f"scale=w='min({args.max_size},iw)':h='min({args.max_size},ih)':force_original_aspect_ratio=decrease:force_divisible_by=2",
        "-fps_mode", "passthrough", "-start_number", "0", str(images/"f%06d.png")]
    subprocess.run(command, check=True, env=tool_env(ffmpeg))
    paths = sorted(images.glob("f*.png"))
    if len(paths) != len(times):
        raise ValueError("Extracted frame count differs from decoded timestamps; inspect working copy")
    with Image.open(paths[0]) as image:
        width, height = image.size
    digest = hashlib.sha256()
    with video.open("rb") as src:
        for block in iter(lambda: src.read(1024*1024), b""):
            digest.update(block)
    manifest = {"schema": "aftereffect-colmap.frames.v1", "source": str(video), "source_sha256": digest.hexdigest(),
        "source_start_seconds": str(times[0]), "fps_num": fps.numerator, "fps_den": fps.denominator,
        "width": width, "height": height, "images_dir": str(images),
        "frames": [{"frame": i, "name": p.name, "time_seconds": str(Fraction(i, 1)/fps)} for i, p in enumerate(paths)]}
    save(out/"manifest.json", manifest)
    print(json.dumps({"prepared": str(out), "frames": len(paths), "size": [width, height], "fps": str(fps)}))


def solve(args):
    manifest_path = args.input.expanduser().resolve()/"manifest.json"
    manifest = load(manifest_path)
    if manifest.get("schema") != "aftereffect-colmap.frames.v1":
        raise ValueError("Unsupported frame manifest")
    images = Path(manifest["images_dir"])
    if not manifest["frames"] or any(not (images/f["name"]).is_file() for f in manifest["frames"]):
        raise ValueError("Prepared images missing")
    exe = binary("colmap", args.colmap)
    extraction = capture([exe, "feature_extractor", "-h"])
    matching = capture([exe, "sequential_matcher", "-h"])
    def option(help_text, *names):
        for n in names:
            if "--"+n+" " in help_text:
                return "--"+n
        raise ValueError(f"Unsupported COLMAP CLI; none of these documented options found: {names}")
    egpu = option(extraction, "FeatureExtraction.use_gpu", "SiftExtraction.use_gpu")
    ethreads = option(extraction, "FeatureExtraction.num_threads", "SiftExtraction.num_threads")
    mgpu = option(matching, "FeatureMatching.use_gpu", "SiftMatching.use_gpu")
    mthreads = option(matching, "FeatureMatching.num_threads", "SiftMatching.num_threads")
    out = fresh(args.out); (out/"sparse").mkdir()
    events = []
    def step(stage, argv):
        event = {"stage": stage, "started_at": datetime.now(timezone.utc).isoformat(), "command": [exe, *argv]}
        events.append(event); save(out/"stages.json", events)
        print(json.dumps({"stage": stage, "log": str(out/(stage+".log"))}), flush=True)
        with (out/(stage+".log")).open("w", encoding="utf-8") as log:
            result = subprocess.run([exe, *argv], stdout=log, stderr=subprocess.STDOUT, env=tool_env(exe))
        event["exit_code"] = result.returncode; event["ended_at"] = datetime.now(timezone.utc).isoformat()
        save(out/"stages.json", events)
        if result.returncode:
            raise ValueError(f"COLMAP {stage} failed with {result.returncode}; read {out/(stage+'.log')}")
    db = str(out/"database.db")
    step("features", ["feature_extractor", "--database_path", db, "--image_path", str(images),
        "--ImageReader.single_camera", "1", "--ImageReader.camera_model", "SIMPLE_RADIAL", egpu, "0", ethreads, str(args.threads)])
    step("matching", ["sequential_matcher", "--database_path", db, mgpu, "0", mthreads, str(args.threads),
        "--SequentialMatching.overlap", str(args.overlap)])
    step("mapping", ["mapper", "--database_path", db, "--image_path", str(images), "--output_path", str(out/"sparse"),
        "--Mapper.num_threads", str(args.threads), "--Mapper.ba_refine_principal_point", "0"])
    models = {}
    for model in (out/"sparse").iterdir():
        p = model/"images.bin"
        if p.is_file():
            with p.open("rb") as stream:
                models[model.name] = struct.unpack("<Q", stream.read(8))[0]
    if not models:
        raise ValueError("COLMAP registered no model. Inspect logs/shot; do not invent camera poses.")
    selected = args.model_id or max(models, key=lambda m: (models[m], m))
    if selected not in models:
        raise ValueError(f"Unknown --model-id; available {models}")
    undistorted = out/"undistorted"
    step("undistort", ["image_undistorter", "--image_path", str(images), "--input_path", str(out/"sparse"/selected),
        "--output_path", str(undistorted), "--output_type", "COLMAP"])
    text = out/"text"; text.mkdir()
    step("text", ["model_converter", "--input_path", str(undistorted/"sparse"), "--output_path", str(text), "--output_type", "TXT"])
    cameras, registered, points = read_model(text)
    missing = [f["name"] for f in manifest["frames"] if f["name"] not in registered]
    solution = {"schema": "aftereffect-colmap.solution.v1", "manifest": str(manifest_path), "text_model": str(text),
        "images_dir": str(undistorted/"images"), "colmap": capture([exe, "-h"]).splitlines()[0],
        "models": models, "selected_model": selected, "registered": len(registered), "total_frames": len(manifest["frames"]),
        "missing_frames": missing, "points": len(points), "ready_for_export": not missing,
        "note": "Registration/reprojection is not independent visual acceptance. Scale is arbitrary."}
    save(out/"solution.json", solution)
    print(json.dumps(solution, ensure_ascii=False))


def write_jsx(scene, out):
    # Small embedded literal, no eval/load of runtime JSON and no network permissions.
    if [f["frame"] for f in scene["frames"]] != list(range(len(scene["frames"]))):
        raise ValueError("JSX requires a complete zero-based frame map")
    fps = Fraction(scene["fps_num"], scene["fps_den"])
    if fps <= 0 or any(Fraction(f["time_seconds"]) != Fraction(f["frame"], 1)/fps for f in scene["frames"]):
        raise ValueError("JSX requires exact CFR timing")
    data = {"width": scene["intrinsics"]["width"], "height": scene["intrinsics"]["height"],
        "fps": scene["fps_num"]/scene["fps_den"], "frameCount": len(scene["frames"]),
        "zoom": scene["intrinsics"]["fx"], "plates": scene["plates"], "firstPlate": scene["frames"][0]["name"], "poses": ae_poses(scene),
        "origin": [scene["intrinsics"]["cx"], scene["intrinsics"]["cy"], 0],
        "plane": scene["world"].get("plane"), "model": scene.get("model"), "modelScale": scene.get("model_scale", 100)}
    glyphs = cloud_glyphs(scene)
    if scene.get("cloud_renderer", "shapes") == "model":
        from pointcloud import model_template, write_glb, write_rgb_check
        data["cloud"] = write_glb(out.parent/"pointcloud.glb",glyphs,data["origin"])
        scene["cloud_model"] = data["cloud"]
        template = model_template("import_cloud_model.jsx")
        write_rgb_check(out.parent)
    else:
        data["points"] = glyphs
        template = (ROOT/"scripts"/"import_scene.jsx").read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
    out.write_text(template.replace("/*__SCENE_DATA__*/", payload), encoding="utf-8")


def overlays(scene, out):
    from PIL import Image, ImageDraw
    k = scene["intrinsics"]; panels = []
    indices = sorted({0, len(scene["frames"])//2, len(scene["frames"])-1})
    for index in indices:
        frame = scene["frames"][index]
        with Image.open(Path(scene["plates"])/frame["name"]) as original:
            im = original.convert("RGB")
        draw = ImageDraw.Draw(im)
        for p in scene["points"]:
            uv = project(frame, p["xyz"], k)
            if uv and 0 <= uv[0] < im.width and 0 <= uv[1] < im.height:
                x, y = uv
                draw.ellipse((x-3, y-3, x+3, y+3), fill=tuple(p["rgb"]), outline="white")
                draw.text((x+4, y), str(p["id"]), fill="yellow", stroke_width=1, stroke_fill="black")
        draw.text((8, 8), f"frame {frame['frame']} | IDs are COLMAP points", fill="white", stroke_width=1, stroke_fill="black")
        im.thumbnail((800, 600)); panels.append(im)
    sheet = Image.new("RGB", (max(p.width for p in panels), sum(p.height for p in panels)))
    top = 0
    for panel in panels:
        sheet.paste(panel, (0, top)); top += panel.height
    sheet.save(out/"review.jpg", quality=92)


def validate_solution(solution):
    if solution.get("ready_for_export") is False:
        raise ValueError("Solution was rejected or has unregistered frames; inspect its report before export")
    if solution.get("method") == "temporal_lk":
        report = load(solution["heldout_report"])
        values = [report["median_error_px"],report["p95_error_px"],report["positive_depth_fraction"]]
        if (solution.get("ready_for_export") is not True or solution.get("heldout_passed") is not True or report.get("passed") is not True
            or report.get("finite") is not True or not all(type(v) in (int,float) and math.isfinite(v) for v in values)
            or type(report.get("unused_tracks")) is not int or report["unused_tracks"] < 20
            or not 0 <= values[0] <= 1.5 or not 0 <= values[1] <= 3 or not .95 <= values[2] <= 1):
            raise ValueError("Temporal heldout image attachment failed; export blocked")


def export_scene(args):
    from PIL import Image
    solution = load(args.solution); manifest = load(solution["manifest"])
    validate_solution(solution)
    if args.cloud_renderer == "model" and args.cloud_limit is not None:
        raise ValueError("Full model display keeps all points; --cloud-limit requires --cloud-renderer shapes")
    cameras, images, points = read_model(solution["text_model"])
    names = [f["name"] for f in manifest["frames"]]
    if names != [f"f{i:06d}.png" for i in range(len(names))]:
        raise ValueError("Use the generated f000000.png frame sequence; arbitrary output paths are not accepted")
    missing = [name for name in names if name not in images]
    if missing:
        raise ValueError(f"{len(missing)}/{len(names)} frames unregistered. Export blocked; inspect solution.json. No interpolation or dropped frames.")
    used = {images[name]["camera_id"] for name in names}
    if len(used) != 1:
        raise ValueError("Starter requires a single shared lens. Do not silently average multiple cameras.")
    camera = cameras[used.pop()]; k = centered_plate(camera)
    frames = [{**images[f["name"]], "frame": f["frame"], "time_seconds": f["time_seconds"]} for f in manifest["frames"]]
    if [f["frame"] for f in frames] != list(range(len(frames))):
        raise ValueError("Frame map must be contiguous from zero")
    out = fresh(args.out); plates = out/"plates"; plates.mkdir()
    for f in frames:
        src = Path(solution["images_dir"])/f["name"]
        with Image.open(src) as image:
            if image.size != (k["source_width"], k["source_height"]):
                raise ValueError("Undistorted plate dimensions differ from camera")
            if k["shift_x"] == 0 and k["shift_y"] == 0 and image.size == (k["width"], k["height"]):
                shutil.copyfile(src, plates/f["name"])
            else:
                image.convert("RGB").transform((k["width"], k["height"]), Image.Transform.AFFINE,
                    (1, 0, -k["shift_x"], 0, 1, -k["shift_y"]),
                    resample=Image.Resampling.BICUBIC, fillcolor="black").save(plates/f["name"])
    ordered = sorted(points.values(),key=lambda p:p["id"])
    limit = args.cloud_limit or 2000
    cloud = ordered if args.cloud_renderer == "model" or len(ordered)<=limit else [ordered[round(i*(len(ordered)-1)/(limit-1))] for i in range(limit)]
    scene = {"schema": "aftereffect-colmap.scene.v1", "intrinsics": k,
        "fps_num": manifest["fps_num"], "fps_den": manifest["fps_den"], "frames": frames,
        "points": select_points(points, frames[0], k, args.max_points), "total_points": len(points), "plates": str(plates),
        "cloud_points": cloud, "cloud_renderer": args.cloud_renderer,
        "point_size_px": args.point_size if args.point_size is not None else (3 if args.cloud_renderer == "model" else 6),
        "world": {"origin": frames[0]["center"], "basis": [[1,0,0],[0,1,0],[0,0,1]], "scale": args.scale},
        "model": str(args.model.expanduser().resolve()) if args.model else None, "model_scale": args.model_scale,
        "note": "Measured sparse RGB cloud. Marker size is a display choice, not object geometry. No semantic surfaces or metric scale inferred."}
    if scene["model"] and (not Path(scene["model"]).is_file() or Path(scene["model"]).suffix.lower() not in {".glb", ".gltf", ".obj", ".fbx"}):
        raise ValueError("Provide an existing GLB/GLTF/OBJ/FBX model")
    if not scene["points"]:
        raise ValueError("No stable visible guide points")
    ae_poses(scene)  # Reject unsupported poses before generating an importer.
    native_ply = solution.get("cloud_ply")
    if native_ply:
        with Path(native_ply).open('rb') as stream:
            header = []
            for _ in range(1000):
                line = stream.readline(65536)
                if not line: break
                header.append(line)
                if line.strip() == b'end_header' or sum(map(len,header))>=65536: break
            if not header or header[0].strip() != b'ply' or f'element vertex {len(ordered)}'.encode() not in [v.strip() for v in header] or header[-1].strip()!=b'end_header':
                raise ValueError("Native PLY header/count differs from the model")
        shutil.copyfile(native_ply,out/"points.ply")
    else:
        with (out/"points.ply").open("x",encoding="ascii") as stream:
            stream.write("ply\nformat ascii 1.0\ncomment COLMAP world coordinates; arbitrary scale\n"
                +f"element vertex {len(ordered)}\nproperty double x\nproperty double y\nproperty double z\n"
                +"property uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n")
            for p in ordered:
                stream.write(" ".join([*(format(v,".17g") for v in p["xyz"]),*(str(v) for v in p["rgb"])])+"\n")
    scene["source_ply"] = str(out/"points.ply")
    write_jsx(scene, out/"import_scene.jsx"); save(out/"scene.json", scene)
    save(out/"review_points.json",scene["points"]); overlays(scene, out)
    save(out/"report.json", {"frames": len(frames), "measured_frames": len(frames), "missing_frames": 0,
        "guide_points": len(scene["points"]), "total_points": len(points), "intrinsics": k,
        "display_cloud_points": len(cloud), "point_size_px": scene["point_size_px"],
        "cloud_renderer": args.cloud_renderer, "full_cloud_display": len(cloud)==len(ordered),
        "median_colmap_point_error_px": statistics.median(p["error"] for p in points.values()),
        "ae_import": "not_run", "visual_attachment": "not_reviewed"})
    print(json.dumps({"export": str(out), "jsx": str(out/"import_scene.jsx"), "review": str(out/"review.jpg"),
                      "instruction": "Review first, then AE > File > Scripts > Run Script File. No project is saved or closed."}))


def anchor(args):
    scene = load(args.scene)
    if scene.get("schema") != "aftereffect-colmap.scene.v1":
        raise ValueError("Unsupported scene")
    ids = [int(s) for s in args.points.split(",")]
    scene["world"] = plane_transform(scene["points"], ids, args.plane, scene["world"]["scale"], args.baseline_units)
    if args.model:
        path = args.model.expanduser().resolve()
        if not path.is_file() or path.suffix.lower() not in {".glb", ".gltf", ".obj", ".fbx"}:
            raise ValueError("Provide an existing GLB/GLTF/OBJ/FBX model")
        scene["model"] = str(path)
    scene["model_scale"] = args.model_scale
    ae_poses(scene)
    out = fresh(args.out)
    if scene.get("source_ply"):
        shutil.copyfile(scene["source_ply"],out/"points.ply");scene["source_ply"]=str(out/"points.ply")
    write_jsx(scene, out/"import_scene.jsx"); save(out/"scene.json", scene); overlays(scene, out)
    print(json.dumps({"export": str(out), "plane": args.plane, "point_ids": ids, "scale_is_metric": False}))


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest="action", required=True)
    q = commands.add_parser("doctor"); q.set_defaults(run=doctor)
    for n in ("colmap", "ffmpeg", "ffprobe"):
        q.add_argument("--"+n)
    q = commands.add_parser("prepare"); q.set_defaults(run=prepare)
    q.add_argument("--video", type=Path, required=True); q.add_argument("--out", type=Path, required=True)
    q.add_argument("--max-size", type=int, default=1600); q.add_argument("--max-frames", type=int, default=240)
    q = commands.add_parser("solve"); q.set_defaults(run=solve)
    q.add_argument("--input", type=Path, required=True); q.add_argument("--out", type=Path, required=True)
    q.add_argument("--colmap"); q.add_argument("--threads", type=int, choices=range(1, 17), default=4)
    q.add_argument("--overlap", type=int, choices=range(2, 31), default=8); q.add_argument("--model-id")
    q = commands.add_parser("export"); q.set_defaults(run=export_scene)
    q.add_argument("--solution", type=Path, required=True); q.add_argument("--out", type=Path, required=True)
    q.add_argument("--max-points", type=int, choices=range(3, 1001), default=80)
    q.add_argument("--cloud-renderer", choices=["model","shapes"], default="model", help="model: all RGB points in one AE24.1+ model; shapes: limited legacy precomp")
    q.add_argument("--cloud-limit", type=int, choices=range(3, 5001), help="explicit shapes-only display cap; default 2000")
    q.add_argument("--point-size", type=float, help="first-frame display pixels; default model3/shapes6")
    q.add_argument("--scale", type=float, default=500); q.add_argument("--model", type=Path)
    q.add_argument("--model-scale", type=float, default=100)
    q = commands.add_parser("anchor"); q.set_defaults(run=anchor)
    q.add_argument("--scene", type=Path, required=True); q.add_argument("--out", type=Path, required=True)
    q.add_argument("--points", required=True, help="origin,X direction,across plane: 3 COLMAP IDs")
    q.add_argument("--plane", choices=["floor", "wall"], required=True)
    q.add_argument("--baseline-units", type=float); q.add_argument("--model", type=Path)
    q.add_argument("--model-scale", type=float, default=100)
    return p


def main():
    args = parser().parse_args()
    try:
        result = args.run(args)
        return result or 0
    except (ValueError, OSError, KeyError, subprocess.SubprocessError, ImportError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
