"""Utility to ensure ffmpeg and ffprobe are available."""

import os
import shutil
import sys
import zipfile
import urllib.request
from pathlib import Path

FFMPEG_ESSENTIALS_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"


def download_ffmpeg(target_dir: str = "bin"):
    dest = Path(target_dir)
    dest.mkdir(exist_ok=True)
    
    ffmpeg_exe = dest / "ffmpeg.exe"
    ffprobe_exe = dest / "ffprobe.exe"
    
    if ffmpeg_exe.exists() and ffprobe_exe.exists():
        print(f"[OK] FFmpeg already exists in {dest}")
        return True

    zip_path = dest / "ffmpeg.zip"
    print(f"[*] Downloading static FFmpeg essentials from {FFMPEG_ESSENTIALS_URL} ...")
    urllib.request.urlretrieve(FFMPEG_ESSENTIALS_URL, zip_path)
    
    print("[*] Extracting ffmpeg.exe and ffprobe.exe ...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.namelist():
            if member.endswith("ffmpeg.exe"):
                with zf.open(member) as source, open(ffmpeg_exe, "wb") as target:
                    shutil.copyfileobj(source, target)
            elif member.endswith("ffprobe.exe"):
                with zf.open(member) as source, open(ffprobe_exe, "wb") as target:
                    shutil.copyfileobj(source, target)

    if zip_path.exists():
        zip_path.unlink()

    if ffmpeg_exe.exists() and ffprobe_exe.exists():
        print(f"[SUCCESS] FFmpeg binaries installed to {dest}")
        return True
    return False


if __name__ == "__main__":
    download_ffmpeg()
