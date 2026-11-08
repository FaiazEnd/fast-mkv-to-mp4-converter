"""FFmpeg execution engine with real-time progress parsing and multi-codec/format support."""

import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

from converter.probe import CREATE_NO_WINDOW, get_ffmpeg_binaries

# Supported output formats and extensions
FORMAT_EXTENSIONS = {
    "MP4 (.mp4)": ".mp4",
    "MKV (.mkv)": ".mkv",
    "MOV (.mov)": ".mov",
    "WebM (.webm)": ".webm",
    "AVI (.avi)": ".avi",
    "TS (.ts)": ".ts",
    "MP3 Audio (.mp3)": ".mp3",
    "M4A Audio (.m4a)": ".m4a",
    "FLAC Audio (.flac)": ".flac",
}

# Video codec map: friendly name -> ffmpeg codec identifier
VIDEO_CODECS = {
    "Copy (100% Lossless, Instant)": "copy",
    "H.264 / AVC (libx264)": "libx264",
    "H.265 / HEVC (libx265)": "libx265",
    "AV1 (libsvtav1)": "libsvtav1",
    "VP9 (libvpx-vp9)": "libvpx-vp9",
    "MPEG-4 (mpeg4)": "mpeg4",
    "None (Disable Video)": "none",
}

# Audio codec map: friendly name -> ffmpeg codec identifier
AUDIO_CODECS = {
    "Copy (100% Lossless, Instant)": "copy",
    "AAC (aac)": "aac",
    "AC3 / Dolby Digital (ac3)": "ac3",
    "E-AC3 / Dolby Digital Plus (eac3)": "eac3",
    "MP3 (libmp3lame)": "libmp3lame",
    "Opus (libopus)": "libopus",
    "FLAC (flac, Lossless)": "flac",
    "ALAC (alac, Apple Lossless)": "alac",
    "PCM 16-bit (pcm_s16le)": "pcm_s16le",
    "None (Disable Audio)": "none",
}

AUDIO_BITRATES = ["Source / Default", "320k", "256k", "192k", "128k", "96k"]
CRF_PRESETS = ["18 (Visually Lossless)", "23 (Default Balance)", "28 (Compact Size)"]
SPEED_PRESETS = ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow"]


@dataclass
class ConversionConfig:
    input_path: str
    output_path: str
    output_format: str = "mp4"
    video_codec: str = "copy"
    audio_codec: str = "copy"
    audio_bitrate: Optional[str] = None
    video_crf: Optional[int] = None
    video_preset: Optional[str] = None


@dataclass
class ProgressUpdate:
    percent: float
    elapsed_sec: float
    speed: str
    eta_sec: float
    fps: float = 0.0
    current_time_sec: float = 0.0


def build_ffmpeg_args(config: ConversionConfig, ffmpeg_path: str) -> List[str]:
    """Construct optimized FFmpeg CLI arguments based on ConversionConfig."""
    args = [ffmpeg_path, "-y", "-i", config.input_path]

    # Video codec setup
    if config.video_codec == "none":
        args.append("-vn")
    else:
        args.extend(["-c:v", config.video_codec])
        if config.video_codec != "copy":
            if config.video_crf is not None:
                args.extend(["-crf", str(config.video_crf)])
            if config.video_preset:
                args.extend(["-preset", config.video_preset])

    # Audio codec setup
    if config.audio_codec == "none":
        args.append("-an")
    else:
        args.extend(["-c:a", config.audio_codec])
        if config.audio_codec != "copy" and config.audio_bitrate:
            args.extend(["-b:a", config.audio_bitrate])

    # Format specific flags
    ext = Path(config.output_path).suffix.lower()
    if ext in {".mp4", ".m4a", ".mov"}:
        args.extend(["-movflags", "+faststart"])

    # Real-time progress monitoring via pipe:1
    args.extend(["-progress", "pipe:1", "-nostats"])
    args.append(config.output_path)
    return args


def parse_progress_block(
    lines: List[str], total_duration: float, start_time: float
) -> Optional[ProgressUpdate]:
    """Parse key-value progress lines into a ProgressUpdate."""
    data: Dict[str, str] = {}
    for line in lines:
        line = line.strip()
        if "=" in line:
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip()

    if not data:
        return None

    # Determine current elapsed media timestamp
    current_sec = 0.0
    if "out_time_us" in data:
        try:
            current_sec = float(data["out_time_us"]) / 1_000_000.0
        except ValueError:
            pass
    elif "out_time_ms" in data:
        try:
            current_sec = float(data["out_time_ms"]) / 1_000.0
        except ValueError:
            pass
    elif "out_time" in data:
        # Format HH:MM:SS.micro
        parts = data["out_time"].split(":")
        if len(parts) == 3:
            try:
                h, m, s = float(parts[0]), float(parts[1]), float(parts[2])
                current_sec = h * 3600 + m * 60 + s
            except ValueError:
                pass

    percent = 0.0
    if total_duration > 0:
        percent = min(100.0, max(0.0, (current_sec / total_duration) * 100.0))

    elapsed_wall_sec = time.time() - start_time if start_time > 0 else 0.0

    raw_speed = data.get("speed", "N/A")
    speed_float = 0.0
    if raw_speed.endswith("x"):
        try:
            speed_float = float(raw_speed[:-1])
        except ValueError:
            pass

    eta_sec = 0.0
    if speed_float > 0 and total_duration > current_sec:
        eta_sec = (total_duration - current_sec) / speed_float
    elif percent > 0 and elapsed_wall_sec > 0:
        remaining_ratio = (100.0 - percent) / percent
        eta_sec = elapsed_wall_sec * remaining_ratio

    fps = 0.0
    try:
        fps = float(data.get("fps", 0))
    except ValueError:
        pass

    return ProgressUpdate(
        percent=round(percent, 2),
        elapsed_sec=round(elapsed_wall_sec, 1),
        speed=raw_speed,
        eta_sec=round(eta_sec, 1),
        fps=fps,
        current_time_sec=round(current_sec, 2),
    )


class FFmpegEngine:
    """Manages an active FFmpeg process, parsing progress and handling cancellation."""

    def __init__(self, ffmpeg_path: Optional[str] = None):
        if not ffmpeg_path:
            ffmpeg_path, _ = get_ffmpeg_binaries()
        self.ffmpeg_path = ffmpeg_path
        self._process: Optional[subprocess.Popen] = None
        self._is_cancelled = False
        self._worker_thread: Optional[threading.Thread] = None
        self._current_output_path: Optional[str] = None

    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def cancel(self) -> None:
        """Cancel current conversion and clean up incomplete output file."""
        self._is_cancelled = True
        proc = self._process
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    proc.kill()
            except Exception:
                pass

        if self._current_output_path and os.path.exists(self._current_output_path):
            try:
                os.remove(self._current_output_path)
            except Exception:
                pass

    def start(
        self,
        config: ConversionConfig,
        total_duration: float,
        on_progress: Callable[[ProgressUpdate], None],
        on_complete: Callable[[bool, Optional[str]], None],
    ) -> None:
        """Start conversion in a background worker thread."""
        if not self.ffmpeg_path:
            raise FileNotFoundError("ffmpeg binary not found.")

        self._is_cancelled = False
        self._current_output_path = config.output_path

        def _worker():
            start_wall = time.time()
            args = build_ffmpeg_args(config, self.ffmpeg_path)

            kwargs = {}
            if sys.platform == "win32":
                kwargs["creationflags"] = CREATE_NO_WINDOW

            try:
                self._process = subprocess.Popen(
                    args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    **kwargs,
                )
            except Exception as e:
                on_complete(False, f"Failed to start FFmpeg process: {e}")
                return

            accumulated_lines: List[str] = []
            stderr_output: List[str] = []

            # Thread to capture stderr without blocking stdout
            def _read_stderr():
                if self._process and self._process.stderr:
                    for err_line in self._process.stderr:
                        stderr_output.append(err_line)

            stderr_thread = threading.Thread(target=_read_stderr, daemon=True)
            stderr_thread.start()

            if self._process.stdout:
                for line in self._process.stdout:
                    if self._is_cancelled:
                        break
                    accumulated_lines.append(line)
                    if line.startswith("progress=") or len(accumulated_lines) >= 12:
                        update = parse_progress_block(
                            accumulated_lines, total_duration, start_wall
                        )
                        if update:
                            on_progress(update)
                        accumulated_lines.clear()

            self._process.wait()
            stderr_thread.join(timeout=1.0)

            if self._is_cancelled:
                if self._current_output_path and os.path.exists(self._current_output_path):
                    try:
                        os.remove(self._current_output_path)
                    except Exception:
                        pass
                on_complete(False, "Cancelled by user.")
                return

            if self._process.returncode == 0:
                # Send 100% progress
                on_progress(
                    ProgressUpdate(
                        percent=100.0,
                        elapsed_sec=round(time.time() - start_wall, 1),
                        speed="Done",
                        eta_sec=0.0,
                    )
                )
                on_complete(True, None)
            else:
                err_text = "".join(stderr_output).strip()
                error_msg = err_text if err_text else f"FFmpeg exited with code {self._process.returncode}"
                on_complete(False, error_msg)

        self._worker_thread = threading.Thread(target=_worker, daemon=True)
        self._worker_thread.start()
