"""Download a single YouTube video as a Full HD (1080p) mp4.

Bakes in the settings that make YouTube downloads reliable:
  * a JavaScript runtime (deno/node/bun) so yt-dlp can solve YouTube's
    signature / "n" challenges (otherwise extraction 403s),
  * 10 MiB ranged HTTP chunks so a long transfer of a large file can't be
    killed by YouTube's mid-download throttling (the classic "403 at N%"),
  * generous retries, and
  * an H.264 + AAC -> mp4 selection capped at 1080p, which plays everywhere
    (unlike 4K, which YouTube only serves as AV1/VP9 needing special codecs).
"""

from __future__ import annotations

import os
import time
from typing import Optional

from yt_dlp import YoutubeDL

from ytpldl.sources import JS_RUNTIMES, ExtractionError

# 10 MiB ranged chunks: short-lived requests dodge throttle-based 403s.
_HTTP_CHUNK = 10 * 1024 * 1024


def build_format(max_height: int = 1080, prefer_h264: bool = True) -> str:
    """Build a yt-dlp format selector capped at ``max_height``.

    When ``prefer_h264`` is True (default), prefer the H.264 video + m4a audio
    combo that muxes into a universally-playable mp4, falling back to the best
    available streams at that height, then to any progressive stream.
    """
    if prefer_h264:
        return (
            f"bv*[height<={max_height}][vcodec^=avc1]+ba[ext=m4a]/"
            f"bv*[height<={max_height}]+ba/"
            f"b[height<={max_height}]/b"
        )
    return f"bv*[height<={max_height}]+ba/b[height<={max_height}]/b"


def download_video(
    url: str,
    output_dir: str,
    max_height: int = 1080,
    cookies_from_browser: Optional[str] = None,
    prefer_h264: bool = True,
    attempts: int = 3,
    quiet: bool = False,
) -> str:
    """Download ``url`` into ``output_dir`` and return the final mp4 path."""
    os.makedirs(output_dir, exist_ok=True)
    outtmpl = os.path.join(output_dir, "%(title)s [%(id)s].%(ext)s")

    opts = {
        "format": build_format(max_height, prefer_h264),
        "merge_output_format": "mp4",
        "outtmpl": outtmpl,
        "js_runtimes": JS_RUNTIMES,
        "http_chunk_size": _HTTP_CHUNK,
        "retries": 10,
        "fragment_retries": 10,
        "extractor_retries": 3,
        "no_warnings": True,
        "quiet": quiet,
        "noprogress": quiet,
        "ignoreerrors": False,
    }
    if cookies_from_browser:
        opts["cookiesfrombrowser"] = (cookies_from_browser,)

    last_err: Optional[Exception] = None
    for attempt in range(1, attempts + 1):
        try:
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
            return _final_path(ydl, info, output_dir)
        except Exception as exc:  # re-extract fresh on transient 403s
            last_err = exc
            if attempt < attempts:
                time.sleep(3 * attempt)

    raise last_err or ExtractionError("video download failed after retries")


def _final_path(ydl: "YoutubeDL", info: dict, output_dir: str) -> str:
    """Resolve the merged output file's path from yt-dlp's result."""
    if info:
        requested = info.get("requested_downloads") or []
        if requested and requested[0].get("filepath"):
            return requested[0]["filepath"]
        try:
            base = ydl.prepare_filename(info)
            merged = os.path.splitext(base)[0] + ".mp4"
            if os.path.exists(merged):
                return merged
            if os.path.exists(base):
                return base
        except Exception:
            pass
    return output_dir
