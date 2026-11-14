"""Account window interaction with synthetic records; no browser or Google calls."""

import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from PySide6.QtWidgets import QApplication, QAbstractItemView
from tools.ytbot import config
from src.ui.accounts_window import AccountsWindow


class AccountWindowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_title_search_and_account_creation_preserve_readonly_history(self):
        records = [
            {
                "title": "First Exact Title",
                "topic": "a topic",
                "state": "scheduled",
                "slot": "2026-11-14 12:00",
                "video_id": "fixture_one",
            },
            {
                "title": "Second Different Title",
                "topic": "another topic",
                "state": "error",
                "slot": "",
                "video_id": "fixture_two",
            },
        ]
        with (
            TemporaryDirectory() as temp,
            patch.object(config, "ROOT", Path(temp)),
            patch("src.ui.accounts_window.library.runs", return_value=records),
        ):
            window = AccountsWindow()
            self.addCleanup(window.deleteLater)
            self.assertEqual(window.table.rowCount(), 2)
            self.assertEqual(
                window.table.editTriggers(), QAbstractItemView.NoEditTriggers
            )
            window.search.setText("FIRST")
            self.assertEqual(window.table.rowCount(), 1)
            self.assertEqual(window.table.item(0, 0).text(), "First Exact Title")
            window.identifier.setText("personal")
            window.label.setText("Personal")
            window.add_account()
            self.assertEqual(window.account.count(), 2)
            self.assertTrue((Path(temp) / ".local/accounts/registry.json").is_file())
            self.assertIsNone(window.browser)
            self.assertIsNone(window.oauth_job)
            window.close()
