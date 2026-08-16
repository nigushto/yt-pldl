"""Checks for the external tools yt-pldl shells out to."""

from __future__ import annotations

import shutil
from typing import List


class MissingDependencyError(RuntimeError):
    """Raised when a required external executable is not on PATH."""


def _find(name: str) -> bool:
    return shutil.which(name) is not None


def check_dependencies() -> None:
    """Verify that ffmpeg (and ffprobe) are available.

    yt-dlp itself is imported as a Python library, so it does not need to be on
    PATH, but ffmpeg is required for the WAV conversion step.
    """
    missing: List[str] = []
    if not _find("ffmpeg"):
        missing.append("ffmpeg")
    if not _find("ffprobe"):
        missing.append("ffprobe")

    if missing:
        joined = ", ".join(missing)
        raise MissingDependencyError(
            f"Required tool(s) not found on PATH: {joined}.\n"
            "Install ffmpeg (which includes ffprobe):\n"
            "  Windows:  winget install Gyan.FFmpeg   (or:  choco install ffmpeg)\n"
            "  macOS:    brew install ffmpeg\n"
            "  Linux:    sudo apt install ffmpeg\n"
            "Then re-run the command."
        )
