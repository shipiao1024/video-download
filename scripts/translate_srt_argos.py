#!/usr/bin/env python
import argparse
import re
from pathlib import Path

import argostranslate.translate


TIMESTAMP_RE = re.compile(r"^\d\d:\d\d:\d\d,\d\d\d\s+-->\s+\d\d:\d\d:\d\d,\d\d\d")


def translate_srt_text(text: str, from_code: str = "en", to_code: str = "zh") -> str:
    lines = text.splitlines()
    out = []
    block = []

    def flush_block():
        if not block:
            return
        source = " ".join(line.strip() for line in block if line.strip())
        if source:
            out.append(argostranslate.translate.translate(source, from_code, to_code))
        block.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_block()
            out.append("")
        elif stripped.isdigit() or TIMESTAMP_RE.match(stripped):
            flush_block()
            out.append(line)
        else:
            block.append(line)

    flush_block()
    return "\n".join(out).rstrip() + "\n"


def collect_srt_files(paths):
    files = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            files.extend(sorted(path.glob("*.en-GB.srt")))
        else:
            files.append(path)
    return files


def main():
    parser = argparse.ArgumentParser(description="Translate en-GB SRT subtitles to local zh-Hans SRT with Argos Translate.")
    parser.add_argument("paths", nargs="+", help="SRT files or directories")
    parser.add_argument("--suffix", default=".zh-Hans.local.srt")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    files = collect_srt_files(args.paths)
    if not files:
        raise SystemExit("No .en-GB.srt files found.")

    for src in files:
        dst = src.with_name(src.name.removesuffix(".en-GB.srt") + args.suffix)
        if dst.exists() and not args.overwrite:
            print(f"skip exists: {dst}")
            continue
        print(f"translate: {src.name} -> {dst.name}")
        translated = translate_srt_text(src.read_text(encoding="utf-8-sig"))
        dst.write_text(translated, encoding="utf-8")


if __name__ == "__main__":
    main()
