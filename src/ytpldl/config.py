"""Runtime configuration for a yt-pldl run."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Everything that steers a single download run.

    Attributes:
        source: ``"auto"`` tries a lossless SoundCloud upgrade per track and
            falls back to YouTube; ``"youtube"`` never touches SoundCloud.
        extended: If True, allow/prefer extended mixes when upgrading from
            SoundCloud. Off by default so runs never silently swap in a longer
            cut than the one queued from YouTube.
        bit_depth: PCM bit depth for the output WAV (16, 24 or 32).
        sample_rate: Target sample rate in Hz for YouTube-sourced audio.
        preserve_native: For lossless SoundCloud sources, keep the file's
            native sample rate / bit depth instead of resampling to the target.
        sc_tolerance: Allowed duration difference (seconds) between the YouTube
            track and a SoundCloud candidate.
        sc_search_n: How many SoundCloud search results to inspect per track.
        artist_threshold / title_threshold: Fuzzy-match cut-offs (0-100).
        output_dir: Where the final ``<Playlist Name>/`` folder is created.
        temp_dir: Scratch folder for intermediate files (auto-created if None).
        keep_temp: Keep the temp folder instead of deleting it at the end.
        number: Prefix output filenames with the playlist index to keep order.
        assume_yes: Skip the interactive "is this playlist public?" prompt.
    """

    source: str = "auto"  # "auto" | "youtube"
    extended: bool = False

    bit_depth: int = 24
    sample_rate: int = 48000
    preserve_native: bool = True

    sc_tolerance: float = 3.0
    sc_search_n: int = 5
    artist_threshold: int = 80
    title_threshold: int = 82

    output_dir: str = "."
    temp_dir: Optional[str] = None
    keep_temp: bool = False
    number: bool = True
    assume_yes: bool = False
