---
name: aftereffect-colmap
description: Set up a clean macOS/Windows computer and teach COLMAP camera/full RGB cloud import into After Effects with Python-generated JSX, fixed-camera point enrichment, and detached jobs with one-shot wakeups. Use in this repository for a student's shot; no AE MCP.
---

# Aftereffect COLMAP

This is a repository-bound teaching skill. Find the repository root containing
`scripts/colmap_ae.py` and run from there. The whole repository must be available;
copying this SKILL.md alone does not install its tools.

## First interaction

1. Inspect the actual OS/shell and repository root. If Python or tools are
   missing, start with [START-HERE](../../../START-HERE.md); do not run a missing
   interpreter or assume this Mac's paths exist on the student's computer.
2. Read only the matching setup when needed:
   [macOS](../../../docs/setup-macos.md) or [Windows](../../../docs/setup-windows.md).
   The stdlib setup helper configures local paths/venv without Git or Pillow.
   Then run `python -B scripts/colmap_ae.py doctor` using the project venv.
   COLMAP/SIFT needs no learned weights. AE is a separately licensed application.
3. Locate the student's clip and a new working directory. Keep their original
   intact. A first clip should be a short, static textured environment, normal
   lens, fixed zoom, constant frame rate and square pixels. No automatic sample
   download, paid API, global environment edits or global skill installation.
4. Explain the next lesson in two or three sentences, then execute the authorized
   step. Do not ask the student to read every reference or install every option.

## Minimal lesson path

Use [workflow](../../../docs/workflow.md) for command details.

- `prepare`: extract every frame of a short CFR clip; record rational FPS and
  source timestamps/hash. Work starts at frame 0. No silent trimming/sampling.
- `solve`: CPU SIFT, sequential matching, mapping, image undistortion and TXT
  export. This runs in the background. Pick one connected reconstruction and
  report its coverage; never merge disconnected models or invent camera keys.
- If SIFT loses a short static shot or self-calibration diverges, read the
  [measured-track fallback](../../../docs/temporal.md). It needs a reviewed mask,
  explicit lens assumption and optional OpenCV, not model weights. Require its
  unused-track gate before export; registration count alone is insufficient.
- `export`: require all prepared frames to be registered. Default to the complete
  RGB cloud in one native GLB model layer (AE24.1+); no display sampling. Size
  markers in first-frame pixels without changing centers. Center the actual undistorted images
  together with their camera intrinsics. Produce `scene.json`, `review.jpg`,
  `report.json`, original-coordinate `points.ply`, `pointcloud.glb`, `check_rgb.jsx`
  and `import_scene.jsx`. Keep the generated assets together.
  Keep the main comp to camera/cloud/source/black background. Source starts off
  so the RGB cloud is visible; turn its eye on to compare against footage.
- On each new AE host, run `check_rgb.jsx` and compare all five reference/model
  color pairs before claiming native color fidelity. The importer measures model
  units and disables cloud lighting. Python/Windows CI is not native Windows AE
  proof. Read [full point clouds](../../../docs/point-cloud.md) for this stage.
- If more real points are requested, `enrich_cloud.py` fixes the accepted cameras
  and runs native COLMAP triangulation. Default fresh SIFT on accepted images;
  reuse only a copied DB with pixel-identical declared source images. Preserve
  camera/lens and existing heldout gates. Do not interpolate or invent points.
- Review the first/middle/last overlays and actual images. Explain plausible
  floor/wall/object depth using visible evidence, not just point coordinates.
  Sparse points do not identify semantics, dense surfaces or metric scale.
- `anchor`: after choosing three visible point IDs with the student, align a
  floor/wall and optionally place a supplied GLB/GLTF/OBJ/FBX. Verify model pivot,
  axes, size and orientation in AE. Native model import/version support varies.
- Run generated JSX via AE's File > Scripts > Run Script File. Python creates
  the JSX because AE does not run Python natively. No MCP, persistent panel,
  network bridge, project overwrite, render or automatic save is needed.
  If this Codex host has no app-control tool, hand the student the exact generated
  JSX path and this menu action; leave native verification pending until observed.

## Long calculations and cheap context

Read [background](../../../docs/background.md) before a long operation.

Use Python for large coordinates and measurements. Read the short `report.json`;
use `review_points.json` only for IDs. Do not paste full scene arrays into context.

- Launch once with `scripts/jobs.py start` into a new absolute job directory.
  It detaches a supervisor; don't use a foreground shell timeout as a job runner.
- Tell the student the job ID, estimated duration range and next check time.
  The estimate must cite a previous similar run or measured progress; if unknown,
  say unknown and choose a conservative first check. No universal ETA promise.
- Save the short continuation goal/paths, then create **one pending wakeup for
  this same chat**, using the native tool actually exposed by the agent.
- Confirm scheduling success/ID/time, record it using `jobs.py wakeup`, then end
  the turn. Continue useful independent work first if it remains. Waiting alone
  is not billed as COLMAP tokens; avoid repeated LLM calls and long log reads.
- On wake, remove or verify auto-removal of that exact reservation FIRST. Confirm
  through the scheduler, then `clear-wakeup` with the same ID. Local JSON cleanup
  is not proof that an external reservation was deleted.
- Read `jobs.py status` once. If still running, reschedule one later wakeup and
  end the turn; never relaunch COLMAP. Default at most 12 checks / 120 minutes,
  after which report and leave the job's actual timeout policy intact.
- If failed, stale, missing, invalid or timed out, keep logs/partials, remove the
  wakeup and explain the observed issue. Do not restart on your own.
  An already-authorized diagnosis/retry may continue with one evidence-based
  changed experiment; do not request the same authorization after each failure.
- If succeeded, verify expected files/coverage and continue the next authorized
  lesson. Remove the reservation on completion, failure or user cancellation.
- If no scheduling tool is available, say automatic wakeup is unavailable and
  give one resume command. Do not claim a task was scheduled, create a hidden
  service, or leave a rapid polling loop to simulate support.

## Laya and progressive development

Laya is optional for short ambiguous lesson-step suggestions; it cannot process
the video, reconstruct geometry or authorize actions. Deterministic operations
and status checks use Python directly. Read [Laya](../../../docs/laya.md) only
when requested or a reusable short decision actually helps. Missing Laya falls
back to the main agent. No default download or model call on every job check.

After each completed lesson, save a small `work/<shot>/next.md`: files, what was
verified, visible failures and one next step. Extend only what that shot requires.
Never claim native AE import or visual attachment passed from Python tests alone.
