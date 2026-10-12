
"""QSS Dark Theme for CapCut Subtitle Extract."""

STYLESHEET = """
* {
    font-family: "Segoe UI", "Inter", "Noto Sans", sans-serif;
    font-size: 13px;
    color: #e5e7eb;
}
QMainWindow, QWidget#central { background: #121316; }
QDialog, QMessageBox { background: #1a1c23; }
QLabel { background: transparent; }

QFrame#card, QFrame#statCard {
    background: #1a1c23;
    border: 1px solid #2d3139;
    border-radius: 8px;
}
QFrame#card QLabel, QFrame#statCard QLabel { border: none; }
QLabel#fieldLabel { color: #9ca3af; font-weight: 600; }
QLabel#statTitle { color: #9ca3af; font-size: 12px; }
QLabel#statValue { font-size: 26px; font-weight: 700; }
QLabel#previewTitle { font-size: 16px; font-weight: 700; }
QLabel#guideText {
    color: #93c5fd;
    background: rgba(59, 130, 246, 0.08);
    border: 1px solid rgba(59, 130, 246, 0.2);
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
}
QLabel#countBadge {
    background: rgba(59, 130, 246, 0.16);
    color: #60a5fa;
    border-radius: 10px;
    padding: 3px 10px;
    font-weight: 600;
    font-size: 12px;
}

QLineEdit {
    background: #121316;
    border: 1px solid #2d3139;
    border-radius: 6px;
    padding: 7px 10px;
    selection-background-color: #3b82f6;
}
QLineEdit:hover { border-color: #3d424d; }
QLineEdit:focus { border-color: #10b981; }

QPushButton {
    background: #23262e;
    border: 1px solid #2d3139;
    border-radius: 6px;
    padding: 7px 14px;
}
QPushButton:hover { background: #2a2e38; border-color: #3b82f6; }
QPushButton:pressed { background: #1f2229; }
QPushButton:disabled { color: #6b7280; background: #1a1c23; border-color: #23262e; }

QPushButton#primary {
    background: #10b981;
    border: 1px solid #10b981;
    color: #04130d;
    font-weight: 700;
}
QPushButton#primary:hover { background: #34d399; border-color: #34d399; }
QPushButton#primary:pressed { background: #0d9668; }
QPushButton#primary:disabled { background: #1f3b33; border-color: #1f3b33; color: #6b8f82; }

QPushButton#accent {
    background: rgba(59, 130, 246, 0.14);
    border: 1px solid #3b82f6;
    color: #93c5fd;
}
QPushButton#accent:hover { background: rgba(59, 130, 246, 0.27); }

QPushButton#subtleBtn {
    background: #1a1c23;
    border: 1px solid #3d424d;
    color: #9ca3af;
    font-size: 12px;
    padding: 5px 10px;
}
QPushButton#subtleBtn:hover {
    color: #e5e7eb;
    border-color: #60a5fa;
    background: #23262e;
}

QComboBox {
    background: #121316;
    border: 1px solid #2d3139;
    border-radius: 6px;
    padding: 7px 10px;
    min-width: 170px;
}
QComboBox:hover { border-color: #3b82f6; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView {
    background: #1a1c23;
    border: 1px solid #2d3139;
    border-radius: 6px;
    selection-background-color: #3b82f6;
    outline: none;
}

QCheckBox { spacing: 7px; background: transparent; }
QCheckBox::indicator, QTableView::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #3d424d;
    border-radius: 4px;
    background: #121316;
}
QCheckBox::indicator:hover, QTableView::indicator:hover { border-color: #10b981; }
QCheckBox::indicator:checked, QTableView::indicator:checked {
    background: #10b981;
    border-color: #10b981;
}

QTableWidget {
    background: #1a1c23;
    border: 1px solid #2d3139;
    border-radius: 8px;
    gridline-color: transparent;
    outline: none;
}
QTableWidget::item { padding: 4px 8px; border-bottom: 1px solid #23262e; }
QTableWidget::item:hover { background: rgba(255, 255, 255, 0.04); }
QTableWidget::item:selected { background: rgba(16, 185, 129, 0.18); color: #ffffff; }

QHeaderView::section {
    background: #1f222a;
    color: #9ca3af;
    border: none;
    border-bottom: 1px solid #2d3139;
    padding: 9px 8px;
    font-weight: 600;
}

QPlainTextEdit#preview {
    background: #0f1013;
    border: 1px solid #2d3139;
    border-radius: 8px;
    padding: 8px;
    font-family: "JetBrains Mono", "Consolas", "Courier New", monospace;
    font-size: 13px;
    selection-background-color: #3b82f6;
}

QLabel#badgeAuto, QLabel#badgeManual, QLabel#badgeMuted, QLabel#badgeError {
    border-radius: 9px;
    padding: 2px 9px;
    font-size: 11px;
    font-weight: 600;
}
QLabel#badgeAuto   { background: rgba(16, 185, 129, 0.18); color: #34d399; }
QLabel#badgeManual { background: rgba(59, 130, 246, 0.18); color: #60a5fa; }
QLabel#badgeMuted  { background: rgba(156, 163, 175, 0.14); color: #9ca3af; }
QLabel#badgeError  { background: rgba(239, 68, 68, 0.18); color: #f87171; }

QSplitter::handle { background: transparent; }
QSplitter::handle:horizontal { width: 10px; }

QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #2d3139; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #3d424d; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #2d3139; border-radius: 4px; min-width: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

QStatusBar { background: #0e0f12; border-top: 1px solid #2d3139; color: #9ca3af; }
QStatusBar QLabel { color: #9ca3af; }
QToolTip { background: #1a1c23; color: #e5e7eb; border: 1px solid #2d3139; padding: 4px; }
"""
