"""Command-line entry point for yt-pldl."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from ytpldl import __version__
from ytpldl.config import Config
from ytpldl.deps import (
    JS_RUNTIME_HINT,
    MissingDependencyError,
    check_dependencies,
    detect_js_runtime,
)
from ytpldl.pipeline import run
from ytpldl.sources import ExtractionError

_KHZ_TO_HZ = {44: 44100, 48: 48000, 88: 88200, 96: 96000, 176: 176400, 192: 192000}


def _parse_wav_format(value: str) -> "tuple[int, int]":
    """Parse a ``bits/khz`` string like ``24/48`` into (bit_depth, sample_rate)."""
    try:
        bits_s, khz_s = value.lower().replace("k", "").split("/")
        bits = int(bits_s)
        khz = int(khz_s)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"invalid wav format '{value}' (expected e.g. 24/48 or 16/44)"
        )
    if bits not in (16, 24, 32):
        raise argparse.ArgumentTypeError("bit depth must be 16, 24 or 32")
    sample_rate = _KHZ_TO_HZ.get(khz, khz * 1000)
    return bits, sample_rate


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ytpldl",
        description=(
            "Download a YouTube playlist as high-resolution WAVs. In auto mode, "
            "each track is upgraded to a free lossless SoundCloud download when "
            "a strongly-matching, unaltered version exists; otherwise YouTube is "
            "used."
        ),
    )
    p.add_argument("url", nargs="?", help="YouTube playlist URL (prompted if omitted)")
    p.add_argument(
        "--source", choices=["auto", "youtube"], default="auto",
        help="auto: try lossless SoundCloud upgrades (default); youtube: YouTube only",
    )
    p.add_argument(
        "--extended", action="store_true",
        help="allow/prefer extended mixes when upgrading from SoundCloud",
    )
    p.add_argument(
        "--wav-format", type=_parse_wav_format, default="24/48", metavar="BITS/KHZ",
        help="output PCM format for YouTube audio, e.g. 24/48 (default) or 16/44",
    )
    p.add_argument(
        "--no-preserve-native", action="store_true",
        help="downsample lossless SoundCloud sources to --wav-format instead of "
             "keeping their native rate",
    )
    p.add_argument(
        "--sc-tolerance", type=float, default=3.0, metavar="SEC",
        help="allowed duration difference for a SoundCloud match (default: 3)",
    )
    p.add_argument(
        "--sc-results", type=int, default=5, metavar="N",
        help="SoundCloud search results to inspect per track (default: 5)",
    )
    p.add_argument(
        "-o", "--output", default=".", metavar="DIR",
        help="directory to create the playlist folder in (default: current dir)",
    )
    p.add_argument(
        "--no-number", action="store_true",
        help="do not prefix filenames with the playlist track number",
    )
    p.add_argument(
        "--cookies-from-browser", metavar="BROWSER", default=None,
        help="pull YouTube cookies from a browser (e.g. chrome, firefox, edge) "
             "to avoid HTTP 403 on stubborn videos; close the browser first",
    )
    p.add_argument("--keep-temp", action="store_true", help="keep intermediate files")
    p.add_argument(
        "-y", "--yes", action="store_true",
        help="skip the interactive 'is this playlist public?' confirmation",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def _prompt_url() -> str:
    try:
        return input("Enter YouTube playlist URL: ").strip()
    except EOFError:
        return ""


def _confirm_public() -> bool:
    print(
        "\nBefore continuing: make sure this playlist is PUBLIC or UNLISTED.\n"
        "Private playlists cannot be downloaded without your account and will fail."
    )
    try:
        answer = input("Is the playlist public/unlisted? [y/N]: ").strip().lower()
    except EOFError:
        return False
    return answer in ("y", "yes")


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
        print("No playlist URL provided.", file=sys.stderr)
        return 2

    if not args.yes and not _confirm_public():
        print("Aborted.")
        return 1

    bit_depth, sample_rate = (
        args.wav_format if isinstance(args.wav_format, tuple)
        else _parse_wav_format(args.wav_format)
    )

    cfg = Config(
        source=args.source,
        extended=args.extended,
        bit_depth=bit_depth,
        sample_rate=sample_rate,
        preserve_native=not args.no_preserve_native,
        sc_tolerance=args.sc_tolerance,
        sc_search_n=args.sc_results,
        output_dir=args.output,
        keep_temp=args.keep_temp,
        number=not args.no_number,
        assume_yes=args.yes,
        cookies_from_browser=args.cookies_from_browser,
    )

    try:
        summary = run(url, cfg)
    except ExtractionError as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130

    return 0 if not summary.failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
