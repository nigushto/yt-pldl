"""Convert any downloaded audio file to a PCM WAV via ffmpeg."""

from __future__ import annotations

import json
import subprocess
from typing import Optional, Tuple

_BITS_TO_CODEC = {16: "pcm_s16le", 24: "pcm_s24le", 32: "pcm_s32le"}


class ConversionError(RuntimeError):
    """Raised when ffmpeg fails to produce a WAV."""


def _probe(path: str) -> Tuple[Optional[int], Optional[int]]:
    """Return (sample_rate, bits_per_sample) for the first audio stream."""
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "a:0",
        "-show_entries", "stream=sample_rate,bits_per_raw_sample,bits_per_sample",
        "-of", "json", path,
    ]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(out.stdout or "{}")
        streams = data.get("streams") or []
        if not streams:
            return None, None
        s = streams[0]
        sr = s.get("sample_rate")
        bits = s.get("bits_per_raw_sample") or s.get("bits_per_sample")
        sr = int(sr) if sr not in (None, "0", 0) else None
        bits = int(bits) if bits not in (None, "0", 0) else None
        return sr, bits
    except Exception:
        return None, None


def _codec_for_bits(bits: Optional[int], default: int) -> str:
    if bits in _BITS_TO_CODEC:
        return _BITS_TO_CODEC[bits]
    if bits and bits > 24:
        return _BITS_TO_CODEC[32]
    if bits and bits > 16:
        return _BITS_TO_CODEC[24]
    return _BITS_TO_CODEC.get(default, "pcm_s24le")


def to_wav(
    src: str,
    dest: str,
    bit_depth: int,
    sample_rate: int,
    preserve_native: bool = False,
) -> None:
    """Transcode ``src`` to a WAV at ``dest``.

    When ``preserve_native`` is True (used for lossless SoundCloud sources), the
    source's native sample rate and bit depth are kept rather than resampled, so
    a 24/96 original is never downgraded. Otherwise the configured target format
    is applied (the right choice for YouTube's 48 kHz Opus).
    """
    codec = _BITS_TO_CODEC.get(bit_depth, "pcm_s24le")
    target_sr = sample_rate

    if preserve_native:
        native_sr, native_bits = _probe(src)
        codec = _codec_for_bits(native_bits, bit_depth)
        if native_sr:
            target_sr = native_sr

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", src,
        "-vn", "-map_metadata", "-1",
        "-c:a", codec,
        "-ar", str(target_sr),
        dest,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise ConversionError(
            f"ffmpeg failed ({proc.returncode}) converting to WAV:\n{proc.stderr.strip()}"
        )
