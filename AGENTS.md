# AFTEREFFECT_COLMAP — classroom starter

Read `.agents/skills/aftereffect-colmap/SKILL.md` for this repository's workflow.
For a computer without prerequisites, start with `START-HERE.md` and only the
current OS setup. Do not attempt Python commands before locating Python.
Load only the current OS setup and the current lesson reference. This repository
is the source of its project skill; do not install or change global agent rules.

- Teach one next step at a time. Inspect the student's actual footage, files and
  installed tools before choosing commands. Preserve student edits and originals.
- Use Python/CLI and generated JSX, never an AE MCP server or a new bridge.
- Long computation runs through `scripts/jobs.py`; use the agent's native
  one-shot scheduler when available and end the turn instead of repeatedly polling.
- The student works in their own fork: `origin` is the fork, `upstream` is
  `hyun2xyz/AFTEREFFECT_COLMAP`. Follow `docs/fork-and-update.md`. Update with
  `git fetch upstream` + `git merge upstream/main`; never reset, force-push or
  discard the student's commits. Before a commit, check `git status` and stop if
  footage, AEP, generated media, weights or `tools.local.json` would be included.
- Codex asks for approval before network commands (git, gh, pip, brew, winget)
  and writes outside this folder. Request it and explain why; never change
  sandbox or security settings to avoid it.
- Keep footage, models, jobs, reports and AEP files in ignored `work/` or a
  student-selected work directory. Never commit their private data or weights.
- Missing frames, failed jobs and unknown app results are not successful tracks.
- Full RGB export keeps every native point in one GLB model layer. Run the
  first-host RGB/unit check; use capped shapes only as an explicit fallback.
- Summarize large scene/models with Python; read report.json and only the small
  review_points.json when needed. Do not load all coordinates or long logs into context.
- Add a feature only for a concrete next lesson/request. Keep core dependencies
  small; do not copy the full vfx-workbench, its archives or old scheduled work.
