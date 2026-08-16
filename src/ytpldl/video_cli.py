"""Command-line entry point for the single-video downloader (``ytvid``)."""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional

from ytpldl import __version__
from ytpldl.deps import (
    JS_RUNTIME_HINT,
    MissingDependencyError,
    check_dependencies,
    detect_js_runtime,
)
from ytpldl.sources import ExtractionError
from ytpldl.video import download_video


def default_videos_dir() -> str:
    """The user's Videos folder (cross-platform)."""
    return os.path.join(os.path.expanduser("~"), "Videos")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ytvid",
        description=(
            "Download a single YouTube video as a Full HD (1080p) mp4 into your "
            "Videos folder. Uses H.264 for maximum compatibility and downloads "
            "in chunks to avoid YouTube's mid-download HTTP 403 throttling."
        ),
    )
    p.add_argument("url", nargs="?", help="YouTube video URL (prompted if omitted)")
    p.add_argument(
        "-o", "--output", default=None, metavar="DIR",
        help="destination folder (default: your Videos folder)",
    )
    p.add_argument(
        "--max-height", type=int, default=1080, metavar="PX",
        help="cap video height, e.g. 1080 (default), 720, 480",
    )
    p.add_argument(
        "--any-codec", action="store_true",
        help="allow VP9/AV1 (smaller/higher-res) instead of preferring H.264; "
             "may need extra codecs to play",
    )
    p.add_argument(
        "--cookies-from-browser", metavar="BROWSER", default=None,
        help="use a browser's cookies (chrome/firefox/edge) if a video still "
             "403s; close the browser first",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def _prompt_url() -> str:
    try:
        return input("Enter YouTube video URL: ").strip()
    except EOFError:
        return ""


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        check_dependencies()
    except MissingDependencyError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if detect_js_runtime() is None:
        print(f"Warning: {JS_RUNTIME_HINT}\n", file=sys.stderr)

    url = args.url or _prompt_url()
    if not url:
        print("No video URL provided.", file=sys.stderr)
        return 2

    output_dir = args.output or default_videos_dir()

    print(f"Downloading up to {args.max_height}p -> {output_dir}")
    try:
        path = download_video(
            url,
            output_dir,
            max_height=args.max_height,
            cookies_from_browser=args.cookies_from_browser,
            prefer_h264=not args.any_codec,
        )
    except ExtractionError as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"\nError: download failed: {exc}", file=sys.stderr)
        return 1

    print(f"\nSaved: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
