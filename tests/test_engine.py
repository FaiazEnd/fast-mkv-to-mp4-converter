import pytest
from unittest.mock import patch, MagicMock
from converter.engine import (
    ConversionConfig,
    ProgressUpdate,
    FFmpegEngine,
    build_ffmpeg_args,
    parse_progress_block,
    FORMAT_EXTENSIONS
)

def test_build_ffmpeg_args_remux():
    config = ConversionConfig(
        input_path="input.mkv",
        output_path="output.mp4",
        video_codec="copy",
        audio_codec="copy"
    )
    args = build_ffmpeg_args(config, ffmpeg_path="ffmpeg")
    assert "-c:v" in args
    assert args[args.index("-c:v") + 1] == "copy"
    assert "-c:a" in args
    assert args[args.index("-c:a") + 1] == "copy"
    assert "-movflags" in args
    assert "+faststart" in args
    assert "-progress" in args
    assert "pipe:1" in args

def test_build_ffmpeg_args_custom_codecs():
    config = ConversionConfig(
        input_path="input.mkv",
        output_path="output.mp4",
        video_codec="libx264",
        audio_codec="aac",
        audio_bitrate="320k",
        video_crf=18,
        video_preset="fast"
    )
    args = build_ffmpeg_args(config, ffmpeg_path="ffmpeg")
    assert args[args.index("-c:v") + 1] == "libx264"
    assert args[args.index("-c:a") + 1] == "aac"
    assert "-b:a" in args
    assert args[args.index("-b:a") + 1] == "320k"
    assert "-crf" in args
    assert args[args.index("-crf") + 1] == "18"
    assert "-preset" in args
    assert args[args.index("-preset") + 1] == "fast"

def test_parse_progress_block():
    raw_lines = [
        "frame=120",
        "fps=60.0",
        "out_time_us=10000000",
        "speed=10.0x",
        "progress=continue"
    ]
    update = parse_progress_block(raw_lines, total_duration=20.0, start_time=0.0)
    assert update is not None
    assert update.percent == 50.0  # 10s out of 20s
    assert update.speed == "10.0x"
    assert update.eta_sec == 1.0  # (20 - 10) / 10.0
    assert update.fps == 60.0

def test_engine_cancel_cleans_up_file(tmp_path):
    out_file = tmp_path / "output.mp4"
    out_file.write_text("partial data")
    
    engine = FFmpegEngine(ffmpeg_path="ffmpeg")
    # Simulate active process
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None
    engine._process = mock_proc
    engine._current_output_path = str(out_file)
    
    engine.cancel()
    assert mock_proc.terminate.called
    assert not out_file.exists()  # should remove partial file
