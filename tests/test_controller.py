import os
import pytest
from unittest.mock import MagicMock, patch
from converter.controller import (
    ConversionController,
    QueueItem,
    QueueItemStatus,
    generate_safe_output_path
)
from converter.probe import MediaInfo

def test_generate_safe_output_path_without_collision(tmp_path):
    input_file = tmp_path / "movie.mkv"
    input_file.write_text("dummy")
    out = generate_safe_output_path(str(input_file), output_dir=None, target_ext=".mp4", overwrite=False)
    assert out == str(tmp_path / "movie.mp4")

def test_generate_safe_output_path_with_collision(tmp_path):
    input_file = tmp_path / "movie.mkv"
    input_file.write_text("dummy")
    collision_file = tmp_path / "movie.mp4"
    collision_file.write_text("exists")
    
    out = generate_safe_output_path(str(input_file), output_dir=None, target_ext=".mp4", overwrite=False)
    assert out == str(tmp_path / "movie_1.mp4")

def test_controller_add_items(tmp_path):
    mkv_1 = tmp_path / "test1.mkv"
    mkv_1.write_text("1")
    mkv_2 = tmp_path / "test2.mkv"
    mkv_2.write_text("2")
    txt_file = tmp_path / "ignore.txt"
    txt_file.write_text("txt")
    
    controller = ConversionController()
    items = controller.add_items([str(mkv_1), str(mkv_2), str(txt_file)])
    assert len(items) == 2
    assert controller.queue_length == 2
    assert items[0].status == QueueItemStatus.PENDING

def test_controller_queue_progression(tmp_path):
    mkv_file = tmp_path / "video.mkv"
    mkv_file.write_text("dummy video")
    
    fake_info = MediaInfo(
        file_path=str(mkv_file),
        duration=10.0,
        size_bytes=1000,
        video_streams=[],
        audio_streams=[],
        can_remux_video=True,
        can_remux_audio=True
    )
    
    controller = ConversionController()
    with patch("converter.controller.probe_media", return_value=fake_info):
        items = controller.add_items([str(mkv_file)])
    
    item = items[0]
    assert item.media_info == fake_info

    # Mock engine execution
    mock_engine = MagicMock()
    controller.engine = mock_engine

    def fake_start(config, duration, on_progress, on_complete):
        # Simulate completion
        on_complete(True, None)

    mock_engine.start.side_effect = fake_start
    
    controller.start()
    assert item.status == QueueItemStatus.COMPLETED
