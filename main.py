#!/usr/bin/env python3
"""
Canvas LMS Automation - Main Entry Point
Refactored: Uses modular Handler architecture
"""
import sys
from PyQt6.QtWidgets import QApplication

import config
from gui.qt import CanvasApp
from gui.config.cfgStyles import DARK_THEME


def main():
    """Main entry point"""
    # Ensure all required directories exist
    config.ensure_dirs()

    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_THEME)

    window = CanvasApp()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
