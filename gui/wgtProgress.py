"""Progress bar widget for console tabs"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt


class ProgressWidget(QWidget):
    """Compact progress indicator with text and progress bar"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(3)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 12px; color: #ccc;")
        self.layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(15)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555;
                border-radius: 3px;
                background-color: #2a2a2a;
                text-align: center;
                font-size: 10px;
                color: #ccc;
            }
            QProgressBar::chunk {
                background-color: #3a7ca5;
                border-radius: 2px;
            }
        """)
        self.layout.addWidget(self.progress_bar)

    def update_progress(self, current, total, status_text=""):
        """Update progress bar and status text

        Args:
            current: Current progress value
            total: Total value (0 for indeterminate)
            status_text: Optional status message
        """
        if total == 0:
            # Indeterminate mode
            self.progress_bar.setRange(0, 0)
            self.progress_bar.setFormat("")
        else:
            # Determinate mode
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
            self.progress_bar.setFormat(f"{current}/{total}")

        if status_text:
            self.status_label.setText(status_text)

    def set_text_only(self, text):
        """Show only text, hide progress bar"""
        self.status_label.setText(text)
        self.progress_bar.hide()


def create_console_with_progress(console_tab_widget, tab_name):
    """Create console tab with embedded progress widget

    Args:
        console_tab_widget: QTabWidget to add tab to
        tab_name: Name for the tab

    Returns:
        tuple: (console_widget, progress_widget)
    """
    from PyQt6.QtWidgets import QTextEdit, QSplitter
    from PyQt6.QtCore import Qt

    # Create splitter (vertical: progress on top, console below)
    splitter = QSplitter(Qt.Orientation.Vertical)

    # Progress widget (top, compact)
    progress_widget = ProgressWidget()
    progress_widget.setMaximumHeight(60)

    # Console widget (bottom, main area)
    console_widget = QTextEdit()
    console_widget.setReadOnly(True)
    console_widget.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: 'Courier New', monospace; font-size: 11px;")

    # Add to splitter
    splitter.addWidget(progress_widget)
    splitter.addWidget(console_widget)
    splitter.setSizes([50, 350])  # Allocate most space to console

    # Add tab
    console_tab_widget.addTab(splitter, tab_name)
    console_tab_widget.setCurrentWidget(splitter)

    return console_widget, progress_widget
