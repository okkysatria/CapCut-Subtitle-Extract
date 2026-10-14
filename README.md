# CapCut Subtitle Extract

A desktop application (PySide6) for scanning CapCut Desktop drafts on Windows, extracting subtitles (ASR auto-captions & manual text), previewing them in real time, and exporting to SRT / VTT / TXT / CSV / JSON.

<p align="center">
  <a href="https://github.com/okkysatria/CapCut-Subtitle-Extract/releases/latest/download/CapCut-Subtitle-Extract.exe">
    <img src="https://img.shields.io/badge/⬇️%20Download%20EXE-v1.0.0-blue?style=for-the-badge&logo=windows" alt="Download EXE"/>
  </a>
  &nbsp;
  <a href="https://github.com/okkysatria/CapCut-Subtitle-Extract/releases/latest">
    <img src="https://img.shields.io/github/v/release/okkysatria/CapCut-Subtitle-Extract?style=for-the-badge&label=Latest%20Release" alt="Latest Release"/>
  </a>
</p>

> **No installation needed.** Just download and run — Python is not required.
> Windows 10 / 11 (64-bit) only.

---

## Structure
```
main.py                 Application entry point
core/capcut_core.py     Core engine: scan, parse, timecodes, format generators (pure Python)
gui/main_window.py      Main GUI window
gui/widgets.py          Custom widgets: Spinner & StatCard
workers/scan_worker.py  Background QThread scanner
workers/export_worker.py Background QThread exporter
styles/theme.py         Modern dark QSS theme
```

## Running from Source
```bash
pip install PySide6
python main.py
```

## Build Standalone .exe
```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --name "CapCut-Subtitle-Extract" main.py
```
Output executable: `dist/CapCut-Subtitle-Extract.exe`

## How to Use (3 Simple Steps)
1. **Scan Projects**: Click the green **`🔍 Scan Projects`** button. The app automatically detects your CapCut Desktop projects folder on Windows.
2. **Review & Select**: Click any project title in the table to inspect its subtitles in the right-hand preview panel.
3. **Export**:
   - For a single project: Click **`💾 Export This Project Only`** in the preview panel.
   - For batch export: Check the boxes for the desired projects, then click **`💾 Export Selected`**.
   - When finished, click **`📂 Open Output Folder`** in the success dialog to open the files directly in Windows Explorer.

## Notes & Features
- Default drafts path: `%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft` (use the `🔄 Default` button to restore if needed).
- Click **`❓ Beginner's Guide`** in the header for step-by-step instructions.
- Press **SPACE** or **Double-Click** any table row to toggle checkboxes.
- Supports graceful task cancellation (`⏹ Cancel Scan` and `⏹ Cancel Export`).
- Export files (`.srt`, `.vtt`, `.txt`, `.csv`) are encoded in `utf-8-sig` (compatible with Windows & Excel); `.json` is encoded in standard `utf-8`.
