from __future__ import annotations

import os
from typing import List, Tuple

from PySide6.QtCore import QThread, Signal

from core import capcut_core as cc


class ExportWorker(QThread):
    progress = Signal(int, int)
    export_finished = Signal(int, str, list, bool)
    export_failed = Signal(str)

    def __init__(self, jobs: List[Tuple[cc.Project, List[cc.Subtitle]]],
                 formats: List[str], out_dir: str, parent=None):
        super().__init__(parent)
        self._jobs = jobs
        self._formats = formats
        self._out_dir = out_dir
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        try:
            os.makedirs(self._out_dir, exist_ok=True)
            total = len(self._jobs)
            files = 0
            errors: List[str] = []
            used: set = set()
            for i, (project, subs) in enumerate(self._jobs, 1):
                if self._cancel:
                    break
                base = cc.unique_basename(project.title, used)
                for fmt in self._formats:
                    if self._cancel:
                        break
                    try:
                        cc.export_file(project, subs, fmt, self._out_dir, base)
                        files += 1
                    except Exception as exc:
                        errors.append(f"{base}.{fmt}: {exc}")
                self.progress.emit(i, total)
            self.export_finished.emit(files, self._out_dir, errors, self._cancel)
        except Exception as exc:
            self.export_failed.emit(str(exc))
