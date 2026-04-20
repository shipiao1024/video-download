import unittest
from unittest.mock import patch

from download_youtube_hd import choose_formats, resolve_video_preference


class ChooseFormatsTests(unittest.TestCase):
    def test_downloads_only_1080p_when_1080p_and_720p_are_both_available(self):
        formats = [
            {"format_id": "302", "vcodec": "vp9", "acodec": "none", "height": 720, "fps": 60, "tbr": 355},
            {"format_id": "303", "vcodec": "vp9", "acodec": "none", "height": 1080, "fps": 60, "tbr": 1389},
            {"format_id": "140", "vcodec": "none", "acodec": "mp4a", "abr": 129},
        ]

        selected = choose_formats(formats, min_height=720, max_height=1080)

        self.assertEqual(selected.video_id, "303")
        self.assertNotIn("302", selected.format_selector)

    def test_prefers_highest_bitrate_1080p_video_and_best_audio(self):
        formats = [
            {"format_id": "18", "vcodec": "avc1", "acodec": "mp4a", "height": 360, "tbr": 202, "filesize": 17630198},
            {"format_id": "298", "vcodec": "avc1", "acodec": "none", "height": 720, "fps": 60, "tbr": 118, "filesize": 10286530},
            {"format_id": "399", "vcodec": "av01", "acodec": "none", "height": 1080, "fps": 60, "tbr": 340, "filesize": 29695672},
            {"format_id": "303", "vcodec": "vp9", "acodec": "none", "height": 1080, "fps": 60, "tbr": 1389, "filesize": 121330000},
            {"format_id": "140", "vcodec": "none", "acodec": "mp4a", "abr": 129, "asr": 44100, "filesize": 11314135},
            {"format_id": "251", "vcodec": "none", "acodec": "opus", "abr": 99, "asr": 48000, "filesize": 8682209},
        ]

        selected = choose_formats(formats, min_height=720, max_height=1080)

        self.assertEqual(selected.video_id, "303")
        self.assertEqual(selected.audio_id, "140")
        self.assertEqual(selected.format_selector, "303+140")
        self.assertEqual(selected.merge_format, "mkv")

    def test_can_choose_more_efficient_1080p_video_when_requested(self):
        formats = [
            {"format_id": "399", "ext": "mp4", "vcodec": "av01", "acodec": "none", "height": 1080, "fps": 60, "tbr": 340, "filesize": 29695672},
            {"format_id": "303", "ext": "webm", "vcodec": "vp9", "acodec": "none", "height": 1080, "fps": 60, "tbr": 1389, "filesize": 121330000},
            {"format_id": "140", "ext": "m4a", "vcodec": "none", "acodec": "mp4a", "abr": 129, "asr": 44100},
        ]

        selected = choose_formats(formats, min_height=720, max_height=1080, video_preference="efficient")

        self.assertEqual(selected.video_id, "399")
        self.assertEqual(selected.audio_id, "140")
        self.assertEqual(selected.format_selector, "399+140")

    def test_ask_mode_requires_explicit_preference_in_non_interactive_shell(self):
        formats = [
            {"format_id": "399", "ext": "mp4", "vcodec": "av01", "acodec": "none", "height": 1080, "fps": 60, "tbr": 340},
            {"format_id": "303", "ext": "webm", "vcodec": "vp9", "acodec": "none", "height": 1080, "fps": 60, "tbr": 1389},
        ]

        with patch("sys.stdin.isatty", return_value=False):
            with self.assertRaisesRegex(ValueError, "--video-preference"):
                resolve_video_preference(formats, "ask")

    def test_ask_mode_requires_explicit_preference_when_prompt_cannot_read_input(self):
        formats = [
            {"format_id": "399", "ext": "mp4", "vcodec": "av01", "acodec": "none", "height": 1080, "fps": 60, "tbr": 340},
            {"format_id": "303", "ext": "webm", "vcodec": "vp9", "acodec": "none", "height": 1080, "fps": 60, "tbr": 1389},
        ]

        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", side_effect=EOFError):
            with self.assertRaisesRegex(ValueError, "--video-preference"):
                resolve_video_preference(formats, "ask")

    def test_falls_back_to_best_available_above_720_when_no_1080_exists(self):
        formats = [
            {"format_id": "135", "vcodec": "avc1", "acodec": "none", "height": 480, "tbr": 58},
            {"format_id": "298", "vcodec": "avc1", "acodec": "none", "height": 720, "fps": 60, "tbr": 118},
            {"format_id": "302", "vcodec": "vp9", "acodec": "none", "height": 720, "fps": 60, "tbr": 355},
            {"format_id": "140", "vcodec": "none", "acodec": "mp4a", "abr": 129},
        ]

        selected = choose_formats(formats, min_height=720, max_height=1080)

        self.assertEqual(selected.video_id, "302")
        self.assertEqual(selected.audio_id, "140")


if __name__ == "__main__":
    unittest.main()
