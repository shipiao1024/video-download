#!/usr/bin/env python
import argparse
import re
import shutil
import subprocess
from pathlib import Path


ID_RE = re.compile(r"\[([^\]]+)\]")


def parse_video_id(name: str) -> str:
    match = ID_RE.search(name)
    if not match:
        raise ValueError(f"Cannot parse video id from filename: {name}")
    return match.group(1)


def find_subtitles_for_video(video: Path) -> tuple[Path, Path]:
    video_id = parse_video_id(video.name)
    root = video.parent
    zh = None
    en = None
    for candidate in sorted(root.glob("*.srt")):
        try:
            candidate_id = parse_video_id(candidate.name)
        except ValueError:
            continue
        if candidate_id != video_id:
            continue
        if candidate.name.endswith(".zh-Hans.local.srt"):
            zh = candidate
        elif candidate.name.endswith(".en-GB.srt"):
            en = candidate
    if zh is None:
        raise FileNotFoundError(f"Missing zh-Hans.local subtitle for {video.name}")
    if en is None:
        raise FileNotFoundError(f"Missing en-GB subtitle for {video.name}")
    return zh, en


def build_mux_command(ffmpeg: str, video: Path, zh_sub: Path, en_sub: Path, output: Path) -> list[str]:
    return [
        ffmpeg,
        "-y",
        "-i",
        str(video),
        "-sub_charenc",
        "UTF-8",
        "-i",
        str(zh_sub),
        "-sub_charenc",
        "UTF-8",
        "-i",
        str(en_sub),
        "-map",
        "0",
        "-map",
        "1:0",
        "-map",
        "2:0",
        "-c",
        "copy",
        "-c:s",
        "srt",
        "-metadata:s:s:0",
        "language=chi",
        "-metadata:s:s:0",
        "title=Chinese Simplified (local)",
        "-metadata:s:s:1",
        "language=eng",
        "-metadata:s:s:1",
        "title=English",
        "-disposition:s:0",
        "default",
        "-disposition:s:1",
        "0",
        str(output),
    ]


def find_ffmpeg(explicit: str | None) -> str:
    if explicit:
        return explicit
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    raise FileNotFoundError("ffmpeg not found. Pass --ffmpeg.")


def mux_directory(directory: Path, output_dir: Path, ffmpeg: str, overwrite: bool = False):
    output_dir.mkdir(parents=True, exist_ok=True)
    videos = sorted(directory.glob("*.mp4"))
    if not videos:
        raise FileNotFoundError(f"No .mp4 files found in {directory}")

    for video in videos:
        zh_sub, en_sub = find_subtitles_for_video(video)
        output = output_dir / f"{video.stem}.with-subs.mkv"
        if output.exists() and not overwrite:
            print(f"skip exists: {output}")
            continue
        command = build_mux_command(ffmpeg, video, zh_sub, en_sub, output)
        print(f"mux: {video.name} -> {output.name}")
        subprocess.run(command, check=True)


def main():
    parser = argparse.ArgumentParser(description="Mux MP4 files with local zh-Hans and en-GB SRT subtitles into MKV.")
    parser.add_argument("directory")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--ffmpeg", default=None)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    directory = Path(args.directory)
    output_dir = Path(args.output_dir) if args.output_dir else directory / "with-subs"
    mux_directory(directory, output_dir, find_ffmpeg(args.ffmpeg), overwrite=args.overwrite)


if __name__ == "__main__":
    main()
