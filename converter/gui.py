"""Modern desktop GUI for MKV to MP4 Converter using CustomTkinter."""

import os
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional, Dict

import customtkinter as ctk

from converter.controller import (
    ConversionController,
    QueueItem,
    QueueItemStatus,
)
from converter.engine import (
    FORMAT_EXTENSIONS,
    VIDEO_CODECS,
    AUDIO_CODECS,
    AUDIO_BITRATES,
    CRF_PRESETS,
    SPEED_PRESETS,
)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class MainWindow(ctk.CTk):
    """Main application window for MKV to MP4 Converter."""

    def __init__(self, controller: Optional[ConversionController] = None):
        super().__init__()
        self.controller = controller or ConversionController()

        self.title("MKV to MP4 Converter - Fast, Light & 100% Audio Preserved")
        self.geometry("980x720")
        self.minsize(860, 600)

        # Wire controller callbacks with thread-safe dispatch
        self.controller.on_item_added = lambda item: self.after(0, self._render_queue_item, item)
        self.controller.on_item_updated = lambda item: self.after(0, self._update_queue_item_ui, item)
        self.controller.on_queue_finished = lambda: self.after(0, self._on_queue_finished)

        self._item_rows: Dict[str, Dict[str, ctk.CTkBaseClass]] = {}

        self._build_ui()

    def _build_ui(self) -> None:
        # 1. Header Frame
        header_frame = ctk.CTkFrame(self, corner_radius=10, fg_color=("gray85", "#1e1e24"))
        header_frame.pack(fill="x", padx=16, pady=(14, 8))

        title_label = ctk.CTkLabel(
            header_frame,
            text="MKV to MP4 Converter",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        title_label.pack(side="left", padx=16, pady=12)

        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Ultra-Fast Remuxing • 100% Lossless Audio Preservation • Multi-Format",
            font=ctk.CTkFont(size=12),
            text_color="gray60",
        )
        subtitle_label.pack(side="left", padx=8, pady=12)

        # 2. Options / Codec Selectors Bar
        options_frame = ctk.CTkFrame(self, corner_radius=10, fg_color=("gray90", "#24242d"))
        options_frame.pack(fill="x", padx=16, pady=6)

        # Output Format
        col1 = ctk.CTkFrame(options_frame, fg_color="transparent")
        col1.pack(side="left", padx=10, pady=8)
        ctk.CTkLabel(col1, text="Container Format:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        self.format_var = ctk.StringVar(value="MP4 (.mp4)")
        self.format_dropdown = ctk.CTkOptionMenu(
            col1,
            variable=self.format_var,
            values=list(FORMAT_EXTENSIONS.keys()),
            command=self._on_options_changed,
            width=140,
        )
        self.format_dropdown.pack(pady=(2, 0))

        # Video Codec
        col2 = ctk.CTkFrame(options_frame, fg_color="transparent")
        col2.pack(side="left", padx=10, pady=8)
        ctk.CTkLabel(col2, text="Video Codec:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        self.video_codec_var = ctk.StringVar(value="Copy (100% Lossless, Instant)")
        self.video_codec_dropdown = ctk.CTkOptionMenu(
            col2,
            variable=self.video_codec_var,
            values=list(VIDEO_CODECS.keys()),
            command=self._on_options_changed,
            width=175,
        )
        self.video_codec_dropdown.pack(pady=(2, 0))

        # Audio Codec (100% Lossless copy default)
        col3 = ctk.CTkFrame(options_frame, fg_color="transparent")
        col3.pack(side="left", padx=10, pady=8)
        ctk.CTkLabel(col3, text="Audio Codec:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        self.audio_codec_var = ctk.StringVar(value="Copy (100% Lossless, Instant)")
        self.audio_codec_dropdown = ctk.CTkOptionMenu(
            col3,
            variable=self.audio_codec_var,
            values=list(AUDIO_CODECS.keys()),
            command=self._on_options_changed,
            width=175,
        )
        self.audio_codec_dropdown.pack(pady=(2, 0))

        # Audio Bitrate
        col4 = ctk.CTkFrame(options_frame, fg_color="transparent")
        col4.pack(side="left", padx=10, pady=8)
        ctk.CTkLabel(col4, text="Audio Bitrate:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        self.audio_bitrate_var = ctk.StringVar(value="Source / Default")
        self.audio_bitrate_dropdown = ctk.CTkOptionMenu(
            col4,
            variable=self.audio_bitrate_var,
            values=AUDIO_BITRATES,
            command=self._on_options_changed,
            width=120,
        )
        self.audio_bitrate_dropdown.pack(pady=(2, 0))

        # Video CRF Quality
        col5 = ctk.CTkFrame(options_frame, fg_color="transparent")
        col5.pack(side="left", padx=10, pady=8)
        ctk.CTkLabel(col5, text="Video CRF Quality:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        self.crf_var = ctk.StringVar(value="23 (Default Balance)")
        self.crf_dropdown = ctk.CTkOptionMenu(
            col5,
            variable=self.crf_var,
            values=CRF_PRESETS,
            command=self._on_options_changed,
            width=150,
        )
        self.crf_dropdown.pack(pady=(2, 0))

        # 3. Queue Action Bar
        action_bar = ctk.CTkFrame(self, fg_color="transparent")
        action_bar.pack(fill="x", padx=16, pady=4)

        self.btn_add_files = ctk.CTkButton(
            action_bar,
            text="+ Add MKV Files",
            width=140,
            command=self._choose_files,
            font=ctk.CTkFont(weight="bold"),
        )
        self.btn_add_files.pack(side="left", padx=(0, 8))

        self.btn_add_folder = ctk.CTkButton(
            action_bar,
            text="+ Add Folder",
            width=120,
            command=self._choose_folder,
            fg_color="#3a3f47",
            hover_color="#4f5661",
        )
        self.btn_add_folder.pack(side="left", padx=(0, 8))

        self.btn_clear = ctk.CTkButton(
            action_bar,
            text="Clear Queue",
            width=100,
            command=self._clear_queue,
            fg_color="#443333",
            hover_color="#663333",
        )
        self.btn_clear.pack(side="left", padx=(0, 8))

        self.btn_out_dir = ctk.CTkButton(
            action_bar,
            text="Output Folder: Same as Source",
            command=self._choose_output_dir,
            fg_color="transparent",
            border_width=1,
            text_color=("gray20", "gray80"),
        )
        self.btn_out_dir.pack(side="right")

        # 4. Scrollable Queue List
        queue_container = ctk.CTkFrame(self, corner_radius=10, fg_color=("gray95", "#18181f"))
        queue_container.pack(fill="both", expand=True, padx=16, pady=6)

        queue_header = ctk.CTkFrame(queue_container, height=28, fg_color=("gray85", "#22222b"))
        queue_header.pack(fill="x", padx=4, pady=(4, 2))

        ctk.CTkLabel(queue_header, text="File Name", font=ctk.CTkFont(weight="bold", size=11)).pack(side="left", padx=12)
        ctk.CTkLabel(queue_header, text="Size", font=ctk.CTkFont(weight="bold", size=11)).pack(side="left", padx=160)
        ctk.CTkLabel(queue_header, text="Detected Codecs", font=ctk.CTkFont(weight="bold", size=11)).pack(side="left", padx=20)
        ctk.CTkLabel(queue_header, text="Status & Progress", font=ctk.CTkFont(weight="bold", size=11)).pack(side="right", padx=30)

        self.queue_scroll = ctk.CTkScrollableFrame(queue_container, fg_color="transparent")
        self.queue_scroll.pack(fill="both", expand=True, padx=4, pady=2)

        self.empty_label = ctk.CTkLabel(
            self.queue_scroll,
            text="No files added yet.\nClick '+ Add MKV Files' or '+ Add Folder' to begin.",
            font=ctk.CTkFont(size=14),
            text_color="gray50",
        )
        self.empty_label.pack(pady=60)

        # 5. Active Conversion Card with Progress Bar
        self.active_card = ctk.CTkFrame(self, corner_radius=10, fg_color=("gray85", "#1c1c24"))
        self.active_card.pack(fill="x", padx=16, pady=6)

        card_top = ctk.CTkFrame(self.active_card, fg_color="transparent")
        card_top.pack(fill="x", padx=16, pady=(10, 4))

        self.current_file_label = ctk.CTkLabel(
            card_top,
            text="Ready to convert",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.current_file_label.pack(side="left")

        self.metrics_label = ctk.CTkLabel(
            card_top,
            text="Progress: 0.0%  |  Speed: --  |  Elapsed: 00:00  |  ETA: --:--",
            font=ctk.CTkFont(size=12),
            text_color="gray70",
        )
        self.metrics_label.pack(side="right")

        # Smooth Progress Bar for Current Conversion
        self.progress_bar = ctk.CTkProgressBar(self.active_card, height=14, corner_radius=7)
        self.progress_bar.set(0.0)
        self.progress_bar.pack(fill="x", padx=16, pady=(2, 8))

        # Overall Queue Progress
        card_bottom = ctk.CTkFrame(self.active_card, fg_color="transparent")
        card_bottom.pack(fill="x", padx=16, pady=(0, 8))

        self.queue_summary_label = ctk.CTkLabel(
            card_bottom,
            text="Queue: 0 files",
            font=ctk.CTkFont(size=11),
            text_color="gray60",
        )
        self.queue_summary_label.pack(side="left")

        self.overall_progress_bar = ctk.CTkProgressBar(card_bottom, height=8, width=250, corner_radius=4)
        self.overall_progress_bar.set(0.0)
        self.overall_progress_bar.pack(side="right")

        # 6. Bottom Controls
        bottom_bar = ctk.CTkFrame(self, fg_color="transparent")
        bottom_bar.pack(fill="x", padx=16, pady=(6, 12))

        self.btn_start = ctk.CTkButton(
            bottom_bar,
            text="Start Conversion",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            width=180,
            command=self._start_conversion,
            fg_color="#1f77d0",
            hover_color="#185fa7",
        )
        self.btn_start.pack(side="left", padx=(0, 10))

        self.btn_cancel = ctk.CTkButton(
            bottom_bar,
            text="Cancel Current",
            height=40,
            width=130,
            command=self._cancel_current,
            fg_color="#6e2d2d",
            hover_color="#8b3939",
            state="disabled",
        )
        self.btn_cancel.pack(side="left", padx=(0, 10))

        self.btn_open_folder = ctk.CTkButton(
            bottom_bar,
            text="Open Output Folder",
            height=40,
            width=150,
            command=self._open_output_folder,
            fg_color="#2b313a",
            hover_color="#3e4652",
        )
        self.btn_open_folder.pack(side="right")

    def _on_options_changed(self, *_) -> None:
        """Sync GUI dropdown values into controller."""
        self.controller.target_format_label = self.format_var.get()
        self.controller.video_codec = VIDEO_CODECS.get(self.video_codec_var.get(), "copy")
        self.controller.audio_codec = AUDIO_CODECS.get(self.audio_codec_var.get(), "copy")

        bitrate = self.audio_bitrate_var.get()
        self.controller.audio_bitrate = None if bitrate.startswith("Source") else bitrate

        crf_choice = self.crf_var.get()
        if "18" in crf_choice:
            self.controller.video_crf = 18
        elif "28" in crf_choice:
            self.controller.video_crf = 28
        else:
            self.controller.video_crf = 23

    def _choose_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Select Video Files",
            filetypes=[
                ("MKV & Video Files", "*.mkv;*.webm;*.avi;*.mov;*.flv;*.ts;*.mp4"),
                ("MKV Video (*.mkv)", "*.mkv"),
                ("All Files (*.*)", "*.*"),
            ],
        )
        if paths:
            self.controller.add_items(list(paths))
            self._update_queue_summary()

    def _choose_folder(self) -> None:
        folder = filedialog.askdirectory(title="Select Folder Containing MKV Videos")
        if folder:
            self.controller.add_items([folder])
            self._update_queue_summary()

    def _choose_output_dir(self) -> None:
        folder = filedialog.askdirectory(title="Choose Output Destination Directory")
        if folder:
            self.controller.output_directory = folder
            disp = Path(folder).name or folder
            self.btn_out_dir.configure(text=f"Output: {disp}")
        else:
            self.controller.output_directory = None
            self.btn_out_dir.configure(text="Output Folder: Same as Source")

    def _clear_queue(self) -> None:
        self.controller.clear_all()
        for row in self._item_rows.values():
            for widget in row.values():
                if isinstance(widget, ctk.CTkBaseClass):
                    widget.destroy()
        self._item_rows.clear()
        self.empty_label.pack(pady=60)
        self.progress_bar.set(0.0)
        self.overall_progress_bar.set(0.0)
        self.current_file_label.configure(text="Ready to convert")
        self.metrics_label.configure(text="Progress: 0.0%  |  Speed: --  |  Elapsed: 00:00  |  ETA: --:--")
        self._update_queue_summary()

    def _render_queue_item(self, item: QueueItem) -> None:
        self.empty_label.pack_forget()

        row_frame = ctk.CTkFrame(self.queue_scroll, height=36, fg_color=("gray90", "#21212b"))
        row_frame.pack(fill="x", pady=2)

        name_label = ctk.CTkLabel(
            row_frame,
            text=item.filename,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
            width=250,
        )
        name_label.pack(side="left", padx=10)

        size_label = ctk.CTkLabel(
            row_frame,
            text=item.file_size_str,
            font=ctk.CTkFont(size=11),
            text_color="gray60",
            width=80,
            anchor="w",
        )
        size_label.pack(side="left", padx=10)

        # Codec badge
        codec_text = "Probing..."
        if item.media_info:
            v_codec = item.media_info.primary_video_codec.upper()
            a_codec = item.media_info.primary_audio_codec.upper()
            codec_text = f"{v_codec} / {a_codec}"
            if item.media_info.can_remux_video and item.media_info.can_remux_audio:
                codec_text += " (Lossless Remux)"
        codec_label = ctk.CTkLabel(
            row_frame,
            text=codec_text,
            font=ctk.CTkFont(size=11),
            text_color="#5cb85c" if "Lossless" in codec_text else "gray70",
            width=180,
            anchor="w",
        )
        codec_label.pack(side="left", padx=10)

        status_label = ctk.CTkLabel(
            row_frame,
            text=item.status.value,
            font=ctk.CTkFont(size=11, weight="bold"),
            width=120,
            anchor="e",
        )
        status_label.pack(side="right", padx=12)

        self._item_rows[item.id] = {
            "frame": row_frame,
            "status": status_label,
            "codec": codec_label,
        }
        self._update_queue_summary()

    def _update_queue_item_ui(self, item: QueueItem) -> None:
        if item.id in self._item_rows:
            status_label = self._item_rows[item.id]["status"]
            if item.status == QueueItemStatus.CONVERTING:
                status_label.configure(text=f"{item.progress:.1f}%", text_color="#1f77d0")
            elif item.status == QueueItemStatus.COMPLETED:
                status_label.configure(text="Completed", text_color="#5cb85c")
            elif item.status == QueueItemStatus.FAILED:
                status_label.configure(text="Failed", text_color="#d9534f")
            elif item.status == QueueItemStatus.CANCELLED:
                status_label.configure(text="Cancelled", text_color="#f0ad4e")

        if item.status == QueueItemStatus.CONVERTING:
            self.current_file_label.configure(text=f"Converting: {item.filename}")
            mins = int(item.elapsed_sec // 60)
            secs = int(item.elapsed_sec % 60)
            self.metrics_label.configure(
                text=f"Progress: {item.progress:.1f}%  |  Speed: {item.speed}  |  Elapsed: {mins:02d}:{secs:02d}  |  ETA: {item.eta}"
            )
            self.progress_bar.set(item.progress / 100.0)

        self._update_queue_summary()

    def _update_queue_summary(self) -> None:
        total = self.controller.queue_length
        completed = self.controller.completed_count
        self.queue_summary_label.configure(text=f"Queue: {completed} / {total} converted")
        if total > 0:
            self.overall_progress_bar.set(completed / float(total))
        else:
            self.overall_progress_bar.set(0.0)

    def _start_conversion(self) -> None:
        if self.controller.queue_length == 0:
            messagebox.showinfo("Queue Empty", "Please add one or more MKV video files first.")
            return

        self._on_options_changed()
        self.btn_start.configure(state="disabled")
        self.btn_cancel.configure(state="normal")
        self.controller.start()

    def _cancel_current(self) -> None:
        self.controller.cancel_current()

    def _on_queue_finished(self) -> None:
        self.btn_start.configure(state="normal")
        self.btn_cancel.configure(state="disabled")
        self.current_file_label.configure(text="All conversions completed!")
        self.progress_bar.set(1.0)
        self._update_queue_summary()
        messagebox.showinfo("Done", "All conversions in queue have finished.")

    def _open_output_folder(self) -> None:
        out_dir = self.controller.output_directory
        if not out_dir:
            # Default to destination of first queue item or current directory
            if self.controller.queue:
                out_dir = str(Path(self.controller.queue[0].output_path).parent)
            else:
                out_dir = os.getcwd()

        if os.path.exists(out_dir):
            if sys.platform == "win32":
                os.startfile(out_dir)
            else:
                subprocess.Popen(["xdg-open", out_dir])


def main():
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
