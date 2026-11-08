import os
import subprocess
import pytest
from pathlib import Path

from converter.probe import probe_media, get_ffmpeg_binaries
from converter.engine import ConversionConfig, FFmpegEngine, ProgressUpdate


def test_end_to_end_remux_conversion(tmp_path):
    ffmpeg_bin, ffprobe_bin = get_ffmpeg_binaries()
    if not ffmpeg_bin or not ffprobe_bin:
        pytest.skip("FFmpeg/ffprobe binaries not found on system.")

    input_mkv = tmp_path / "test_sample.mkv"
    output_mp4 = tmp_path / "test_sample.mp4"

    # 1. Generate a synthetic 3-second MKV with H.264 video and AAC audio
    gen_cmd = [
        ffmpeg_bin,
        "-y",
        "-f", "lavfi", "-i", "testsrc=duration=3:size=320x240:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=3",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-b:a", "128k",
        str(input_mkv)
    ]
    gen_res = subprocess.run(gen_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert gen_res.returncode == 0, f"Failed to generate test MKV: {gen_res.stderr.decode()}"
    assert input_mkv.exists()

    # 2. Probe input media
    probe_in = probe_media(str(input_mkv), ffprobe_path=ffprobe_bin)
    assert round(probe_in.duration) == 3
    assert probe_in.can_remux_video is True
    assert probe_in.can_remux_audio is True
    assert probe_in.primary_audio_codec == "aac"
    assert probe_in.primary_video_codec == "h264"

    # 3. Perform conversion / remuxing with progress tracking
    progress_records = []
    completed_event = {"done": False, "success": False, "error": None}

    def on_progress(p: ProgressUpdate):
        progress_records.append(p)

    def on_complete(success: bool, err):
        completed_event["done"] = True
        completed_event["success"] = success
        completed_event["error"] = err

    config = ConversionConfig(
        input_path=str(input_mkv),
        output_path=str(output_mp4),
        video_codec="copy",
        audio_codec="copy"
    )

    engine = FFmpegEngine(ffmpeg_path=ffmpeg_bin)
    engine.start(config, probe_in.duration, on_progress, on_complete)

    # Wait for completion
    import time
    timeout = 10.0
    start = time.time()
    while not completed_event["done"] and (time.time() - start) < timeout:
        time.sleep(0.1)

    assert completed_event["done"] is True
    assert completed_event["success"] is True, f"Conversion failed: {completed_event['error']}"
    assert output_mp4.exists()
    assert output_mp4.stat().st_size > 0

    # 4. Verify 100% audio fidelity preservation and duration
    probe_out = probe_media(str(output_mp4), ffprobe_path=ffprobe_bin)
    assert round(probe_out.duration) == 3
    assert probe_out.primary_audio_codec == "aac"
    assert probe_out.primary_video_codec == "h264"
    assert len(progress_records) > 0
    assert progress_records[-1].percent == 100.0
