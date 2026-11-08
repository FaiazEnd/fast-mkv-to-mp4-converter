# Fast MKV to MP4 Converter Pro

[![Version](https://img.shields.io/badge/version-1.0.0-ff4d4d.svg)](https://github.com/FaiazEnd/mkv-to-mp4-converter-releases/releases/latest)
[![Windows 10/11](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-blue.svg)](https://github.com/FaiazEnd/mkv-to-mp4-converter-releases/releases/latest)
[![Audio](https://img.shields.io/badge/Audio-100%25%20Lossless-2ecc71.svg)](https://github.com/FaiazEnd/mkv-to-mp4-converter-releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)

An ultra-fast, lightweight, and modern Windows desktop application that converts/remuxes `.mkv` files to `.mp4` (and other popular media formats) while **preserving 100% audio fidelity**, displaying real-time progress bars, and shipping as a small portable `.exe`.

🌐 **Official Website & Documentation:**  
👉 **[https://faiazend.github.io/mkv-to-mp4-converter-releases/](https://faiazend.github.io/mkv-to-mp4-converter-releases/)**

⚡ **Direct Download (Small Standalone Binary):**  
👉 **[Download MKV_to_MP4_Converter.exe (~30.5 MB)](https://github.com/FaiazEnd/mkv-to-mp4-converter-releases/releases/latest/download/MKV_to_MP4_Converter.exe)**

---

## Key Features

- **100% Lossless Audio Preservation:** Audio streams are copied bit-for-bit (`-c:a copy`) with zero generational degradation and instant processing.
- **Ultra-Fast Remuxing:** When the video stream is H.264, HEVC (H.265), or AV1, the video stream is also copied losslessly (`-c:v copy`). Multi-gigabyte videos convert in seconds at disk I/O speed.
- **Accurate Real-Time Progress Bar:** Displays percentage (0%–100%), processing speed (e.g. `45.2x`), elapsed time, and ETA countdown during each conversion.
- **Sharp Modern Executive UI:** Built with sharp geometric edges, dark & light mode toggle, and responsive status cards matching the studio aesthetic.
- **Wide Format & Codec Support:**
  - **Containers:** MP4, MKV, MOV, WebM, AVI, TS, MP3, FLAC, M4A
  - **Video Codecs:** Lossless Copy, H.264 (libx264), H.265 (libx265), AV1 (libsvtav1), VP9, MPEG-4, Audio Only
  - **Audio Codecs:** Lossless Copy (Default), AAC, AC3, E-AC3, MP3, Opus, FLAC, ALAC, PCM 16-bit
  - **Audio Bitrates:** Source / Default, 320k, 256k, 192k, 128k, 96k
  - **Quality (CRF):** 18 (Visually Lossless), 23 (Balanced), 28 (Compact)
- **Batch Processing:** Add multiple files or entire folders to the conversion queue with collision-safe auto naming (`_1.mp4`).
- **Small Portable Executable (~30.5 MB):** Standalone `.exe` with zero Python or setup needed.

---

## Running from Source

```bash
# Clone the repository
git clone https://github.com/FaiazEnd/fast-mkv-to-mp4-converter.git
cd fast-mkv-to-mp4-converter

# Install dependencies
pip install -r requirements.txt

# Run application
python main.py
```

## Running Unit & Integration Tests

```bash
python -m pytest tests/ -v
```

## Compiling Standalone Executable

```bash
# Build lightweight ~30MB executable:
python build_exe.py
```
Output executable is generated in `dist/MKV_to_MP4_Converter.exe`.
