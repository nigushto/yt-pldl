"""Fuzzy matching + variant detection used by the source resolver.

These functions decide whether a SoundCloud candidate is *the same intended
track* as the YouTube one. The bar is deliberately high: a remix/flip/edit on
SoundCloud must never be substituted for an unaltered YouTube track.
"""

from __future__ import annotations

import re
from typing import Optional, Set, Tuple

from rapidfuzz import fuzz

# Canonical variant markers. If a SoundCloud title carries one of these and the
# YouTube title does NOT, the candidate is an altered version and is rejected.
# ``extended`` is handled specially by the resolver (opt-in via --extended).
_VARIANT_PATTERNS = {
    "remix": r"\bremix(es)?\b",
    "flip": r"\bflip\b",
    "edit": r"\bedit\b",
    "bootleg": r"\bbootleg\b",
    "vip": r"\bvip\b",
    "mashup": r"\bmash[\s-]?up\b",
    "rework": r"\brework\b",
    "cover": r"\bcover\b",
    "remake": r"\bremake\b",
    "nightcore": r"\bnightcore\b",
    "sped up": r"\bsped[\s-]?up\b",
    "slowed": r"\bslowed\b",
    "reverb": r"\breverb\b",
    "acoustic": r"\bacoustic\b",
    "instrumental": r"\binstrumental\b",
    "live": r"\blive\b",
    "karaoke": r"\bkaraoke\b",
    "reprise": r"\breprise\b",
    "dub": r"\bdub\b",
    "radio edit": r"\bradio[\s-]?edit\b",
    "club mix": r"\bclub[\s-]?mix\b",
    "extended": r"\bextended\b",
}
_VARIANT_COMPILED = {k: re.compile(v, re.IGNORECASE) for k, v in _VARIANT_PATTERNS.items()}

_BRACKETS = re.compile(r"[\(\[\{][^\(\)\[\]\{\}]*[\)\]\}]")
_FEAT = re.compile(r"\b(feat\.?|ft\.?|featuring)\b.*", re.IGNORECASE)
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def detect_variants(text: str) -> Set[str]:
    """Return the set of variant markers present in a title."""
    return {name for name, rx in _VARIANT_COMPILED.items() if rx.search(text or "")}


def core_title(text: str) -> str:
    """Reduce a title to its core song name for similarity comparison.

    Strips bracketed groups, ``feat.`` clauses and all variant words so that
    ``"Song (XYZ Remix) [Official Video]"`` and ``"Song"`` compare as equal.
    """
    s = (text or "").lower()
    s = _BRACKETS.sub(" ", s)
    s = _FEAT.sub(" ", s)
    for rx in _VARIANT_COMPILED.values():
        s = rx.sub(" ", s)
    s = _NON_ALNUM.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def _norm(text: str) -> str:
    s = (text or "").lower()
    s = _NON_ALNUM.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def title_similarity(a: str, b: str) -> int:
    """0-100 similarity of two song titles, ignoring variant/bracket noise."""
    ca, cb = core_title(a), core_title(b)
    if not ca or not cb:
        return 0
    return int(fuzz.token_set_ratio(ca, cb))


def artist_similarity(yt_artist: str, cand_artist: str, cand_title: str) -> int:
    """How strongly the YouTube artist appears in the candidate.

    SoundCloud often stores the artist in the uploader name *or* embeds it in
    the track title, so we check the YouTube artist against both.
    """
    artist = _norm(yt_artist)
    if not artist:
        return 0
    haystack = _norm(f"{cand_artist} {cand_title}")
    return int(fuzz.partial_ratio(artist, haystack))


def variant_conflict(
    yt_title: str, cand_title: str, allow_extended: bool
) -> Optional[str]:
    """Return the offending variant marker if the candidate is altered.

    A conflict exists when the candidate carries a variant marker that the
    YouTube source does not. When ``allow_extended`` is True, an ``extended``
    marker on the candidate is permitted.
    """
    yt_vars = detect_variants(yt_title)
    cand_vars = detect_variants(cand_title)
    extra = cand_vars - yt_vars
    if allow_extended:
        extra.discard("extended")
    if extra:
        # Return a stable, human-readable marker for logging.
        return sorted(extra)[0]
    return None


def duration_ok(
    yt_duration: Optional[float],
    cand_duration: Optional[float],
    tolerance: float,
    extended: bool,
) -> Tuple[bool, str]:
    """Check whether the candidate's length is acceptable.

    Returns (ok, reason). In extended mode a longer candidate is allowed;
    otherwise the durations must be within ``tolerance`` seconds.
    """
    if not yt_duration or not cand_duration:
        # Unknown duration on either side -> caller should compensate with a
        # stricter title threshold. We don't hard-fail here.
        return True, "duration-unknown"

    diff = cand_duration - yt_duration
    if extended:
        if diff >= -tolerance:  # same length or longer
            return True, "extended-ok"
        return False, f"shorter-than-source ({diff:+.0f}s)"

    if abs(diff) <= tolerance:
        return True, "within-tolerance"
    return False, f"duration-mismatch ({diff:+.0f}s)"
