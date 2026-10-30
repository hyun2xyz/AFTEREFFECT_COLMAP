"""Bootstrap/config invariants; no software download or package installation."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"scripts"))
import setup_environment as setup


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="setup class 한글 ")
        self.root = Path(self.temp.name)
        (self.root/"requirements.txt").write_text("Pillow>=13,<14\n", encoding="utf-8")
        (self.root/"requirements-tracking.txt").write_text("numpy>=2,<3\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def tool(self, stem):
        path = self.root/"tools with spaces"/(stem+".exe")
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(b"fixture; never executed")
        path.chmod(0o700)
        return path

    def tools(self):
        return {name: str(self.tool(name)) for name in setup.TOOLS}

    def state(self, *, ready=False):
        return {"exists": True, "version": [3, 13, 7], "supported_python": True, "ready": ready,
                "prefix": str(self.root/".venv"), "base_prefix": str(self.root/"base-python"),
                "packages": {"Pillow": "13.0.0" if ready else None, "numpy": None, "opencv-python-headless": None}}

    def make_venv(self):
        path = setup.venv_python(self.root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture; never executed")
        (self.root/".venv/pyvenv.cfg").write_text("home = fixture\n", encoding="utf-8")

    def test_helper_loads_without_site_packages(self):
        result = subprocess.run([sys.executable, "-S", "-B", str(ROOT/"scripts/setup_environment.py"), "--help"],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--configure", result.stdout)

    def test_check_is_read_only_and_tolerates_missing_prerequisites(self):
        before = sorted(str(path.relative_to(self.root)) for path in self.root.rglob("*"))
        with patch.object(setup.shutil, "which", return_value=None), patch.object(setup, "common_candidates", return_value=[]), patch.dict(os.environ, {}, clear=True):
            result = setup.check(self.root)
        self.assertFalse(result["ready_for_doctor"])
        self.assertTrue(all(tool["path"] is None for tool in result["tools"].values()))
        self.assertEqual(result["after_effects"]["native_import"], "not_verified")
        self.assertEqual(before, sorted(str(path.relative_to(self.root)) for path in self.root.rglob("*")))

    def test_configure_source_zip_writes_absolute_paths_without_changing_path(self):
        tools = self.tools()
        relative = {name: str(Path(value).relative_to(self.root)) for name, value in tools.items()}
        with patch.object(setup, "probe_tool", return_value={"version": "fixture"}), patch.dict(os.environ, {}, clear=True):
            result = setup.configure(self.root, relative)
            self.assertNotIn("PATH", os.environ)
        self.assertTrue(result["configured"])
        self.assertFalse((self.root/".git").exists())
        self.assertEqual(json.loads((self.root/"tools.local.json").read_text(encoding="utf-8")), tools)
        self.assertFalse(list(self.root.glob(".tools-local-*")))

    def test_tool_precedence_is_argument_environment_config_path(self):
        files = {source: str(self.tool(source)) for source in ("argument", "environment", "config", "path")}
        (self.root/"tools.local.json").write_text(json.dumps({"colmap": files["config"]}), encoding="utf-8")
        with patch.object(setup, "probe_tool", return_value={"version": "fixture"}), patch.object(setup.shutil, "which", return_value=files["path"]), patch.dict(os.environ, {"COLMAP_BINARY": files["environment"]}, clear=True):
            self.assertEqual(setup.find_tools(self.root, {"colmap": files["argument"]})["colmap"]["path"], files["argument"])
            self.assertEqual(setup.find_tools(self.root)["colmap"]["path"], files["environment"])
            del os.environ["COLMAP_BINARY"]
            self.assertEqual(setup.find_tools(self.root)["colmap"]["path"], files["config"])
            (self.root/"tools.local.json").unlink()
            self.assertEqual(setup.find_tools(self.root)["colmap"]["path"], files["path"])

    def test_bad_explicit_path_does_not_fall_back_or_overwrite_config(self):
        tools = self.tools()
        config = self.root/"tools.local.json"
        original = json.dumps(tools)
        config.write_text(original, encoding="utf-8")
        with patch.object(setup, "probe_tool", side_effect=lambda name, path: {"version": "ok"} if path.is_file() else {"error": "missing"}):
            result = setup.configure(self.root, {"colmap": "missing.exe"})
        self.assertFalse(result["configured"])
        self.assertEqual(result["tools"]["colmap"]["source"], "argument")
        self.assertEqual(config.read_text(encoding="utf-8"), original)

    def test_rejects_batch_wrappers_and_reports_version_failure(self):
        wrapper = self.root/"COLMAP.bat"
        wrapper.write_text("fixture", encoding="utf-8")
        with patch.object(setup.subprocess, "run") as run:
            self.assertIn("wrapper", setup.probe_tool("colmap", wrapper)["error"])
            run.assert_not_called()
        result = subprocess.CompletedProcess([], 1, "", "required runtime DLL missing")
        with patch.object(setup.subprocess, "run", return_value=result):
            report = setup.probe_tool("colmap", self.tool("colmap"))
        self.assertIn("DLL missing", report["output_tail"])
        self.assertFalse(report["output_truncated"])

    def test_windows_common_locations_include_extracted_zip_folder(self):
        local = self.root/"local app data"
        path = local/"AFTEREFFECT_COLMAP/tools/FFmpeg/ffmpeg-version/bin/ffmpeg.exe"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"fixture")
        candidates = setup.common_candidates("ffmpeg", self.root, {"LOCALAPPDATA": str(local)}, "Windows")
        self.assertIn(path, candidates)

    def test_install_is_explicit_project_only_and_tracking_is_opt_in(self):
        with patch.object(setup.venv, "EnvBuilder") as builder, patch.object(setup, "venv_state", side_effect=lambda root: self.state()), patch.object(setup.subprocess, "run") as run, patch.dict(os.environ, {"PATH": "unchanged", "PIP_TARGET": "outside-project"}, clear=True):
            builder.return_value.create.side_effect = lambda directory: self.make_venv()
            result = setup.install(self.root)
            self.assertTrue(result["installed"])
            builder.assert_called_once_with(with_pip=True)
            command = run.call_args.args[0]
            self.assertEqual(command[0], str(setup.venv_python(self.root)))
            self.assertIn("--require-virtualenv", command)
            self.assertIn("--no-user", command)
            self.assertIn(str(self.root/"requirements.txt"), command)
            self.assertNotIn(str(self.root/"requirements-tracking.txt"), command)
            self.assertNotIn("PIP_TARGET", run.call_args.kwargs["env"])
            self.assertEqual(run.call_args.kwargs["env"]["PIP_CONFIG_FILE"], os.devnull)
            self.assertEqual(os.environ["PATH"], "unchanged")
            result = setup.install(self.root, tracking=True)
            self.assertTrue(result["tracking_requested"])
            self.assertIn(str(self.root/"requirements-tracking.txt"), run.call_args.args[0])
            builder.return_value.create.assert_called_once()

    def test_existing_nonvenv_python_cannot_receive_packages(self):
        self.make_venv()
        data = self.state()
        data["prefix"] = data["base_prefix"] = str(self.root/"outside-project")
        result = subprocess.CompletedProcess([], 0, json.dumps(data), "")
        with patch.object(setup.subprocess, "run", return_value=result) as run:
            with self.assertRaisesRegex(ValueError, "does not belong"):
                setup.install(self.root)
            self.assertEqual(run.call_count, 1)  # interpreter probe only; pip never called

    def test_optional_tracking_never_runs_with_check(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            setup.main(["--check", "--tracking"], root=self.root)
        self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
