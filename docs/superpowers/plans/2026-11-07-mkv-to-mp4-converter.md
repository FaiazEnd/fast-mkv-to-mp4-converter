# MKV to MP4 Converter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a lightweight, high-performance Windows desktop application that converts/remuxes MKV files to MP4 with 100% audio preservation, real-time progress bars, and packaged as a standalone `.exe`.

**Architecture:** The application employs a decoupled architecture: a media probing and FFmpeg subprocess engine with real-time `-progress pipe:1` parsing, an asynchronous queue controller that manages state transitions on worker threads, and a modern `customtkinter` desktop GUI that displays per-conversion progress bars, speed, and ETA without UI freezing. The system is packaged into a self-contained executable with embedded FFmpeg binaries.

**Tech Stack:** Python 3.14+, `customtkinter`, `pytest`, static FFmpeg/FFprobe, PyInstaller.

**Spec:** `docs/superpowers/specs/2026-11-07-mkv-to-mp4-converter-design.md`

## Global Constraints

- Audio Preservation: Audio must be copied losslessly (`-c:a copy`) whenever the MP4 container supports the codec; if incompatible (e.g. TrueHD or raw PCM), provide automatic fallback to 320kbps AAC or ALAC.
- Fast Remuxing: Video streams matching H.264 / HEVC / AV1 must default to lossless stream copy (`-c:v copy`) for instant near-zero-CPU conversion.
- Progress Reporting: Conversion progress must report percentage (0.0 to 100.0), processing speed (e.g. `24.5x`), and ETA in seconds based on `out_time_us` parsed from FFmpeg.
- Clean Windows Integration: Subprocesses must run with `CREATE_NO_WINDOW` (`0x08000000`) so no command prompt flashes appear.
- Packaging: Must compile to a single portable `.exe` that executes on Windows without requiring pre-installed Python or FFmpeg.

## Review Focus

1. Corrupted or unreadable MKV files: Probe or conversion fails gracefully, marks item as `FAILED` with human-readable error, and does not crash or halt the rest of the queue.
2. Space characters and Unicode in file paths: FFmpeg commands properly quote paths and preserve UTF-8 filenames.
3. Destination collision: When `video.mp4` already exists, generate a safe unique name (e.g., `video (1).mp4`) or follow user overwrite setting.
4. User Cancellation: Cancelling an in-progress conversion immediately terminates the subprocess tree and removes any partially written `.mp4` file.
5. Incompatible audio/video streams in MKV: Correctly detect when stream copy is impossible and switch to fallback transcoding while retaining maximum audio fidelity.

---

### Task 1: Binary Locator & Media Probe

**Files:**
- Create: `converter/__init__.py`
- Create: `converter/probe.py`
- Test: `tests/test_probe.py`

**Interfaces:**
- Consumes: Standard library (`subprocess`, `shutil`, `json`, `os`, `sys`, `pathlib`)
- Produces:
  - `get_ffmpeg_binaries() -> tuple[str, str]` (returns paths to `ffmpeg.exe` and `ffprobe.exe`)
  - `class StreamInfo`: `codec_type: str`, `codec_name: str`, `channels: int | None`, `bitrate: int | None`
  - `class MediaInfo`: `duration: float`, `video_streams: list[StreamInfo]`, `audio_streams: list[StreamInfo]`, `can_remux_video: bool`, `can_remux_audio: bool`
  - `probe_media(file_path: str, ffprobe_path: str | None = None) -> MediaInfo`

- [ ] **Step 1: Write failing tests for binary discovery and media probing**

Create `tests/test_probe.py` testing:
- `test_get_ffmpeg_binaries_finds_paths`: checks path resolution.
- `test_probe_media_parses_json`: mocks `ffprobe` JSON response and checks `MediaInfo` properties (`duration`, `can_remux_video`, `can_remux_audio`).
- `test_probe_media_handles_invalid_file`: asserts `RuntimeError` or `ValueError` raised on corrupt output.

- [ ] **Step 2: Run test to verify failure**

Run: `py -m pytest tests/test_probe.py -v`
Expected: FAIL (modules not found)

- [ ] **Step 3: Implement `converter/probe.py`**

Implement `get_ffmpeg_binaries()` searching:
1. `sys._MEIPASS/bin` (for PyInstaller)
2. Application directory `./bin`
3. System `PATH` via `shutil.which`

Implement `MediaInfo`, `StreamInfo`, and `probe_media()` using `subprocess.run([ffprobe, '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', file_path])`. Compute `can_remux_video` (True for `h264`, `hevc`, `av1`, `mpeg4`) and `can_remux_audio` (True for `aac`, `ac3`, `eac3`, `mp3`, `flac`, `alac`, `opus`).

- [ ] **Step 4: Run test to verify it passes**

Run: `py -m pytest tests/test_probe.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add converter/__init__.py converter/probe.py tests/test_probe.py
git commit -m "feat(probe): add ffmpeg binary resolution and media probing"
```

---

### Task 2: Conversion Engine with Real-Time Progress Parsing

**Files:**
- Create: `converter/engine.py`
- Test: `tests/test_engine.py`

**Interfaces:**
- Consumes: `converter.probe.MediaInfo`
- Produces:
  - `class ConversionConfig`: `input_path: str`, `output_path: str`, `mode: str` ('remux' | 'transcode_video' | 'fallback_audio'), `audio_bitrate: str`
  - `class ProgressUpdate`: `percent: float`, `elapsed_sec: float`, `speed: str`, `eta_sec: float`
  - `class FFmpegEngine`:
    - `start(config: ConversionConfig, total_duration: float, on_progress: Callable[[ProgressUpdate], None], on_complete: Callable[[bool, str | None], None]) -> None`
    - `cancel() -> None`
    - `is_running() -> bool`

- [ ] **Step 1: Write failing tests for conversion command builder and progress parsing**

Create `tests/test_engine.py` testing:
- `test_build_ffmpeg_command_remux`: asserts `-c:v copy` and `-c:a copy` in generated arguments.
- `test_build_ffmpeg_command_fallback_audio`: asserts `-c:v copy -c:a aac -b:a 320k` when audio re-encoding needed.
- `test_parse_progress_line`: tests parsing lines from `-progress pipe:1` such as `out_time_us=50000000` and `speed=25.0x` into accurate `ProgressUpdate`.
- `test_engine_cancellation`: tests `cancel()` stops subprocess and removes incomplete output file.

- [ ] **Step 2: Run test to verify failure**

Run: `py -m pytest tests/test_engine.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `converter/engine.py`**

Implement `build_ffmpeg_args(config, ffmpeg_path)`:
- Includes `-movflags +faststart` for web/streaming optimized MP4.
- Includes `-progress pipe:1 -nostats`.
- Sets Windows `CREATE_NO_WINDOW = 0x08000000`.

Implement `FFmpegEngine`:
- Runs in background thread reading stdout line-by-line.
- Calculates `percent = (out_time_sec / total_duration) * 100`.
- Calculates `eta = (total_duration - out_time_sec) / speed_float` when speed is available.
- Handles clean process termination on `cancel()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `py -m pytest tests/test_engine.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add converter/engine.py tests/test_engine.py
git commit -m "feat(engine): add ffmpeg conversion engine with progress tracking"
```

---

### Task 3: Queue Controller & State Management

**Files:**
- Create: `converter/controller.py`
- Test: `tests/test_controller.py`

**Interfaces:**
- Consumes: `converter.probe.probe_media`, `converter.engine.FFmpegEngine`
- Produces:
  - `class QueueItemStatus(Enum)`: `PENDING`, `PROBING`, `CONVERTING`, `COMPLETED`, `FAILED`, `CANCELLED`
  - `class QueueItem`: `id: str`, `input_path: str`, `output_path: str`, `status: QueueItemStatus`, `media_info: MediaInfo | None`, `progress: float`, `speed: str`, `eta: str`, `error_msg: str | None`
  - `class ConversionController`:
    - `add_items(paths: list[str]) -> list[QueueItem]`
    - `remove_item(item_id: str) -> None`
    - `clear_queue() -> None`
    - `start() -> None`
    - `pause() -> None`
    - `cancel_current() -> None`
    - `set_output_directory(dir_path: str | None) -> None`

- [ ] **Step 1: Write failing tests for queue controller**

Create `tests/test_controller.py` testing:
- `test_add_files_and_directories`: adds files, ignores non-MKV files unless requested, creates `QueueItem`s.
- `test_safe_output_path_generation`: ensures collisions are renamed (e.g. `file_1.mp4`).
- `test_queue_state_progression`: mock engine to verify status moves from `PENDING` -> `CONVERTING` -> `COMPLETED`.
- `test_controller_handles_failure`: mock failure to verify next queue item continues.

- [ ] **Step 2: Run test to verify failure**

Run: `py -m pytest tests/test_controller.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `converter/controller.py`**

Implement queue management, auto-naming, background thread orchestration, and thread-safe UI update callbacks.

- [ ] **Step 4: Run test to verify it passes**

Run: `py -m pytest tests/test_controller.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add converter/controller.py tests/test_controller.py
git commit -m "feat(controller): add conversion queue controller and state machine"
```

---

### Task 4: Modern Desktop GUI with CustomTkinter

**Files:**
- Create: `converter/gui.py`
- Create: `converter/app.py`
- Test: `tests/test_gui_smoke.py`

**Interfaces:**
- Consumes: `converter.controller.ConversionController`
- Produces:
  - `class ConverterApp(customtkinter.CTk)`: main application window
  - `main() -> None`: entry point

- [ ] **Step 1: Write smoke test for GUI instantiation**

Create `tests/test_gui_smoke.py` verifying `ConverterApp` initializes its widgets (progress bars, buttons, labels) without unhandled exceptions.

- [ ] **Step 2: Run smoke test to verify failure**

Run: `py -m pytest tests/test_gui_smoke.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `converter/gui.py` and `converter/app.py`**

Build modern dark-mode GUI using `customtkinter`:
- Header with Title and Mode selector (`Smart Remux (Lossless, Fast)` / `Force Video Encode`).
- Drag-and-drop / "Add MKV Files" & "Add Folder" buttons.
- Queue table displaying filename, size, audio codec, video codec, and status badge.
- Current Conversion Panel:
  - Filename being processed
  - Real-time animated Progress Bar (0% to 100%)
  - Status labels: `Percentage: 45.2%`, `Speed: 34.1x`, `ETA: 00:12`
- Queue Overall Progress Bar (e.g. `3 of 10 completed`).
- Control buttons: `Start Conversion`, `Cancel Current`, `Clear Completed`.
- Settings drawer: Output folder selector, overwrite checkbox.

- [ ] **Step 4: Run test to verify GUI instantiates cleanly**

Run: `py -m pytest tests/test_gui_smoke.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add converter/gui.py converter/app.py tests/test_gui_smoke.py
git commit -m "feat(gui): implement modern customtkinter desktop UI with progress bars"
```

---

### Task 5: Packaging & Standalone .EXE Build

**Files:**
- Create: `scripts/download_ffmpeg.py`
- Create: `build_exe.py`
- Create: `main.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: Python 3.14, PyInstaller, static `ffmpeg.exe` and `ffprobe.exe`
- Produces: `dist/MKV_to_MP4_Converter.exe` (single standalone binary)

- [ ] **Step 1: Implement static FFmpeg fetcher (`scripts/download_ffmpeg.py`)**

Write helper script that checks for local `bin/ffmpeg.exe` and `bin/ffprobe.exe`. If missing, downloads official static Windows build (Gyan / BtbN release zip) and extracts the 2 binaries directly to `./bin/`.

- [ ] **Step 2: Execute FFmpeg setup script**

Run: `py scripts/download_ffmpeg.py`
Verify `bin/ffmpeg.exe` and `bin/ffprobe.exe` exist and execute (`./bin/ffmpeg.exe -version`).

- [ ] **Step 3: Implement `build_exe.py` using PyInstaller**

Configure PyInstaller build:
```python
# Parameters:
# --noconsole (no black terminal window)
# --onefile (single .exe bundle)
# --add-binary "bin/ffmpeg.exe;bin"
# --add-binary "bin/ffprobe.exe;bin"
# --name "MKV_to_MP4_Converter"
```

- [ ] **Step 4: Run build script and compile `.exe`**

Run: `py build_exe.py`
Verify `dist/MKV_to_MP4_Converter.exe` is created.

- [ ] **Step 5: End-to-end integration test with synthetic MKV**

Generate a short test MKV video (`test_sample.mkv`) with H.264 video and AAC audio.
Run conversion via engine / executable to `test_sample.mp4`.
Verify:
1. Returncode is 0.
2. Output file exists and duration matches input duration.
3. Audio stream is intact and matches input audio codec 100%.

- [ ] **Step 6: Commit**

```bash
git add main.py build_exe.py scripts/download_ffmpeg.py README.md
git commit -m "feat(build): add packaging pipeline producing standalone .exe"
```
