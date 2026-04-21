MISSING_SOURCE_SUBTITLE_MESSAGE = (
    "No .en-GB.srt files found. The default subtitle translation workflow requires "
    "an existing English subtitle track and cannot recreate YouTube-style translated CC. "
    "Use a separate transcription workflow instead."
)


def missing_subtitle_message(video_name: str, missing_kind: str) -> str:
    return (
        f"Missing {missing_kind} subtitle for {video_name}. "
        "The default subtitle workflow requires source English subtitles plus local Chinese translation. "
        "If the source video has no subtitle track, use a separate transcription workflow instead."
    )
