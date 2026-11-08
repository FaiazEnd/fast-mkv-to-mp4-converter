import json
import pytest
from unittest.mock import patch, MagicMock
from converter.probe import (
    get_ffmpeg_binaries,
    StreamInfo,
    MediaInfo,
    probe_media,
    find_binary
)

def test_find_binary_checks_local_and_system(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_ffmpeg = fake_bin / "ffmpeg.exe"
    fake_ffmpeg.write_text("fake binary")
    
    found = find_binary("ffmpeg", search_dir=str(fake_bin))
    assert found == str(fake_ffmpeg)

def test_probe_media_parses_ffprobe_json(tmp_path):
    sample_file = tmp_path / "sample.mkv"
    sample_file.write_bytes(b"dummy mkv content")

    sample_ffprobe_output = {
        "format": {
            "duration": "125.500",
            "size": "52428800",
            "bit_rate": "3341915"
        },
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1920,
                "height": 1080,
                "bit_rate": "3000000"
            },
            {
                "codec_type": "audio",
                "codec_name": "aac",
                "channels": 6,
                "sample_rate": "48000",
                "bit_rate": "384000"
            }
        ]
    }
    
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = json.dumps(sample_ffprobe_output)
    
    with patch("subprocess.run", return_value=mock_res):
        info = probe_media(str(sample_file), ffprobe_path="ffprobe")
        assert info.duration == 125.5
        assert len(info.video_streams) == 1
        assert info.video_streams[0].codec_name == "h264"
        assert len(info.audio_streams) == 1
        assert info.audio_streams[0].codec_name == "aac"
        assert info.can_remux_video is True
        assert info.can_remux_audio is True

def test_probe_media_detects_incompatible_video(tmp_path):
    sample_file = tmp_path / "sample.mkv"
    sample_file.write_bytes(b"dummy mkv content")

    sample_ffprobe_output = {
        "format": {"duration": "60.0"},
        "streams": [
            {"codec_type": "video", "codec_name": "vp9"},
            {"codec_type": "audio", "codec_name": "flac"}
        ]
    }
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = json.dumps(sample_ffprobe_output)
    
    with patch("subprocess.run", return_value=mock_res):
        info = probe_media(str(sample_file), ffprobe_path="ffprobe")
        assert info.can_remux_video is False
        assert info.can_remux_audio is True

def test_probe_media_handles_invalid_file(tmp_path):
    corrupt_file = tmp_path / "corrupted.mkv"
    corrupt_file.write_bytes(b"corrupt")

    mock_res = MagicMock()
    mock_res.returncode = 1
    mock_res.stderr = "Invalid data found when processing input"
    
    with patch("subprocess.run", return_value=mock_res):
        with pytest.raises(RuntimeError) as exc_info:
            probe_media(str(corrupt_file), ffprobe_path="ffprobe")
        assert "Failed to probe" in str(exc_info.value)
