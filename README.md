# yt-pldl

Download a **YouTube playlist** as high-resolution **WAV** files — and, when a
genuinely **lossless free download exists on SoundCloud**, transparently grab
that instead so you get a true lossless copy of the *intended* track.

The YouTube playlist is always the **master queue**: it decides what gets
downloaded and in what order. SoundCloud is only ever used as a *lossless
upgrade* for a track you already queued, never as a discovery source.

---

## Features

- 🎵 Download an entire YouTube playlist as WAVs (24-bit/48 kHz by default).
- 🎚️ **Auto lossless upgrade** — per track, search SoundCloud and use the
  artist-enabled free **WAV/FLAC/AIFF** download when it strongly matches.
- 🛡️ **Never swaps in an altered version.** Remixes, flips, edits, bootlegs,
  VIPs, sped-up/slowed edits, etc. are rejected unless *your* queued track is
  that same variant. Duration + artist + title all have to agree.
- 🎛️ **Extended mixes are opt-in** (`--extended`).
- 🧹 Cleans filenames (strips `(Official Video)`, trailing `[videoID]`, …).
- 📁 Drops everything into a folder named after the playlist.
- ♻️ Lossy-only SoundCloud results (e.g. 320 kbps MP3) are ignored — it falls
  back to YouTube, so you never trade down.

## How the SoundCloud upgrade is decided (per track)

```
YouTube track (artist, title, duration, is-remix?)
        │
        ▼
  search SoundCloud  ──►  a candidate is accepted ONLY IF:
        (a) artist matches (fuzzy)
        (b) title matches (fuzzy)
        (c) duration within tolerance (default ±3s)
        (d) NOT an altered variant unless your track is that same variant
        (e) a free download exists AND it is lossless (wav/flac/aiff)
        │
   qualifies? ── yes ──►  download lossless original from SoundCloud
        │
        └──── no ─────►  download best audio (Opus) from YouTube
                              │
                              ▼
                 convert to WAV · clean name · move to <Playlist>/
```

## Requirements

- **Python 3.9+**
- **ffmpeg** (includes **ffprobe**) on your `PATH`
  - Windows: `winget install Gyan.FFmpeg` (or `choco install ffmpeg`)
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt install ffmpeg`
- **A JavaScript runtime** — **Node**, **Deno**, or **Bun** on your `PATH`.
  YouTube now requires solving JS challenges to unlock audio streams; without a
  runtime many tracks fail with `HTTP 403`. Any one works:
  - Node: <https://nodejs.org> (`winget install OpenJS.NodeJS`)
  - Deno: <https://deno.land> (`winget install DenoLand.Deno`)

`yt-dlp` is installed automatically as a Python dependency. yt-dlp uses whatever
JS runtime it finds, so you don't need to configure anything.

### Dealing with occasional HTTP 403

YouTube runs rate-limiting/anti-bot experiments, so a track may 403 on the first
try. yt-pldl automatically retries each track with a short back-off, which
clears almost all of these. For a playlist that still has a stubborn failure,
pass browser cookies (authenticated requests rarely get throttled):

```bash
ytpldl "https://youtube.com/playlist?list=..." --cookies-from-browser firefox
```

Close the browser first so its cookie database isn't locked.

## Install

From source (until published to PyPI):

```bash
git clone https://github.com/nigushto/yt-pldl.git
cd yt-pldl
pip install .
```

Or, for development:

```bash
pip install -e ".[dev]"
```

This installs the `ytpldl` command.

## Usage

Interactive (prompts for the URL and a public/unlisted confirmation):

```bash
ytpldl
```

Direct:

```bash
ytpldl "https://www.youtube.com/playlist?list=PLxxxxxxxx"
```

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `--source auto\|youtube` | `auto` tries lossless SoundCloud upgrades; `youtube` skips SoundCloud | `auto` |
| `--extended` | Allow/prefer extended mixes from SoundCloud | off |
| `--wav-format BITS/KHZ` | Output PCM format for YouTube audio, e.g. `24/48`, `16/44` | `24/48` |
| `--no-preserve-native` | Downsample lossless SoundCloud sources instead of keeping native rate | off |
| `--sc-tolerance SEC` | Allowed duration difference for a SoundCloud match | `3` |
| `--sc-results N` | SoundCloud search results inspected per track | `5` |
| `--cookies-from-browser BROWSER` | Use a browser's YouTube cookies to avoid 403s (e.g. `firefox`, `chrome`, `edge`) | none |
| `-o, --output DIR` | Where the playlist folder is created | current dir |
| `--no-number` | Don't prefix filenames with the track number | off |
| `--keep-temp` | Keep intermediate files | off |
| `-y, --yes` | Skip the "is this playlist public?" prompt | off |

### Examples

```bash
# CD-quality WAVs, YouTube only
ytpldl -o ~/Music "https://youtube.com/playlist?list=..." --source youtube --wav-format 16/44

# Prefer extended mixes when a lossless SoundCloud match exists
ytpldl --extended "https://youtube.com/playlist?list=..."
```

## Bonus: download a single video (`ytvid`)

The package also installs a **`ytvid`** command that downloads one YouTube video
as a **Full HD (1080p) mp4** into your **Videos folder**:

```bash
ytvid                                         # prompts for the URL
ytvid "https://www.youtube.com/watch?v=..."   # straight to your Videos folder
```

It prefers **H.264** so the file plays everywhere (4K on YouTube is only served
as AV1/VP9, which needs special codecs), and downloads in 10 MiB chunks so large
files don't die to YouTube's mid-download `HTTP 403` throttling.

| Flag | Description | Default |
|------|-------------|---------|
| `-o, --output DIR` | Destination folder | your Videos folder |
| `--max-height PX` | Cap height, e.g. `1080`, `720`, `480` | `1080` |
| `--any-codec` | Allow VP9/AV1 (smaller/higher-res, may need codecs) | off |
| `--cookies-from-browser BROWSER` | Use browser cookies to beat stubborn 403s | none |

```bash
# 720p to a specific folder
ytvid "https://youtube.com/watch?v=..." --max-height 720 -o "D:\Clips"
```

## A note on audio quality

YouTube's best audio is **Opus (~160 kbps, lossy)**. Converting it to WAV gives
you an uncompressed file, but it does **not** add fidelity beyond the source.
The SoundCloud path is the only way this tool obtains genuinely lossless audio,
and only when the artist has enabled a free lossless download.

## Legal

This tool only accesses **downloads that uploaders have explicitly enabled**
and content you are permitted to access. It does not bypass private playlists,
paywalls, or download-disabled tracks. Respect YouTube's and SoundCloud's Terms
of Service and applicable copyright law in your jurisdiction. You are
responsible for how you use it.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

[MIT](LICENSE)
