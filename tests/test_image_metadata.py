"""Unit tests for Image Metadata Inspector module."""

import json
import tempfile
import unittest
from pathlib import Path

# Add image-metadata-extractor to path for testing
import sys
MODULE_DIR = Path(__file__).resolve().parent.parent / "image-metadata-extractor"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from inspector import format_metadata_summary, parse_metadata_file, scan_metadata_files


class TestImageMetadataInspector(unittest.TestCase):
    """Test suite for image metadata parsing and inspection."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_parse_valid_metadata_file(self):
        meta_file = self.dir_path / "img_01_metadata.json"
        sample_data = {
            "source": "dalle_metadata",
            "pageTitle": "Cyberpunk City",
            "timestamp": "2026-08-18T15:00:00Z",
            "dalle": {
                "prompt": "Futuristic neon city at night",
                "seed": 123456
            }
        }
        meta_file.write_text(json.dumps(sample_data), encoding="utf-8")

        parsed = parse_metadata_file(meta_file)
        self.assertEqual(parsed["source"], "dalle_metadata")
        self.assertEqual(parsed["dalle"]["seed"], 123456)

    def test_scan_metadata_files(self):
        f1 = self.dir_path / "a_metadata.json"
        f2 = self.dir_path / "b_metadata.json"
        f1.write_text(json.dumps({"source": "test1"}), encoding="utf-8")
        f2.write_text(json.dumps({"source": "test2"}), encoding="utf-8")

        entries = scan_metadata_files(self.dir_path)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0][0].name, "a_metadata.json")

    def test_format_metadata_summary(self):
        data = {
            "source": "sse_stream_part",
            "pageTitle": "Abstract Landscape",
            "timestamp": "2026-08-18T12:00:00Z",
            "alt": "A peaceful mountain lake with sunset colors"
        }
        summary = format_metadata_summary(Path("img_metadata.json"), data)
        self.assertIn("Abstract Landscape", summary)
        self.assertIn("mountain lake", summary)


if __name__ == "__main__":
    unittest.main()
