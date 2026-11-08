"""Build script to compile MKV to MP4 Converter into a lightweight standalone .exe."""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def build(include_embedded_ffmpeg=False):
    app_root = Path(__file__).resolve().parent
    assets_dir = app_root / "assets"
    icon_file = assets_dir / "icon.ico"

    if not icon_file.exists():
        print("[*] Generating icons...")
        subprocess.run([sys.executable, str(app_root / "scripts" / "generate_logo.py")], check=True)

    print(f"[*] Starting PyInstaller build (small_size={not include_embedded_ffmpeg})...")

    pyinstaller_cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        "--clean",
        "--name", "MKV_to_MP4_Converter",
        f"--icon={icon_file}",
        "--collect-all", "customtkinter",
        f"--add-data={assets_dir};assets",
    ]

    if include_embedded_ffmpeg:
        bin_dir = app_root / "bin"
        ffmpeg_bin = bin_dir / "ffmpeg.exe"
        ffprobe_bin = bin_dir / "ffprobe.exe"
        if ffmpeg_bin.exists() and ffprobe_bin.exists():
            pyinstaller_cmd.extend([
                f"--add-binary={ffmpeg_bin};bin",
                f"--add-binary={ffprobe_bin};bin",
            ])

    pyinstaller_cmd.append(str(app_root / "main.py"))

    print(f"Executing: {' '.join(pyinstaller_cmd)}")
    result = subprocess.run(pyinstaller_cmd, cwd=str(app_root))
    if result.returncode != 0:
        print("[ERROR] PyInstaller build failed!")
        sys.exit(result.returncode)

    dist_exe = app_root / "dist" / "MKV_to_MP4_Converter.exe"
    if dist_exe.exists():
        size_mb = dist_exe.stat().st_size / (1024 * 1024)
        print("=" * 60)
        print(f"[SUCCESS] Standalone small-size executable created successfully!")
        print(f"Location: {dist_exe}")
        print(f"Size: {size_mb:.2f} MB")
        print("=" * 60)
    else:
        print("[ERROR] Output executable not found in dist/")
        sys.exit(1)


if __name__ == "__main__":
    build(include_embedded_ffmpeg=False)
