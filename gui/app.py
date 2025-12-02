"""Canvas LMS Automation - Main Application"""
import sys, os, threading, subprocess, platform
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QStackedWidget, QWidget, QVBoxLayout,
    QLabel, QDialog, QTextEdit, QHBoxLayout, QPushButton, QMessageBox, QAbstractItemView
)
from PyQt6.QtCore import pyqtSignal, QObject, QEvent, Qt
from PyQt6.uic import loadUi

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from func import checkStatus
from gui.styles import get_app_stylesheet, COLORS


def _resource_path(path):
    """Get resource path (dev + PyInstaller)"""
    try:
        return os.path.join(sys._MEIPASS, path)
    except Exception:
        return os.path.join(os.path.abspath("."), path)


# === SIGNALS ===
class AppSignals(QObject):
    """All application signals"""
    status_update = pyqtSignal()
    tab_content_update = pyqtSignal(str)
    auto_detail_status = pyqtSignal(str)
    preview_refresh = pyqtSignal()
    quiz_not_started = pyqtSignal()
    quiz_status_update = pyqtSignal(dict)
    category_refresh = pyqtSignal()
    toast_show = pyqtSignal(str, str, int)


# === MAIN APPLICATION ===
class CanvasApp(QMainWindow):
    """Main Application - Simple Python GUI"""

    def __init__(self):
        super().__init__()

        # === APPLY THEME ===
        self.setStyleSheet(get_app_stylesheet())

        # === SIGNALS ===
        self.signals = AppSignals()
        self._connect_signals()

        # === DATA ===
        from gui._internal.mgrData import DataManager
        from gui._internal.mgrDone import DoneManager
        self.dm = DataManager()
        self.done_mgr = DoneManager()
        self.course_detail_mgr = None
        self.auto_detail_mgr = None
        self.learn_sitting_widget = None
        self.history_mode = False

        # === MISSION CONTROL ===
        from gui._internal.wgtMissionControl import MissionControl
        self.mission_control = MissionControl()

        # === LOAD UI ===
        self._init_ui()

        # === VIEWS (replace handlers) ===
        from gui.main_view import MainView
        from gui.auto_view import AutoView
        from gui.detail_view import DetailView
        from gui.course_view import CourseView
        from gui.settings_view import SettingsView

        self.main_view = MainView(self)
        self.auto_view = AutoView(self)
        self.detail_view = DetailView(self)
        self.course_view = CourseView(self)
        self.settings_view = SettingsView(self)

        # === SIDEBAR (after views) ===
        from gui._internal.wgtSidebar import GlobalSidebar
        self.sidebar = GlobalSidebar(self, parent=self)
        self.sidebar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.sidebar.raise_()
        self._position_sidebar()

        # === KEYBOARD ===
        from gui._internal.keyboard import KeyboardHandler
        self.keyboard_handler = KeyboardHandler(self)
        self.keyboard_handler.install_list_event_filters()

        # === BINDINGS ===
        self._init_bindings()

        # === STARTUP ===
        self.dm.load_all()
        self._archive_past_todos()
        self.main_view.show_launcher()
        self._check_status()

        # === WINDOW ===
        self.setWindowTitle("Canvas LMS Automation")
        self.resize(1200, 675)  # 3/4 of original size
        self.installEventFilter(self)

    def _connect_signals(self):
        """Connect all signals to slots"""
        self.signals.status_update.connect(self._update_status)
        self.signals.tab_content_update.connect(self._update_tab_content)
        self.signals.auto_detail_status.connect(self._update_detail_status)
        self.signals.preview_refresh.connect(self._refresh_preview)
        self.signals.quiz_not_started.connect(self._on_quiz_not_started)
        self.signals.quiz_status_update.connect(self._update_quiz_status)
        self.signals.category_refresh.connect(self._refresh_category)
        self.signals.toast_show.connect(self._show_toast)

    def _init_ui(self):
        """Initialize UI structure"""
        # Container with sidebar margin
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 70, 0)
        layout.setSpacing(0)

        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget)
        self.setCentralWidget(container)

        # Load .ui files and apply theme
        self.main_window = loadUi(_resource_path('gui/ui/main.ui'))
        self.automation_window = loadUi(_resource_path('gui/ui/automation.ui'))
        self.course_detail_window = loadUi(_resource_path('gui/ui/course_detail.ui'))
        self.launcher_overlay = loadUi(_resource_path('gui/ui/launcher.ui'))
        self.settings_overlay = loadUi(_resource_path('gui/ui/settings_overlay.ui'))

        # Apply theme to all loaded windows (except settings_overlay which has its own transparent style)
        for w in [self.main_window, self.automation_window, self.course_detail_window,
                  self.launcher_overlay]:
            w.setStyleSheet(get_app_stylesheet())

        # Settings overlay keeps its own stylesheet for transparency
        # Don't override with global theme

        # AutoDetail is pure Python widget
        from gui._internal.wgtAutoDetailModern import ModernAutoDetailWidget
        self.auto_detail_window = ModernAutoDetailWidget()

        # Add to stack
        for w in [self.main_window, self.automation_window, self.course_detail_window, self.auto_detail_window]:
            self.stacked_widget.addWidget(w)

        # Status widgets
        self.status_widgets = {k: getattr(self.main_window, f'{k}Indicator')
                               for k in ['account', 'cookie', 'todos', 'network', 'courses']}

        # Enable external links
        for dv in [self.main_window.detailView, self.automation_window.automatableOpenDetailView,
                   self.automation_window.automatableCloseDetailView, self.automation_window.automatableDetailView,
                   self.automation_window.allItemsDetailView, self.course_detail_window.detailView]:
            dv.setOpenExternalLinks(True)

        # Drag-drop for course detail
        self.course_detail_window.itemList.setAcceptDrops(True)
        self.course_detail_window.itemList.setDragEnabled(False)
        self.course_detail_window.itemList.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)

        # Toggles
        from gui.widgets import IOSToggle
        self.history_toggle = IOSToggle(width=50, height=24)
        hist_label = QLabel("History")
        hist_label.setStyleSheet(f"font-size: 11px; color: {COLORS['text_secondary']};")
        hist_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_window.historyToggleLayout.addWidget(hist_label)
        self.main_window.historyToggleLayout.addWidget(self.history_toggle)

        self.thinking_toggle = IOSToggle(width=50, height=24)
        self.thinking_toggle.setChecked(True)
        self._replace_placeholder(self.auto_detail_window.thinkingTogglePlaceholder, self.thinking_toggle)

        self.manual_mode_toggle = IOSToggle(width=50, height=24)
        self._replace_placeholder(self.settings_overlay.manualModeTogglePlaceholder, self.manual_mode_toggle)

        # Hide old buttons
        for btn in ['getCookieBtn', 'getTodoBtn', 'getCourseBtn', 'gSyllAllBtn', 'cleanBtn', 'automationTopBtn', 'sittingBtn']:
            if hasattr(self.main_window, btn):
                getattr(self.main_window, btn).setVisible(False)

        # Category list
        self.main_window.categoryList.addItems(["Courses", "TODOs", "Files"])
        self.main_window.courseDetailBtn.setVisible(False)
        self.main_window.filterWidget.setVisible(False)  # Hidden until TODOs selected

        self.stacked_widget.setCurrentWidget(self.main_window)

        # Launcher overlay
        self.launcher_overlay.setParent(self.main_window)
        self.launcher_overlay.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        from gui.widgets import TodoItemDelegate, CourseItemDelegate
        self.launcher_overlay.todoList.setItemDelegate(TodoItemDelegate(self.launcher_overlay.todoList, launcher_mode=True))
        self.launcher_overlay.courseList.setItemDelegate(CourseItemDelegate(self.launcher_overlay.courseList))

        # Add HUD corner decorations to centerPanel
        self._add_hud_corners()

        # Add colored icons to launcher buttons
        self._add_launcher_button_icons()

        self.main_window.installEventFilter(self)
        self.launcher_overlay.todoList.installEventFilter(self)
        self.launcher_overlay.courseList.installEventFilter(self)

        # Settings overlay
        self.settings_overlay.setParent(self)
        self.settings_overlay.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.settings_overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)  # Enable translucent background
        self.settings_overlay.setAutoFillBackground(False)  # Allow transparency

        # Ensure contentContainer has proper attributes for rounded corners
        if hasattr(self.settings_overlay, 'contentContainer'):
            self.settings_overlay.contentContainer.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Block mouse events from passing through (prevent clicking through overlay)
        self.settings_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        self.settings_overlay.hide()
        self.sitting_window = self.settings_overlay

        # Install event filter for clicking outside to close
        self.settings_overlay.installEventFilter(self)

        # Sidebar (deferred to after views are created)
        self.sidebar = None

    def _add_launcher_button_icons(self):
        """Add colored square icons to launcher buttons"""
        from PyQt6.QtGui import QPixmap, QPainter, QIcon, QColor
        from PyQt6.QtCore import QSize

        def create_square_icon(color, size=8):
            """Create a small colored square icon"""
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.fillRect(0, 0, size, size, color)
            painter.end()
            return QIcon(pixmap)

        # Automation button - orange square
        orange_icon = create_square_icon(QColor(245, 158, 11))
        self.launcher_overlay.automationBtn.setIcon(orange_icon)
        self.launcher_overlay.automationBtn.setIconSize(QSize(8, 8))
        self.launcher_overlay.automationBtn.setText("  AUTOMATION")

        # Settings button - gray square
        gray_icon = create_square_icon(QColor(107, 114, 128))
        self.launcher_overlay.settingsBtn.setIcon(gray_icon)
        self.launcher_overlay.settingsBtn.setIconSize(QSize(8, 8))
        self.launcher_overlay.settingsBtn.setText("  SETTINGS")

    def _add_hud_corners(self):
        """Add HUD corner decorations to centerPanel"""
        from PyQt6.QtWidgets import QWidget
        from PyQt6.QtCore import Qt

        center_panel = self.launcher_overlay.centerPanel
        corner_size = 20
        offset = -2

        # Create corner widgets
        positions = [
            ('tl', offset, offset),  # top-left
            ('tr', None, offset),    # top-right
            ('bl', offset, None),    # bottom-left
            ('br', None, None),      # bottom-right
        ]

        self.hud_corners = []
        for name, left, top in positions:
            corner = QWidget(center_panel)
            corner.setObjectName('hudCorner')
            corner.setFixedSize(corner_size, corner_size)
            corner.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

            # Set stylesheet for each corner (different borders removed)
            if name == 'tl':
                corner.setStyleSheet('QWidget#hudCorner { background: transparent; border: 2px solid #3b82f6; border-bottom: none; border-right: none; }')
            elif name == 'tr':
                corner.setStyleSheet('QWidget#hudCorner { background: transparent; border: 2px solid #3b82f6; border-bottom: none; border-left: none; }')
            elif name == 'bl':
                corner.setStyleSheet('QWidget#hudCorner { background: transparent; border: 2px solid #3b82f6; border-top: none; border-right: none; }')
            elif name == 'br':
                corner.setStyleSheet('QWidget#hudCorner { background: transparent; border: 2px solid #3b82f6; border-top: none; border-left: none; }')

            self.hud_corners.append((corner, name, left, top))

        # Position will be set in resizeEvent
        center_panel.installEventFilter(self)

    def _position_hud_corners(self):
        """Position HUD corners on centerPanel"""
        if not hasattr(self, 'hud_corners'):
            return

        center_panel = self.launcher_overlay.centerPanel
        w, h = center_panel.width(), center_panel.height()

        for corner, name, left, top in self.hud_corners:
            offset = -2
            if name == 'tl':
                corner.move(offset, offset)
            elif name == 'tr':
                corner.move(w - corner.width() + abs(offset), offset)
            elif name == 'bl':
                corner.move(offset, h - corner.height() + abs(offset))
            elif name == 'br':
                corner.move(w - corner.width() + abs(offset), h - corner.height() + abs(offset))

    def _replace_placeholder(self, placeholder, widget):
        """Replace placeholder with widget"""
        if placeholder and placeholder.parent():
            layout = placeholder.parent().layout()
            if layout:
                idx = layout.indexOf(placeholder)
                layout.removeWidget(placeholder)
                placeholder.deleteLater()
                layout.insertWidget(idx, widget)

    def _position_sidebar(self):
        """Position sidebar at right edge"""
        w = self.sidebar.width() or self.sidebar.collapsed_width
        self.sidebar.move(self.width() - w, 0)
        self.sidebar.setFixedHeight(self.height())

    def _init_bindings(self):
        """Initialize all button bindings"""
        from gui._internal import utilQtInteract as qt_interact
        mw, sw, aw, cdw, adw = self.main_window, self.settings_overlay, self.automation_window, self.course_detail_window, self.auto_detail_window

        # Main window
        mw.backBtn.clicked.connect(self.main_view.show_launcher)
        mw.getCookieBtn.clicked.connect(lambda: qt_interact.on_get_cookie_clicked(None, self))
        mw.getTodoBtn.clicked.connect(lambda: qt_interact.on_get_todo_clicked(None, self))
        mw.getCourseBtn.clicked.connect(lambda: qt_interact.on_get_course_clicked(None, self))
        mw.gSyllAllBtn.clicked.connect(lambda: qt_interact.on_gsyll_all_clicked(None, self))
        mw.cleanBtn.clicked.connect(self.settings_view.show_clean_dialog)
        mw.automationTopBtn.clicked.connect(self.auto_view.open)
        mw.sittingBtn.clicked.connect(self.settings_view.show)
        mw.openFolderBtn.clicked.connect(self.main_view.on_open_folder_clicked)
        mw.courseDetailBtn.clicked.connect(self.course_view.open)
        mw.categoryList.currentRowChanged.connect(self.main_view.on_category_changed)
        mw.itemList.currentRowChanged.connect(self.main_view.on_item_changed)
        mw.itemList.itemChanged.connect(self.main_view.on_checkbox_changed)
        mw.itemList.itemDoubleClicked.connect(self.main_view.on_item_double_clicked)
        for f in [mw.filterHomework, mw.filterQuiz, mw.filterDiscussion, mw.filterAutomatable]:
            f.stateChanged.connect(self.main_view.apply_filters)

        # Settings overlay
        sw.backBtn.clicked.connect(self.settings_view.hide)
        sw.submitBtn.clicked.connect(lambda: qt_interact.on_submit_clicked(sw.accountInput, sw.passwordInput, sw.keyInput, self.stacked_widget, mw, self.manual_mode_toggle))
        sw.saveApiBtn.clicked.connect(self.settings_view.save_api_key)
        sw.savePrefBtn.clicked.connect(lambda: self.settings_view.save_preference(sw.baseUrlInput.text()))
        sw.refreshTasksBtn.clicked.connect(self.settings_view.refresh_tasks_table)
        sw.stopTaskBtn.clicked.connect(self.settings_view.stop_selected_task)
        sw.stopAllTasksBtn.clicked.connect(self.settings_view.stop_all_tasks)

        def on_manual_mode_changed(state):
            is_manual = (state == 2)
            sw.keyInput.setEnabled(not is_manual)
            sw.keyInput.setPlaceholderText("TOTP Key (Disabled)" if is_manual else "TOTP Key")
        self.manual_mode_toggle.stateChanged.connect(on_manual_mode_changed)

        # Automation window
        aw.backBtn.clicked.connect(lambda: qt_interact.on_back_clicked(self.stacked_widget, mw))
        aw.getTodoBtn.clicked.connect(lambda: qt_interact.on_get_todo_clicked(None, self))
        aw.cleanBtn.clicked.connect(lambda: qt_interact.on_clean_clicked(None, self))

        for tab_idx, prefix in enumerate(['automatableOpen', 'automatableClose', 'automatable', 'allItems']):
            cat_list = getattr(aw, f'{prefix}CategoryList')
            item_list = getattr(aw, f'{prefix}ItemList')
            cat_list.currentRowChanged.connect(lambda idx, ti=tab_idx: self.auto_view.on_category_changed(idx, ti))
            item_list.currentRowChanged.connect(lambda idx, ti=tab_idx: self.auto_view.on_item_changed(idx, ti))
            item_list.itemChanged.connect(self.auto_view.on_checkbox_changed)
            item_list.itemDoubleClicked.connect(self.auto_view.on_item_double_clicked)

        # Course detail window
        cdw.backBtn.clicked.connect(lambda: qt_interact.on_back_clicked(self.stacked_widget, mw))
        cdw.openSyllabusFolderBtn.clicked.connect(self.course_view.on_open_syllabus_folder)
        cdw.openTextbookFolderBtn.clicked.connect(self.course_view.on_open_textbook_folder)
        cdw.deconTextbookBtn.clicked.connect(self.course_view.on_decon_textbook)
        cdw.loadFromDeconBtn.clicked.connect(lambda: qt_interact.on_load_from_decon_clicked(self))
        cdw.learnMaterialBtn.clicked.connect(lambda: qt_interact.on_learn_material_clicked(self))
        cdw.itemList.itemDoubleClicked.connect(self.course_view.on_item_double_clicked)
        cdw.categoryList.currentRowChanged.connect(self.course_view.on_category_changed)
        cdw.itemList.currentRowChanged.connect(self.course_view.on_item_changed)
        cdw.itemList.dragEnterEvent = self.course_view.drag_enter
        cdw.itemList.dragMoveEvent = self.course_view.drag_move
        cdw.itemList.dropEvent = self.course_view.drag_drop

        # Auto detail window
        def on_back():
            self.detail_view.stop_quiz_timer()
            qt_interact.on_back_clicked(self.stacked_widget, mw)
        adw.back_clicked.connect(on_back)
        adw.folder_clicked.connect(self.detail_view.on_folder_clicked)
        adw.debug_clicked.connect(self.detail_view.on_debug_clicked)
        adw.again_clicked.connect(self.detail_view.on_again_clicked)
        adw.preview_clicked.connect(self.detail_view.on_preview_clicked)
        adw.submit_clicked.connect(self.detail_view.on_submit_clicked)
        adw.viewDetailBtn.clicked.connect(self.detail_view.on_view_detail_clicked)
        adw.product_changed.connect(self.detail_view.on_product_changed)
        adw.model_changed.connect(self.detail_view.on_model_changed)
        adw.tab_changed.connect(self.detail_view.on_tab_changed)
        self.detail_view.init_model_selection()

        # Launcher overlay
        self.launcher_overlay.dashboardBtn.clicked.connect(self.main_view.hide_launcher)
        self.launcher_overlay.automationBtn.clicked.connect(lambda: (self.main_view.hide_launcher(), self.auto_view.open()))
        self.launcher_overlay.settingsBtn.clicked.connect(self.settings_view.show)
        self.launcher_overlay.courseList.itemDoubleClicked.connect(self.main_view.on_course_double_clicked)
        self.launcher_overlay.todoList.itemDoubleClicked.connect(self.main_view.on_todo_double_clicked)

        # Toggles
        self.history_toggle.stateChanged.connect(self.main_view.on_history_toggle)

        # Sidebar
        def navigate(page_id):
            if page_id == 'launch':
                self.stacked_widget.setCurrentWidget(mw)
                self.main_view.show_launcher()
            elif page_id == 'main':
                self.stacked_widget.setCurrentWidget(mw)
                self.main_view.hide_launcher()
            elif page_id == 'auto':
                self.auto_view.open()
            elif page_id == 'settings':
                self.settings_view.show()
        self.sidebar.navigate.connect(navigate)

        # Initial state
        self.settings_view.load_login_info()
        self.settings_view.load_api_settings()

    def _archive_past_todos(self):
        """Archive past todos"""
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'func'))
            from mgrHistory import archive_past_todos
            archive_past_todos()
        except Exception:
            pass

    def _check_status(self):
        """Initial status check"""
        from gui._internal import utilQtInteract
        if os.path.exists(config.COOKIES_FILE):
            age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(config.COOKIES_FILE))
            if age > timedelta(hours=24):
                print("[INFO] Cookies expired, auto-refreshing...")
                utilQtInteract.on_get_cookie_clicked(None, self)

        self._update_status()
        self._update_user_info()

        status = checkStatus.get_all_status()
        if status['cookie'] == 1:
            if status['courses'] == 0:
                utilQtInteract.on_get_course_clicked(None, self)
            utilQtInteract.on_get_todo_clicked(None, self)

        threading.Thread(target=self._status_daemon, daemon=True).start()

    def _status_daemon(self):
        """Background status update"""
        import time
        while True:
            time.sleep(30)
            self.signals.status_update.emit()

    # === SIGNAL SLOTS ===
    def _update_status(self):
        from gui._internal import utilQtInteract
        utilQtInteract.update_status_indicators(self.status_widgets, checkStatus)

    def _update_user_info(self):
        from gui._internal import utilQtInteract
        utilQtInteract.update_user_info_labels(
            self.main_window.emailLabel, self.main_window.nameLabel, self.main_window.idLabel)

    def _update_tab_content(self, html):
        if hasattr(self, 'course_view'):
            self.course_view.update_html(html)

    def _update_detail_status(self, text):
        if self.auto_detail_window:
            self.auto_detail_window.previewStatusLabel.setText(text)

    def _refresh_preview(self):
        self.detail_view.refresh_preview()

    def _on_quiz_not_started(self):
        self.detail_view.on_quiz_not_started()

    def _update_quiz_status(self, status):
        self.detail_view.update_quiz_status_bar(status)

    def _refresh_category(self):
        self.course_view.refresh_category()

    def _show_toast(self, message, msg_type, duration):
        from gui.widgets import show_toast
        show_toast(self, message, msg_type, duration)

    def show_toast(self, message, msg_type='success', duration=3000):
        """Thread-safe toast"""
        self.signals.toast_show.emit(message, msg_type, duration)

    # === EVENTS ===
    def eventFilter(self, obj, event):
        if obj == self.main_window and event.type() == QEvent.Type.Resize:
            self.main_view.update_launcher_geometry()
            return False
        if hasattr(self, 'launcher_overlay') and obj == self.launcher_overlay.centerPanel and event.type() == QEvent.Type.Resize:
            self._position_hud_corners()
            return False

        # Settings overlay - click outside to close
        if hasattr(self, 'settings_overlay') and obj == self.settings_overlay and event.type() == QEvent.Type.MouseButtonPress:
            # Check if click is outside contentContainer
            content = self.settings_overlay.contentContainer
            if content:
                click_pos = event.pos()
                content_rect = content.geometry()
                if not content_rect.contains(click_pos):
                    self.settings_view.hide()
                    return True

        if event.type() == QEvent.Type.KeyPress:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_M:
                self.mission_control.setVisible(not self.mission_control.isVisible())
                if self.mission_control.isVisible():
                    self.mission_control.raise_()
                return True
        return self.keyboard_handler.handle_event(obj, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'sidebar'):
            self._position_sidebar()

    # === UTILITY ===
    def open_folder(self, path):
        """Open folder cross-platform"""
        if path and os.path.exists(path):
            {'Windows': lambda: os.startfile(path),
             'Darwin': lambda: subprocess.run(['open', path]),
             'Linux': lambda: subprocess.run(['xdg-open', path])
            }.get(platform.system(), lambda: None)()


def main():
    """Entry point"""
    app = QApplication(sys.argv)
    window = CanvasApp()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
