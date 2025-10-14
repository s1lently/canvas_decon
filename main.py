#!/usr/bin/env python3
"""
Canvas LMS Automation - Main Entry Point
Orchestrates: gui.qt (UI init) + gui.qt_interact (button logic) + checkStatus (status checks)
"""
import sys
from PyQt6.QtWidgets import QApplication

from gui.qt import init_qt_window
from gui.styles import DARK_THEME


def init():
    """Initialize: styles + Qt window + interactions + status"""
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_THEME)

    window = init_qt_window()  # Calls qt_interact + checkStatus inside
    window.show()

    return app


def main():
    """Main entry"""
    app = init()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
