"""Queue controller and conversion workflow manager."""

import os
import uuid
import threading
from enum import Enum
from pathlib import Path
from typing import Callable, List, Optional, Dict, Any

from converter.engine import (
    ConversionConfig,
    FFmpegEngine,
    ProgressUpdate,
    FORMAT_EXTENSIONS,
)
from converter.probe import MediaInfo, probe_media

VALID_INPUT_EXTENSIONS = {
    ".mkv", ".webm", ".avi", ".mov", ".flv", ".ts", ".mp4", ".m4v", ".wmv", ".vob", ".mpg", ".mpeg"
}


class QueueItemStatus(Enum):
    PENDING = "Pending"
    PROBING = "Probing"
    CONVERTING = "Converting"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"


class QueueItem:
    def __init__(self, input_path: str, output_path: str):
        self.id = str(uuid.uuid4())
        self.input_path = input_path
        self.output_path = output_path
        self.status = QueueItemStatus.PENDING
        self.media_info: Optional[MediaInfo] = None
        self.progress: float = 0.0
        self.speed: str = "N/A"
        self.eta: str = "--:--"
        self.elapsed_sec: float = 0.0
        self.error_msg: Optional[str] = None

    @property
    def filename(self) -> str:
        return Path(self.input_path).name

    @property
    def file_size_str(self) -> str:
        try:
            sz = os.path.getsize(self.input_path)
            if sz > 1024 * 1024 * 1024:
                return f"{sz / (1024 * 1024 * 1024):.2f} GB"
            elif sz > 1024 * 1024:
                return f"{sz / (1024 * 1024):.1f} MB"
            return f"{sz / 1024:.0f} KB"
        except Exception:
            return "Unknown"


def generate_safe_output_path(
    input_path: str,
    output_dir: Optional[str] = None,
    target_ext: str = ".mp4",
    overwrite: bool = False,
) -> str:
    """Generate a collision-safe destination path."""
    src = Path(input_path)
    stem = src.stem
    dest_dir = Path(output_dir) if output_dir else src.parent

    base_candidate = dest_dir / f"{stem}{target_ext}"
    if overwrite or not base_candidate.exists():
        return str(base_candidate.resolve())

    counter = 1
    while True:
        candidate = dest_dir / f"{stem}_{counter}{target_ext}"
        if not candidate.exists():
            return str(candidate.resolve())
        counter += 1


class ConversionController:
    """Controls the conversion queue, options, and engine coordination."""

    def __init__(self, engine: Optional[FFmpegEngine] = None):
        self.engine = engine or FFmpegEngine()
        self.queue: List[QueueItem] = []
        self.output_directory: Optional[str] = None
        self.overwrite: bool = False
        self.target_format_label: str = "MP4 (.mp4)"
        self.video_codec: str = "copy"
        self.audio_codec: str = "copy"
        self.audio_bitrate: Optional[str] = None
        self.video_crf: Optional[int] = None
        self.video_preset: Optional[str] = None

        self._current_index: int = -1
        self._is_running: bool = False
        self._lock = threading.Lock()

        # Callbacks for UI updates
        self.on_item_added: Optional[Callable[[QueueItem], None]] = None
        self.on_item_updated: Optional[Callable[[QueueItem], None]] = None
        self.on_queue_finished: Optional[Callable[[], None]] = None

    @property
    def queue_length(self) -> int:
        return len(self.queue)

    @property
    def completed_count(self) -> int:
        return sum(1 for item in self.queue if item.status == QueueItemStatus.COMPLETED)

    @property
    def target_extension(self) -> str:
        return FORMAT_EXTENSIONS.get(self.target_format_label, ".mp4")

    def add_items(self, paths: List[str]) -> List[QueueItem]:
        """Add files or directories to the conversion queue."""
        added: List[QueueItem] = []
        target_ext = self.target_extension

        for p_str in paths:
            p = Path(p_str)
            if not p.exists():
                continue

            candidates = []
            if p.is_dir():
                for root, _, files in os.walk(p):
                    for file in files:
                        if Path(file).suffix.lower() in VALID_INPUT_EXTENSIONS:
                            candidates.append(os.path.join(root, file))
            elif p.is_file() and p.suffix.lower() in VALID_INPUT_EXTENSIONS:
                candidates.append(str(p))

            for cand_path in candidates:
                out_path = generate_safe_output_path(
                    cand_path,
                    output_dir=self.output_directory,
                    target_ext=target_ext,
                    overwrite=self.overwrite,
                )
                item = QueueItem(input_path=cand_path, output_path=out_path)
                
                # Probe metadata
                try:
                    info = probe_media(cand_path, ffprobe_path=None)
                    item.media_info = info
                except Exception:
                    pass

                with self._lock:
                    self.queue.append(item)
                    added.append(item)

                if self.on_item_added:
                    self.on_item_added(item)

        return added

    def remove_item(self, item_id: str) -> None:
        """Remove an item from the queue if not currently converting."""
        with self._lock:
            for i, item in enumerate(self.queue):
                if item.id == item_id:
                    if item.status == QueueItemStatus.CONVERTING:
                        self.cancel_current()
                    self.queue.pop(i)
                    break

    def clear_completed(self) -> None:
        """Clear all finished/cancelled/failed items from queue."""
        with self._lock:
            self.queue = [
                item for item in self.queue
                if item.status in (QueueItemStatus.PENDING, QueueItemStatus.CONVERTING)
            ]

    def clear_all(self) -> None:
        """Clear the whole queue, cancelling any active conversion."""
        if self._is_running:
            self.cancel_all()
        with self._lock:
            self.queue.clear()

    def start(self) -> None:
        """Start or resume queue conversion."""
        if self._is_running:
            return
        self._is_running = True
        self._process_next()

    def _process_next(self) -> None:
        """Process the next pending item in the queue."""
        next_item: Optional[QueueItem] = None
        with self._lock:
            for item in self.queue:
                if item.status == QueueItemStatus.PENDING:
                    next_item = item
                    break

        if not next_item or not self._is_running:
            self._is_running = False
            if self.on_queue_finished:
                self.on_queue_finished()
            return

        next_item.status = QueueItemStatus.CONVERTING
        if self.on_item_updated:
            self.on_item_updated(next_item)

        # Refresh output path based on current settings
        next_item.output_path = generate_safe_output_path(
            next_item.input_path,
            output_dir=self.output_directory,
            target_ext=self.target_extension,
            overwrite=self.overwrite,
        )

        # Ensure media info is probed
        if not next_item.media_info:
            try:
                next_item.media_info = probe_media(next_item.input_path)
            except Exception:
                pass

        total_duration = next_item.media_info.duration if next_item.media_info else 0.0

        config = ConversionConfig(
            input_path=next_item.input_path,
            output_path=next_item.output_path,
            output_format=self.target_extension.lstrip("."),
            video_codec=self.video_codec,
            audio_codec=self.audio_codec,
            audio_bitrate=self.audio_bitrate,
            video_crf=self.video_crf,
            video_preset=self.video_preset,
        )

        def _on_progress(update: ProgressUpdate):
            next_item.progress = update.percent
            next_item.speed = update.speed
            next_item.elapsed_sec = update.elapsed_sec
            if update.eta_sec > 0:
                mins = int(update.eta_sec // 60)
                secs = int(update.eta_sec % 60)
                next_item.eta = f"{mins:02d}:{secs:02d}"
            else:
                next_item.eta = "00:00"
            if self.on_item_updated:
                self.on_item_updated(next_item)

        def _on_complete(success: bool, error_msg: Optional[str]):
            if success:
                next_item.status = QueueItemStatus.COMPLETED
                next_item.progress = 100.0
                next_item.eta = "00:00"
            else:
                if error_msg == "Cancelled by user.":
                    next_item.status = QueueItemStatus.CANCELLED
                else:
                    next_item.status = QueueItemStatus.FAILED
                    next_item.error_msg = error_msg

            if self.on_item_updated:
                self.on_item_updated(next_item)

            if self._is_running:
                # Proceed to next item
                self._process_next()

        self.engine.start(config, total_duration, _on_progress, _on_complete)

    def cancel_current(self) -> None:
        """Cancel active conversion and proceed."""
        self.engine.cancel()

    def cancel_all(self) -> None:
        """Stop queue processing and cancel active conversion."""
        self._is_running = False
        self.engine.cancel()
