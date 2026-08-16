"""End-to-end orchestration: queue -> resolve -> download -> WAV -> organize."""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass, field
from typing import List, Optional

from ytpldl import convert, naming, resolver, sources
from ytpldl.config import Config


@dataclass
class RunSummary:
    playlist_title: str = ""
    output_folder: str = ""
    total: int = 0
    from_soundcloud: int = 0
    from_youtube: int = 0
    failed: List[str] = field(default_factory=list)


def _unique_path(folder: str, filename: str) -> str:
    base, ext = os.path.splitext(filename)
    candidate = os.path.join(folder, filename)
    i = 2
    while os.path.exists(candidate):
        candidate = os.path.join(folder, f"{base} ({i}){ext}")
        i += 1
    return candidate


def run(url: str, cfg: Config) -> RunSummary:
    """Execute the full pipeline for ``url``. Returns a summary."""
    summary = RunSummary()

    print("Reading playlist...")
    playlist_title, entries = sources.extract_playlist(url)
    summary.playlist_title = playlist_title
    summary.total = len(entries)

    folder_name = naming.sanitize_filename(playlist_title)
    out_folder = os.path.join(os.path.abspath(cfg.output_dir), folder_name)
    os.makedirs(out_folder, exist_ok=True)
    summary.output_folder = out_folder

    temp_root = cfg.temp_dir or tempfile.mkdtemp(prefix="ytpldl_")
    os.makedirs(temp_root, exist_ok=True)

    print(f'Playlist: "{playlist_title}"  ({summary.total} tracks)')
    print(f"Output:   {out_folder}")
    print(f"Mode:     source={cfg.source}"
          + (", extended-mixes" if cfg.extended else "")
          + f", {cfg.bit_depth}-bit/{cfg.sample_rate // 1000}kHz\n")

    try:
        for idx, entry in enumerate(entries, start=1):
            label = entry.get("title") or entry.get("id") or f"track {idx}"
            prefix = f"[{idx}/{summary.total}]"
            try:
                _process_track(idx, entry, cfg, out_folder, temp_root, summary, prefix)
            except KeyboardInterrupt:
                raise
            except Exception as exc:  # keep going; one bad track shouldn't stop all
                print(f"{prefix} FAILED: {label}\n         {exc}")
                summary.failed.append(label)
    finally:
        if not cfg.keep_temp and not cfg.temp_dir:
            shutil.rmtree(temp_root, ignore_errors=True)

    _print_summary(summary)
    return summary


def _process_track(
    idx: int,
    entry: dict,
    cfg: Config,
    out_folder: str,
    temp_root: str,
    summary: RunSummary,
    prefix: str,
) -> None:
    info = sources.extract_track(entry)
    if not info:
        raise RuntimeError("unavailable (Private/deleted/region-locked)")

    yt_title = info.get("title") or ""
    yt_artist, parsed_title = sources.parse_artist_title(info)
    yt_duration = info.get("duration")
    display = clean = naming.clean_title(yt_title)
    print(f"{prefix} {display}")

    pick: Optional[resolver.SoundCloudPick] = resolver.resolve_source(
        yt_artist, parsed_title, yt_duration, cfg
    )

    if pick is not None:
        print(f"         -> SoundCloud lossless ({pick.ext}, match {pick.score})")
        src_path = sources.download_soundcloud(pick.url, pick.format_id, temp_root)
        preserve = cfg.preserve_native
        summary.from_soundcloud += 1
    else:
        print("         -> YouTube (best audio / Opus)")
        yt_url = info.get("webpage_url") or f"https://www.youtube.com/watch?v={info.get('id')}"
        src_path = sources.download_youtube(yt_url, temp_root)
        preserve = False
        summary.from_youtube += 1

    # Convert to WAV in temp, then move into the playlist folder.
    tmp_wav = os.path.join(temp_root, f"track_{idx}.wav")
    convert.to_wav(
        src_path, tmp_wav,
        bit_depth=cfg.bit_depth,
        sample_rate=cfg.sample_rate,
        preserve_native=preserve,
    )

    # Source audio no longer needed.
    try:
        os.remove(src_path)
    except OSError:
        pass

    final_name = naming.output_filename(clean, idx, cfg.number)
    final_path = _unique_path(out_folder, final_name)
    shutil.move(tmp_wav, final_path)
    print(f"         OK  {os.path.basename(final_path)}")


def _print_summary(s: RunSummary) -> None:
    print("\n" + "-" * 60)
    print(f'Done: "{s.playlist_title}"')
    print(f"  Saved to:      {s.output_folder}")
    print(f"  From SoundCloud: {s.from_soundcloud}")
    print(f"  From YouTube:    {s.from_youtube}")
    if s.failed:
        print(f"  Failed ({len(s.failed)}):")
        for f in s.failed:
            print(f"    - {f}")
    print("-" * 60)
