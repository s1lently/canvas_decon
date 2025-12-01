#!/usr/bin/env python3
"""Canvas LMS Automation - Main Entry Point"""
import sys
from PyQt6.QtWidgets import QApplication

import config
from gui.app import CanvasApp


def main():
    """Main entry point"""
    config.ensure_dirs()
    app = QApplication(sys.argv)
    window = CanvasApp()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
