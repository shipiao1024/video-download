---
name: video-download
description: Use when downloading online videos with yt-dlp where the user wants selectable quality, YouTube 720p or higher, best 1080p, separate audio/video stream merging, ffmpeg setup, subtitles, local Chinese translation, or a repeatable high-quality video download workflow on Windows.
---

# Video Download

## Overview

Use the bundled scripts to avoid fragile manual `yt-dlp -f` selectors. The workflow covers video download, English subtitle retrieval with rate limiting, local Chinese subtitle translation, and lossless MKV subtitle muxing.

## Environment Setup

Use Windows PowerShell. Install and verify these dependencies before running the workflow.

1. Python 3.11+:
   ```powershell
   python --version
   python -m pip --version
   ```
2. `yt-dlp`:
   ```powershell
   python -m pip install -U yt-dlp
   python -m yt_dlp --version
   ```
3. `ffmpeg` and `ffprobe`:
   - If `ffmpeg` is already on `PATH`, verify it:
     ```powershell
     ffmpeg -version
     ffprobe -version
     ```
   - If it is not on `PATH`, download a Windows static build, unzip it, and pass the `bin` folder or `ffmpeg.exe` explicitly:
     ```powershell
     $toolsDir = "C:\tools"
     New-Item -ItemType Directory -Force -Path $toolsDir | Out-Null
     curl.exe -L "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -o "$toolsDir\ffmpeg-release-essentials.zip"
     Expand-Archive -LiteralPath "$toolsDir\ffmpeg-release-essentials.zip" -DestinationPath "$toolsDir\ffmpeg" -Force
     ```
     Then use:
     ```powershell
     --ffmpeg-location "C:\tools\ffmpeg\ffmpeg-<version>-essentials_build\bin"
     --ffmpeg "C:\tools\ffmpeg\ffmpeg-<version>-essentials_build\bin\ffmpeg.exe"
     ```
4. Local subtitle translation with Argos Translate:
   ```powershell
   python -m pip install -U argostranslate
   python -c "import argostranslate.package as p; p.update_package_index(); pkg=next(pkg for pkg in p.get_available_packages() if pkg.from_code=='en' and pkg.to_code=='zh'); path=pkg.download(); p.install_from_path(path)"
   ```
   Verify the local model is installed:
   ```powershell
   python -c "import argostranslate.translate as t; print(t.translate('Hello world', 'en', 'zh'))"
   ```
5. Optional YouTube extraction improvements:
   - `yt-dlp` may warn that no JavaScript runtime is available. This can reduce available formats for some videos. Install a supported runtime only if extraction starts failing or formats are missing.
   - `yt-dlp` may warn about missing impersonation dependencies. Install them only if YouTube requests fail because impersonation is required.

## Output Contract

When the workflow finishes, report these items clearly:

- selected video resolution, codec, FPS, and bitrate preference
- selected audio format
- final container format
- output directory
- whether subtitles were downloaded
- whether local Chinese translation was generated
- whether `with-subs\*.mkv` was created

## Workflow

1. Complete the Environment Setup section.
2. Confirm the user's same-resolution preference before downloading:
   - `highest-bitrate`: larger file, less compressed source, use when preserving quality is more important than size.
   - `efficient`: smaller file, prefer newer/more efficient codecs such as AV1, use when storage/transfer size matters.
   - Do not infer this choice from urgency, batch size, or previous runs. If the user has not explicitly chosen one in the current request, ask before downloading.
3. Run the bundled script:
   ```powershell
   python C:\Users\Administrator\.codex\skills\video-download\scripts\download_youtube_hd.py "YOUTUBE_URL" -o "D:\youtube download" --ffmpeg-location "C:\path\to\ffmpeg\bin"
   ```
4. Report the selected video format, audio format, merge container, and final output path.

## Subtitle Workflow

Use this workflow when the user asks for CC subtitles, translated subtitles, Chinese subtitles, or subtitles integrated into video files.

1. Download English subtitles first. Prefer YouTube manual `en-GB` subtitles and request only one language to avoid 429 throttling:
   ```powershell
   python -m yt_dlp --skip-download --write-subs --sub-langs "en-GB" --sub-format "srt" --no-overwrites -P "OUTPUT_DIR" -o "%(title).200B [%(id)s].%(ext)s" "VIDEO_URL"
   ```
   For playlists or many videos, process one video at a time and sleep at least 30 seconds between videos. Do not request `zh-Hans`, `zh-Hant`, and many translated languages in one batch unless the user accepts a high 429 risk.
2. Install local translation dependencies when missing:
   ```powershell
   python -m pip install -U argostranslate
   python -c "import argostranslate.package as p; p.update_package_index(); pkg=next(pkg for pkg in p.get_available_packages() if pkg.from_code=='en' and pkg.to_code=='zh'); path=pkg.download(); p.install_from_path(path)"
   ```
3. Translate English SRT files locally to Simplified Chinese:
   ```powershell
   python C:\Users\Administrator\.codex\skills\video-download\scripts\translate_srt_argos.py "OUTPUT_DIR" --overwrite
   ```
   This creates `*.zh-Hans.local.srt` and preserves SRT numbering and timestamps.
4. Soft-mux video plus subtitles into MKV without re-encoding:
   ```powershell
   python C:\Users\Administrator\.codex\skills\video-download\scripts\mux_subtitles.py "OUTPUT_DIR" --ffmpeg "C:\path\to\ffmpeg.exe" --overwrite
   ```
   This writes files under `OUTPUT_DIR\with-subs`.

## Subtitle Muxing Rules

- Keep original `.mp4`, `.en-GB.srt`, and `.zh-Hans.local.srt` files.
- Create new `.with-subs.mkv` files in a `with-subs` subfolder.
- Mux one video track, one audio track, and two subtitle tracks.
- Set `chi / Chinese Simplified (local)` as the default subtitle track.
- Set `eng / English` as the secondary subtitle track.
- Use soft subtitles. Do not burn subtitles into the video unless the user explicitly asks for hard subtitles.
- Do not re-encode video or audio during muxing.

## Selection Rules

- Select only video streams with height `>=720` and `<=1080`.
- Download only one video stream: if 1080p exists, select only 1080p; if not, select the highest available stream at 720p or higher.
- Within the selected resolution, use the confirmed video preference:
  - `highest-bitrate`: prefer highest FPS, then highest bitrate, then largest file size.
  - `efficient`: prefer highest FPS, then more efficient codecs, then lower bitrate/file size.
- In non-interactive or batch execution, pass the confirmed preference explicitly with `--video-preference highest-bitrate` or `--video-preference efficient`.
- If no explicit preference has been confirmed, stop and ask the user. Never silently default to `highest-bitrate`.
- Select audio-only by highest audio bitrate, then sample rate, then file size.
- Use `mkv` unless the selected codecs are MP4-compatible without transcoding.
- Do not force transcode just to produce MP4 unless the user explicitly asks.

## Useful Commands

List/select formats without downloading:

```powershell
python C:\Users\Administrator\.codex\skills\video-download\scripts\download_youtube_hd.py "YOUTUBE_URL" --list-only --video-preference ask --ffmpeg-location "C:\path\to\ffmpeg\bin"
```

Download the larger/highest-bitrate version:

```powershell
python C:\Users\Administrator\.codex\skills\video-download\scripts\download_youtube_hd.py "YOUTUBE_URL" --video-preference highest-bitrate --ffmpeg-location "C:\path\to\ffmpeg\bin"
```

Download the smaller/more efficient version:

```powershell
python C:\Users\Administrator\.codex\skills\video-download\scripts\download_youtube_hd.py "YOUTUBE_URL" --video-preference efficient --ffmpeg-location "C:\path\to\ffmpeg\bin"
```

Translate English subtitles locally:

```powershell
python C:\Users\Administrator\.codex\skills\video-download\scripts\translate_srt_argos.py "OUTPUT_DIR" --overwrite
```

Mux local Chinese and English subtitles into MKV:

```powershell
python C:\Users\Administrator\.codex\skills\video-download\scripts\mux_subtitles.py "OUTPUT_DIR" --ffmpeg "C:\path\to\ffmpeg.exe" --overwrite
```

## Common Mistakes

- `best[ext=mp4]` usually picks a lower single-file format because high-resolution YouTube streams often separate video and audio.
- `bestvideo+bestaudio` may pick AV1 or another codec that is high quality but not the highest bitrate. Use the script when the user asks for "1080p highest".
- Same resolution does not mean same bitrate or same compression. Confirm whether the user wants `highest-bitrate` or `efficient` before downloading.
- `--video-preference ask` is only for an interactive terminal. In automation, loops, or multi-video downloads, ask the user first and then pass the chosen value explicitly.
- Missing `ffmpeg` causes separate streams to remain unmerged or fail to merge.
- Requesting many YouTube subtitle languages at once often triggers `HTTP Error 429`. Prefer `en-GB` first, then translate locally.
- A downloaded YouTube `zh-Hans.vtt` is not the same artifact as local translation. Keep local translations named `.zh-Hans.local.srt`.
- If a video has no subtitle track, do not promise YouTube-style translated CC output. Report that no source subtitle exists, then stop or ask whether the user wants an external transcription workflow instead.
