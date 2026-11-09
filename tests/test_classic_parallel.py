"""Bounded Classic parallel-rendering contracts from docs/STANDARD-MODE.md."""

from pathlib import Path
from tempfile import TemporaryDirectory
import os
import unittest
from unittest.mock import patch

from src.engine.classic_parallel import (
    build_mux_command, build_part_command, frame_ranges, parallel_workers, render_parallel_video,
)


class TestClassicParallel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_given_long_classic_video_then_parallelism_is_bounded_by_measured_policy(self):
        self.assertEqual(parallel_workers(120, True, cpus=16), 4)
        self.assertEqual(parallel_workers(600, True, cpus=4), 1)
        self.assertEqual(parallel_workers(119, True, cpus=16), 1)
        self.assertEqual(parallel_workers(600, False, cpus=16), 4)

    def test_given_fractional_duration_then_ranges_cover_every_frame_once_in_order(self):
        ranges = frame_ranges(120.13, 30, 4)
        self.assertEqual(ranges, [(0, 901), (901, 1802), (1802, 2703), (2703, 3604)])
        self.assertEqual(sum(end-start for start, end in ranges), 3604)

    def test_given_later_chunk_then_loop_phase_and_subtitles_use_global_time(self):
        with TemporaryDirectory() as directory:
            subtitle = Path(directory) / "captions.ass"
            subtitle.touch()
            command = build_part_command(Path("loop.mp4"), subtitle, Path("part.mp4"),
                                         1800, 2700, 1920, 1080, 30, True, 24)
            self.assertNotIn("-ss", command)
            filters = command[command.index("-filter_complex") + 1]
            self.assertIn("trim=start_frame=360,setpts=PTS-STARTPTS", filters)
            self.assertLess(filters.index("trim="), filters.index("scale="))
            self.assertLess(filters.index("setpts=PTS-STARTPTS"), filters.index("scale="))
            self.assertLess(filters.index("setpts=PTS+60.000000/TB"), filters.index("subtitles="))
            self.assertLess(filters.index("subtitles="), filters.rindex("setpts=PTS-STARTPTS"))
            self.assertEqual(command[command.index("-frames:v") + 1], "900")
            self.assertEqual(command[command.index("-qp") + 1], "28")
            self.assertEqual(command[command.index("-preset") + 1], "p3")
            self.assertIn("-an", command)

    def test_given_non_integer_chunk_time_then_loop_offset_cannot_round_up_and_skip_a_frame(self):
        command = build_part_command(Path("loop.mp4"), None, Path("part.mp4"),
                                     1802, 2703, 1920, 1080, 30, True, 24)
        filters = command[command.index("-filter_complex") + 1]
        self.assertIn("trim=start_frame=362,setpts=PTS-STARTPTS", filters)
        self.assertEqual(command[command.index("-frames:v") + 1], "901")

    def test_given_finished_video_chunks_then_mux_copies_video_and_mixes_audio_only_once(self):
        with TemporaryDirectory() as directory:
            music = Path(directory) / "music.mp3"
            music.touch()
            command = build_mux_command(Path("concat.txt"), Path("full.wav"), music,
                                        Path("out.mp4"), 120, 2, .15)
            self.assertEqual(command[command.index("-c:v") + 1], "copy")
            self.assertEqual(command[command.index("-b:a") + 1], "128k")
            self.assertIn("amix=inputs=2:duration=longest:normalize=0", command[command.index("-filter_complex") + 1])
            self.assertIn("full.wav", command)

    def test_given_parallel_failure_then_existing_single_pass_renderer_is_used(self):
        with patch("src.engine.classic_parallel.run_command", side_effect=RuntimeError("NVENC busy")), \
             patch("src.engine.classic_parallel.get_audio_duration", return_value=24), \
             patch("src.engine.classic_parallel.render_single_pass_video", return_value=True) as fallback:
            self.assertTrue(render_parallel_video(Path("loop.mp4"), Path("full.wav"), None,
                                                  None, Path("out.mp4"), total_duration=120,
                                                  background_is_video=True, fps=30))
            self.assertEqual(fallback.call_args.kwargs["total_duration"], 120)
            self.assertEqual(fallback.call_args.kwargs["fps"], 30)

    def test_given_long_classic_job_then_worker_keeps_subtitles_duration_and_original_quality(self):
        from src.core.standard_video_worker import RenderWorker
        for theme, fps in (("", 15), ("religious", 30)):
            with self.subTest(theme=theme), \
                 patch("src.core.standard_video_worker.get_audio_duration", return_value=90), \
                 patch("src.core.standard_video_worker.parallel_workers", return_value=4), \
                 patch("src.core.standard_video_worker.transcribe_audio_to_segments",
                       return_value=[{"start": 60, "end": 65, "text": "Still synchronized."}]) as transcribe, \
                 patch("src.core.standard_video_worker.render_parallel_video", return_value=True) as render, \
                 patch("src.core.standard_video_worker.render_single_pass_video") as single:
                results = []
                worker = RenderWorker(Path("image.png"), Path("voice.wav"), None, Path("out.mp4"),
                                      2, .15, "YouTube Standard (16:9)", background_theme=theme)
                worker.finished.connect(lambda ok, message: results.append(ok))
                worker.run()
                self.assertEqual(results, [True])
                transcribe.assert_called_once()
                single.assert_not_called()
                self.assertIsNotNone(render.call_args.args[3])
                self.assertEqual(render.call_args.kwargs["fps"], fps)
                self.assertEqual(render.call_args.kwargs["total_duration"], 120)
                self.assertEqual(render.call_args.kwargs["width"], 1920)
                self.assertEqual(render.call_args.kwargs["height"], 1080)


if __name__ == "__main__":
    unittest.main()
