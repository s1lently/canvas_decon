"""
Dark Next.js-style theme for PyQt6
"""

DARK_THEME = """
QMainWindow, QWidget {
    background-color: #0a0a0a;
    color: #ededed;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 14px;
}

QPushButton {
    background-color: #1a1a1a;
    color: #ededed;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #2a2a2a;
    border-color: #3a3a3a;
}

QPushButton:pressed {
    background-color: #0f0f0f;
}

QLineEdit {
    background-color: #1a1a1a;
    color: #ededed;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 10px 16px;
    selection-background-color: #2563eb;
}

QLineEdit:focus {
    border-color: #3b82f6;
    outline: none;
}

QTextEdit {
    background-color: #0f0f0f;
    color: #ededed;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 12px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 13px;
}

QTextEdit:focus {
    border-color: #3b82f6;
}

QTabWidget::pane {
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    background-color: #0f0f0f;
}

QTabBar::tab {
    background-color: #1a1a1a;
    color: #ededed;
    border: 1px solid #2a2a2a;
    border-bottom: none;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}

QTabBar::tab:selected {
    background-color: #0f0f0f;
    border-color: #3b82f6;
}

QTabBar::tab:hover {
    background-color: #2a2a2a;
}

QLabel {
    color: #ededed;
}

QListWidget {
    background-color: #0f0f0f;
    color: #ededed;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 8px;
    outline: none;
}

QListWidget::item {
    padding: 8px;
    border-radius: 4px;
    margin: 2px 0;
}

QListWidget::item:selected {
    background-color: #2563eb;
    color: #ffffff;
}

QListWidget::item:hover {
    background-color: #1a1a1a;
}

QListWidget:focus {
    border-color: #3b82f6;
}

/* Scrollbar styling */
QScrollBar:vertical {
    background: #0f0f0f;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background: #2a2a2a;
    border-radius: 6px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #3a3a3a;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: #0f0f0f;
    height: 12px;
    border-radius: 6px;
}

QScrollBar::handle:horizontal {
    background: #2a2a2a;
    border-radius: 6px;
    min-width: 20px;
}

QScrollBar::handle:horizontal:hover {
    background: #3a3a3a;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
"""
