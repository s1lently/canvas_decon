"""
Canvas LMS Automation - Lightweight Qt Router (Refactored)
Original: 1824 lines → New: ~250 lines (86% reduction)
All business logic moved to qt_utils/ handlers
"""
import sys, os, threading
from datetime import datetime, timedelta
from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtCore import pyqtSignal, QObject, QEvent

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config, checkStatus
from gui import utilQtInteract
from gui.mgrData import DataManager
from gui.mgrDone import DoneManager
from gui import rdrToast

# Import all handlers
from gui.qt_utils.window_handlers.launcher_handler import LauncherHandler
from gui.qt_utils.window_handlers.main_window_handler import MainWindowHandler
from gui.qt_utils.window_handlers.automation_window_handler import AutomationWindowHandler
from gui.qt_utils.window_handlers.course_detail_window_handler import CourseDetailWindowHandler
from gui.qt_utils.window_handlers.auto_detail_window_handler import AutoDetailWindowHandler
from gui.qt_utils.window_handlers.sitting_window_handler import SittingWindowHandler
from gui.qt_utils.event_handlers.keyboard_handler import KeyboardHandler
from gui.qt_utils.initializers.ui_initializer import UIInitializer
from gui.qt_utils.initializers.signal_initializer import SignalInitializer


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
        self.resize(1400, 800)
        self.installEventFilter(self)

    # === STATUS & UPDATES ===
    def check_status(self):
        """Initial status check + auto-fix"""
        mt = self.main_window.consoleTabWidget.widget(0)
        console = mt.findChild(self.main_window.consoleOutput.__class__) if mt else None

        # Check cookie expiry
        if os.path.exists(config.COOKIES_FILE):
            cookie_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(config.COOKIES_FILE))
            if cookie_age > timedelta(hours=24):
                if console:
                    console.append("[INFO] Cookies expired, auto-refreshing...")
                utilQtInteract.on_get_cookie_clicked(self.main_window.consoleTabWidget)

        self.update_status()
        self.update_user_info()

        # Auto-fetch data
        status = checkStatus.get_all_status()
        if status['cookie'] == 1:
            if console:
                console.append("[INFO] Cookie valid, checking data...")

            if status['courses'] == 0:
                if console:
                    console.append("[INFO] Fetching courses...")
                utilQtInteract.on_get_course_clicked(self.main_window.consoleTabWidget, self)

            # Always fetch TODOs on startup
            if console:
                console.append("[INFO] Auto-fetching todos...")
            utilQtInteract.on_get_todo_clicked(self.main_window.consoleTabWidget, self)

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
        if self.course_detail_window:
            self.course_detail_window.detailView.setHtml(html)

    def _update_auto_detail_status(self, status_text):
        """Update AutoDetail status label"""
        if self.auto_detail_window:
            self.auto_detail_window.previewStatusLabel.setText(status_text)

    def _refresh_auto_detail_preview(self):
        """Refresh AutoDetail preview"""
        self.auto_detail_handler.refresh_preview()

    def _refresh_current_category(self):
        """Refresh current category in CourseDetail"""
        self.course_detail_handler.refresh_current_category()

    # === EVENT HANDLING ===
    def eventFilter(self, obj, event):
        """Global event filter - delegates to KeyboardHandler"""
        # Handle main window resize for launcher
        if obj == self.main_window and event.type() == QEvent.Type.Resize:
            self.launcher_handler.update_geometry()
            return False

        # Delegate all other events to keyboard handler
        return self.keyboard_handler.handle_event(obj, event)


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
