---
name: aftereffect-colmap
description: Teach a minimal macOS/Windows COLMAP-to-After-Effects workflow with Python-generated JSX, sparse camera/RGB guide points, floor or wall alignment, and detached jobs with one-shot agent wakeups. Use in this repository for a student's shot; no AE MCP or full automatic VFX pipeline.
---

# Aftereffect COLMAP

This is a repository-bound teaching skill. Find the repository root containing
`scripts/colmap_ae.py` and run from there. The whole repository must be available;
copying this SKILL.md alone does not install its tools.

## First interaction

1. Inspect the actual OS, Python, `colmap`, FFmpeg and AE availability. Run
   `python -B scripts/colmap_ae.py doctor` with the project venv interpreter.
2. If setup is missing, read only the matching reference:
   [macOS](../../../docs/setup-macos.md) or [Windows](../../../docs/setup-windows.md).
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
- `export`: require all prepared frames to be registered. Preserve RGB on a
  small set of native AE guide shapes. Center the actual undistorted images
  together with their camera intrinsics. Produce `scene.json`, `review.jpg`,
  `report.json` and a visible, reviewable `import_scene.jsx`.
- Review the first/middle/last overlays and actual images. Explain plausible
  floor/wall/object depth using visible evidence, not just point coordinates.
  Sparse points do not identify semantics, dense surfaces or metric scale.
- `anchor`: after choosing three visible point IDs with the student, align a
  floor/wall and optionally place a supplied GLB/GLTF/OBJ/FBX. Verify model pivot,
  axes, size and orientation in AE. Native model import/version support varies.
- Run generated JSX via AE's File > Scripts > Run Script File. Python creates
  the JSX because AE does not run Python natively. No MCP, persistent panel,
  network bridge, project overwrite, render or automatic save is needed.

## Long calculations and cheap context

Read [background](../../../docs/background.md) before a long operation.

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
