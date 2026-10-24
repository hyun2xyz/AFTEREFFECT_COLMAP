"""Integration tests use real short-lived commands, without external services."""

from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest


RUNNER = Path(__file__).resolve().parents[1] / "scripts" / "jobs.py"
TERMINAL = {"succeeded", "failed", "timeout"}


def process_alive(pid):
    """Check a test-owned PID without Windows os.kill(pid, 0), which is unsafe."""
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE only
        if not handle:
            return False
        try:
            return kernel.WaitForSingleObject(handle, 0) == 0x102  # WAIT_TIMEOUT
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    # A reparented zombie on a Linux CI runner cannot execute any more code.
    stat = Path(f"/proc/{pid}/stat")
    try:
        if stat.exists() and stat.read_text().rsplit(")", 1)[1].split()[0] == "Z":
            return False
    except FileNotFoundError:
        return False
    return True


class JobsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="classroom jobs ")
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def cli(self, *arguments, expected=None):
        result = subprocess.run(
            [sys.executable, str(RUNNER), *map(str, arguments)],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=10,
            shell=False,
        )
        if expected is not None:
            self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def start(self, job, code, *arguments, timeout_minutes="0.2"):
        result = self.cli(
            "start", "--job", job,
            "--estimate-minutes", "0.1",
            "--timeout-minutes", timeout_minutes,
            "--", sys.executable, "-c", code, *arguments,
            expected=0,
        )
        return json.loads(result.stdout)

    def status(self, job, *arguments):
        result = self.cli("status", "--job", job, *arguments)
        return json.loads(result.stdout), result.returncode

    def wait_terminal(self, job, timeout=8):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            record, returncode = self.status(job)
            if record["state"] in TERMINAL:
                return record, returncode
            self.assertIn(record["state"], {"starting", "running"}, record)
            time.sleep(0.03)
        self.fail(f"job did not finish: {self.status(job)}")

    def test_success_logs_compact_status_and_bounded_tail(self):
        job = self.root / "success"
        started = self.start(
            job,
            "import sys; print('hello'); print('warning', file=sys.stderr); print('x' * 100000)",
        )
        status, returncode = self.wait_terminal(job)
        self.assertEqual((status["state"], status["exit_code"], returncode), ("succeeded", 0, 0))
        self.assertEqual(started["job_id"], status["job_id"])
        self.assertIsInstance(status["pid"], int)
        self.assertIsInstance(status["worker_pid"], int)
        self.assertTrue(status["heartbeat_recent"])
        self.assertIsNotNone(status["started_at"])
        self.assertIsNotNone(status["estimated_finish_at"])
        self.assertGreaterEqual(status["elapsed_seconds"], 0)
        self.assertNotIn("log_tail", status)
        self.assertLess(len(json.dumps(status)), 4000)
        self.assertEqual(Path(status["logs"]["stderr"]).read_text(), "warning\n")
        tail, _ = self.status(job, "--tail", 1)
        self.assertLessEqual(len(tail["log_tail"]["stdout"].encode()), 32 * 1024)
        self.assertEqual(tail["log_tail"]["stderr"], "warning")
        self.cli("status", "--job", job, "--tail", 201, expected=2)

    def test_nonzero_exit_is_failed(self):
        job = self.root / "failure"
        self.start(job, "import sys; print('before failure'); sys.exit(7)")
        status, returncode = self.wait_terminal(job)
        self.assertEqual((status["state"], status["exit_code"], returncode), ("failed", 7, 1))
        self.assertIn("before failure", Path(status["logs"]["stdout"]).read_text())

    def test_detached_command_survives_foreground_cli_exit(self):
        job = self.root / "detached"
        gate = self.root / "launcher returned.gate"
        marker = self.root / "after launcher exit.txt"
        self.start(
            job,
            "import pathlib,sys,time\n"
            "gate = pathlib.Path(sys.argv[1])\n"
            "deadline = time.monotonic() + 8\n"
            "while not gate.exists():\n"
            "    if time.monotonic() >= deadline:\n"
            "        raise TimeoutError('foreground CLI never released gate')\n"
            "    time.sleep(0.02)\n"
            "pathlib.Path(sys.argv[2]).write_text('alive')\n",
            gate, marker,
        )
        self.assertFalse(marker.exists())
        record, _ = self.status(job)
        self.assertIn(record["state"], {"starting", "running"})
        # This point is reached only after the foreground CLI has exited.
        gate.write_text("released")
        status, _ = self.wait_terminal(job)
        self.assertEqual(status["state"], "succeeded")
        self.assertEqual(marker.read_text(), "alive")

    def test_duplicate_start_and_completed_directory_reuse_are_rejected(self):
        job = self.root / "one use"
        self.start(job, "import time; time.sleep(0.5)")
        manifest = (job / "job.json").read_bytes()
        for attempt in range(2):
            rejected = self.cli(
                "start", "--job", job, "--estimate-minutes", "1", "--timeout-minutes", "1",
                "--", sys.executable, "-c", "raise Exception('must never run')", expected=2,
            )
            self.assertIn("already exists", rejected.stderr)
            self.assertEqual((job / "job.json").read_bytes(), manifest)
            if attempt == 0:
                status, _ = self.wait_terminal(job)
                self.assertEqual(status["state"], "succeeded")
        saved = (job / "status.json").read_bytes()
        self.cli("_worker", "--job", job, expected=1)
        self.assertEqual((job / "status.json").read_bytes(), saved)

    def test_simultaneous_starts_have_exactly_one_winner(self):
        job = self.root / "race"
        command = [
            sys.executable, str(RUNNER), "start", "--job", str(job),
            "--estimate-minutes", "1", "--timeout-minutes", "1", "--",
            sys.executable, "-c", "import time; time.sleep(0.25)",
        ]
        launchers = [
            subprocess.Popen(
                command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, encoding="utf-8", shell=False,
            )
            for _ in range(2)
        ]
        outputs = [launcher.communicate(timeout=10) for launcher in launchers]
        self.assertEqual(sorted(launcher.returncode for launcher in launchers), [0, 2], outputs)
        status, _ = self.wait_terminal(job)
        self.assertEqual(status["state"], "succeeded")

    def test_timeout_terminates_owned_child_and_preserves_timeout(self):
        unrelated = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(10)"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            shell=False,
        )
        try:
            job = self.root / "timeout"
            marker = self.root / "must not finish.txt"
            self.start(
                job,
                "import pathlib,sys,time; time.sleep(5); pathlib.Path(sys.argv[1]).write_text('finished')",
                marker,
                timeout_minutes="0.002",
            )
            status, returncode = self.wait_terminal(job)
            self.assertEqual((status["state"], returncode), ("timeout", 1))
            self.assertIsNotNone(status["exit_code"])
            self.assertFalse(marker.exists())
            self.assertIsNone(unrelated.poll(), "runner killed an unrelated process")
            if os.name == "posix":
                with self.assertRaises(ProcessLookupError):
                    os.kill(status["pid"], 0)
            again, _ = self.status(job)
            self.assertEqual(again["state"], "timeout")
        finally:
            unrelated.terminate()
            unrelated.wait(timeout=5)

    @unittest.skipUnless(os.name == "posix", "requires a POSIX SIGTERM handler")
    def test_timeout_stays_timeout_when_child_handles_term_with_exit_zero(self):
        job = self.root / "timeout with graceful exit"
        self.start(
            job,
            "import signal,sys,time; signal.signal(signal.SIGTERM, lambda *_: sys.exit(0)); time.sleep(5)",
            timeout_minutes="0.003",
        )
        status, returncode = self.wait_terminal(job)
        self.assertEqual((status["state"], status["exit_code"], returncode), ("timeout", 0, 1))

    def test_timeout_cleans_grandchild_and_preserves_unrelated_process(self):
        unrelated = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(15)"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            shell=False,
        )
        pid_file = self.root / "grandchild.pid"
        grandchild_pid = None
        try:
            job = self.root / "timeout tree"
            grandchild_code = (
                "import os,pathlib,signal,sys,time; "
                "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                "pathlib.Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(15)"
            )
            self.start(
                job,
                "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',sys.argv[1],sys.argv[2]], shell=False); time.sleep(15)",
                grandchild_code, pid_file,
                timeout_minutes="0.04",
            )
            status, returncode = self.wait_terminal(job)
            self.assertEqual((status["state"], returncode), ("timeout", 1))
            self.assertTrue(pid_file.exists(), "grandchild did not start before timeout")
            grandchild_pid = int(pid_file.read_text())
            deadline = time.monotonic() + 3
            while process_alive(grandchild_pid) and time.monotonic() < deadline:
                time.sleep(0.03)
            self.assertFalse(process_alive(grandchild_pid), "owned grandchild survived timeout")
            self.assertFalse(process_alive(status["pid"]), "owned child survived timeout")
            self.assertIsNone(unrelated.poll(), "unrelated process was terminated")
            self.assertNotIn("inspect descendants", status.get("error", ""))
        finally:
            if grandchild_pid is not None and process_alive(grandchild_pid):
                if os.name == "nt":
                    subprocess.run(
                        [str(Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "taskkill.exe"),
                         "/PID", str(grandchild_pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5, shell=False,
                    )
                else:
                    os.kill(grandchild_pid, signal.SIGKILL)
            unrelated.terminate()
            unrelated.wait(timeout=5)

    def test_unicode_spaces_and_shell_metacharacters_are_literal(self):
        job = self.root / "한글 작업 폴더"
        literal = "한글 공백 ; $(echo forbidden) & *"
        self.start(job, "import sys; sys.stdout.buffer.write((sys.argv[1]+'\\n').encode('utf-8'))", literal)
        status, _ = self.wait_terminal(job)
        self.assertEqual(status["state"], "succeeded")
        self.assertEqual(Path(status["logs"]["stdout"]).read_text(encoding="utf-8"), literal + "\n")
        self.assertEqual(status["command"][-1], literal)

    def test_wakeup_records_only_and_clears_only_matching_id(self):
        job = self.root / "wakeup"
        self.start(job, "pass")
        self.wait_terminal(job)
        result = self.cli(
            "wakeup", "--job", job, "--automation-id", "automation-a",
            "--at", "2030-01-02T10:00:00+09:00", expected=0,
        )
        record = json.loads(result.stdout)
        self.assertTrue(record["record_only"])
        self.assertFalse(record["external_automation_changed"])
        self.assertEqual(record["at"], "2030-01-02T01:00:00.000Z")
        status, _ = self.status(job)
        self.assertEqual(status["wakeup"], {
            "automation_id": "automation-a", "nextcheck_at": "2030-01-02T01:00:00.000Z",
        })
        saved = (job / "wakeup.json").read_bytes()
        self.cli(
            "wakeup", "--job", job, "--automation-id", "automation-b",
            "--at", "2030-01-02T12:00:00Z", expected=2,
        )
        wrong = self.cli(
            "clear-wakeup", "--job", job, "--automation-id", "automation-b", expected=1,
        )
        self.assertFalse(json.loads(wrong.stdout)["cleared"])
        self.assertEqual((job / "wakeup.json").read_bytes(), saved)
        correct = self.cli(
            "clear-wakeup", "--job", job, "--automation-id", "automation-a", expected=0,
        )
        self.assertTrue(json.loads(correct.stdout)["cleared"])
        self.assertFalse(json.loads(correct.stdout)["external_automation_changed"])
        self.assertFalse((job / "wakeup.json").exists())
        status, _ = self.status(job)
        self.assertNotIn("wakeup", status)
        missing = self.cli(
            "clear-wakeup", "--job", job, "--automation-id", "automation-a", expected=0,
        )
        self.assertFalse(json.loads(missing.stdout)["cleared"])

    def test_missing_stale_and_corrupt_status_never_report_success_or_restart(self):
        missing, returncode = self.status(self.root / "missing")
        self.assertEqual((missing["state"], returncode), ("missing", 1))
        job = self.root / "stale"
        marker = self.root / "run count.txt"
        self.start(
            job,
            "import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_text(p.read_text()+'x' if p.exists() else 'x')",
            marker,
        )
        self.wait_terminal(job)
        record = json.loads((job / "status.json").read_text())
        record.update(state="running", finished_at=None, exit_code=None, heartbeat_at="2000-01-01T00:00:00Z")
        (job / "status.json").write_text(json.dumps(record))
        stale, returncode = self.status(job)
        self.assertEqual((stale["state"], stale["heartbeat_recent"], returncode), ("stale", False, 1))
        self.cli("_worker", "--job", job, expected=1)
        self.assertEqual(marker.read_text(), "x")
        (job / "status.json").write_text("{")
        corrupt, returncode = self.status(job)
        self.assertEqual((corrupt["state"], returncode), ("invalid", 1))
        record.update(heartbeat_at=None)
        (job / "status.json").write_text(json.dumps(record))
        corrupt, returncode = self.status(job)
        self.assertEqual((corrupt["state"], returncode), ("invalid", 1))


if __name__ == "__main__":
    unittest.main()
