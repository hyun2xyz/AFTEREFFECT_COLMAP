"""Project-only setup helper; runs with Python's standard library, before Pillow.

This never installs OS applications, changes system PATH, launches AE, or creates
a scheduler. --install is the only action that creates a venv/installs packages.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import venv

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ("colmap", "ffmpeg", "ffprobe")
SUPPORTED_PYTHON = {(3, 12), (3, 13)}


def absolute(value, root):
    path = Path(value).expanduser()
    # Preserve stable Homebrew bin symlinks instead of pinning a Cellar version.
    return Path(os.path.abspath(path if path.is_absolute() else root/path))


def settings(root):
    path = root/"tools.local.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("tools.local.json is not valid UTF-8 JSON; preserve and fix it before configuring") from exc
    if (not isinstance(data, dict) or set(data)-set(TOOLS)
            or any(not isinstance(value, str) or not value.strip() for value in data.values())):
        raise ValueError("tools.local.json must contain only colmap/ffmpeg/ffprobe path strings")
    return data


def common_candidates(name, root, environ=None, system=None):
    environ = os.environ if environ is None else environ
    system = platform.system() if system is None else system
    if system == "Darwin":
        return [Path(prefix)/"bin"/name for prefix in ("/opt/homebrew", "/usr/local")]
    if system != "Windows":
        return []
    filename = name+".exe"
    package = "COLMAP" if name == "colmap" else "FFmpeg"
    bases = [Path("C:/Tools")/package]
    if environ.get("LOCALAPPDATA"):
        bases.insert(0, Path(environ["LOCALAPPDATA"])/"AFTEREFFECT_COLMAP"/"tools"/package)
    if environ.get("ProgramFiles"):
        bases.append(Path(environ["ProgramFiles"])/package)
    candidates = []
    for base in bases:
        candidates.extend([base/"bin"/filename, base/filename])
        candidates.extend(sorted(base.glob("*/"+filename)))
        candidates.extend(sorted(base.glob("*/bin/"+filename)))
    return candidates


def tool_env(path):
    result = os.environ.copy()
    result["PYTHONUTF8"] = "1"
    if os.name == "nt":
        result["PATH"] = str(path.parent)+os.pathsep+result.get("PATH", "")
        for directory in (path.parent.parent/"plugins", path.parent/"plugins"):
            if directory.is_dir():
                result["QT_PLUGIN_PATH"] = str(directory)
                break
    return result


def probe_tool(name, path):
    if not path.is_file() or path.suffix.lower() in {".bat", ".cmd"}:
        return {"error": "Use an existing actual executable, not a .bat/.cmd wrapper"}
    if os.name != "nt" and not os.access(path, os.X_OK):
        return {"error": "File is not executable"}
    try:
        result = subprocess.run([str(path), "-h" if name == "colmap" else "-version"],
                                capture_output=True, encoding="utf-8", errors="replace",
                                timeout=15, env=tool_env(path))
    except (OSError, subprocess.SubprocessError) as exc:
        return {"error": str(exc)}
    output = result.stdout+result.stderr
    if result.returncode:
        return {"error": f"Version check exited {result.returncode}", "output_tail": output[-2000:],
                "output_truncated": len(output) > 2000}
    version = next((line.strip() for line in output.splitlines() if name.lower() in line.lower()), None)
    return {"version": version} if version else {"error": "No recognizable version output"}


def find_tools(root, explicit=None):
    explicit, configured = explicit or {}, settings(root)
    result = {}
    for name in TOOLS:
        candidates = [(explicit.get(name), "argument"), (os.environ.get(name.upper()+"_BINARY"), "environment"),
                      (configured.get(name), "tools.local.json"), (shutil.which(name), "PATH")]
        chosen = next(((value, source) for value, source in candidates if value), None)
        if chosen is None:
            common = common_candidates(name, root)
            if name == "ffprobe" and result.get("ffmpeg", {}).get("path"):
                common.insert(0, Path(result["ffmpeg"]["path"]).with_name("ffprobe.exe" if os.name == "nt" else "ffprobe"))
            chosen = next(((str(path), "common location") for path in common if path.is_file()), None)
        if chosen is None:
            result[name] = {"path": None, "error": "Not found; read the matching docs/setup-*.md"}
            continue
        value, source = chosen
        path = absolute(value, root)
        result[name] = {"path": str(path), "source": source, **probe_tool(name, path)}
    return result


def venv_python(root):
    return root/".venv"/("Scripts/python.exe" if os.name == "nt" else "bin/python")


def venv_state(root):
    directory, python = root/".venv", venv_python(root)
    state = {"path": str(directory), "python": str(python), "exists": directory.exists(), "ready": False}
    if directory.is_symlink():
        return {**state, "error": "A symlinked .venv is not a project-owned install target"}
    if not (directory/"pyvenv.cfg").is_file() or not python.is_file():
        return {**state, "error": "Project .venv is missing or incomplete"}
    code = """import importlib.metadata as m,json,sys
p={}
for name in ('Pillow','numpy','opencv-python-headless'):
 try:p[name]=m.version(name)
 except m.PackageNotFoundError:p[name]=None
print(json.dumps(dict(version=list(sys.version_info[:3]),prefix=sys.prefix,base_prefix=sys.base_prefix,packages=p)))
"""
    try:
        result = subprocess.run([str(python), "-I", "-B", "-c", code], check=True,
                                capture_output=True, encoding="utf-8", errors="replace", timeout=15)
        data = json.loads(result.stdout)
        if Path(data["prefix"]).resolve() != directory.resolve() or data["prefix"] == data["base_prefix"]:
            raise ValueError("Interpreter does not belong to this project's .venv")
        supported = tuple(data["version"][:2]) in SUPPORTED_PYTHON
        pillow = data["packages"]["Pillow"]
        pillow_ready = bool(pillow and 11 <= int(pillow.split(".")[0]) < 13)
        return {**state, **data, "supported_python": supported, "ready": supported and pillow_ready}
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as exc:
        return {**state, "error": str(exc)}


def ae_candidates():
    paths = []
    if platform.system() == "Darwin":
        for base in (Path("/Applications"), Path.home()/"Applications"):
            paths.extend(base.glob("Adobe After Effects*/Adobe After Effects*.app"))
            paths.extend(base.glob("Adobe After Effects*.app"))
    elif platform.system() == "Windows" and os.environ.get("ProgramFiles"):
        paths.extend((Path(os.environ["ProgramFiles"])/"Adobe").glob("Adobe After Effects*/Support Files/AfterFX.exe"))
    return sorted({str(path) for path in paths if path.exists() and "Render Engine" not in path.name})


def check(root, explicit=None):
    tools, environment = find_tools(root, explicit), venv_state(root)
    return {"schema": "aftereffect-colmap.setup.v1", "root": str(root), "os": platform.platform(),
            "python": {"path": sys.executable, "version": platform.python_version(),
                       "supported": sys.version_info[:2] in SUPPORTED_PYTHON},
            "venv": environment, "tools": tools,
            "after_effects": {"common_location_candidates": ae_candidates(), "native_import": "not_verified",
                              "note": "Detection does not verify license, version support or an AE composition"},
            "ready_for_doctor": environment["ready"] and all("error" not in tool for tool in tools.values())}


def configure(root, explicit=None):
    tools = find_tools(root, explicit)
    missing = [name for name, tool in tools.items() if "error" in tool]
    if missing:
        return {"configured": False, "tools": tools, "error": "No file written; fix: "+", ".join(missing)}
    path, temporary = root/"tools.local.json", None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=root,
                                         prefix=".tools-local-", suffix=".json", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump({name: tools[name]["path"] for name in TOOLS}, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {"configured": True, "config": str(path), "tools": tools, "system_path_changed": False}


def install(root, tracking=False):
    requirements = [root/"requirements.txt"]
    if tracking:
        requirements.append(root/"requirements-tracking.txt")
    if any(not path.is_file() for path in requirements):
        raise ValueError("Requirements file missing; use the complete starter folder")
    directory = root/".venv"
    if directory.is_symlink():
        raise ValueError("Refusing to install into a symlinked .venv")
    if not directory.exists():
        if sys.version_info[:2] not in SUPPORTED_PYTHON:
            raise ValueError("Create the project environment with Python 3.13 (or 3.12)")
        venv.EnvBuilder(with_pip=True).create(directory)
    state = venv_state(root)
    if "error" in state or not state.get("supported_python"):
        raise ValueError("Preserve the existing .venv and inspect it before installing: "+state.get("error", "unsupported Python version"))
    command = [str(venv_python(root)), "-I", "-m", "pip", "--isolated", "--require-virtualenv", "install", "--no-user"]
    for path in requirements:
        command += ["-r", str(path)]
    env = {name: value for name, value in os.environ.items() if not name.startswith("PIP_")}
    env["PIP_CONFIG_FILE"] = os.devnull
    subprocess.run(command, check=True, env=env)
    return {"installed": True, "venv_python": str(venv_python(root)), "tracking_requested": tracking,
            "requirements": [path.name for path in requirements], "native_ae": "not_verified"}


def main(argv=None, root=ROOT):
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true", help="read/probe only; no setup changes")
    action.add_argument("--configure", action="store_true", help="write verified local executable paths to tools.local.json")
    action.add_argument("--install", action="store_true", help="create/reuse project .venv and install requirements.txt")
    parser.add_argument("--tracking", action="store_true", help="with --install only: also install optional tracking requirements")
    for name in TOOLS:
        parser.add_argument("--"+name, help="actual executable path; relative paths start at the repository root")
    args = parser.parse_args(argv)
    if args.tracking and not args.install:
        parser.error("--tracking requires --install")
    explicit = {name: getattr(args, name) for name in TOOLS if getattr(args, name)}
    if args.install and explicit:
        parser.error("Tool path options belong to --check or --configure")
    try:
        root = Path(root).expanduser().resolve()
        result = install(root, args.tracking) if args.install else configure(root, explicit) if args.configure else check(root, explicit)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("installed") or result.get("configured") or result.get("ready_for_doctor") else 1
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
