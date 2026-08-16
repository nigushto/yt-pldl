"""yt-pldl: download a YouTube playlist as high-resolution WAVs.

The YouTube playlist is always the master queue. When ``source="auto"`` each
track is optionally upgraded to a genuinely lossless free download from
SoundCloud, but only when artist + title + duration match strongly and the
SoundCloud version is not an altered variant (remix/flip/edit/...).
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
