"""Binary locator and media probe service for MKV to MP4 Converter."""

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

# Windows flag to prevent console window from popping up
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

# Video codecs supported for direct copy into MP4
MP4_COMPATIBLE_VIDEO_CODECS = {"h264", "hevc", "av1", "mpeg4"}

# Audio codecs supported for direct copy into MP4
MP4_COMPATIBLE_AUDIO_CODECS = {"aac", "ac3", "eac3", "mp3", "opus", "flac", "alac"}


@dataclass
class StreamInfo:
    codec_type: str
    codec_name: str
    channels: Optional[int] = None
    sample_rate: Optional[str] = None
    bitrate: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None


@dataclass
class MediaInfo:
    file_path: str
    duration: float
    size_bytes: int
    video_streams: List[StreamInfo]
    audio_streams: List[StreamInfo]
    can_remux_video: bool
    can_remux_audio: bool

    @property
    def primary_video_codec(self) -> str:
        return self.video_streams[0].codec_name if self.video_streams else "none"

    @property
    def primary_audio_codec(self) -> str:
        return self.audio_streams[0].codec_name if self.audio_streams else "none"


def find_binary(binary_name: str, search_dir: Optional[str] = None) -> Optional[str]:
    """Locate a binary in PyInstaller bundle, local bin directory, or system PATH."""
    ext = ".exe" if sys.platform == "win32" else ""
    full_name = f"{binary_name}{ext}"

    # 1. Custom search dir if provided
    if search_dir:
        cand = Path(search_dir) / full_name
        if cand.exists():
            return str(cand.resolve())

    # 2. PyInstaller temporary bundle directory
    if hasattr(sys, "_MEIPASS"):
        cand = Path(sys._MEIPASS) / "bin" / full_name
        if cand.exists():
            return str(cand.resolve())
        cand = Path(sys._MEIPASS) / full_name
        if cand.exists():
            return str(cand.resolve())

    # 3. Application local directory (adjacent to script/executable)
    app_dir = Path(__file__).resolve().parent.parent
    local_cand = app_dir / "bin" / full_name
    if local_cand.exists():
        return str(local_cand.resolve())

    # 4. System PATH
    found = shutil.which(binary_name)
    if found:
        return str(Path(found).resolve())

    return None


def get_ffmpeg_binaries() -> tuple[Optional[str], Optional[str]]:
    """Return paths for ffmpeg and ffprobe binaries."""
    ffmpeg_path = find_binary("ffmpeg")
    ffprobe_path = find_binary("ffprobe")
    return ffmpeg_path, ffprobe_path


def probe_media(file_path: str, ffprobe_path: Optional[str] = None) -> MediaInfo:
    """Extract stream details and check container compatibility using ffprobe."""
    if not ffprobe_path:
        _, ffprobe_path = get_ffmpeg_binaries()
        if not ffprobe_path:
            raise FileNotFoundError("ffprobe binary not found. Please install FFmpeg or bundle it in ./bin.")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Input file does not exist: {file_path}")

    cmd = [
        ffprobe_path,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        file_path
    ]

    try:
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = CREATE_NO_WINDOW

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            **kwargs
        )
    except Exception as e:
        raise RuntimeError(f"Failed to execute ffprobe: {e}") from e

    if result.returncode != 0:
        raise RuntimeError(f"Failed to probe media file '{file_path}': {result.stderr.strip()}")

    try:
        data = json.loads(result.stdout)
    except Exception as e:
        raise RuntimeError(f"Could not parse ffprobe output: {e}") from e

    format_info = data.get("format", {})
    raw_duration = format_info.get("duration", "0")
    try:
        duration = float(raw_duration)
    except (ValueError, TypeError):
        duration = 0.0

    raw_size = format_info.get("size", "0")
    try:
        size_bytes = int(raw_size)
    except (ValueError, TypeError):
        size_bytes = os.path.getsize(file_path) if os.path.exists(file_path) else 0

    streams = data.get("streams", [])
    video_streams: List[StreamInfo] = []
    audio_streams: List[StreamInfo] = []

    for s in streams:
        stype = s.get("codec_type")
        codec_name = (s.get("codec_name") or "").lower()
        if not codec_name:
            continue

        raw_bitrate = s.get("bit_rate")
        bitrate = int(raw_bitrate) if raw_bitrate and raw_bitrate.isdigit() else None

        if stype == "video":
            info = StreamInfo(
                codec_type="video",
                codec_name=codec_name,
                width=s.get("width"),
                height=s.get("height"),
                bitrate=bitrate
            )
            video_streams.append(info)
        elif stype == "audio":
            info = StreamInfo(
                codec_type="audio",
                codec_name=codec_name,
                channels=s.get("channels"),
                sample_rate=s.get("sample_rate"),
                bitrate=bitrate
            )
            audio_streams.append(info)

    # Check remux compatibility:
    # Video can be remuxed if primary video codec is supported by MP4
    can_remux_video = False
    if video_streams:
        can_remux_video = video_streams[0].codec_name in MP4_COMPATIBLE_VIDEO_CODECS

    # Audio can be remuxed if all audio streams are supported by MP4
    can_remux_audio = True if audio_streams else False
    for a in audio_streams:
        if a.codec_name not in MP4_COMPATIBLE_AUDIO_CODECS:
            can_remux_audio = False
            break

    return MediaInfo(
        file_path=file_path,
        duration=duration,
        size_bytes=size_bytes,
        video_streams=video_streams,
        audio_streams=audio_streams,
        can_remux_video=can_remux_video,
        can_remux_audio=can_remux_audio
    )
