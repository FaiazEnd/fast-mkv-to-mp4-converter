"""Sharp modern UI for MKV to MP4 Converter matching the executive dashboard aesthetic."""

import os
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional, Dict

import customtkinter as ctk
from PIL import Image

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
from converter.probe import get_ffmpeg_binaries, download_ffmpeg_essentials

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


def get_asset_path(filename: str) -> str:
    """Resolve asset path in standard dev or PyInstaller bundle."""
    if hasattr(sys, "_MEIPASS"):
        p = Path(sys._MEIPASS) / "assets" / filename
        if p.exists():
            return str(p)
    dev_path = Path(__file__).resolve().parent.parent / "assets" / filename
    return str(dev_path)


class ModernDashboardWindow(ctk.CTk):
    """Sharp, modern geometric Dashboard UI for MKV to MP4 Converter."""

    def __init__(self, controller: Optional[ConversionController] = None):
        super().__init__()
        self.controller = controller or ConversionController()

        self.title("MKV to MP4 Converter Pro • 100% Lossless Audio")
        self.geometry("1120x760")
        self.minsize(980, 660)

        # Set Window Icon
        icon_path = get_asset_path("icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        # Set default appearance mode
        self.current_mode = "Dark"
        ctk.set_appearance_mode(self.current_mode)

        # Configure root window background (sharp minimalist palette)
        self.configure(fg_color=("#f0f2f5", "#141518"))

        # Connect controller callbacks safely to UI thread
        self.controller.on_item_added = lambda item: self.after(0, self._render_queue_item, item)
        self.controller.on_item_updated = lambda item: self.after(0, self._update_queue_item_ui, item)
        self.controller.on_queue_finished = lambda: self.after(0, self._on_queue_finished)

        self._item_rows: Dict[str, Dict[str, ctk.CTkBaseClass]] = {}

        self._build_dashboard_layout()

    def _build_dashboard_layout(self) -> None:
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=22, pady=20)

        # 1. Top Navbar
        self._build_navbar()

        # 2. Body with 2 columns
        self.body_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.body_frame.pack(fill="both", expand=True, pady=(16, 0))

        # Left Column (Queue & Stats)
        self.left_col = ctk.CTkFrame(self.body_frame, fg_color="transparent")
        self.left_col.pack(side="left", fill="both", expand=True, padx=(0, 16))

        # Right Column (Studio Control Panel)
        self.right_col = ctk.CTkFrame(
            self.body_frame,
            width=320,
            corner_radius=0,  # SHARP EDGES
            fg_color=("#ffffff", "#1b1c22"),
            border_width=1,
            border_color=("#e0e3eb", "#2a2b34")
        )
        self.right_col.pack(side="right", fill="y")
        self.right_col.pack_propagate(False)

        # Build Components
        self._build_metric_cards()
        self._build_queue_section()
        self._build_active_conversion_card()
        self._build_sidebar()

    def _build_navbar(self) -> None:
        """Top bar with sharp logo, navigation tabs, and theme switch."""
        navbar = ctk.CTkFrame(self.main_container, height=48, fg_color="transparent")
        navbar.pack(fill="x")

        # Load Logo image for brand badge
        logo_png = get_asset_path("logo_256.png")
        if os.path.exists(logo_png):
            try:
                pil_img = Image.open(logo_png)
                self.brand_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(34, 34))
                brand_icon = ctk.CTkLabel(navbar, image=self.brand_img, text="")
                brand_icon.pack(side="left", padx=(0, 12))
            except Exception:
                pass

        title_lbl = ctk.CTkLabel(
            navbar,
            text="MKV STUDIO",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=("#1a1c22", "#ffffff")
        )
        title_lbl.pack(side="left", padx=(0, 18))

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
            text="Batch Converter",
            font=ctk.CTkFont(size=13),
            text_color=("#6c7080", "#8f92a1")
        )
        nav_queue.pack(side="left", padx=12)

        # Right side: Theme Switch (Light/Dark)
        self.theme_switch = ctk.CTkSwitch(
            navbar,
            text="Dark Mode",
            command=self._toggle_theme,
            font=ctk.CTkFont(size=12, weight="bold"),
            progress_color="#ff4d4d",
            corner_radius=0,  # SHARP SWITCH
            switch_width=42,
            switch_height=20
        )
        self.theme_switch.select()
        self.theme_switch.pack(side="right")

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
        """Top row of stat summary cards with sharp edges and color accents."""
        metrics_row = ctk.CTkFrame(self.left_col, fg_color="transparent")
        metrics_row.pack(fill="x", pady=(0, 14))

        # Card 1: Lossless Audio Mode Badge
        c1 = ctk.CTkFrame(
            metrics_row,
            corner_radius=0,  # SHARP EDGES
            fg_color=("#ffffff", "#1b1c22"),
            border_width=1,
            border_color=("#e0e3eb", "#2a2b34")
        )
        c1.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # Coral red top accent line
        accent_1 = ctk.CTkFrame(c1, height=3, corner_radius=0, fg_color="#ff4d4d")
        accent_1.pack(fill="x")

        ctk.CTkLabel(
            c1,
            text="AUDIO QUALITY",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#ff4d4d"
        ).pack(anchor="w", padx=16, pady=(12, 2))

        ctk.CTkLabel(
            c1,
            text="100% Bit-for-Bit",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=("#1a1c22", "#ffffff")
        ).pack(anchor="w", padx=16)

        ctk.CTkLabel(
            c1,
            text="Lossless Audio Stream Copy",
            font=ctk.CTkFont(size=11),
            text_color=("#6c7080", "#8f92a1")
        ).pack(anchor="w", padx=16, pady=(2, 12))

        # Card 2: Queue Metrics
        c2 = ctk.CTkFrame(
            metrics_row,
            corner_radius=0,  # SHARP EDGES
            fg_color=("#ffffff", "#1b1c22"),
            border_width=1,
            border_color=("#e0e3eb", "#2a2b34")
        )
        c2.pack(side="left", fill="both", expand=True, padx=(0, 10))

        accent_2 = ctk.CTkFrame(c2, height=3, corner_radius=0, fg_color="#f5a623")
        accent_2.pack(fill="x")

        ctk.CTkLabel(
            c2,
            text="QUEUE PROGRESS",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#f5a623"
        ).pack(anchor="w", padx=16, pady=(12, 2))

        self.stat_queue_lbl = ctk.CTkLabel(
            c2,
            text="0 / 0 Done",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=("#1a1c22", "#ffffff")
        )
        self.stat_queue_lbl.pack(anchor="w", padx=16)

        self.stat_sub_lbl = ctk.CTkLabel(
            c2,
            text="Waiting for video files",
            font=ctk.CTkFont(size=11),
            text_color=("#6c7080", "#8f92a1")
        )
        self.stat_sub_lbl.pack(anchor="w", padx=16, pady=(2, 12))

        # Card 3: Engine Mode Indicator
        c3 = ctk.CTkFrame(
            metrics_row,
            corner_radius=0,  # SHARP EDGES
            fg_color=("#ffffff", "#1b1c22"),
            border_width=1,
            border_color=("#e0e3eb", "#2a2b34")
        )
        c3.pack(side="left", fill="both", expand=True)

        accent_3 = ctk.CTkFrame(c3, height=3, corner_radius=0, fg_color="#2ecc71")
        accent_3.pack(fill="x")

        ctk.CTkLabel(
            c3,
            text="PROCESSING ENGINE",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#2ecc71"
        ).pack(anchor="w", padx=16, pady=(12, 2))

        self.stat_engine_lbl = ctk.CTkLabel(
            c3,
            text="Ultra-Fast Remux",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=("#1a1c22", "#ffffff")
        )
        self.stat_engine_lbl.pack(anchor="w", padx=16)

        ctk.CTkLabel(
            c3,
            text="Disk I/O Speed (Near 0% CPU)",
            font=ctk.CTkFont(size=11),
            text_color=("#6c7080", "#8f92a1")
        ).pack(anchor="w", padx=16, pady=(2, 12))

    def _build_queue_section(self) -> None:
        """Card containing the file list with sharp borders and sharp action buttons."""
        self.queue_card = ctk.CTkFrame(
            self.left_col,
            corner_radius=0,  # SHARP EDGES
            fg_color=("#ffffff", "#1b1c22"),
            border_width=1,
            border_color=("#e0e3eb", "#2a2b34")
        )
        self.queue_card.pack(fill="both", expand=True, pady=(0, 14))

        # Card Header with Action Buttons
        card_header = ctk.CTkFrame(self.queue_card, fg_color="transparent", height=42)
        card_header.pack(fill="x", padx=18, pady=(14, 8))

        ctk.CTkLabel(
            card_header,
            text="Task Queue",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("#1a1c22", "#ffffff")
        ).pack(side="left")

        # Sharp Action Buttons on top right
        btn_clear = ctk.CTkButton(
            card_header,
            text="Clear",
            width=65,
            height=30,
            corner_radius=0,  # SHARP
            fg_color=("#f0f2f6", "#262730"),
            hover_color=("#e2e5ec", "#333540"),
            text_color=("#6c7080", "#8f92a1"),
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._clear_queue
        )
        btn_clear.pack(side="right", padx=(6, 0))

        btn_folder = ctk.CTkButton(
            card_header,
            text="+ Add Folder",
            width=95,
            height=30,
            corner_radius=0,  # SHARP
            fg_color=("#f0f2f6", "#262730"),
            hover_color=("#e2e5ec", "#333540"),
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
            corner_radius=0,  # SHARP
            fg_color="#ff4d4d",
            hover_color="#e63939",
            text_color="#ffffff",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._choose_files
        )
        btn_files.pack(side="right")

        # Table Column Header
        col_header = ctk.CTkFrame(self.queue_card, height=26, fg_color=("#f8f9fb", "#15161c"), corner_radius=0)
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
            text="STREAM CODECS",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("#6c7080", "#8f92a1")
        ).pack(side="right", padx=60)

        # Scrollable Task List
        self.queue_scroll = ctk.CTkScrollableFrame(self.queue_card, fg_color="transparent", corner_radius=0)
        self.queue_scroll.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.empty_label = ctk.CTkLabel(
            self.queue_scroll,
            text="No files added yet.\nClick '+ Add MKV Files' or '+ Add Folder' to begin.",
            font=ctk.CTkFont(size=13),
            text_color=("#8f92a1", "#6c7080")
        )
        self.empty_label.pack(pady=50)

    def _build_active_conversion_card(self) -> None:
        """Card at the bottom showing active conversion with sharp progress bar and metrics."""
        self.active_card = ctk.CTkFrame(
            self.left_col,
            corner_radius=0,  # SHARP EDGES
            fg_color=("#ffffff", "#1b1c22"),
            border_width=1,
            border_color=("#e0e3eb", "#2a2b34")
        )
        self.active_card.pack(fill="x")

        top_info = ctk.CTkFrame(self.active_card, fg_color="transparent")
        top_info.pack(fill="x", padx=18, pady=(12, 6))

        self.current_file_label = ctk.CTkLabel(
            top_info,
            text="Standby",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("#1a1c22", "#ffffff")
        )
        self.current_file_label.pack(side="left")

        self.metrics_label = ctk.CTkLabel(
            top_info,
            text="0.0%  •  Speed: --  •  ETA: --:--",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#ff4d4d"
        )
        self.metrics_label.pack(side="right")

        # Sleek Sharp Progress Bar
        self.progress_bar = ctk.CTkProgressBar(
            self.active_card,
            height=8,
            corner_radius=0,  # SHARP RECTANGULAR BAR
            progress_color="#ff4d4d",
            fg_color=("#f0f2f6", "#262730")
        )
        self.progress_bar.set(0.0)
        self.progress_bar.pack(fill="x", padx=18, pady=(0, 14))

    def _build_sidebar(self) -> None:
        """Right Studio Panel with sharp dropdowns, output selector, and sharp action buttons."""
        sidebar_content = ctk.CTkFrame(self.right_col, fg_color="transparent")
        sidebar_content.pack(fill="both", expand=True, padx=20, pady=20)

        # Header Badge
        studio_badge = ctk.CTkFrame(
            sidebar_content,
            corner_radius=0,  # SHARP
            fg_color=("#f8f9fb", "#23242c"),
            border_width=1,
            border_color=("#e0e3eb", "#30323c")
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
            fg_color=("#f0f2f6", "#24252e"),
            button_color="#ff4d4d",
            button_hover_color="#e63939",
            text_color=("#1a1c22", "#ffffff"),
            dropdown_fg_color=("#ffffff", "#24252e"),
            dropdown_text_color=("#1a1c22", "#ffffff"),
            corner_radius=0,  # SHARP
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
            fg_color=("#f0f2f6", "#24252e"),
            button_color="#ff4d4d",
            button_hover_color="#e63939",
            text_color=("#1a1c22", "#ffffff"),
            dropdown_fg_color=("#ffffff", "#24252e"),
            dropdown_text_color=("#1a1c22", "#ffffff"),
            corner_radius=0,  # SHARP
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
            fg_color=("#f0f2f6", "#24252e"),
            button_color="#ff4d4d",
            button_hover_color="#e63939",
            text_color=("#1a1c22", "#ffffff"),
            dropdown_fg_color=("#ffffff", "#24252e"),
            dropdown_text_color=("#1a1c22", "#ffffff"),
            corner_radius=0,  # SHARP
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
            fg_color=("#f0f2f6", "#24252e"),
            button_color="#ff4d4d",
            button_hover_color="#e63939",
            text_color=("#1a1c22", "#ffffff"),
            dropdown_fg_color=("#ffffff", "#24252e"),
            dropdown_text_color=("#1a1c22", "#ffffff"),
            corner_radius=0,  # SHARP
            height=34
        )
        self.audio_bitrate_dropdown.pack(fill="x", pady=(0, 10))

        # Output Folder Selector
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
            fg_color=("#f0f2f6", "#24252e"),
            hover_color=("#e2e5ec", "#30323c"),
            text_color=("#1a1c22", "#ffffff"),
            corner_radius=0,  # SHARP
            height=34
        )
        self.btn_out_dir.pack(fill="x", pady=(0, 16))

        # Sharp Action Buttons
        self.btn_start = ctk.CTkButton(
            sidebar_content,
            text="▶  Start Converting",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=44,
            corner_radius=0,  # SHARP EDGES
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
            corner_radius=0,  # SHARP EDGES
            command=self._cancel_current,
            fg_color=("#f0f2f6", "#24252e"),
            hover_color=("#e2e5ec", "#30323c"),
            text_color=("#6c7080", "#8f92a1"),
            state="disabled"
        )
        self.btn_cancel.pack(fill="x", pady=(0, 8))

        self.btn_open_folder = ctk.CTkButton(
            sidebar_content,
            text="📂 Open Output Folder",
            font=ctk.CTkFont(size=12),
            height=34,
            corner_radius=0,  # SHARP EDGES
            command=self._open_output_folder,
            fg_color="transparent",
            hover_color=("#f0f2f6", "#24252e"),
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
            corner_radius=0,  # SHARP EDGES
            fg_color=("#f8f9fb", "#23242c")
        )
        row_frame.pack(fill="x", pady=2)

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

        # Status badge
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
        self.stat_queue_lbl.configure(text=f"{completed} / {total} Done")
        if total > 0:
            self.stat_sub_lbl.configure(text=f"{total - completed} pending tasks in queue")
        else:
            self.stat_sub_lbl.configure(text="Waiting for video files")

    def _check_and_ensure_ffmpeg(self) -> bool:
        ffmpeg_bin, ffprobe_bin = get_ffmpeg_binaries()
        if ffmpeg_bin and ffprobe_bin:
            return True

        # Need to download FFmpeg engine
        resp = messagebox.askyesno(
            "Media Engine Required",
            "FFmpeg media engine was not detected on your system.\n\n"
            "Would you like to auto-download the portable lightweight FFmpeg engine now?\n"
            "(One-time download ~25MB, saved to your local app data)",
        )
        if not resp:
            return False

        # Show download progress dialog
        dlg = ctk.CTkToplevel(self)
        dlg.title("Downloading Media Engine...")
        dlg.geometry("400x180")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()

        lbl_status = ctk.CTkLabel(dlg, text="Connecting to archive...", font=ctk.CTkFont(size=12, weight="bold"))
        lbl_status.pack(pady=(24, 10))

        bar = ctk.CTkProgressBar(dlg, width=320, height=8, corner_radius=0, progress_color="#ff4d4d")
        bar.set(0.0)
        bar.pack(pady=10)

        download_success = {"value": False, "error": None}

        def _do_download():
            try:
                def _prog(pct, msg):
                    self.after(0, lambda: (bar.set(pct / 100.0), lbl_status.configure(text=msg)))

                download_ffmpeg_essentials(progress_callback=_prog)
                download_success["value"] = True
            except Exception as e:
                download_success["error"] = str(e)
            finally:
                self.after(0, dlg.destroy)

        t = threading.Thread(target=_do_download, daemon=True)
        t.start()
        self.wait_window(dlg)

        if download_success["value"]:
            messagebox.showinfo("Success", "FFmpeg engine downloaded and ready!")
            return True
        else:
            messagebox.showerror("Download Failed", f"Could not download engine:\n{download_success['error']}")
            return False

    def _start_conversion(self) -> None:
        if self.controller.queue_length == 0:
            messagebox.showinfo("Queue Empty", "Please add one or more MKV video files first.")
            return

        if not self._check_and_ensure_ffmpeg():
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


# Alias for MainWindow
MainWindow = ModernDashboardWindow


def main():
    app = ModernDashboardWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
