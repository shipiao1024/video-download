#!/usr/bin/env python
import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import yt_dlp
except ImportError:  # pragma: no cover - exercised by users without yt-dlp
    yt_dlp = None


@dataclass(frozen=True)
class SelectedFormats:
    video_id: str
    audio_id: str | None
    format_selector: str
    merge_format: str
    video_height: int
    video_fps: float
    video_tbr: float
    video_preference: str


def _num(value, default=0):
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _is_video_only(fmt):
    return fmt.get("vcodec") not in (None, "none") and fmt.get("acodec") in (None, "none")


def _is_audio_only(fmt):
    return fmt.get("acodec") not in (None, "none") and fmt.get("vcodec") in (None, "none")


def _codec_efficiency_rank(fmt):
    codec = (fmt.get("vcodec") or "").lower()
    if codec.startswith("av01"):
        return 4
    if codec.startswith("vp9"):
        return 3
    if codec.startswith("hev") or codec.startswith("hvc"):
        return 2
    if codec.startswith("avc") or codec.startswith("h264"):
        return 1
    return 0


def video_candidates_for_target_height(formats, min_height=720, max_height=1080):
    candidates = []
    for fmt in formats:
        height = int(_num(fmt.get("height")))
        if not _is_video_only(fmt) or height < min_height or height > max_height:
            continue
        candidates.append(fmt)

    if not candidates:
        raise ValueError(f"No video-only format found between {min_height}p and {max_height}p")

    target_height = max(int(_num(fmt.get("height"))) for fmt in candidates)
    return [fmt for fmt in candidates if int(_num(fmt.get("height"))) == target_height]


def choose_video(target_candidates, video_preference="highest-bitrate"):
    if video_preference == "efficient":
        return max(
            target_candidates,
            key=lambda fmt: (
                _num(fmt.get("fps")),
                _codec_efficiency_rank(fmt),
                -_num(fmt.get("tbr")),
                -_num(fmt.get("filesize") or fmt.get("filesize_approx")),
            ),
        )

    if video_preference != "highest-bitrate":
        raise ValueError(f"Unsupported video preference: {video_preference}")

    return max(
        target_candidates,
        key=lambda fmt: (
            _num(fmt.get("fps")),
            _num(fmt.get("tbr")),
            _num(fmt.get("filesize") or fmt.get("filesize_approx")),
        ),
    )


def choose_formats(formats, min_height=720, max_height=1080, video_preference="highest-bitrate"):
    target_candidates = video_candidates_for_target_height(formats, min_height, max_height)
    video = choose_video(target_candidates, video_preference)

    audio_candidates = [fmt for fmt in formats if _is_audio_only(fmt)]
    audio = None
    if audio_candidates:
        audio = max(
            audio_candidates,
            key=lambda fmt: (
                _num(fmt.get("abr")),
                _num(fmt.get("asr")),
                _num(fmt.get("filesize") or fmt.get("filesize_approx")),
            ),
        )

    video_id = str(video["format_id"])
    audio_id = str(audio["format_id"]) if audio else None
    selector = f"{video_id}+{audio_id}" if audio_id else video_id
    merge_format = _merge_format(video, audio)

    return SelectedFormats(
        video_id=video_id,
        audio_id=audio_id,
        format_selector=selector,
        merge_format=merge_format,
        video_height=int(_num(video.get("height"))),
        video_fps=_num(video.get("fps")),
        video_tbr=_num(video.get("tbr")),
        video_preference=video_preference,
    )


def _merge_format(video, audio):
    video_ext = (video.get("ext") or "").lower()
    audio_ext = (audio.get("ext") or "").lower() if audio else ""
    video_codec = (video.get("vcodec") or "").lower()
    audio_codec = (audio.get("acodec") or "").lower() if audio else ""
    mp4_audio = audio_ext in ("m4a", "mp4") or audio_codec.startswith("mp4a")
    mp4_video = video_ext == "mp4" and not video_codec.startswith(("vp9", "av01"))
    return "mp4" if mp4_video and (audio is None or mp4_audio) else "mkv"


def find_ffmpeg_location(explicit):
    if explicit:
        path = Path(explicit)
        if path.is_file() and path.name.lower() == "ffmpeg.exe":
            return str(path.parent)
        return str(path)

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return str(Path(ffmpeg).parent)

    workspace_ffmpeg = Path.cwd() / "tools" / "ffmpeg"
    matches = list(workspace_ffmpeg.rglob("ffmpeg.exe")) if workspace_ffmpeg.exists() else []
    if matches:
        return str(matches[0].parent)

    return None


def describe_video_candidates(candidates):
    rows = []
    for fmt in sorted(candidates, key=lambda item: (_num(item.get("fps")), _num(item.get("tbr"))), reverse=True):
        filesize = _num(fmt.get("filesize") or fmt.get("filesize_approx"))
        size_text = f"{filesize / 1024 / 1024:.2f} MiB" if filesize else "unknown size"
        rows.append(
            f"{fmt.get('format_id')}: {int(_num(fmt.get('height')))}p "
            f"{_num(fmt.get('fps')):g}fps, codec={fmt.get('vcodec')}, "
            f"tbr={_num(fmt.get('tbr')):g}, {size_text}"
        )
    return rows


def resolve_video_preference(candidates, requested):
    if requested != "ask" or len(candidates) <= 1:
        return requested if requested != "ask" else "highest-bitrate"

    print("Video candidates at the selected resolution:")
    for row in describe_video_candidates(candidates):
        print(f"  - {row}")

    if not sys.stdin.isatty():
        raise _preference_required_error()

    while True:
        try:
            answer = input("Choose video preference [highest-bitrate/efficient] (default: highest-bitrate): ").strip().lower()
        except EOFError as exc:
            raise _preference_required_error() from exc
        if not answer:
            return "highest-bitrate"
        if answer in ("highest-bitrate", "efficient"):
            return answer
        print("Please enter highest-bitrate or efficient.")


def _preference_required_error():
    return ValueError(
        "Video bitrate/compression preference must be confirmed before downloading. "
        "Pass --video-preference highest-bitrate or --video-preference efficient."
    )


def download(url, output_dir, ffmpeg_location=None, min_height=720, max_height=1080, list_only=False, video_preference="ask"):
    if yt_dlp is None:
        raise RuntimeError("yt-dlp is not installed. Install with: python -m pip install -U yt-dlp")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    ffmpeg_path = find_ffmpeg_location(ffmpeg_location)
    if not ffmpeg_path:
        raise RuntimeError("ffmpeg was not found. Install ffmpeg or pass --ffmpeg-location.")

    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": False, "ffmpeg_location": ffmpeg_path}) as ydl:
        info = ydl.extract_info(url, download=False)

    target_candidates = video_candidates_for_target_height(info.get("formats", []), min_height, max_height)
    resolved_preference = resolve_video_preference(target_candidates, video_preference)
    selected = choose_formats(
        info.get("formats", []),
        min_height=min_height,
        max_height=max_height,
        video_preference=resolved_preference,
    )
    print(
        f"Selected video {selected.video_id}: {selected.video_height}p "
        f"{selected.video_fps:g}fps, tbr={selected.video_tbr:g}; "
        f"preference={selected.video_preference}; audio {selected.audio_id or 'none'}"
    )

    if list_only:
        return selected

    ydl_opts = {
        "format": selected.format_selector,
        "ffmpeg_location": ffmpeg_path,
        "merge_output_format": selected.merge_format,
        "paths": {"home": str(output_path)},
        "outtmpl": {"default": "%(title).200B [%(id)s] %(height)sp-%(format_id)s.%(ext)s"},
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return selected


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Download one best YouTube video stream: 1080p when available, otherwise the best available stream at 720p or higher, then merge audio with ffmpeg."
    )
    parser.add_argument("url")
    parser.add_argument("-o", "--output-dir", default=r"D:\youtube download")
    parser.add_argument("--ffmpeg-location", default=None)
    parser.add_argument("--min-height", type=int, default=720)
    parser.add_argument("--max-height", type=int, default=1080)
    parser.add_argument(
        "--video-preference",
        choices=("ask", "highest-bitrate", "efficient"),
        default="ask",
        help="ask for a choice, prefer larger/high-bitrate video, or prefer more efficient compression/smaller files",
    )
    parser.add_argument("--list-only", action="store_true", help="Select formats without downloading")
    args = parser.parse_args(argv)

    try:
        download(
            args.url,
            args.output_dir,
            ffmpeg_location=args.ffmpeg_location,
            min_height=args.min_height,
            max_height=args.max_height,
            video_preference=args.video_preference,
            list_only=args.list_only,
        )
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
