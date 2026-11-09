"""Integration contract: a loadable Chrome-only package with shared settings."""

import importlib.util
import json
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location('chrome_build', ROOT / 'scripts/build-chrome.py')
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class ChromePackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = BUILDER.build_chrome(ROOT)
        cls.manifest = json.loads((cls.folder / 'manifest.json').read_text())

    def test_given_chrome_build_then_no_firefox_permissions_or_background_scripts(self):
        self.assertEqual(self.manifest['manifest_version'], 3)
        self.assertEqual(self.manifest['background']['type'], 'module')
        self.assertEqual(self.manifest['permissions'],
                         ['downloads', 'storage', 'activeTab', 'tabCapture', 'offscreen'])
        self.assertEqual(self.manifest['minimum_chrome_version'], '116')
        self.assertNotIn('browser_specific_settings', self.manifest)
        self.assertNotIn('scripts', self.manifest['background'])
        shortcut = self.manifest['commands']['_execute_action']['suggested_key']['default']
        self.assertEqual(shortcut, 'Ctrl+Shift+U')

    def test_given_chrome_manifest_then_all_referenced_resources_exist(self):
        main = next(script for script in self.manifest['content_scripts'] if script.get('world') == 'MAIN')
        self.assertEqual(main['run_at'], 'document_start')
        self.assertEqual(main['matches'], ['https://chatgpt.com/*'])
        files = [self.manifest['background']['service_worker'],
                 self.manifest['action']['default_popup'], self.manifest['action']['default_icon']]
        files.extend(file for script in self.manifest['content_scripts'] for file in script['js'])
        for file in files:
            self.assertTrue((self.folder / file).is_file(), f'Missing {file}')
        icon = (self.folder / self.manifest['action']['default_icon']).read_bytes()
        self.assertEqual(icon[:8], bytes.fromhex('89504e470d0a1a0a'))

    def test_given_chrome_popup_then_keep_shared_settings_and_load_namespace_adapter_first(self):
        popup = (self.folder / 'popup.html').read_text()
        self.assertLess(popup.index('src/chrome/browser-api.js'), popup.index('src/popup.js'))
        self.assertEqual((self.folder / 'src/popup.js').read_text(), (ROOT / 'src/popup.js').read_text())
        self.assertIn('src/chrome/recorder-popup.js', popup)
        self.assertTrue((self.folder / 'src/chrome/recorder.html').is_file())

    def test_given_chrome_archive_then_include_no_python_user_media_or_firefox_background(self):
        with zipfile.ZipFile(ROOT / 'dist/chatgpt-audio-capture-chrome-v0.1.0.zip') as archive:
            entries = archive.namelist()
            self.assertIn('manifest.json', entries)
            self.assertIn('src/chrome/background.js', entries)
            self.assertNotIn('src/background.js', entries)
            self.assertTrue(all(not file.endswith(('.py', '.pyc', '.mp4')) for file in entries))
            self.assertTrue(all('.local/' not in file for file in entries))
            for file in entries:
                self.assertEqual(archive.read(file), (self.folder / file).read_bytes())
