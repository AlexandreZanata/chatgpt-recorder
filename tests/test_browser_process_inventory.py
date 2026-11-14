"""Browser isolation and live-display regression checks without real accounts."""
import os
from pathlib import Path
import shlex
import socket
import tempfile
import unittest
from unittest import mock

from tools.ytbot import config, runtime


class BrowserRuntimeContracts(unittest.TestCase):
    def test_profile_matching_handles_both_argv_layouts_without_matching_other_profiles(self):
        for flattened in (False, True):
            with self.subTest(flattened=flattened), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                proc = root / "proc"
                proc.mkdir()
                chrome = root / "chrome"
                chrome.touch()
                other = root / "python"
                other.touch()
                profile = root / "bot profile"
                vectors = {
                    "101": (chrome, [str(chrome), f"--user-data-dir={profile}"]),
                    "102": (chrome, [str(chrome), f"--user-data-dir={profile}-other"]),
                    "103": (chrome, [str(chrome), f"--user-data-dir={profile}", "--type=renderer"]),
                    "104": (other, [str(other), f"--user-data-dir={profile}"]),
                }
                for pid, (executable, args) in vectors.items():
                    entry = proc / pid
                    entry.mkdir()
                    entry.joinpath("exe").symlink_to(executable)
                    data = os.fsencode(shlex.join(args)) if flattened else b"\0".join(map(os.fsencode, args))
                    entry.joinpath("cmdline").write_bytes(data + b"\0")
                with mock.patch.object(runtime, "Path", side_effect=lambda p: proc if p == "/proc" else Path(p)), mock.patch.object(config, "PROFILE", profile):
                    self.assertEqual(runtime._chrome_pids(), [101])

    def test_malformed_flattened_command_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entry = root / "101"
            entry.mkdir()
            entry.joinpath("cmdline").write_bytes(b"chrome '--user-data-dir=unterminated\0")
            with mock.patch.object(runtime, "Path", return_value=root):
                self.assertEqual(list(runtime._browser_processes()), [])

    def test_failed_shutdown_preserves_profile_lock_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            singleton = root / "SingletonLock"
            singleton.write_text("existing browser lock")
            with mock.patch.object(config, "PROFILE", root), mock.patch.object(runtime, "_chrome_pids", return_value=[101]), mock.patch.object(runtime.os, "kill"), mock.patch.object(runtime.time, "sleep"):
                with self.assertRaisesRegex(RuntimeError, "locks were preserved"):
                    runtime.stop_hidden_chrome()
            self.assertEqual(singleton.read_text(), "existing browser lock")

    def test_display_readiness_distinguishes_missing_live_and_stale_sockets(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "display"
            self.assertFalse(runtime._display_running(path))
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
                server.bind(str(path))
                server.listen()
                self.assertTrue(runtime._display_running(path))
            self.assertTrue(path.exists())
            self.assertFalse(runtime._display_running(path))
