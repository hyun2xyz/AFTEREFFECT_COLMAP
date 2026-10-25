"""Opt-in native temporal smoke; run through scripts/jobs.py, not unit discovery.

Reuse the 12-frame synthetic prepared folder produced by tests/smoke_colmap.py.
Its known static planes and 600px lens justify a full allow-mask in this fixture
only. This is not an automatic mask or a lens guess for student footage.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"scripts"))
from colmap_ae import fresh, load, save


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True, help="synthetic prepared directory from smoke_colmap.py")
    parser.add_argument("--out", type=Path, required=True, help="new smoke output directory")
    parser.add_argument("--colmap")
    args = parser.parse_args()
    manifest_path = args.prepared.expanduser().resolve()/"manifest.json"
    manifest = load(manifest_path)
    if ((manifest["width"], manifest["height"]) != (640, 480)
            or len(manifest["frames"]) != 12 or Path(manifest["source"]).name != "synthetic.mp4"):
        raise ValueError("Use only the generated smoke_colmap.py fixture (12 frames, 640x480, known focal 600px)")
    out = fresh(args.out)
    mask = out/"static-mask.json"
    save(mask, {"width": 640, "height": 480, "polygons": [[[0, 0], [639, 0], [639, 479], [0, 479]]]})
    command = [sys.executable, "-B", str(ROOT/"scripts/temporal_solve.py"),
               "--manifest", str(manifest_path), "--mask", str(mask), "--focal-px", "600",
               "--min-angle", "1.5", "--out", str(out/"solve"), "--threads", "2"]
    if args.colmap:
        command += ["--colmap", args.colmap]
    started = time.monotonic()
    subprocess.run(command, check=True)
    solution = load(out/"solve/solution.json")
    heldout = load(out/"solve/heldout-report.json")
    tracks = load(out/"solve/tracking-report.json")
    assert solution["method"] == "temporal_lk" and solution["ready_for_export"], solution
    assert solution["registered"] == solution["total_frames"] == tracks["frames"] == 12, solution
    assert not solution["missing_frames"] and solution["points"] >= 100, solution
    assert solution["heldout_passed"] and heldout["passed"] and heldout["finite"], heldout
    assert heldout["median_error_px"] <= 1.5 and heldout["p95_error_px"] <= 3, heldout
    assert heldout["positive_depth_fraction"] >= .95 and heldout["unused_tracks"] >= 20, heldout
    assert solution["lens_assumption"]["focal_px"] == 600 and not solution["weak_depth"], solution
    stages = load(out/"solve/stages.json")
    assert all(stage["exit_code"] == 0 for stage in stages), stages
    assert stages[0]["command"][1] == "database_creator" and stages[1]["command"][1] == "feature_importer", stages
    report = {"native_temporal_smoke": "passed", "frames": 12, "train_tracks": tracks["train_tracks"],
              "heldout_tracks": heldout["unused_tracks"], "median_error_px": heldout["median_error_px"],
              "p95_error_px": heldout["p95_error_px"], "positive_depth_fraction": heldout["positive_depth_fraction"],
              "elapsed_seconds": round(time.monotonic()-started, 2), "native_AE": "not_run"}
    save(out/"smoke-report.json", report)
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
