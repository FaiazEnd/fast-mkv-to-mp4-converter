# MKV to MP4 Converter

An ultra-fast, lightweight, and modern Windows desktop application that converts/remuxes `.mkv` files to `.mp4` (and other popular media formats) while **preserving 100% audio fidelity**, displaying real-time progress bars, and shipping as a single standalone `.exe` with zero external dependencies required.

---

## Key Features

- **100% Lossless Audio Preservation:** Audio streams are copied bit-for-bit (`-c:a copy`) with zero generational degradation and instant processing.
- **Ultra-Fast Remuxing:** When the video stream is H.264, HEVC (H.265), or AV1, the video stream is also copied losslessly (`-c:v copy`). Multi-gigabyte videos convert in seconds at disk I/O speed.
- **Accurate Real-Time Progress Bar:** Displays percentage (0%–100%), processing speed (e.g. `45.2x`), elapsed time, and ETA countdown during each conversion.
- **Wide Format & Codec Support:**
  - **Containers:** MP4, MKV, MOV, WebM, AVI, TS, MP3, FLAC, M4A
  - **Video Codecs:** Lossless Copy, H.264 (libx264), H.265 (libx265), AV1 (libsvtav1), VP9, MPEG-4, Audio Only
  - **Audio Codecs:** Lossless Copy (Default), AAC, AC3, E-AC3, MP3, Opus, FLAC, ALAC, PCM 16-bit
  - **Audio Bitrates:** Source / Default, 320k, 256k, 192k, 128k, 96k
  - **Quality (CRF):** 18 (Visually Lossless), 23 (Balanced), 28 (Compact)
- **Batch Processing:** Add multiple files or entire folders to the conversion queue.
- **Standalone `.exe`:** Bundled into a single portable `.exe` with static FFmpeg and FFprobe embedded—no installation, Python, or PATH setup required.

---

## Running from Source

```bash
# Install dependencies
pip install -r requirements.txt

# Run application
python main.py
```

## Running Tests

```bash
python -m pytest tests/ -v
```

## Building Standalone `.exe`

```bash
python build_exe.py
```
The compiled single-file binary will be placed in `dist/MKV_to_MP4_Converter.exe`.
