"""Turn messy YouTube titles into clean, filesystem-safe filenames."""

from __future__ import annotations

import re

# Windows-illegal filename characters (also unsafe to keep on other OSes).
_ILLEGAL = re.compile(r'[\\/:*?"<>|]')

# Reserved device names on Windows.
_RESERVED = {
    "con", "prn", "aux", "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}

# Keywords that, when found inside a (...) or [...] group, mark that group as
# junk to strip from the *display filename* (not from matching).
_JUNK_KEYWORDS = [
    "official music video",
    "official video",
    "official audio",
    "official lyric video",
    "official lyrics video",
    "official visualizer",
    "official hd video",
    "lyric video",
    "lyrics video",
    "visualizer",
    "audio only",
    "full audio",
    "hd audio",
    "hq audio",
    "free download",
    "free dl",
    "out now",
    "hd",
    "hq",
    "4k",
    "mv",
    "m/v",
]

_BRACKET_GROUP = re.compile(r"[\(\[\{]([^\(\)\[\]\{\}]*)[\)\]\}]")

# Trailing " [dQw4w9WgXcQ]" style 11-char YouTube id tags.
_YT_ID_TAG = re.compile(r"\s*[\[\(]([A-Za-z0-9_-]{11})[\]\)]\s*$")


def _looks_like_junk(inner: str) -> bool:
    low = inner.strip().lower()
    if not low:
        return True
    return any(kw in low for kw in _JUNK_KEYWORDS)


def clean_title(title: str) -> str:
    """Strip YouTube id tags and promotional junk from a title.

    Keeps meaningful parenthetical content (e.g. ``(Extended Mix)``,
    ``(feat. X)``, ``(XYZ Remix)``) while removing things like
    ``(Official Video)`` or a trailing ``[videoID]``.
    """
    text = title or ""

    # Drop a trailing bare YouTube id tag.
    text = _YT_ID_TAG.sub("", text)

    # Remove bracket groups that are purely promotional junk.
    def _replace(match: "re.Match[str]") -> str:
        return "" if _looks_like_junk(match.group(1)) else match.group(0)

    prev = None
    while prev != text:
        prev = text
        text = _BRACKET_GROUP.sub(_replace, text)

    # Collapse whitespace and tidy dangling separators.
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s*[-–—|]\s*$", "", text).strip()
    text = re.sub(r"^\s*[-–—|]\s*", "", text).strip()
    return text


def sanitize_filename(name: str, max_length: int = 180) -> str:
    """Make a string safe to use as a single path component."""
    text = _ILLEGAL.sub("", name or "")
    text = text.replace("\0", "")
    text = re.sub(r"\s+", " ", text).strip()
    # Trailing dots/spaces are illegal on Windows.
    text = text.rstrip(" .")

    if not text:
        text = "untitled"

    if text.lower() in _RESERVED:
        text = f"_{text}"

    if len(text) > max_length:
        text = text[:max_length].rstrip(" .")

    return text


def output_filename(clean: str, index: int, number: bool) -> str:
    """Compose the final ``.wav`` filename for a track."""
    base = sanitize_filename(clean)
    if number:
        return f"{index:02d} - {base}.wav"
    return f"{base}.wav"
