"""Modern Fintech / Executive Dashboard styling for MKV to MP4 Converter."""

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
)

# Color Palette inspired by the modern sleek dark UI with coral-red & amber highlights
THEME = {
    "dark": {
        "bg": "#16171b",            # Deep slate background
        "card_bg": "#1f2026",       # Elevated card background
        "card_sub_bg": "#282a32",   # Inner nested widgets
        "sidebar_bg": "#1c1d22",    # Right panel background
        "accent": "#ff4d4d",        # Vibrant coral red
        "accent_hover": "#e63939",
        "secondary_accent": "#f5a623", # Amber yellow
        "text": "#ffffff",
        "text_sub": "#8f92a1",
        "border": "#2c2d36",
        "success": "#2ecc71",
        "warning": "#f39c12",
        "danger": "#e74c3c"
    },
    "light": {
        "bg": "#f4f5f9",            # Clean soft light gray
        "card_bg": "#ffffff",       # Pure white cards
        "card_sub_bg": "#f0f2f6",   # Inner nested widgets
        "sidebar_bg": "#eaecef",    # Right panel background
        "accent": "#ff4d4d",        # Vibrant coral red
        "accent_hover": "#e63939",
        "secondary_accent": "#f5a623",
        "text": "#1a1c22",
        "text_sub": "#6c7080",
        "border": "#dbe0ea",
        "success": "#27ae60",
        "warning": "#d35400",
        "danger": "#c0392b"
    }
}


class ModernDashboardWindow(ctk.CTk):
    """Sleek, modern Dashboard style UI for media conversion with Light/Dark mode."""

    def __init__(self, controller: Optional[ConversionController] = None):
        super().__init__()
        self.controller = controller or ConversionController()

        self.title("Media Studio Pro • Ultra-Fast MKV to MP4 Converter")
        self.geometry("1100x740")
        self.minsize(980, 640)

        # Set default appearance mode
        self.current_mode = "Dark"
        ctk.set_appearance_mode(self.current_mode)
        ctk.set_default_color_theme("blue")

        # Configure root window background
        self.configure(fg_color=("#f4f5f9", "#16171b"))

        # Connect controller callbacks safely to UI thread
        self.controller.on_item_added = lambda item: self.after(0, self._render_queue_item, item)
        self.controller.on_item_updated = lambda item: self.after(0, self._update_queue_item_ui, item)
        self.controller.on_queue_finished = lambda: self.after(0, self._on_queue_finished)

        self._item_rows: Dict[str, Dict[str, ctk.CTkBaseClass]] = {}

        self._build_dashboard_layout()

    def _build_dashboard_layout(self) -> None:
        # Main layout: Left Content Area + Right Profile & Quick Stats Sidebar
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # ----------------- TOP NAVIGATION BAR -----------------
        self._build_navbar()

        # ----------------- BODY: 2 COLUMNS -----------------
        self.body_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.body_frame.pack(fill="both", expand=True, pady=(16, 0))

        # Left Column (70% width): Queue & Conversion Hub
        self.left_col = ctk.CTkFrame(self.body_frame, fg_color="transparent")
        self.left_col.pack(side="left", fill="both", expand=True, padx=(0, 14))

        # Right Column (30% width): Studio Engine Settings & Stats Panel
        self.right_col = ctk.CTkFrame(
            self.body_frame,
            width=320,
            corner_radius=18,
            fg_color=("#ffffff", "#1f2026"),
            border_width=1,
            border_color=("#e2e5ec", "#2a2b34")
        )
        self.right_col.pack(side="right", fill="y", padx=(0, 0))
        self.right_col.pack_propagate(False)

        # Build Left Section Components
        self._build_metric_cards()
        self._build_queue_section()
        self._build_active_conversion_card()

        # Build Right Section Components
        self._build_sidebar()

    def _build_navbar(self) -> None:
        """Top bar with Brand pill, navigation items, and Theme toggle switch."""
        navbar = ctk.CTkFrame(self.main_container, height=52, fg_color="transparent")
        navbar.pack(fill="x")

        # Brand Icon Badge (Red/White badge style from inspiration image)
        brand_icon = ctk.CTkButton(
            navbar,
            text="●",
            width=38,
            height=38,
            corner_radius=19,
            fg_color="#ff4d4d",
            hover_color="#e63939",
            text_color="#ffffff",
            font=ctk.CTkFont(size=20, weight="bold"),
            command=None
        )
        brand_icon.pack(side="left", padx=(0, 12))

        title_lbl = ctk.CTkLabel(
            navbar,
            text="Media Studio",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=("#1a1c22", "#ffffff")
        )
        title_lbl.pack(side="left", padx=(0, 20))

        # Nav links
        nav_dashboard = ctk.CTkLabel(
            navbar,
            text="Dashboard",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ff4d4d"
        )
        nav_dashboard.pack(side="left", padx=12)

        nav_queue = ctk.CTkLabel(
            navbar,
            text="Conversion Queue",
            font=ctk.CTkFont(size=13),
            text_color=("#6c7080", "#8f92a1")
        )
        nav_queue.pack(side="left", padx=12)

        # Right side of navbar: Theme Switch (Light/Dark) & Mode badge
        self.theme_switch = ctk.CTkSwitch(
            navbar,
            text="Dark Mode",
            command=self._toggle_theme,
            font=ctk.CTkFont(size=12, weight="bold"),
            progress_color="#ff4d4d",
            switch_width=44,
            switch_height=22
        )
        self.theme_switch.select()
        self.theme_switch.pack(side="right", padx=(10, 0))

    def _toggle_theme(self) -> None:
        if self.theme_switch.get() == 1:
            self.current_mode = "Dark"
            ctk.set_appearance_mode("Dark")
            self.theme_switch.configure(text="Dark Mode")
        else:
            self.current_mode = "Light"
            ctk.set_appearance_mode("Light")
            self.theme_switch.configure(text="Light Mode")

    def _build_metric_cards(self) -> None:
        """Top row of stat summary cards (Files in Queue, Processed, Audio Mode)."""
        metrics_row = ctk.CTkFrame(self.left_col, fg_color="transparent")
        metrics_row.pack(fill="x", pady=(0, 12))

        # Card 1: Lossless Audio Mode Badge
        c1 = ctk.CTkFrame(
            metrics_row,
            corner_radius=16,
            fg_color=("#ffffff", "#1f2026"),
            border_width=1,
            border_color=("#e2e5ec", "#2a2b34")
        )
        c1.pack(side="left", fill="both", expand=True, padx=(0, 8))

        ctk.CTkLabel(
            c1,
            text="AUDIO PRESERVATION",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("#ff4d4d", "#ff4d4d")
        ).pack(anchor="w", padx=16, pady=(12, 2))

        ctk.CTkLabel(
            c1,
            text="100% Bit-for-Bit",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("#1a1c22", "#ffffff")
        ).pack(anchor="w", padx=16)

        ctk.CTkLabel(
            c1,
            text="Stream Copy • Zero generation loss",
            font=ctk.CTkFont(size=11),
            text_color=("#6c7080", "#8f92a1")
        ).pack(anchor="w", padx=16, pady=(2, 12))

        # Card 2: Queue Metrics
        c2 = ctk.CTkFrame(
            metrics_row,
            corner_radius=16,
            fg_color=("#ffffff", "#1f2026"),
            border_width=1,
            border_color=("#e2e5ec", "#2a2b34")
        )
        c2.pack(side="left", fill="both", expand=True, padx=(0, 8))

        ctk.CTkLabel(
            c2,
            text="CONVERSION STATUS",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("#f5a623", "#f5a623")
        ).pack(anchor="w", padx=16, pady=(12, 2))

        self.stat_queue_lbl = ctk.CTkLabel(
            c2,
            text="0 / 0 Completed",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("#1a1c22", "#ffffff")
        )
        self.stat_queue_lbl.pack(anchor="w", padx=16)

        self.stat_sub_lbl = ctk.CTkLabel(
            c2,
            text="Queue is waiting for videos",
            font=ctk.CTkFont(size=11),
            text_color=("#6c7080", "#8f92a1")
        )
        self.stat_sub_lbl.pack(anchor="w", padx=16, pady=(2, 12))

        # Card 3: Instant Remux Engine Indicator
        c3 = ctk.CTkFrame(
            metrics_row,
            corner_radius=16,
            fg_color=("#ffffff", "#1f2026"),
            border_width=1,
            border_color=("#e2e5ec", "#2a2b34")
        )
        c3.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(
            c3,
            text="ENGINE MODE",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("#2ecc71", "#2ecc71")
        ).pack(anchor="w", padx=16, pady=(12, 2))

        self.stat_engine_lbl = ctk.CTkLabel(
            c3,
            text="Ultra-Fast Remux",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("#1a1c22", "#ffffff")
        )
        self.stat_engine_lbl.pack(anchor="w", padx=16)

        ctk.CTkLabel(
            c3,
            text="Direct Stream Copy Enabled",
            font=ctk.CTkFont(size=11),
            text_color=("#6c7080", "#8f92a1")
        ).pack(anchor="w", padx=16, pady=(2, 12))

    def _build_queue_section(self) -> None:
        """Card containing the file list with modern clean typography and action bar."""
        self.queue_card = ctk.CTkFrame(
            self.left_col,
            corner_radius=16,
            fg_color=("#ffffff", "#1f2026"),
            border_width=1,
            border_color=("#e2e5ec", "#2a2b34")
        )
        self.queue_card.pack(fill="both", expand=True, pady=(0, 12))

        # Card Header with Action Buttons
        card_header = ctk.CTkFrame(self.queue_card, fg_color="transparent", height=42)
        card_header.pack(fill="x", padx=18, pady=(14, 8))

        ctk.CTkLabel(
            card_header,
            text="Task Queue",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("#1a1c22", "#ffffff")
        ).pack(side="left")

        # Action Buttons on top right
        btn_clear = ctk.CTkButton(
            card_header,
            text="Clear",
            width=70,
            height=30,
            corner_radius=8,
            fg_color=("#f0f2f6", "#2a2b34"),
            hover_color=("#e2e5ec", "#353742"),
            text_color=("#6c7080", "#8f92a1"),
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._clear_queue
        )
        btn_clear.pack(side="right", padx=(6, 0))

        btn_folder = ctk.CTkButton(
            card_header,
            text="+ Add Folder",
            width=100,
            height=30,
            corner_radius=8,
            fg_color=("#f0f2f6", "#2a2b34"),
            hover_color=("#e2e5ec", "#353742"),
            text_color=("#1a1c22", "#ffffff"),
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._choose_folder
        )
        btn_folder.pack(side="right", padx=(6, 0))

        btn_files = ctk.CTkButton(
            card_header,
            text="+ Add MKV Files",
            width=120,
            height=30,
            corner_radius=8,
            fg_color="#ff4d4d",
            hover_color="#e63939",
            text_color="#ffffff",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._choose_files
        )
        btn_files.pack(side="right")

        # Table Column Header
        col_header = ctk.CTkFrame(self.queue_card, height=26, fg_color=("#f8f9fb", "#18191f"), corner_radius=8)
        col_header.pack(fill="x", padx=16, pady=(0, 6))

        ctk.CTkLabel(
            col_header,
            text="FILE NAME",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("#6c7080", "#8f92a1")
        ).pack(side="left", padx=16)

        ctk.CTkLabel(
            col_header,
            text="STATUS",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("#6c7080", "#8f92a1")
        ).pack(side="right", padx=24)

        ctk.CTkLabel(
            col_header,
            text="CODECS",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("#6c7080", "#8f92a1")
        ).pack(side="right", padx=60)

        # Scrollable Task List
        self.queue_scroll = ctk.CTkScrollableFrame(self.queue_card, fg_color="transparent")
        self.queue_scroll.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.empty_label = ctk.CTkLabel(
            self.queue_scroll,
            text="No files added yet.\nClick '+ Add MKV Files' or '+ Add Folder' to begin your conversions.",
            font=ctk.CTkFont(size=13),
            text_color=("#8f92a1", "#6c7080")
        )
        self.empty_label.pack(pady=50)

    def _build_active_conversion_card(self) -> None:
        """Card at the bottom showing active conversion, smooth progress bar, and metrics."""
        self.active_card = ctk.CTkFrame(
            self.left_col,
            corner_radius=16,
            fg_color=("#ffffff", "#1f2026"),
            border_width=1,
            border_color=("#e2e5ec", "#2a2b34")
        )
        self.active_card.pack(fill="x")

        top_info = ctk.CTkFrame(self.active_card, fg_color="transparent")
        top_info.pack(fill="x", padx=18, pady=(14, 6))

        self.current_file_label = ctk.CTkLabel(
            top_info,
            text="Standby",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#1a1c22", "#ffffff")
        )
        self.current_file_label.pack(side="left")

        self.metrics_label = ctk.CTkLabel(
            top_info,
            text="0.0%  •  Speed: --  •  ETA: --:--",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#ff4d4d", "#ff4d4d")
        )
        self.metrics_label.pack(side="right")

        # Sleek Coral Progress Bar
        self.progress_bar = ctk.CTkProgressBar(
            self.active_card,
            height=10,
            corner_radius=5,
            progress_color="#ff4d4d",
            fg_color=("#f0f2f6", "#2a2b34")
        )
        self.progress_bar.set(0.0)
        self.progress_bar.pack(fill="x", padx=18, pady=(0, 14))

    def _build_sidebar(self) -> None:
        """Right Studio Panel: Codec controls, format options, and primary Start button."""
        sidebar_content = ctk.CTkFrame(self.right_col, fg_color="transparent")
        sidebar_content.pack(fill="both", expand=True, padx=20, pady=20)

        # Header Profile / Studio Badge (James Martinia style in screenshot)
        studio_badge = ctk.CTkFrame(
            sidebar_content,
            corner_radius=14,
            fg_color=("#f8f9fb", "#282a32"),
            border_width=1,
            border_color=("#e2e5ec", "#33353f")
        )
        studio_badge.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            studio_badge,
            text="CONVERSION SETTINGS",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#ff4d4d"
        ).pack(anchor="w", padx=14, pady=(10, 2))

        ctk.CTkLabel(
            studio_badge,
            text="Studio Engine Control",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#1a1c22", "#ffffff")
        ).pack(anchor="w", padx=14, pady=(0, 10))

        # Format Selector
        ctk.CTkLabel(
            sidebar_content,
            text="Output Container Format",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#6c7080", "#8f92a1")
        ).pack(anchor="w", pady=(4, 2))

        self.format_var = ctk.StringVar(value="MP4 (.mp4)")
        self.format_dropdown = ctk.CTkOptionMenu(
            sidebar_content,
            variable=self.format_var,
            values=list(FORMAT_EXTENSIONS.keys()),
            command=self._on_options_changed,
            fg_color=("#f0f2f6", "#282a32"),
            button_color="#ff4d4d",
            button_hover_color="#e63939",
            text_color=("#1a1c22", "#ffffff"),
            dropdown_fg_color=("#ffffff", "#282a32"),
            dropdown_text_color=("#1a1c22", "#ffffff"),
            corner_radius=8,
            height=34
        )
        self.format_dropdown.pack(fill="x", pady=(0, 10))

        # Video Codec Selector
        ctk.CTkLabel(
            sidebar_content,
            text="Video Codec",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#6c7080", "#8f92a1")
        ).pack(anchor="w", pady=(4, 2))

        self.video_codec_var = ctk.StringVar(value="Copy (100% Lossless, Instant)")
        self.video_codec_dropdown = ctk.CTkOptionMenu(
            sidebar_content,
            variable=self.video_codec_var,
            values=list(VIDEO_CODECS.keys()),
            command=self._on_options_changed,
            fg_color=("#f0f2f6", "#282a32"),
            button_color="#ff4d4d",
            button_hover_color="#e63939",
            text_color=("#1a1c22", "#ffffff"),
            dropdown_fg_color=("#ffffff", "#282a32"),
            dropdown_text_color=("#1a1c22", "#ffffff"),
            corner_radius=8,
            height=34
        )
        self.video_codec_dropdown.pack(fill="x", pady=(0, 10))

        # Audio Codec Selector (100% Lossless copy default)
        ctk.CTkLabel(
            sidebar_content,
            text="Audio Codec (Preservation)",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#6c7080", "#8f92a1")
        ).pack(anchor="w", pady=(4, 2))

        self.audio_codec_var = ctk.StringVar(value="Copy (100% Lossless, Instant)")
        self.audio_codec_dropdown = ctk.CTkOptionMenu(
            sidebar_content,
            variable=self.audio_codec_var,
            values=list(AUDIO_CODECS.keys()),
            command=self._on_options_changed,
            fg_color=("#f0f2f6", "#282a32"),
            button_color="#ff4d4d",
            button_hover_color="#e63939",
            text_color=("#1a1c22", "#ffffff"),
            dropdown_fg_color=("#ffffff", "#282a32"),
            dropdown_text_color=("#1a1c22", "#ffffff"),
            corner_radius=8,
            height=34
        )
        self.audio_codec_dropdown.pack(fill="x", pady=(0, 10))

        # Audio Bitrate
        ctk.CTkLabel(
            sidebar_content,
            text="Audio Bitrate (If Re-encoding)",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#6c7080", "#8f92a1")
        ).pack(anchor="w", pady=(4, 2))

        self.audio_bitrate_var = ctk.StringVar(value="Source / Default")
        self.audio_bitrate_dropdown = ctk.CTkOptionMenu(
            sidebar_content,
            variable=self.audio_bitrate_var,
            values=AUDIO_BITRATES,
            command=self._on_options_changed,
            fg_color=("#f0f2f6", "#282a32"),
            button_color="#ff4d4d",
            button_hover_color="#e63939",
            text_color=("#1a1c22", "#ffffff"),
            dropdown_fg_color=("#ffffff", "#282a32"),
            dropdown_text_color=("#1a1c22", "#ffffff"),
            corner_radius=8,
            height=34
        )
        self.audio_bitrate_dropdown.pack(fill="x", pady=(0, 10))

        # Destination Folder Selector Button
        ctk.CTkLabel(
            sidebar_content,
            text="Output Destination",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#6c7080", "#8f92a1")
        ).pack(anchor="w", pady=(4, 2))

        self.btn_out_dir = ctk.CTkButton(
            sidebar_content,
            text="📁 Same as Source",
            command=self._choose_output_dir,
            fg_color=("#f0f2f6", "#282a32"),
            hover_color=("#e2e5ec", "#353742"),
            text_color=("#1a1c22", "#ffffff"),
            corner_radius=8,
            height=34
        )
        self.btn_out_dir.pack(fill="x", pady=(0, 16))

        # Bottom Action Buttons
        self.btn_start = ctk.CTkButton(
            sidebar_content,
            text="▶  Start Converting",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=44,
            corner_radius=10,
            command=self._start_conversion,
            fg_color="#ff4d4d",
            hover_color="#e63939",
            text_color="#ffffff"
        )
        self.btn_start.pack(fill="x", pady=(4, 8))

        self.btn_cancel = ctk.CTkButton(
            sidebar_content,
            text="⏹  Cancel Current",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=36,
            corner_radius=10,
            command=self._cancel_current,
            fg_color=("#f0f2f6", "#282a32"),
            hover_color=("#e2e5ec", "#353742"),
            text_color=("#6c7080", "#8f92a1"),
            state="disabled"
        )
        self.btn_cancel.pack(fill="x", pady=(0, 8))

        self.btn_open_folder = ctk.CTkButton(
            sidebar_content,
            text="📂 Open Output Folder",
            font=ctk.CTkFont(size=12),
            height=34,
            corner_radius=10,
            command=self._open_output_folder,
            fg_color="transparent",
            hover_color=("#f0f2f6", "#282a32"),
            text_color=("#6c7080", "#8f92a1")
        )
        self.btn_open_folder.pack(fill="x")

    def _on_options_changed(self, *_) -> None:
        """Sync dropdown values into controller."""
        self.controller.target_format_label = self.format_var.get()
        self.controller.video_codec = VIDEO_CODECS.get(self.video_codec_var.get(), "copy")
        self.controller.audio_codec = AUDIO_CODECS.get(self.audio_codec_var.get(), "copy")

        bitrate = self.audio_bitrate_var.get()
        self.controller.audio_bitrate = None if bitrate.startswith("Source") else bitrate

        if self.controller.video_codec == "copy":
            self.stat_engine_lbl.configure(text="Ultra-Fast Remux")
        else:
            self.stat_engine_lbl.configure(text="Encoding Active")

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
            self.btn_out_dir.configure(text=f"📁 {disp}")
        else:
            self.controller.output_directory = None
            self.btn_out_dir.configure(text="📁 Same as Source")

    def _clear_queue(self) -> None:
        self.controller.clear_all()
        for row in self._item_rows.values():
            for widget in row.values():
                if isinstance(widget, ctk.CTkBaseClass):
                    widget.destroy()
        self._item_rows.clear()
        self.empty_label.pack(pady=50)
        self.progress_bar.set(0.0)
        self.current_file_label.configure(text="Standby")
        self.metrics_label.configure(text="0.0%  •  Speed: --  •  ETA: --:--")
        self._update_queue_summary()

    def _render_queue_item(self, item: QueueItem) -> None:
        self.empty_label.pack_forget()

        row_frame = ctk.CTkFrame(
            self.queue_scroll,
            height=44,
            corner_radius=10,
            fg_color=("#f8f9fb", "#282a32")
        )
        row_frame.pack(fill="x", pady=3)

        # File name and size
        info_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        info_frame.pack(side="left", padx=14, pady=6)

        name_label = ctk.CTkLabel(
            info_frame,
            text=item.filename,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#1a1c22", "#ffffff"),
            anchor="w"
        )
        name_label.pack(anchor="w")

        size_label = ctk.CTkLabel(
            info_frame,
            text=item.file_size_str,
            font=ctk.CTkFont(size=10),
            text_color=("#6c7080", "#8f92a1"),
            anchor="w"
        )
        size_label.pack(anchor="w")

        # Status badge on the right
        status_label = ctk.CTkLabel(
            row_frame,
            text=item.status.value,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#6c7080", "#8f92a1")
        )
        status_label.pack(side="right", padx=18)

        # Codec badge
        codec_text = "Probing..."
        if item.media_info:
            v_codec = item.media_info.primary_video_codec.upper()
            a_codec = item.media_info.primary_audio_codec.upper()
            codec_text = f"{v_codec} / {a_codec}"
            if item.media_info.can_remux_video and item.media_info.can_remux_audio:
                codec_text += " • Lossless"

        codec_label = ctk.CTkLabel(
            row_frame,
            text=codec_text,
            font=ctk.CTkFont(size=11),
            text_color="#2ecc71" if "Lossless" in codec_text else ("#6c7080", "#8f92a1")
        )
        codec_label.pack(side="right", padx=30)

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
                status_label.configure(text=f"{item.progress:.1f}%", text_color="#ff4d4d")
            elif item.status == QueueItemStatus.COMPLETED:
                status_label.configure(text="✓ Done", text_color="#2ecc71")
            elif item.status == QueueItemStatus.FAILED:
                status_label.configure(text="✕ Failed", text_color="#e74c3c")
            elif item.status == QueueItemStatus.CANCELLED:
                status_label.configure(text="Cancelled", text_color="#f39c12")

        if item.status == QueueItemStatus.CONVERTING:
            self.current_file_label.configure(text=f"Converting: {item.filename}")
            mins = int(item.elapsed_sec // 60)
            secs = int(item.elapsed_sec % 60)
            self.metrics_label.configure(
                text=f"{item.progress:.1f}%  •  Speed: {item.speed}  •  Elapsed: {mins:02d}:{secs:02d}  •  ETA: {item.eta}"
            )
            self.progress_bar.set(item.progress / 100.0)

        self._update_queue_summary()

    def _update_queue_summary(self) -> None:
        total = self.controller.queue_length
        completed = self.controller.completed_count
        self.stat_queue_lbl.configure(text=f"{completed} / {total} Completed")
        if total > 0:
            self.stat_sub_lbl.configure(text=f"{total - completed} pending tasks in queue")
        else:
            self.stat_sub_lbl.configure(text="Queue is waiting for videos")

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
            if self.controller.queue:
                out_dir = str(Path(self.controller.queue[0].output_path).parent)
            else:
                out_dir = os.getcwd()

        if os.path.exists(out_dir):
            if sys.platform == "win32":
                os.startfile(out_dir)
            else:
                subprocess.Popen(["xdg-open", out_dir])


# Keep MainWindow alias for compatibility
MainWindow = ModernDashboardWindow


def main():
    app = ModernDashboardWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
