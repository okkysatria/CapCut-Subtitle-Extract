from __future__ import annotations

import os

from PySide6.QtCore import QThread, Signal

from core import capcut_core as cc


class ScanWorker(QThread):
    project_found = Signal(object)
    progress = Signal(int, int)
    scan_finished = Signal(int, int, bool)
    scan_failed = Signal(str)

    def __init__(self, root: str, parent=None):
        super().__init__(parent)
        self._root = root
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        try:
            if not os.path.isdir(self._root):
                raise FileNotFoundError(f"Folder not found: {self._root}")
            projects = cc.scan_projects(
                self._root,
                on_project=self.project_found.emit,
                on_progress=self.progress.emit,
                should_cancel=lambda: self._cancel,
            )
            total_subs = sum(p.total for p in projects)
            self.scan_finished.emit(len(projects), total_subs, self._cancel)
        except Exception as exc:
            self.scan_failed.emit(str(exc))
