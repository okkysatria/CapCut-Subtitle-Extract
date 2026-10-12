from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QEvent, QSettings, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QFileDialog, QFrame, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit,
    QPushButton, QSplitter, QStatusBar, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from core import capcut_core as cc
from gui.widgets import Spinner, StatCard
from workers.export_worker import ExportWorker
from workers.scan_worker import ScanWorker

COL_CHECK, COL_NAME, COL_BADGE, COL_TOTAL, COL_DATE = range(5)


def fmt_int(n: int) -> str:
    return f"{n:,}".replace(",", ".")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CapCut Subtitle Extract")
        self.resize(1360, 840)
        self.setMinimumSize(1000, 640)

        # Set window icon if available
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "app_icon.ico")
        if os.path.exists(icon_path):
            from PySide6.QtGui import QIcon
            self.setWindowIcon(QIcon(icon_path))

        self.settings = QSettings("CapCutSubtitleExtract", "CapCutSubtitleExtract")
        self.projects: List[cc.Project] = []
        self._scan_worker: Optional[ScanWorker] = None
        self._export_worker: Optional[ExportWorker] = None
        self._stat_auto = 0
        self._stat_manual = 0
        self._stat_subs = 0

        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(150)
        self._filter_timer.timeout.connect(self._apply_filters)

        self._build_ui()
        self._load_settings()
        self._set_status("Ready. Click “Scan Projects” to begin.")

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 12)
        root.setSpacing(12)

        root.addWidget(self._build_path_card())
        root.addLayout(self._build_stats())
        root.addWidget(self._build_toolbar())
        root.addWidget(self._build_split(), 1)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.sel_label = QLabel("0 selected")
        self.status.addPermanentWidget(self.sel_label)

    def _build_path_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        grid = QVBoxLayout(card)
        grid.setContentsMargins(14, 12, 14, 12)
        grid.setSpacing(10)

        top_row = QHBoxLayout()
        step_guide = QLabel("<b>Workflow:</b> 1. Scan Projects &nbsp;➜&nbsp; 2. Select Project &nbsp;➜&nbsp; 3. Export Subtitles")
        step_guide.setObjectName("guideText")
        self.btn_help = QPushButton("Guide")
        self.btn_help.setObjectName("subtleBtn")
        self.btn_help.setToolTip("Show step-by-step instructions")
        self.btn_help.clicked.connect(self._show_help_dialog)
        top_row.addWidget(step_guide, 1)
        top_row.addWidget(self.btn_help)
        grid.addLayout(top_row)

        row1 = QHBoxLayout()
        lbl1 = QLabel("CapCut Draft Folder")
        lbl1.setObjectName("fieldLabel")
        lbl1.setFixedWidth(140)
        self.draft_edit = QLineEdit()
        self.draft_edit.setPlaceholderText("Path to com.lveditor.draft directory")
        self.draft_edit.setClearButtonEnabled(True)
        self.btn_reset_draft = QPushButton("Default")
        self.btn_reset_draft.setToolTip("Reset to default Windows CapCut draft location")
        self.btn_reset_draft.clicked.connect(self._reset_draft_folder)
        self.btn_browse_draft = QPushButton("Browse")
        self.btn_browse_draft.clicked.connect(self._browse_draft)
        self.spinner = Spinner()
        self.btn_scan = QPushButton("Scan Projects")
        self.btn_scan.setObjectName("primary")
        self.btn_scan.setMinimumWidth(160)
        self.btn_scan.setToolTip("Scan CapCut drafts and extract subtitle tracks")
        self.btn_scan.clicked.connect(self._on_scan)

        row1.addWidget(lbl1)
        row1.addWidget(self.draft_edit, 1)
        row1.addWidget(self.btn_reset_draft)
        row1.addWidget(self.btn_browse_draft)
        row1.addSpacing(6)
        row1.addWidget(self.spinner)
        row1.addWidget(self.btn_scan)

        row2 = QHBoxLayout()
        lbl2 = QLabel("Export Destination")
        lbl2.setObjectName("fieldLabel")
        lbl2.setFixedWidth(140)
        self.export_edit = QLineEdit()
        self.export_edit.setPlaceholderText("Output folder for exported subtitle files")
        self.export_edit.setClearButtonEnabled(True)
        self.btn_browse_export = QPushButton("Browse")
        self.btn_browse_export.clicked.connect(self._browse_export)
        self.btn_open_export = QPushButton("Open Folder")
        self.btn_open_export.setToolTip("Open export destination in Windows Explorer")
        self.btn_open_export.clicked.connect(self._open_export_folder)

        row2.addWidget(lbl2)
        row2.addWidget(self.export_edit, 1)
        row2.addWidget(self.btn_browse_export)
        row2.addWidget(self.btn_open_export)

        grid.addLayout(row1)
        grid.addLayout(row2)
        return card

    def _build_stats(self) -> QHBoxLayout:
        lay = QHBoxLayout()
        lay.setSpacing(12)
        self.card_projects = StatCard("Total Projects", "#e5e7eb")
        self.card_subs = StatCard("Total Subtitles", "#10b981")
        self.card_auto = StatCard("Auto-Captions (ASR)", "#3b82f6")
        self.card_manual = StatCard("Manual Text", "#f59e0b")
        for c in (self.card_projects, self.card_subs, self.card_auto, self.card_manual):
            lay.addWidget(c, 1)
        return lay

    def _build_toolbar(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(10)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search projects or subtitle text…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setMinimumWidth(240)
        self.search_edit.textChanged.connect(lambda _t: self._filter_timer.start())

        self.origin_combo = QComboBox()
        self.origin_combo.addItem("All Subtitles", cc.ORIGIN_ALL)
        self.origin_combo.addItem("Auto-Captions Only (ASR)", cc.ORIGIN_AUTO)
        self.origin_combo.addItem("Manual Text Only", cc.ORIGIN_MANUAL)
        self.origin_combo.setToolTip("Filter by subtitle origin")
        self.origin_combo.currentIndexChanged.connect(self._on_origin_changed)

        lay.addWidget(self.search_edit, 1)
        lay.addWidget(self.origin_combo)
        lay.addSpacing(10)

        lbl_fmt = QLabel("Format:")
        lbl_fmt.setObjectName("fieldLabel")
        lay.addWidget(lbl_fmt)

        format_tooltips = {
            "srt": "SRT: Standard subtitle format with timecodes",
            "txt": "TXT: Plain text transcript without timestamps",
            "vtt": "VTT: WebVTT format for web players",
            "csv": "CSV: Spreadsheet format with timestamps and text",
            "json": "JSON: Structured subtitle data",
        }

        self.format_checks: Dict[str, QCheckBox] = {}
        for fmt, default in (("srt", True), ("txt", True), ("vtt", False),
                             ("csv", False), ("json", False)):
            cb = QCheckBox(fmt.upper())
            cb.setChecked(default)
            cb.setToolTip(format_tooltips.get(fmt, ""))
            self.format_checks[fmt] = cb
            lay.addWidget(cb)
        lay.addSpacing(10)

        self.btn_select_all = QPushButton("Select All")
        self.btn_select_all.setToolTip("Select all visible projects")
        self.btn_select_all.clicked.connect(self._select_all)
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setToolTip("Clear project selection")
        self.btn_clear.clicked.connect(self._clear_selection)
        self.btn_export = QPushButton("Export Selected")
        self.btn_export.setObjectName("primary")
        self.btn_export.setMinimumWidth(140)
        self.btn_export.setToolTip("Export checked projects in selected formats")
        self.btn_export.clicked.connect(self._on_export)
        lay.addWidget(self.btn_select_all)
        lay.addWidget(self.btn_clear)
        lay.addWidget(self.btn_export)
        return card

    def _build_split(self) -> QSplitter:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["", "Project Name", "Type", "Subtitles", "Modified"])
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(42)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        hh = self.table.horizontalHeader()
        hh.setHighlightSections(False)
        hh.setSectionResizeMode(COL_CHECK, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(COL_BADGE, QHeaderView.ResizeMode.Interactive)
        hh.setSectionResizeMode(COL_TOTAL, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(COL_DATE, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(COL_CHECK, 40)
        self.table.setColumnWidth(COL_BADGE, 190)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.cellDoubleClicked.connect(lambda r, _c: self._toggle_row_check(r))
        self.table.installEventFilter(self)

        panel = QFrame()
        panel.setObjectName("card")
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(14, 12, 14, 14)
        pl.setSpacing(10)

        head = QHBoxLayout()
        self.preview_title = QLabel("Select a project to preview")
        self.preview_title.setObjectName("previewTitle")
        self.preview_title.setWordWrap(True)
        self.preview_badge = QLabel("0 subtitles")
        self.preview_badge.setObjectName("countBadge")
        head.addWidget(self.preview_title, 1)
        head.addWidget(self.preview_badge)

        btns = QHBoxLayout()
        self.btn_copy_text = QPushButton("Copy Text")
        self.btn_copy_text.setObjectName("accent")
        self.btn_copy_text.setToolTip("Copy plain text transcript to clipboard")
        self.btn_copy_text.clicked.connect(self._copy_clean_text)

        self.btn_copy_srt = QPushButton("Copy SRT")
        self.btn_copy_srt.setObjectName("accent")
        self.btn_copy_srt.setToolTip("Copy SRT formatted subtitles to clipboard")
        self.btn_copy_srt.clicked.connect(self._copy_srt)

        self.btn_export_single = QPushButton("Export Current")
        self.btn_export_single.setObjectName("primary")
        self.btn_export_single.setToolTip("Export subtitles for the currently selected project")
        self.btn_export_single.clicked.connect(self._on_export_current_only)

        btns.addWidget(self.btn_copy_text)
        btns.addWidget(self.btn_copy_srt)
        btns.addSpacing(6)
        btns.addWidget(self.btn_export_single)
        btns.addStretch(1)

        self.preview = QPlainTextEdit()
        self.preview.setObjectName("preview")
        self.preview.setReadOnly(True)
        self.preview.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        mono = QFont("Consolas")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        mono.setFamilies(["JetBrains Mono", "Consolas", "Courier New", "Monospace"])
        mono.setPointSize(10)
        self.preview.setFont(mono)
        self.preview.setPlaceholderText("Select a project from the table to preview subtitles.")

        pl.addLayout(head)
        pl.addLayout(btns)
        pl.addWidget(self.preview, 1)

        splitter.addWidget(self.table)
        splitter.addWidget(panel)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 5)
        splitter.setSizes([680, 640])
        return splitter

    def _load_settings(self) -> None:
        default_export = os.path.join(os.path.expanduser("~"), "Documents", "CapCut-Subtitles")
        self.draft_edit.setText(self.settings.value("draft_dir", cc.DEFAULT_DRAFT_DIR))
        self.export_edit.setText(self.settings.value("export_dir", default_export))
        geo = self.settings.value("geometry")
        if geo is not None:
            self.restoreGeometry(geo)

    def _save_settings(self) -> None:
        self.settings.setValue("draft_dir", self.draft_edit.text().strip())
        self.settings.setValue("export_dir", self.export_edit.text().strip())
        self.settings.setValue("geometry", self.saveGeometry())

    def _set_status(self, msg: str, timeout: int = 0) -> None:
        self.status.showMessage(msg, timeout)

    def _origin(self) -> str:
        return self.origin_combo.currentData()

    def _subs_for(self, project: cc.Project) -> List[cc.Subtitle]:
        return cc.filter_by_origin(project.subtitles, self._origin())

    def _selected_row(self) -> int:
        rows = self.table.selectionModel().selectedRows()
        return rows[0].row() if rows else -1

    def _checked_rows(self) -> List[int]:
        out = []
        for r in range(self.table.rowCount()):
            item = self.table.item(r, COL_CHECK)
            if item and item.checkState() == Qt.CheckState.Checked:
                out.append(r)
        return out

    def _toggle_row_check(self, row: int) -> None:
        if 0 <= row < self.table.rowCount():
            item = self.table.item(row, COL_CHECK)
            if item:
                new_state = (
                    Qt.CheckState.Unchecked
                    if item.checkState() == Qt.CheckState.Checked
                    else Qt.CheckState.Checked
                )
                item.setCheckState(new_state)

    def eventFilter(self, obj, event):
        if obj is self.table and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
                row = self._selected_row()
                if row >= 0:
                    self._toggle_row_check(row)
                    return True
        return super().eventFilter(obj, event)

    def _browse_draft(self) -> None:
        start = self.draft_edit.text().strip() or os.path.expanduser("~")
        path = QFileDialog.getExistingDirectory(self, "Select CapCut Draft Folder", start)
        if path:
            self.draft_edit.setText(os.path.normpath(path))

    def _browse_export(self) -> None:
        start = self.export_edit.text().strip() or os.path.expanduser("~")
        path = QFileDialog.getExistingDirectory(self, "Select Export Folder", start)
        if path:
            self.export_edit.setText(os.path.normpath(path))

    def _open_export_folder(self) -> None:
        path = self.export_edit.text().strip()
        if not path:
            QMessageBox.warning(self, "Export Folder", "Export folder path is not set.")
            return
        try:
            os.makedirs(path, exist_ok=True)
        except OSError as exc:
            QMessageBox.warning(self, "Export Folder", f"Cannot open folder:\n{exc}")
            return
        if hasattr(os, "startfile"):
            os.startfile(path)
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _on_scan(self) -> None:
        if self._scan_worker is not None:
            self._scan_worker.cancel()
            self.btn_scan.setEnabled(False)
            self.btn_scan.setText("Cancelling…")
            self._set_status("Cancelling scan process…")
            return
        root = self.draft_edit.text().strip()
        if not os.path.isdir(root):
            QMessageBox.warning(
                self, "Folder Not Found",
                "Invalid CapCut draft folder.\nPlease select your 'com.lveditor.draft' folder manually.",
            )
            return
        self._save_settings()
        self._reset_results()
        self.table.setUpdatesEnabled(False)

        worker = ScanWorker(root, self)
        worker.project_found.connect(self._on_project_found)
        worker.progress.connect(self._on_scan_progress)
        worker.scan_finished.connect(self._on_scan_finished)
        worker.scan_failed.connect(self._on_scan_failed)
        worker.finished.connect(self._on_scan_thread_done)
        self._scan_worker = worker
        self._set_scan_busy(True)
        self._set_status("Scanning projects…")
        worker.start()

    def _set_scan_busy(self, busy: bool) -> None:
        self.btn_scan.setText("⏹ Cancel Scan" if busy else "🔍 Scan Projects")
        self.btn_scan.setEnabled(True)
        self.btn_browse_draft.setEnabled(not busy)
        self.draft_edit.setEnabled(not busy)
        if busy:
            self.spinner.start()
        else:
            self.spinner.stop()

    def _reset_results(self) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        self.table.blockSignals(False)
        self.projects.clear()
        self._stat_auto = self._stat_manual = self._stat_subs = 0
        self._update_stats()
        self._show_preview(None)
        self._update_selected_label()

    def _on_project_found(self, project: cc.Project) -> None:
        self.projects.append(project)
        self._stat_subs += project.total
        self._stat_auto += project.auto_count
        self._stat_manual += project.manual_count
        self._add_row(project)
        self._update_stats()

    def _on_scan_progress(self, done: int, total: int) -> None:
        self._set_status(f"Scanning… {done}/{total} folders")

    def _on_scan_finished(self, n_projects: int, n_subs: int, cancelled: bool) -> None:
        self.table.setUpdatesEnabled(True)
        prefix = "Scan cancelled" if cancelled else "Scan completed"
        self._set_status(
            f"{prefix}: Found {fmt_int(n_projects)} projects ({fmt_int(n_subs)} subtitles)"
        )
        if self.table.rowCount() and self._selected_row() < 0:
            for r in range(self.table.rowCount()):
                if not self.table.isRowHidden(r):
                    self.table.selectRow(r)
                    break

    def _on_scan_failed(self, message: str) -> None:
        self.table.setUpdatesEnabled(True)
        self._set_status(f"Scan failed: {message}")
        QMessageBox.critical(self, "Scan Failed", message)

    def _on_scan_thread_done(self) -> None:
        self.table.setUpdatesEnabled(True)
        if self._scan_worker is not None:
            self._scan_worker.deleteLater()
            self._scan_worker = None
        self._set_scan_busy(False)

    def _add_row(self, project: cc.Project) -> None:
        row = self.table.rowCount()
        self.table.blockSignals(True)
        self.table.insertRow(row)

        chk = QTableWidgetItem()
        chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
                     | Qt.ItemFlag.ItemIsSelectable)
        chk.setCheckState(Qt.CheckState.Unchecked)
        self.table.setItem(row, COL_CHECK, chk)

        name = QTableWidgetItem(project.title)
        name.setToolTip(f"{project.title}\n{project.folder}")
        self.table.setItem(row, COL_NAME, name)

        self.table.setCellWidget(row, COL_BADGE, self._make_badges(project))

        total = QTableWidgetItem(fmt_int(project.total))
        total.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, COL_TOTAL, total)

        date = "-"
        if project.modified:
            date = datetime.fromtimestamp(project.modified).strftime("%d-%m-%Y %H:%M")
        self.table.setItem(row, COL_DATE, QTableWidgetItem(date))
        self.table.blockSignals(False)

        self.table.setRowHidden(row, not self._row_visible(project))

    def _make_badges(self, project: cc.Project) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(6, 0, 6, 0)
        lay.setSpacing(6)

        def badge(text: str, obj: str) -> QLabel:
            lb = QLabel(text)
            lb.setObjectName(obj)
            return lb

        if project.error:
            b = badge("Error", "badgeError")
            b.setToolTip(project.error)
            lay.addWidget(b)
        else:
            if project.auto_count:
                lay.addWidget(badge(f"Auto {fmt_int(project.auto_count)}", "badgeAuto"))
            if project.manual_count:
                lay.addWidget(badge(f"Manual {fmt_int(project.manual_count)}", "badgeManual"))
            if not project.total:
                lay.addWidget(badge("Empty", "badgeMuted"))
        lay.addStretch(1)
        return w

    def _row_visible(self, project: cc.Project) -> bool:
        subs = self._subs_for(project)
        if self._origin() != cc.ORIGIN_ALL and not subs:
            return False
        query = self.search_edit.text().strip().lower()
        if not query:
            return True
        if query in project.title.lower():
            return True
        return any(query in s.text.lower() for s in subs)

    def _apply_filters(self) -> None:
        for row, project in enumerate(self.projects):
            self.table.setRowHidden(row, not self._row_visible(project))
        cur = self._selected_row()
        if cur >= 0 and self.table.isRowHidden(cur):
            self.table.clearSelection()
            self._show_preview(None)

    def _on_origin_changed(self) -> None:
        self._apply_filters()
        self._on_selection_changed()

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() == COL_CHECK:
            self._update_selected_label()

    def _update_selected_label(self) -> None:
        self.sel_label.setText(f"{len(self._checked_rows())} selected")

    def _select_all(self) -> None:
        self.table.blockSignals(True)
        for r in range(self.table.rowCount()):
            if not self.table.isRowHidden(r):
                self.table.item(r, COL_CHECK).setCheckState(Qt.CheckState.Checked)
        self.table.blockSignals(False)
        self._update_selected_label()

    def _clear_selection(self) -> None:
        self.table.blockSignals(True)
        for r in range(self.table.rowCount()):
            self.table.item(r, COL_CHECK).setCheckState(Qt.CheckState.Unchecked)
        self.table.blockSignals(False)
        self._update_selected_label()

    def _update_stats(self) -> None:
        self.card_projects.set_value(len(self.projects))
        self.card_subs.set_value(self._stat_subs)
        self.card_auto.set_value(self._stat_auto)
        self.card_manual.set_value(self._stat_manual)

    def _on_selection_changed(self) -> None:
        row = self._selected_row()
        self._show_preview(self.projects[row] if 0 <= row < len(self.projects) else None)

    def _current_project(self) -> Optional[cc.Project]:
        row = self._selected_row()
        return self.projects[row] if 0 <= row < len(self.projects) else None

    def _reset_draft_folder(self) -> None:
        self.draft_edit.setText(cc.DEFAULT_DRAFT_DIR)
        self._set_status("CapCut draft folder reset to Windows default.", 3000)

    def _show_help_dialog(self) -> None:
        msg = QMessageBox(self)
        msg.setWindowTitle("Beginner's Guide - CapCut Subtitle Extract")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText("<h3>How to Extract Subtitles from CapCut</h3>")
        text = (
            "<p>This application reads project drafts from CapCut Desktop and automatically extracts subtitles.</p>"
            "<ol>"
            "<li><b>Generate Subtitles in CapCut:</b><br>"
            "Open your video in CapCut Desktop ➜ go to <b>Text</b> ➜ select <b>Auto captions</b> ➜ click <b>Generate</b>. Wait until subtitles appear on your timeline, then save the project.</li><br>"
            "<li><b>Scan Projects:</b><br>"
            "Open this app and click the green <b>🔍 Scan Projects</b> button. All your CapCut projects will be listed on the left.</li><br>"
            "<li><b>Review & Copy:</b><br>"
            "Click any project in the left table to inspect its subtitles. You can copy the clean transcript or timecoded SRT directly to clipboard with <b>Copy Text</b> or <b>Copy SRT</b>.</li><br>"
            "<li><b>Export to Files:</b><br>"
            "Select your desired formats (<b>SRT</b> for YouTube/video players, or <b>TXT</b> for reading), then click <b>💾 Export This Project Only</b>.<br>"
            "Or check multiple projects and click <b>💾 Export Selected</b> to batch export.</li>"
            "</ol>"
            "<p><i>The output destination folder will automatically open once exporting is done.</i></p>"
        )
        msg.setInformativeText(text)
        msg.addButton("Got It", QMessageBox.ButtonRole.AcceptRole)
        msg.exec()

    def _show_preview(self, project: Optional[cc.Project]) -> None:
        if project is None:
            self.preview_title.setText("Select a project to preview")
            self.preview_badge.setText("0 subtitles")
            self.preview.setPlainText(
                "Instructions:\n\n"
                "1. Click 'Scan Projects' to detect your CapCut drafts.\n"
                "2. Select a project from the table to preview subtitles.\n"
                "3. Click 'Export Current' to export, or check multiple projects and click 'Export Selected'.\n\n"
                "Shortcuts:\n"
                "• Press Space or double-click to toggle row selection."
            )
            self.btn_copy_text.setEnabled(False)
            self.btn_copy_srt.setEnabled(False)
            self.btn_export_single.setEnabled(False)
            return

        subs = self._subs_for(project)
        self.preview_title.setText(project.title)
        self.preview_badge.setText(f"{fmt_int(len(subs))} subtitles")
        has_subs = bool(subs)
        self.btn_copy_text.setEnabled(has_subs)
        self.btn_copy_srt.setEnabled(has_subs)
        self.btn_export_single.setEnabled(has_subs)

        if project.error:
            self.preview.setPlainText(
                f"⚠️ Error reading project:\n{project.error}\n\n"
                "Note: If CapCut is currently running and locking this file, close CapCut and scan again."
            )
            return
        if not subs:
            self.preview.setPlainText(
                "(No subtitles found in this project for the selected filter)\n\n"
                "Make sure you have generated 'Auto captions' or created text tracks in CapCut."
            )
            return

        lines = []
        for i, s in enumerate(subs, 1):
            tag = "Auto (ASR)" if s.origin == cc.ORIGIN_AUTO else "Manual"
            lines.append(
                f"#{i} [{tag}]  {cc.format_srt_time(s.start_us)} --> {cc.format_srt_time(s.end_us)}\n"
                f"{s.text}\n"
            )
        self.preview.setPlainText("\n".join(lines))

    def _copy_to_clipboard(self, text: str, label: str) -> None:
        QGuiApplication.clipboard().setText(text)
        self._set_status(f"{label} copied to clipboard.", 4000)

    def _copy_clean_text(self) -> None:
        project = self._current_project()
        subs = self._subs_for(project) if project else []
        if not subs:
            self._set_status("No text available to copy.", 3000)
            return
        self._copy_to_clipboard("\n".join(s.text for s in subs), "Clean text")

    def _copy_srt(self) -> None:
        project = self._current_project()
        subs = self._subs_for(project) if project else []
        if not subs:
            self._set_status("No subtitles available to copy.", 3000)
            return
        self._copy_to_clipboard(cc.to_srt(subs), "SRT format")

    def _on_export_current_only(self) -> None:
        project = self._current_project()
        if not project:
            QMessageBox.information(self, "Select Project", "Please select a project from the table first.")
            return
        subs = self._subs_for(project)
        if not subs:
            QMessageBox.information(self, "No Subtitles", "This project has no subtitles to export.")
            return
        formats = [f for f, cb in self.format_checks.items() if cb.isChecked()]
        if not formats:
            QMessageBox.information(self, "Select Format", "Please select at least one export format (e.g. SRT or TXT).")
            return
        out_dir = self.export_edit.text().strip()
        if not out_dir:
            QMessageBox.warning(self, "Export Folder", "Export folder path is required.")
            return

        self._save_settings()
        worker = ExportWorker([(project, subs)], formats, out_dir, self)
        worker.progress.connect(lambda d, t: self._set_status(f"Exporting {project.title}…"))
        worker.export_finished.connect(
            lambda files, folder, errors, cancelled: self._on_export_finished(files, folder, errors, 0, cancelled)
        )
        worker.export_failed.connect(self._on_export_failed)
        worker.finished.connect(self._on_export_thread_done)
        self._export_worker = worker
        self.btn_export.setText("⏹ Cancel Export")
        self.btn_export.setEnabled(True)
        self._set_status(f"Exporting {project.title}…")
        worker.start()

    def _on_export(self) -> None:
        if self._export_worker is not None:
            self._export_worker.cancel()
            self.btn_export.setEnabled(False)
            self.btn_export.setText("Cancelling…")
            self._set_status("Cancelling export process…")
            return
        rows = self._checked_rows()
        if not rows:
            QMessageBox.information(self, "Export", "Please check at least one project in the table first.")
            return
        formats = [f for f, cb in self.format_checks.items() if cb.isChecked()]
        if not formats:
            QMessageBox.information(self, "Select Format", "Please select at least one export format (e.g. SRT or TXT).")
            return
        out_dir = self.export_edit.text().strip()
        if not out_dir:
            QMessageBox.warning(self, "Export Folder", "Export destination folder is required.")
            return

        jobs: List[Tuple[cc.Project, List[cc.Subtitle]]] = []
        skipped = 0
        for r in rows:
            project = self.projects[r]
            subs = self._subs_for(project)
            if subs:
                jobs.append((project, subs))
            else:
                skipped += 1
        if not jobs:
            QMessageBox.information(self, "Export", "Selected projects do not have any subtitles to export.")
            return

        self._save_settings()
        worker = ExportWorker(jobs, formats, out_dir, self)
        worker.progress.connect(lambda d, t: self._set_status(f"Exporting… {d}/{t} projects"))
        worker.export_finished.connect(
            lambda files, folder, errors, cancelled: self._on_export_finished(files, folder, errors, skipped, cancelled)
        )
        worker.export_failed.connect(self._on_export_failed)
        worker.finished.connect(self._on_export_thread_done)
        self._export_worker = worker
        self.btn_export.setText("⏹ Cancel Export")
        self.btn_export.setEnabled(True)
        self._set_status("Exporting…")
        worker.start()

    def _on_export_finished(self, files: int, folder: str, errors: list, skipped: int, cancelled: bool = False) -> None:
        prefix = "Export cancelled" if cancelled else "Export completed"
        msg = f"{prefix}: {fmt_int(files)} files saved to {folder}"
        if skipped:
            msg += f" ({skipped} projects without subtitles skipped)"
        self._set_status(msg)

        if not cancelled and files > 0:
            box = QMessageBox(self)
            box.setWindowTitle("Export Complete")
            box.setIcon(QMessageBox.Icon.Information)
            box.setText(f"<h3>{fmt_int(files)} subtitle files exported successfully.</h3>")
            detail = f"Destination folder:<br><b>{folder}</b>"
            if skipped:
                detail += f"<br><br><small>{skipped} projects skipped (no subtitles found).</small>"
            box.setInformativeText(detail)
            btn_open = box.addButton("Open Output Folder", QMessageBox.ButtonRole.AcceptRole)
            box.addButton("Close", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() == btn_open:
                self._open_export_folder()

        if errors:
            QMessageBox.warning(
                self, "Write Errors",
                "The following files could not be saved:\n\n" + "\n".join(errors[:15]),
            )

    def _on_export_failed(self, message: str) -> None:
        self._set_status(f"Export failed: {message}")
        QMessageBox.critical(self, "Export Failed", message)

    def _on_export_thread_done(self) -> None:
        if self._export_worker is not None:
            self._export_worker.deleteLater()
            self._export_worker = None
        self.btn_export.setEnabled(True)
        self.btn_export.setText("Export Selected")

    def closeEvent(self, event) -> None:
        self._save_settings()
        for w in (self._scan_worker, self._export_worker):
            if w is not None:
                w.cancel()
                w.wait(3000)
        super().closeEvent(event)
