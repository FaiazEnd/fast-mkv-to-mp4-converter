"""Build script to compile MKV to MP4 Converter into a standalone single .exe file."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from converter.probe import get_ffmpeg_binaries, find_binary


def prepare_binaries():
    """Ensure ffmpeg.exe and ffprobe.exe are in the local ./bin directory for bundling."""
    app_root = Path(__file__).resolve().parent
    bin_dir = app_root / "bin"
    bin_dir.mkdir(exist_ok=True)

    ffmpeg_target = bin_dir / "ffmpeg.exe"
    ffprobe_target = bin_dir / "ffprobe.exe"

    if ffmpeg_target.exists() and ffprobe_target.exists():
        print(f"[OK] FFmpeg binaries already present in {bin_dir}")
        return str(bin_dir)

    # Search for ffmpeg in PATH or standard installation paths
    ffmpeg_src = find_binary("ffmpeg")
    ffprobe_src = find_binary("ffprobe")

    # Also search common winget install paths if not in PATH yet
    if not ffmpeg_src or not ffprobe_src:
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        candidates = list(Path(local_app_data).glob("Microsoft/WinGet/Packages/**/*ffmpeg.exe"))
        if candidates:
            ffmpeg_src = str(candidates[0])
            probe_cand = candidates[0].parent / "ffprobe.exe"
            if probe_cand.exists():
                ffprobe_src = str(probe_cand)

    if ffmpeg_src and os.path.exists(ffmpeg_src):
        print(f"[+] Copying ffmpeg from {ffmpeg_src} -> {ffmpeg_target}")
        shutil.copy2(ffmpeg_src, ffmpeg_target)

    if ffprobe_src and os.path.exists(ffprobe_src):
        print(f"[+] Copying ffprobe from {ffprobe_src} -> {ffprobe_target}")
        shutil.copy2(ffprobe_src, ffprobe_target)

    if not ffmpeg_target.exists() or not ffprobe_target.exists():
        raise RuntimeError(
            "Could not locate ffmpeg.exe and ffprobe.exe. Please ensure FFmpeg is installed or place them in ./bin/"
        )

    return str(bin_dir)


def build():
    app_root = Path(__file__).resolve().parent
    bin_dir = prepare_binaries()

    ffmpeg_bin = os.path.join(bin_dir, "ffmpeg.exe")
    ffprobe_bin = os.path.join(bin_dir, "ffprobe.exe")

    print("[*] Starting PyInstaller build...")

    pyinstaller_cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name", "MKV_to_MP4_Converter",
        "--collect-all", "customtkinter",
        f"--add-binary={ffmpeg_bin};bin",
        f"--add-binary={ffprobe_bin};bin",
        str(app_root / "main.py")
    ]

    print(f"Executing: {' '.join(pyinstaller_cmd)}")
    result = subprocess.run(pyinstaller_cmd, cwd=str(app_root))
    if result.returncode != 0:
        print("[ERROR] PyInstaller build failed!")
        sys.exit(result.returncode)

    dist_exe = app_root / "dist" / "MKV_to_MP4_Converter.exe"
    if dist_exe.exists():
        size_mb = dist_exe.stat().st_size / (1024 * 1024)
        print("=" * 60)
        print(f"[SUCCESS] Standalone executable created successfully!")
        print(f"Location: {dist_exe}")
        print(f"Size: {size_mb:.2f} MB")
        print("=" * 60)
    else:
        print("[ERROR] Output executable not found in dist/")
        sys.exit(1)


if __name__ == "__main__":
    build()
