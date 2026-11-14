"""Repeatable browser onboarding contracts; no downloads or real accounts."""
from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

from tools.ytbot import account_commands, browser_install, config, onboarding, runtime
from tools.ytbot.accounts_store import AccountStore, private_directory, write_private


class BrowserInstallation(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        patcher = patch.object(config, "ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        mode = patch.object(config, "BROWSER_MODE", "system")
        mode.start()
        self.addCleanup(mode.stop)
        private_directory(browser_install.root())

    def register_browser(self, version="150.0.0.1"):
        binary = browser_install.root() / version / "chrome-linux64/chrome"
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b"fixture")
        binary.chmod(0o700)
        write_private(browser_install.root() / "browser.json", {"schema": 1, "version": version})
        return binary

    def test_extension_loading_and_profile_downgrade_guard(self):
        binary = self.register_browser()
        extension = self.root / "dist/chrome"
        extension.mkdir(parents=True)
        (extension / "manifest.json").write_text("{}")
        profile = self.root / "dedicated profile"
        profile.mkdir()
        with patch.object(config, "BROWSER_MODE", "managed"), patch.object(config, "EXT_PATH", extension), patch.object(config, "PROFILE", profile):
            self.assertEqual(browser_install.executable(), str(binary))
            self.assertIn(f"--load-extension={extension}", browser_install.arguments())
            self.assertNotIn("--no-sandbox", browser_install.arguments())
            (profile / "Last Version").write_text("151.0.0.1")
            with self.assertRaisesRegex(RuntimeError, "update"):
                browser_install.executable()

    def test_archive_is_fully_validated_before_extraction(self):
        for name, mode in [("../outside", 0), ("/outside", 0), ("chrome-linux64/link", 0o120777)]:
            with self.subTest(name=name):
                archive = self.root / "bad.zip"
                with zipfile.ZipFile(archive, "w") as package:
                    package.writestr("chrome-linux64/good", b"not written")
                    info = zipfile.ZipInfo(name)
                    info.external_attr = mode << 16
                    package.writestr(info, b"outside")
                target = self.root / "extract"
                target.mkdir(exist_ok=True)
                with self.assertRaises(ValueError):
                    browser_install.extract_archive(archive, target)
                self.assertEqual(list(target.iterdir()), [])

    def test_archive_permissions_and_expansion_limit(self):
        archive = self.root / "good.zip"
        with zipfile.ZipFile(archive, "w") as package:
            info = zipfile.ZipInfo("chrome-linux64/chrome")
            info.external_attr = 0o100755 << 16
            package.writestr(info, b"fixture")
        target = self.root / "extract"
        target.mkdir()
        with patch.object(browser_install, "MAX_EXTRACTED", 1):
            with self.assertRaises(ValueError):
                browser_install.extract_archive(archive, target)
        browser_install.extract_archive(archive, target)
        self.assertEqual((target / "chrome-linux64/chrome").stat().st_mode & 0o7777, 0o700)

    def test_official_index_cannot_redirect_installation_to_another_host(self):
        payload = {"channels": {"Stable": {"version": "150.0.0.1", "downloads": {"chrome": [{"platform": "linux64", "url": "https://example.invalid/browser.zip"}]}}}}
        with patch.object(browser_install.urllib.request, "urlopen", return_value=io.BytesIO(json.dumps(payload).encode())):
            with self.assertRaisesRegex(ValueError, "Google URL"):
                browser_install.install()
        self.assertFalse((browser_install.root() / "browser.json").exists())

    def test_rerun_reuses_browser_preserves_accounts_and_smoke_failure_keeps_previous(self):
        self.register_browser()
        store = AccountStore()
        store.create("personal", "Personal")
        before = store.path.read_bytes()
        payload = {"channels": {"Stable": {"version": "150.0.0.1", "downloads": {"chrome": [{"platform": "linux64", "url": "https://storage.googleapis.com/chrome-for-testing-public/150.0.0.1/linux64/chrome-linux64.zip"}]}}}}
        with patch.object(browser_install.urllib.request, "urlopen", side_effect=lambda *_a, **_k: io.BytesIO(json.dumps(payload).encode())) as download, patch.object(browser_install, "smoke_check"):
            browser_install.install()
            browser_install.install()
        self.assertEqual(download.call_count, 2, "only the version index is fetched on rerun")
        self.assertEqual(store.path.read_bytes(), before)
        metadata = (browser_install.root() / "browser.json").read_bytes()
        with patch.object(browser_install.urllib.request, "urlopen", return_value=io.BytesIO(json.dumps(payload).encode())), patch.object(browser_install, "smoke_check", side_effect=RuntimeError("sandbox")):
            with self.assertRaises(RuntimeError):
                browser_install.install()
        self.assertEqual((browser_install.root() / "browser.json").read_bytes(), metadata)

    def test_desktop_setup_preserves_registry_and_handles_paths_with_spaces(self):
        store = AccountStore()
        store.create("personal", "Personal")
        store.bind("fallem-prince", "personal", config.CHANNEL_ID)
        before = store.path.read_bytes()
        with patch.dict(os.environ, {"XDG_DATA_HOME": str(self.root / "desktop data")}), patch.object(onboarding.sys, "executable", '/a b/py%thon'):
            onboarding.prepare()
            onboarding.prepare()
        self.assertEqual(store.path.read_bytes(), before)
        entry = (self.root / "desktop data/applications/youtubebot-accounts.desktop").read_text()
        self.assertIn('Exec="/a b/py%%thon" -m tools.ytbot accounts ui', entry)

    def test_visible_connection_opens_both_sites_in_same_account_without_automation_flags(self):
        store = AccountStore()
        store.create("work", "Work")
        previous = config.PROFILE, config.CDP_PORT, config.ACCOUNT_ID
        self.addCleanup(lambda: (setattr(config, "PROFILE", previous[0]), setattr(config, "CDP_PORT", previous[1]), setattr(config, "ACCOUNT_ID", previous[2])))
        with patch.dict(os.environ, {"DISPLAY": ":1"}), patch.object(runtime, "stop_hidden_chrome"), patch.object(runtime, "_write_preferences"), patch.object(browser_install, "executable", return_value="/safe/chrome"), patch.object(browser_install, "arguments", return_value=["--load-extension=/safe/dist/chrome"]), patch.object(account_commands.subprocess, "Popen") as launch, patch.object(config, "EXT_PATH", self.root):
            launch.return_value.wait.return_value = 0
            account_commands.browser_connect("work", store)
        args = launch.call_args.args[0]
        self.assertIn(account_commands.SIGN_IN, args)
        self.assertIn("https://chatgpt.com/", args)
        self.assertIn(f"--user-data-dir={store.profile('work')}", args)
        self.assertFalse(any("remote-debugging" in arg or "enable-automation" in arg for arg in args))
        launch.return_value.wait.assert_called_once()

    def test_existing_account_switch_keeps_system_profile_and_channel_binding(self):
        store = AccountStore()
        store.create("work", "Work")
        original = store.profile("work")
        (original / "existing-login-marker").write_text("preserve")
        store.bind("fallem-prince", "work", config.CHANNEL_ID)
        binding = store.load()["bindings"]
        self.register_browser()
        store.use_managed_browser("work")
        self.assertNotEqual(store.profile("work"), original)
        self.assertEqual((original / "existing-login-marker").read_text(), "preserve")
        self.assertEqual(store.load()["bindings"], binding)
        store.use_managed_browser("work")
        self.assertEqual(store.profile("work"), store.root / "browser-managed/work")
        with self.assertRaises(ValueError):
            store.use_managed_browser("legacy")

    def test_finish_login_terminates_only_its_own_browser_and_restores_handler(self):
        store = AccountStore()
        store.create("work", "Work")
        handlers = []
        process = Mock()
        def wait():
            handlers[0](15, None)
            return -15
        process.wait.side_effect = wait
        with patch.dict(os.environ, {"DISPLAY": ":1"}), patch.object(config, "PROFILE"), patch.object(config, "CDP_PORT"), patch.object(config, "ACCOUNT_ID"), patch.object(config, "BROWSER_MODE"), patch.object(runtime, "stop_hidden_chrome"), patch.object(runtime, "_write_preferences"), patch.object(browser_install, "executable", return_value="/safe/chrome"), patch.object(browser_install, "arguments", return_value=[]), patch.object(account_commands.subprocess, "Popen", return_value=process), patch.object(account_commands.signal, "signal", side_effect=lambda _sig, handler: handlers.append(handler) or "original") as signal_handler, patch.object(config, "EXT_PATH", self.root):
            account_commands.browser_connect("work", store)
        process.terminate.assert_called_once()
        self.assertEqual(signal_handler.call_args.args[1], "original")

    def test_partial_readiness_never_reports_ready_or_rebinds_account(self):
        from tools.ytbot import account
        store = AccountStore()
        store.create("work", "Work")
        extension = Mock()
        extension.evaluate.return_value = True
        chatgpt = Mock()
        chatgpt.evaluate.return_value = False
        context = Mock()
        context.new_page.side_effect = [extension, chatgpt]
        with patch.object(config, "PROFILE"), patch.object(config, "CDP_PORT"), patch.object(config, "ACCOUNT_ID"), patch.object(config, "BROWSER_MODE"), patch.object(runtime, "start_hidden_chrome"), patch.object(runtime, "connect_hidden", return_value=(Mock(), context)), patch.object(account, "ensure_channel"), patch("playwright.sync_api.sync_playwright"):
            result = account_commands.check_connection("fallem-prince", "work", store)
        self.assertEqual(result, {"channel_verified": True, "extension_ready": True, "chatgpt_authenticated": False, "ready": False})
        self.assertEqual(store.load()["bindings"], {})

    def test_preferences_do_not_replace_browser_extension_registration(self):
        profile = self.root / "profile"
        (profile / "Default").mkdir(parents=True)
        prefs = profile / "Default/Preferences"
        settings = {config.EXT_ID: {"state": 1, "manifest": {"name": "Capture"}}, "other": {"state": 0}}
        prefs.write_text(json.dumps({"extensions": {"settings": settings}, "keep": True}))
        with patch.object(config, "PROFILE", profile):
            runtime._write_preferences()
        data = json.loads(prefs.read_text())
        self.assertEqual(data["extensions"]["settings"], settings)
        self.assertTrue(data["keep"])


if __name__ == "__main__":
    unittest.main()
