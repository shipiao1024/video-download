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
curl.exe -L "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -o "TOOLS_DIR\ffmpeg-release-essentials.zip"
Expand-Archive -LiteralPath "TOOLS_DIR\ffmpeg-release-essentials.zip" -DestinationPath "TOOLS_DIR\ffmpeg" -Force
```

Then use:

```powershell
--ffmpeg-location "TOOLS_DIR\ffmpeg\ffmpeg-<version>-essentials_build\bin"
--ffmpeg "TOOLS_DIR\ffmpeg\ffmpeg-<version>-essentials_build\bin\ffmpeg.exe"
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

## Core Rules

- Download only one video stream.
- If `1080p` exists, use only `1080p`.
- If `1080p` does not exist, use the best available stream at `720p` or higher.
- Never silently default bitrate/compression preference in non-interactive or batch mode.
- Ask the user to choose:
  - `highest-bitrate`
  - `efficient`
- For subtitle workflows, prefer downloading `en-GB` first, then translate locally.
- Avoid requesting many subtitle languages in one batch because YouTube often returns `HTTP 429`.

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

## Tests

```powershell
python .\scripts\test_download_youtube_hd.py
python .\scripts\test_subtitle_workflow.py
```

## Branch Naming

`master` and `main` are both valid Git branch names.

Changing `master` to `main` usually means:

- using the newer default branch naming convention
- making the repository consistent with most new GitHub repositories
- reducing future confusion when integrations assume `main`

It does **not** change code behavior. It only changes the default branch name and related Git references.
