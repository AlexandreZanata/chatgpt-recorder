"""Generation-only and readiness evidence; no accounts, remote browser or media calls."""
import unittest
from unittest.mock import Mock,patch
from pathlib import Path
import tempfile
from tools.ytbot import preflight

class ReadinessContracts(unittest.TestCase):
    def test_missing_both_accounts_names_both_and_never_claims_video_work(self):
        value=preflight.result({"google":"login_required","chatgpt":"login_required"})
        self.assertFalse(value["ready"]);self.assertEqual(value["code"],"login_required")
        self.assertIn("google e chatgpt",value["summary"]);self.assertIn("Nenhum vídeo",value["summary"])
    def test_unknown_dom_is_not_reported_as_logout_or_ready(self):
        page=Mock();page.url="https://chatgpt.com/";page.locator.return_value.first.is_visible.return_value=False
        self.assertEqual(preflight.inspect_page(page,"chatgpt"),"unknown")
        value=preflight.result({"google":"ready","chatgpt":"unknown"})
        self.assertEqual(value["code"],"readiness_unknown");self.assertNotIn("não está logada",value["summary"])
    def test_positive_page_evidence_and_redirect_to_login_are_distinct(self):
        page=Mock();page.url="https://accounts.google.com/ServiceLogin"
        self.assertEqual(preflight.inspect_page(page,"google","UC_SYNTHETIC"),"login_required")
        page.url="https://studio.youtube.com/channel/UC_SYNTHETIC";page.locator.return_value.first.is_visible.side_effect=[False,True]
        self.assertEqual(preflight.inspect_page(page,"google","UC_SYNTHETIC"),"ready")
    def test_generation_reuses_asset_pipeline_and_never_calls_upload(self):
        from tools.ytbot import generation,pipeline,config,logic
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);video=root/"run";video.mkdir();(video/"video.mp4").write_bytes(b"synthetic video")
            with patch.object(config,"RUNS",root),patch.object(generation.topics,"prepare_topics",return_value=["Synthetic topic"]),patch.object(pipeline,"asset_stage",return_value=video) as assets,patch.object(pipeline,"upload_stage") as upload,patch.object(logic,"record_event"),patch.object(logic,"write_records_markdown"):
                self.assertEqual(generation.run_generation(1,object()),[])
                assets.assert_called_once();upload.assert_not_called()
