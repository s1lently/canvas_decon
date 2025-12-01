"""
Canvas LMS Automation - Qt Router
All business logic delegated to gui/handlers/
"""
import sys, os, threading, subprocess, platform
from datetime import datetime, timedelta
from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtCore import pyqtSignal, QObject, QEvent, Qt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config, checkStatus
from gui.core import utilQtInteract
from gui.core.mgrData import DataManager
from gui.core.mgrDone import DoneManager
from gui.widgets import rdrToast
from gui.widgets.wgtMissionControl import MissionControl

# Import handlers & initializers (flattened structure)
from gui.handlers import (
    LauncherHandler, MainWindowHandler, AutomationWindowHandler,
    CourseDetailWindowHandler, AutoDetailWindowHandler,
    SittingWindowHandler, KeyboardHandler
)
from gui.init import UIInitializer, SignalInitializer


# === SIGNALS ===
class StatusUpdateSignal(QObject):
    """Status check result updates"""
    update = pyqtSignal()


class TabContentSignal(QObject):
    """Course tab content updates"""
    update_html = pyqtSignal(str)


class AutoDetailSignal(QObject):
    """AutoDetail status and preview updates"""
    status_update = pyqtSignal(str)
    preview_refresh = pyqtSignal()
    quiz_not_started = pyqtSignal()
    quiz_status_update = pyqtSignal(dict)  # Real-time quiz status


class CourseDetailSignal(QObject):
    """CourseDetail category refresh"""
    refresh_category = pyqtSignal()


class ToastSignal(QObject):
    """Toast notification display"""
    show = pyqtSignal(str, str, int)  # message, msg_type, duration


# === MAIN APPLICATION ===
class CanvasApp(QMainWindow):
    """
    Lightweight Qt Router - All business logic delegated to handlers

    Architecture:
    - 6 Window Handlers (LauncherHandler, MainWindowHandler, etc.)
    - 1 Event Handler (KeyboardHandler)
    - 2 Initializers (UIInitializer, SignalInitializer)
    - 3 Content Processors (HTMLProcessor, TabLoader, PreviewLoader)
    """

    def __init__(self):
        super().__init__()

        # === DATA MANAGERS ===
        self.dm = DataManager()
        self.done_mgr = DoneManager()
        self.course_detail_mgr = None  # Lazy init
        self.auto_detail_mgr = None    # Lazy init
        self.learn_sitting_widget = None  # LearnSittingWidget for Textbook
        self.mission_control = MissionControl()  # Global task manager

        # === STATE ===
        self.history_mode = False

        # === SIGNALS ===
        self.status_signal = StatusUpdateSignal()
        self.status_signal.update.connect(self.update_status)

        self.tab_content_signal = TabContentSignal()
        self.tab_content_signal.update_html.connect(self._update_course_detail_html)

        self.auto_detail_signal = AutoDetailSignal()
        self.auto_detail_signal.status_update.connect(self._update_auto_detail_status)
        self.auto_detail_signal.preview_refresh.connect(self._refresh_auto_detail_preview)
        self.auto_detail_signal.quiz_not_started.connect(self._on_quiz_not_started)
        self.auto_detail_signal.quiz_status_update.connect(self._update_quiz_status)

        self.course_detail_signal = CourseDetailSignal()
        self.course_detail_signal.refresh_category.connect(self._refresh_current_category)

        self.toast_signal = ToastSignal()
        self.toast_signal.show.connect(self._show_toast_slot)

        # === WINDOW HANDLERS ===
        self.launcher_handler = LauncherHandler(self)
        self.main_handler = MainWindowHandler(self)
        self.automation_handler = AutomationWindowHandler(self)
        self.course_detail_handler = CourseDetailWindowHandler(self)
        self.auto_detail_handler = AutoDetailWindowHandler(self)
        self.sitting_handler = SittingWindowHandler(self)
        self.keyboard_handler = KeyboardHandler(self)

        # === INITIALIZE ===
        UIInitializer.init_qt(self)
        SignalInitializer.init_button_bindings(self)
        UIInitializer.init_data_viewer(self)
        self.keyboard_handler.install_list_event_filters()
        self.check_status()

        # === WINDOW PROPERTIES ===
        self.setWindowTitle("Canvas LMS Automation")
        self.resize(1600, 900)  # Increased resolution for better visibility
        self.installEventFilter(self)

        # Position sidebar after window resize
        if hasattr(self, 'sidebar'):
            UIInitializer._position_sidebar(self)

    # === STATUS & UPDATES ===
    def check_status(self):
        """Initial status check + auto-fix"""
        # Check cookie expiry
        if os.path.exists(config.COOKIES_FILE):
            cookie_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(config.COOKIES_FILE))
            if cookie_age > timedelta(hours=24):
                print("[INFO] Cookies expired, auto-refreshing...")
                utilQtInteract.on_get_cookie_clicked(None, self)

        self.update_status()
        self.update_user_info()

        # Auto-fetch data
        status = checkStatus.get_all_status()
        if status['cookie'] == 1:
            print("[INFO] Cookie valid, checking data...")

            if status['courses'] == 0:
                print("[INFO] Fetching courses...")
                utilQtInteract.on_get_course_clicked(None, self)

            # Always fetch TODOs on startup (via Mission Control)
            print("[INFO] Auto-fetching todos...")
            utilQtInteract.on_get_todo_clicked(None, self)

        # Start status update daemon
        threading.Thread(target=self._status_update_daemon, daemon=True).start()

    def _status_update_daemon(self):
        """Background thread: Update status every 30s"""
        import time
        while True:
            time.sleep(30)
            self.status_signal.update.emit()

    def update_status(self):
        """Update status indicators"""
        utilQtInteract.update_status_indicators(self.status_widgets, checkStatus)

    def update_user_info(self):
        """Update user info labels"""
        utilQtInteract.update_user_info_labels(
            self.main_window.emailLabel,
            self.main_window.nameLabel,
            self.main_window.idLabel
        )

    # === TOAST NOTIFICATIONS ===
    def show_toast(self, message, msg_type='success', duration=3000):
        """Show toast notification (thread-safe)"""
        self.toast_signal.show.emit(message, msg_type, duration)

    def _show_toast_slot(self, message, msg_type, duration):
        """Slot: Create toast in main thread"""
        rdrToast.show_toast(self, message, msg_type, duration)

    # === SIGNAL SLOTS (Thread-safe UI updates) ===
    def _update_course_detail_html(self, html):
        """Update CourseDetail HTML view"""
        if hasattr(self, 'course_detail_handler'):
            self.course_detail_handler.update_html(html)

    def _update_auto_detail_status(self, status_text):
        """Update AutoDetail status label"""
        if self.auto_detail_window:
            self.auto_detail_window.previewStatusLabel.setText(status_text)

    def _refresh_auto_detail_preview(self):
        """Refresh AutoDetail preview"""
        self.auto_detail_handler.refresh_preview()

    def _on_quiz_not_started(self):
        """Handle quiz not started signal"""
        self.auto_detail_handler.on_quiz_not_started()

    def _update_quiz_status(self, status):
        """Update quiz status bar with real-time data"""
        self.auto_detail_handler.update_quiz_status_bar(status)

    def _refresh_current_category(self):
        """Refresh current category in CourseDetail"""
        self.course_detail_handler.refresh_current_category()

    # === UTILITY METHODS ===
    def _open_folder(self, path):
        """Open folder in system file manager (cross-platform)"""
        if path and os.path.exists(path):
            {
                'Windows': lambda: os.startfile(path),
                'Darwin': lambda: subprocess.run(['open', path]),
                'Linux': lambda: subprocess.run(['xdg-open', path])
            }.get(platform.system(), lambda: None)()

    def _show_clean_dialog(self):
        """Show clean dialog for deleting temporary files"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QHBoxLayout, QPushButton, QMessageBox
        from io import StringIO

        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from clean import preview_deletion, clean_directory, build_tree, print_tree
        except ImportError:
            QMessageBox.warning(self, "Error", "Clean module not found")
            return

        to_delete = preview_deletion()
        if not to_delete:
            return QMessageBox.information(self, "Clean", "No files to clean!")

        tree_output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = tree_output
        print_tree(build_tree(to_delete))
        sys.stdout = old_stdout

        dialog = QDialog(self)
        dialog.setWindowTitle("Clean Confirmation")
        dialog.setMinimumSize(600, 400)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("The following files will be deleted:"))
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(f"Found {len(to_delete)} files to clean:\n\n{tree_output.getvalue()}")
        layout.addWidget(text_edit)
        button_layout = QHBoxLayout()
        yes_btn, cancel_btn = QPushButton("Yes"), QPushButton("Cancel")
        yes_btn.clicked.connect(lambda: (
            clean_directory(to_delete),
            QMessageBox.information(self, "Clean", "Files cleaned successfully!"),
            dialog.accept()
        ))
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(yes_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        dialog.exec()

    # === EVENT HANDLING ===
    def eventFilter(self, obj, event):
        """Global event filter - delegates to KeyboardHandler"""
        # Handle main window resize for launcher
        if obj == self.main_window and event.type() == QEvent.Type.Resize:
            self.launcher_handler.update_geometry()
            return False

        # Ctrl+M: Toggle Mission Control
        if event.type() == QEvent.Type.KeyPress:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_M:
                if self.mission_control.isVisible():
                    self.mission_control.hide()
                else:
                    self.mission_control.show()
                    self.mission_control.raise_()
                return True

        # Delegate all other events to keyboard handler
        return self.keyboard_handler.handle_event(obj, event)

    def resizeEvent(self, event):
        """Handle window resize - reposition floating sidebar"""
        super().resizeEvent(event)
        if hasattr(self, 'sidebar'):
            from gui.init import UIInitializer
            UIInitializer._position_sidebar(self)


# === APPLICATION ENTRY POINT ===
def main():
    """Application entry point"""
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = CanvasApp()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
