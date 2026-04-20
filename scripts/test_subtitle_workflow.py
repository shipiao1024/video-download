import unittest
from pathlib import Path
from unittest.mock import patch

from mux_subtitles import build_mux_command, find_subtitles_for_video, parse_video_id
from translate_srt_argos import translate_srt_text


class SubtitleWorkflowTests(unittest.TestCase):
    def test_translate_srt_preserves_indices_and_timestamps(self):
        source = "1\n00:00:01,000 --> 00:00:03,000\nHello world.\n\n"

        with patch("argostranslate.translate.translate", return_value="你好，世界。"):
            translated = translate_srt_text(source)

        self.assertIn("1", translated)
        self.assertIn("00:00:01,000 --> 00:00:03,000", translated)
        self.assertIn("你好，世界。", translated)

    def test_parse_video_id_from_downloaded_filename(self):
        self.assertEqual(parse_video_id("01-Introduction [_tHVJuIbc-s] 1080p-137+140.mp4"), "_tHVJuIbc-s")

    def test_find_subtitles_for_video_by_id(self):
        root = Path("test-output-subtitle-workflow")
        root.mkdir(exist_ok=True)
        try:
            video = root / "01-Introduction [_tHVJuIbc-s] 1080p-137+140.mp4"
            zh = root / "01-Introduction [_tHVJuIbc-s].zh-Hans.local.srt"
            en = root / "01-Introduction [_tHVJuIbc-s].en-GB.srt"
            for path in (video, zh, en):
                path.write_text("", encoding="utf-8")

            found_zh, found_en = find_subtitles_for_video(video)
        finally:
            for path in root.glob("*"):
                path.unlink()
            root.rmdir()

        self.assertEqual(found_zh.name, zh.name)
        self.assertEqual(found_en.name, en.name)

    def test_mux_command_sets_chinese_default_and_english_secondary(self):
        command = build_mux_command(
            ffmpeg="ffmpeg",
            video=Path("video.mp4"),
            zh_sub=Path("video.zh-Hans.local.srt"),
            en_sub=Path("video.en-GB.srt"),
            output=Path("video.with-subs.mkv"),
        )

        self.assertIn("-disposition:s:0", command)
        self.assertIn("default", command)
        self.assertIn("-metadata:s:s:0", command)
        self.assertIn("language=chi", command)
        self.assertIn("-metadata:s:s:1", command)
        self.assertIn("language=eng", command)


if __name__ == "__main__":
    unittest.main()
