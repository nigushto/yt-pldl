"""Thin wrappers around yt-dlp for extraction, search and download."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from yt_dlp import YoutubeDL

# Free-download originals we treat as genuinely lossless.
LOSSLESS_EXTS = {"wav", "flac", "aif", "aiff", "alac"}

_QUIET_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "noprogress": True,
    "ignoreerrors": True,
}


class ExtractionError(RuntimeError):
    """Raised when yt-dlp cannot extract usable info from a URL."""


def _watch_url(entry: Dict[str, Any]) -> str:
    url = entry.get("url") or entry.get("webpage_url")
    if url and str(url).startswith("http"):
        return str(url)
    vid = entry.get("id")
    if vid:
        return f"https://www.youtube.com/watch?v={vid}"
    raise ExtractionError("playlist entry has no resolvable URL")


def extract_playlist(url: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Return (playlist_title, flat_entries) for a playlist URL."""
    opts = {**_QUIET_OPTS, "extract_flat": True, "skip_download": True}
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        raise ExtractionError(
            "Could not read the playlist. Double-check the URL and that the "
            "playlist is Public or Unlisted (not Private)."
        )

    entries = [e for e in (info.get("entries") or []) if e]
    if not entries:
        raise ExtractionError(
            "The playlist appears to be empty or inaccessible (it may be "
            "Private, region-locked, or the URL may point to a single video)."
        )

    title = info.get("title") or info.get("id") or "playlist"
    return title, entries


def extract_track(entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Full (non-flat) metadata for a single playlist entry."""
    url = _watch_url(entry)
    opts = {**_QUIET_OPTS, "skip_download": True}
    with YoutubeDL(opts) as ydl:
        try:
            return ydl.extract_info(url, download=False)
        except Exception:  # pragma: no cover - network/availability dependent
            return None


def parse_artist_title(info: Dict[str, Any]) -> Tuple[str, str]:
    """Best-effort (artist, title) split for a YouTube track."""
    artist = info.get("artist") or info.get("creator") or ""
    track = info.get("track") or ""
    if artist and track:
        return artist.strip(), track.strip()

    title = info.get("title") or ""
    # Common "Artist - Title" convention.
    for sep in (" - ", " – ", " — "):
        if sep in title:
            left, right = title.split(sep, 1)
            return left.strip(), right.strip()

    fallback_artist = info.get("uploader") or info.get("channel") or ""
    return fallback_artist.strip(), title.strip()


def search_soundcloud(query: str, n: int) -> List[Dict[str, Any]]:
    """Full-extract the top ``n`` SoundCloud results for ``query``.

    Non-flat so each entry carries ``formats``, ``duration`` and ``uploader``.
    """
    opts = {**_QUIET_OPTS, "skip_download": True}
    with YoutubeDL(opts) as ydl:
        try:
            info = ydl.extract_info(f"scsearch{n}:{query}", download=False)
        except Exception:  # pragma: no cover - network dependent
            return []
    if not info:
        return []
    return [e for e in (info.get("entries") or []) if e]


def find_lossless_download(entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return the artist-enabled original download format if it's lossless.

    SoundCloud exposes an artist-enabled free download as a format whose id or
    note mentions "download"/"original". We only accept it when its container
    extension is lossless; a 320 kbps MP3 original is ignored so the run falls
    back to YouTube.
    """
    for fmt in entry.get("formats") or []:
        fid = str(fmt.get("format_id") or "").lower()
        note = str(fmt.get("format_note") or "").lower()
        ext = str(fmt.get("ext") or "").lower()
        is_original = "download" in fid or "original" in fid or note in {"original", "download"}
        if is_original and ext in LOSSLESS_EXTS:
            return fmt
    return None


def _pick_single_output(tempdir: str, before: set) -> str:
    after = set(os.listdir(tempdir))
    new = [f for f in (after - before) if not f.endswith(".part")]
    if not new:
        raise ExtractionError("download produced no output file")
    # Largest new file is the media file.
    new.sort(key=lambda f: os.path.getsize(os.path.join(tempdir, f)), reverse=True)
    return os.path.join(tempdir, new[0])


def download_youtube(url: str, tempdir: str) -> str:
    """Download the best audio-only stream (Opus) into tempdir; return path."""
    before = set(os.listdir(tempdir))
    outtmpl = os.path.join(tempdir, "%(id)s.%(ext)s")
    opts = {
        **_QUIET_OPTS,
        "ignoreerrors": False,
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
    }
    with YoutubeDL(opts) as ydl:
        ydl.extract_info(url, download=True)
    return _pick_single_output(tempdir, before)


def download_soundcloud(url: str, format_id: str, tempdir: str) -> str:
    """Download a specific SoundCloud format (the lossless original)."""
    before = set(os.listdir(tempdir))
    outtmpl = os.path.join(tempdir, "sc_%(id)s.%(ext)s")
    opts = {
        **_QUIET_OPTS,
        "ignoreerrors": False,
        "format": format_id,
        "outtmpl": outtmpl,
    }
    with YoutubeDL(opts) as ydl:
        ydl.extract_info(url, download=True)
    return _pick_single_output(tempdir, before)
