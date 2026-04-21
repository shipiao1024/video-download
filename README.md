# video-download

Codex skill for repeatable online video download workflows on Windows.

This skill focuses on:

- downloading YouTube and other online videos with `yt-dlp`
- selecting one best video stream from `720p` to `1080p`
- requiring explicit bitrate/compression preference confirmation
- downloading English subtitles with lower 429 risk
- translating subtitles locally to Simplified Chinese
- muxing video plus Chinese and English subtitles into `.mkv` without re-encoding

The skill definition lives in [SKILL.md](./SKILL.md).

## Quick Start

Use PowerShell on Windows.

1. Install Python dependencies:
   ```powershell
   python -m pip install -U yt-dlp argostranslate
   ```
2. Prepare `ffmpeg`:
   - If `ffmpeg` is already on `PATH`, verify it with `ffmpeg -version`.
   - Otherwise download a static build and remember the `bin` directory path.
3. Confirm the user's same-resolution preference before downloading:
   - `highest-bitrate`: larger files, less compressed source
   - `efficient`: smaller files, prefer more efficient codecs when available
4. Download one video:
   ```powershell
   python C:\Users\Administrator\.codex\skills\video-download\scripts\download_youtube_hd.py "YOUTUBE_URL" --video-preference highest-bitrate --ffmpeg-location "C:\path\to\ffmpeg\bin" -o "D:\youtube download"
   ```
5. If subtitles are needed, download English subtitles first, translate locally, then mux:
   ```powershell
   python C:\Users\Administrator\.codex\skills\video-download\scripts\translate_srt_argos.py "D:\youtube download\OUTPUT_DIR" --overwrite
   python C:\Users\Administrator\.codex\skills\video-download\scripts\mux_subtitles.py "D:\youtube download\OUTPUT_DIR" --ffmpeg "C:\path\to\ffmpeg.exe" --overwrite
   ```

## Repository Layout

- [SKILL.md](./SKILL.md): Codex skill instructions
- [agents/openai.yaml](./agents/openai.yaml): UI metadata
- [scripts/download_youtube_hd.py](./scripts/download_youtube_hd.py): video format selection and download
- [scripts/translate_srt_argos.py](./scripts/translate_srt_argos.py): local subtitle translation
- [scripts/mux_subtitles.py](./scripts/mux_subtitles.py): MKV subtitle muxing
- [scripts/test_download_youtube_hd.py](./scripts/test_download_youtube_hd.py): download workflow tests
- [scripts/test_subtitle_workflow.py](./scripts/test_subtitle_workflow.py): subtitle workflow tests

## Environment Setup

Use Windows PowerShell.

### 1. Python

```powershell
python --version
python -m pip --version
```

### 2. yt-dlp

```powershell
python -m pip install -U yt-dlp
python -m yt_dlp --version
```

### 3. ffmpeg and ffprobe

If `ffmpeg` is already on `PATH`:

```powershell
ffmpeg -version
ffprobe -version
```

If not, download a Windows static build and pass it explicitly:

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

### 4. Local subtitle translation

Install Argos Translate:

```powershell
python -m pip install -U argostranslate
```

Install the English to Chinese local model:

```powershell
python -c "import argostranslate.package as p; p.update_package_index(); pkg=next(pkg for pkg in p.get_available_packages() if pkg.from_code=='en' and pkg.to_code=='zh'); path=pkg.download(); p.install_from_path(path)"
```

Verify it:

```powershell
python -c "import argostranslate.translate as t; print(t.translate('Hello world', 'en', 'zh'))"
```

### 5. Recommended verification

Before first use, verify the three hard dependencies:

```powershell
python -m yt_dlp --version
ffmpeg -version
python -c "import argostranslate.translate as t; print(t.translate('test', 'en', 'zh'))"
```

## Core Rules

- Download only one video stream.
- If `1080p` exists, use only `1080p`.
- If `1080p` does not exist, use the best available stream at `720p` or higher.
- Never silently default bitrate/compression preference in non-interactive or batch mode.
- Require an explicit choice between `highest-bitrate` and `efficient`.
- For subtitle workflows, prefer downloading `en-GB` first, then translate locally.
- Avoid requesting many subtitle languages in one batch because YouTube often returns `HTTP 429`.
- If the source video has no subtitle track, this workflow cannot fabricate YouTube-style translated CC. In that case, switch to a separate transcription workflow.

## End-to-End Example

### 1. Inspect formats first

```powershell
python C:\Users\Administrator\.codex\skills\video-download\scripts\download_youtube_hd.py "https://www.youtube.com/watch?v=VIDEO_ID" --list-only --video-preference ask --ffmpeg-location "C:\tools\ffmpeg\ffmpeg-<version>-essentials_build\bin"
```

### 2. Download the final video

Quality-first:

```powershell
python C:\Users\Administrator\.codex\skills\video-download\scripts\download_youtube_hd.py "https://www.youtube.com/watch?v=VIDEO_ID" --video-preference highest-bitrate --ffmpeg-location "C:\tools\ffmpeg\ffmpeg-<version>-essentials_build\bin" -o "D:\youtube download"
```

Storage-first:

```powershell
python C:\Users\Administrator\.codex\skills\video-download\scripts\download_youtube_hd.py "https://www.youtube.com/watch?v=VIDEO_ID" --video-preference efficient --ffmpeg-location "C:\tools\ffmpeg\ffmpeg-<version>-essentials_build\bin" -o "D:\youtube download"
```

### 3. Download English subtitles separately

```powershell
python -m yt_dlp --skip-download --write-subs --sub-langs "en-GB" --sub-format "srt" --sleep-interval 25 --max-sleep-interval 40 -P "D:\youtube download" -o "%(playlist_index)02d - %(title).200B [%(id)s].%(ext)s" "https://www.youtube.com/watch?v=VIDEO_ID"
```

### 4. Translate and mux

```powershell
python C:\Users\Administrator\.codex\skills\video-download\scripts\translate_srt_argos.py "D:\youtube download" --overwrite
python C:\Users\Administrator\.codex\skills\video-download\scripts\mux_subtitles.py "D:\youtube download" --ffmpeg "C:\tools\ffmpeg\ffmpeg-<version>-essentials_build\bin\ffmpeg.exe" --overwrite
```

### 5. Expected output

After a successful run, the directory normally contains:

- original merged video file such as `.mp4` or `.mkv`
- original English subtitle file such as `.en-GB.srt`
- local Chinese subtitle file such as `.zh-Hans.local.srt`
- final subtitle-muxed file under `with-subs\*.mkv`

## Common Commands

### Inspect formats without downloading

```powershell
python .\scripts\download_youtube_hd.py "YOUTUBE_URL" --list-only --video-preference ask --ffmpeg-location "C:\path\to\ffmpeg\bin"
```

### Download quality-first version

```powershell
python .\scripts\download_youtube_hd.py "YOUTUBE_URL" --video-preference highest-bitrate --ffmpeg-location "C:\path\to\ffmpeg\bin"
```

### Download smaller, more efficient version

```powershell
python .\scripts\download_youtube_hd.py "YOUTUBE_URL" --video-preference efficient --ffmpeg-location "C:\path\to\ffmpeg\bin"
```

### Translate English subtitles locally

```powershell
python .\scripts\translate_srt_argos.py "OUTPUT_DIR" --overwrite
```

### Mux subtitles into MKV

```powershell
python .\scripts\mux_subtitles.py "OUTPUT_DIR" --ffmpeg "C:\path\to\ffmpeg.exe" --overwrite
```

## Subtitle Workflow

Recommended order:

1. Download video
2. Download English subtitles with `yt-dlp`
3. Translate English subtitles locally to `zh-Hans.local.srt`
4. Mux video + Chinese subtitle + English subtitle into `.mkv`

The muxing workflow:

- keeps original `.mp4`
- keeps original `.en-GB.srt`
- keeps local `.zh-Hans.local.srt`
- writes new `.with-subs.mkv` files to `with-subs/`
- sets Chinese as the default subtitle track
- sets English as the secondary subtitle track
- does not re-encode video or audio

If the source video does not provide an English subtitle track, the translation and muxing flow cannot produce equivalent YouTube CC subtitles from nothing. That case needs a separate speech-to-text pipeline, which is outside this skill's default workflow.

## Bitrate Preference

The same `1080p` label can point to very different streams. Resolution only tells you the pixel dimensions, not the compression level.

- `highest-bitrate`
  - use when the user wants the least compressed source within the chosen resolution
  - tends to create much larger files
  - often prefers AVC or another less efficient stream when it preserves more bits
- `efficient`
  - use when the user wants a smaller file at the same resolution
  - tends to prefer newer codecs such as AV1 when available
  - file size can be much smaller even though the video is still `1080p`

This is why two downloaded `1080p` files can differ a lot in size.

## Tests

```powershell
python .\scripts\test_download_youtube_hd.py
python .\scripts\test_subtitle_workflow.py
```

## Troubleshooting

### Two `1080p` files have very different sizes

That is normal. They may use different codecs, bitrates, frame rates, or compression profiles. The workflow now forces a user choice between `highest-bitrate` and `efficient` so this tradeoff is explicit.

### Why English subtitles first instead of direct Chinese subtitles

Direct translated subtitle fetching from YouTube is much more likely to hit throttling, especially in playlists. Pulling one English subtitle track first and translating locally is slower but more stable.

### Can subtitles be integrated into the video file

Yes. `scripts/mux_subtitles.py` creates a new `.mkv` file with soft subtitles. Video and audio are copied without re-encoding.

### Why no silent default for bitrate preference

Because `1080p` alone is not enough to decide the correct stream. For the same resolution, users may want either better source quality or smaller output size. The workflow must ask or require an explicit flag.

### What happens when the video has no subtitles

This workflow depends on an existing English subtitle track. If YouTube does not provide one, local translation cannot start. The scripts now fail explicitly and tell the operator to move to a separate transcription workflow instead of pretending the normal CC translation flow still applies.

## Branch Naming

`master` and `main` are both valid Git branch names.

Changing `master` to `main` usually means:

- using the newer default branch naming convention
- making the repository consistent with most new GitHub repositories
- reducing future confusion when integrations assume `main`

It does **not** change code behavior. It only changes the default branch name and related Git references.
