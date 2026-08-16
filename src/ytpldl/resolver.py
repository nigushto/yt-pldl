"""Decide, per track, whether to upgrade to a lossless SoundCloud download."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ytpldl import matching
from ytpldl.config import Config
from ytpldl import sources


@dataclass
class SoundCloudPick:
    """A qualifying SoundCloud candidate chosen to replace YouTube audio."""

    url: str
    format_id: str
    ext: str
    title: str
    score: int


def _candidate_artist(entry: Dict[str, Any]) -> str:
    return entry.get("uploader") or entry.get("uploader_id") or ""


def qualifies(
    entry: Dict[str, Any],
    yt_artist: str,
    yt_title: str,
    yt_duration: Optional[float],
    cfg: Config,
) -> Optional[SoundCloudPick]:
    """Return a SoundCloudPick if ``entry`` clears every gate, else None."""
    # (e) Lossless gate first — cheapest way to reject most results.
    fmt = sources.find_lossless_download(entry)
    if fmt is None:
        return None

    cand_title = entry.get("title") or ""
    cand_artist = _candidate_artist(entry)
    cand_duration = entry.get("duration")

    # (d) Variant guard — never accept an altered version.
    conflict = matching.variant_conflict(yt_title, cand_title, cfg.extended)
    if conflict is not None:
        return None

    # (a) Artist match.
    if matching.artist_similarity(yt_artist, cand_artist, cand_title) < cfg.artist_threshold:
        return None

    # (b) Title match — require a higher bar when duration is unknown.
    title_score = matching.title_similarity(yt_title, cand_title)
    duration_known = bool(yt_duration and cand_duration)
    title_bar = cfg.title_threshold if duration_known else max(cfg.title_threshold, 90)
    if title_score < title_bar:
        return None

    # (c) Duration match.
    ok, _reason = matching.duration_ok(
        yt_duration, cand_duration, cfg.sc_tolerance, cfg.extended
    )
    if not ok:
        return None

    return SoundCloudPick(
        url=entry.get("webpage_url") or entry.get("url") or "",
        format_id=str(fmt.get("format_id")),
        ext=str(fmt.get("ext") or "wav"),
        title=cand_title,
        score=title_score,
    )


def resolve_source(
    yt_artist: str,
    yt_title: str,
    yt_duration: Optional[float],
    cfg: Config,
) -> Optional[SoundCloudPick]:
    """Search SoundCloud and return the best qualifying lossless pick, if any.

    Returns None to mean "download from YouTube" — either because ``source`` is
    ``youtube`` or because nothing on SoundCloud cleared the bar.
    """
    if cfg.source == "youtube":
        return None

    query = f"{yt_artist} {yt_title}".strip()
    if cfg.extended:
        query = f"{query} extended mix"

    entries = sources.search_soundcloud(query, cfg.sc_search_n)

    picks: List[SoundCloudPick] = []
    for entry in entries:
        pick = qualifies(entry, yt_artist, yt_title, yt_duration, cfg)
        if pick is not None:
            picks.append(pick)

    if not picks:
        return None

    # Best title score wins; ties broken toward the earliest (most relevant)
    # search result, which is already the input order.
    picks.sort(key=lambda p: p.score, reverse=True)
    return picks[0]
