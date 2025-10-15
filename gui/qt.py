import sys, os, time, threading, json, re, requests, html2text, webbrowser, subprocess, platform; from datetime import datetime, timedelta
from io import StringIO
from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QListWidgetItem, QListWidget, QMessageBox, QStyledItemDelegate, QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout, QLineEdit
from PyQt6.QtCore import pyqtSignal, QObject, Qt, QEvent
from PyQt6.uic import loadUi
from bs4 import BeautifulSoup
import markdown as md_lib
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config, checkStatus; from gui import qt_interact, formatters, delegates, model_config, toast_notification
from gui.data_manager import DataManager
from gui.done_manager import DoneManager
from gui.course_detail_manager import CourseDetailManager
from gui.auto_detail_manager import AutoDetailManager
from gui.styles import DARK_THEME
from gui.ios_toggle import IOSToggle
class StatusUpdateSignal(QObject):
    update = pyqtSignal()
class TabContentSignal(QObject):
    update_html = pyqtSignal(str)
class AutoDetailSignal(QObject):
    status_update = pyqtSignal(str)
    preview_refresh = pyqtSignal()
class CourseDetailSignal(QObject):
    refresh_category = pyqtSignal()
class ToastSignal(QObject):
    show = pyqtSignal(str, str, int)  # message, msg_type, duration
class CanvasApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.dm, self.done_mgr, self.course_detail_mgr, self.auto_detail_mgr = DataManager(), DoneManager(), None, None
        self.history_mode = False; self.status_signal = StatusUpdateSignal()
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
        self.init_qt()
        self.init_button_bindings()
        self.init_data_viewer()
        self.check_status()
        self.setWindowTitle("Canvas LMS Automation")
        self.resize(1400, 800)
        self.installEventFilter(self)
        self._install_list_event_filters()
    def init_qt(self):
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        ui_dir = os.path.join(os.path.dirname(__file__), 'ui'); self.main_window = loadUi(os.path.join(ui_dir, 'main.ui'))
        self.sitting_window = loadUi(os.path.join(ui_dir, 'sitting.ui')); self.automation_window = loadUi(os.path.join(ui_dir, 'automation.ui'))
        self.course_detail_window = loadUi(os.path.join(ui_dir, 'course_detail.ui')); self.auto_detail_window = loadUi(os.path.join(ui_dir, 'autoDetail.ui'))
        self.launcher_overlay = loadUi(os.path.join(ui_dir, 'launcher.ui'))
        for w in [self.main_window, self.sitting_window, self.automation_window, self.course_detail_window, self.auto_detail_window]:
            self.stacked_widget.addWidget(w)
        self.status_widgets = {k: getattr(self.main_window, f'{k}Indicator') for k in ['account', 'cookie', 'todos', 'network', 'courses']}
        for dv in [self.main_window.detailView, self.automation_window.automatableOpenDetailView, self.automation_window.automatableCloseDetailView,
                   self.automation_window.automatableDetailView, self.automation_window.allItemsDetailView, self.course_detail_window.detailView,
                   self.auto_detail_window.assignmentDetailView, self.auto_detail_window.refFilesView, self.auto_detail_window.aiPreviewView]:
            dv.setOpenExternalLinks(True)
        self.ios_toggle_main = IOSToggle(width=50, height=24)
        self.main_window.categoryColumnLayout.addWidget(self.ios_toggle_main)
        self.ios_toggles_auto = [IOSToggle(width=50, height=24) for _ in range(4)]
        for toggle, layout in zip(self.ios_toggles_auto, ['automatableOpenCategoryLayout', 'automatableCloseCategoryLayout', 'automatableCategoryLayout', 'allItemsCategoryLayout']):
            getattr(self.automation_window, layout).addWidget(toggle)
        self.ios_toggle_course_detail = IOSToggle(width=50, height=24)
        self.course_detail_window.toggleLayout.addWidget(self.ios_toggle_course_detail)
        self.ios_toggle_course_detail.stateChanged.connect(lambda: self.on_course_detail_category_changed(self.course_detail_window.categoryList.currentRow()))
        # Enable drag-and-drop for course detail itemList
        self.course_detail_window.itemList.setAcceptDrops(True)
        self.course_detail_window.itemList.setDragEnabled(False)
        self.course_detail_window.itemList.dragEnterEvent = self._course_item_drag_enter
        self.course_detail_window.itemList.dragMoveEvent = self._course_item_drag_move
        self.course_detail_window.itemList.dropEvent = self._course_item_drop
        self.history_toggle = IOSToggle(width=50, height=24); hist_label = QLabel("History")
        hist_label.setStyleSheet("font-size: 11px; color: #aaa;")
        hist_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_window.historyToggleLayout.addWidget(hist_label)
        self.main_window.historyToggleLayout.addWidget(self.history_toggle)
        self.history_toggle.setChecked(False)
        self.stacked_widget.setCurrentWidget(self.main_window)
        self._init_launcher_overlay_ui()
    def _init_launcher_overlay_ui(self):
        """Initialize launcher overlay UI without data (defer data population)"""
        from PyQt6.QtWidgets import QWidget
        from PyQt6.QtCore import Qt as QtCore
        self.launcher_overlay.setParent(self.main_window)
        self.launcher_overlay.setAttribute(QtCore.WidgetAttribute.WA_StyledBackground, True)
        self.launcher_overlay.dashboardBtn.clicked.connect(self._hide_launcher)
        self.launcher_overlay.automationBtn.clicked.connect(lambda: (self._hide_launcher(), self.on_automation_top_clicked()))
        self.launcher_overlay.settingsBtn.clicked.connect(lambda: qt_interact.on_login_clicked(self.main_window, self.stacked_widget, self.sitting_window, self))
        self.launcher_overlay.courseList.itemDoubleClicked.connect(self._on_launcher_course_double_clicked)
        self.launcher_overlay.todoList.itemDoubleClicked.connect(self._on_launcher_todo_double_clicked)
        self.launcher_overlay.todoList.setItemDelegate(delegates.TodoItemDelegate(self.launcher_overlay.todoList))
        self.main_window.installEventFilter(self)  # Track main_window resizes
        self.launcher_overlay.todoList.installEventFilter(self)
        self.launcher_overlay.courseList.installEventFilter(self)
    def _show_launcher(self):
        """Show launcher overlay with updated data and geometry"""
        self._populate_launcher_data()
        self._update_launcher_geometry()
        self.launcher_overlay.raise_()
        self.launcher_overlay.show()
    def _update_launcher_geometry(self):
        """Update launcher overlay geometry to match main window size"""
        if hasattr(self, 'launcher_overlay') and self.launcher_overlay:
            self.launcher_overlay.setGeometry(0, 0, self.main_window.width(), self.main_window.height())
    def _populate_launcher_data(self):
        """Populate launcher overlay with TODO and Course data"""
        self.launcher_overlay.todoList.clear()
        self.launcher_overlay.courseList.clear()
        for todo in self.dm.get('todos'):
            item = QListWidgetItem(f"{todo.get('course_name', '')} - {todo.get('name', '')}")
            item.setData(Qt.ItemDataRole.UserRole, self.dm.classify_todo(todo))
            item.setData(Qt.ItemDataRole.UserRole + 1, todo)
            self.launcher_overlay.todoList.addItem(item)
        for course in self.dm.get('courses'):
            item = QListWidgetItem(course.get('name', 'Unknown'))
            self.launcher_overlay.courseList.addItem(item)
    def _hide_launcher(self):
        """Hide the launcher overlay"""
        self.launcher_overlay.hide()
    def _load_current_login_info(self):
        """Load and display current login account info"""
        try:
            if os.path.exists(config.ACCOUNT_CONFIG_FILE):
                with open(config.ACCOUNT_CONFIG_FILE) as f:
                    account_data = json.load(f); account = account_data.get('account', '--')
                    self.sitting_window.accountDisplayLabel.setText(f"Account: {account}")
        except:
            self.sitting_window.accountDisplayLabel.setText("Account: --")
    def _load_api_settings(self):
        """Load current API settings into the form"""
        try:
            if os.path.exists(config.ACCOUNT_CONFIG_FILE):
                with open(config.ACCOUNT_CONFIG_FILE) as f:
                    config_data = json.load(f)
                    gemini_key = config_data.get('gemini_api_key', '')
                    if gemini_key:
                        display_key = gemini_key[:10] + '...' if len(gemini_key) > 10 else gemini_key
                        self.sitting_window.geminiApiInput.setText(display_key)
                        self.sitting_window.geminiApiInput.setProperty('full_key', gemini_key)
                    claude_key = config_data.get('claude_api_key', '')
                    if claude_key:
                        display_key = claude_key[:10] + '...' if len(claude_key) > 10 else claude_key
                        self.sitting_window.claudeApiInput.setText(display_key)
                        self.sitting_window.claudeApiInput.setProperty('full_key', claude_key)
        except:
            pass
    def _on_gemini_api_focus(self):
        """Clear Gemini API key input if it contains masked value"""
        if self.sitting_window.geminiApiInput.text().endswith('...'):
            self.sitting_window.geminiApiInput.clear()
    def _on_claude_api_focus(self):
        """Clear Claude API key input if it contains masked value"""
        if self.sitting_window.claudeApiInput.text().endswith('...'):
            self.sitting_window.claudeApiInput.clear()
    def _save_api_key(self):
        """Save both API keys to account_config.json"""
        gemini_key = self.sitting_window.geminiApiInput.text(); claude_key = self.sitting_window.claudeApiInput.text()
        if gemini_key.endswith('...'):
            full_key = self.sitting_window.geminiApiInput.property('full_key')
            if full_key:
                gemini_key = full_key
            else:
                gemini_key = ''
        if claude_key.endswith('...'):
            full_key = self.sitting_window.claudeApiInput.property('full_key')
            if full_key:
                claude_key = full_key
            else:
                claude_key = ''
        if not gemini_key and not claude_key:
            QMessageBox.warning(self, "Error", "Please enter at least one API key!")
            return
        try:
            config_data = {}
            if os.path.exists(config.ACCOUNT_CONFIG_FILE):
                with open(config.ACCOUNT_CONFIG_FILE) as f:
                    config_data = json.load(f)
            if gemini_key:
                config_data['gemini_api_key'] = gemini_key
            if claude_key:
                config_data['claude_api_key'] = claude_key
            with open(config.ACCOUNT_CONFIG_FILE, 'w') as f:
                json.dump(config_data, f, indent=2)
            saved_keys = []
            if gemini_key:
                saved_keys.append("Gemini")
            if claude_key:
                saved_keys.append("Claude")
            QMessageBox.information(self, "Success", f"{' and '.join(saved_keys)} API Key(s) saved successfully!\nRestart the app to apply changes.")
            self._load_api_settings()  # Reload to show masked keys
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save API keys: {str(e)}")
    def _save_preference(self, base_url):
        """Save preference (base_url) to account_config.json"""
        if not base_url:
            QMessageBox.warning(self, "Error", "Please enter a base URL!")
            return
        try:
            config_data = {}
            if os.path.exists(config.ACCOUNT_CONFIG_FILE):
                with open(config.ACCOUNT_CONFIG_FILE) as f:
                    config_data = json.load(f)
            if 'preference' not in config_data:
                config_data['preference'] = {}; config_data['preference']['base_url'] = base_url
            with open(config.ACCOUNT_CONFIG_FILE, 'w') as f:
                json.dump(config_data, f, indent=2)
            QMessageBox.information(self, "Success", "Preference saved successfully!\nRestart the app to apply changes.")
            self.sitting_window.baseUrlInput.clear()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save preference: {str(e)}")
    def _on_launcher_course_double_clicked(self, item):
        """Handle double-click on launcher course list -> open CourseDetail"""
        course_name = item.text(); courses = self.dm.get('courses')
        for i, course in enumerate(courses):
            if course.get('name') == course_name:
                self.course_detail_mgr = CourseDetailManager(course, self.dm.get('todos'), self.dm.get('history_todos'))
                self.populate_course_detail_window()
                self._hide_launcher()
                self.stacked_widget.setCurrentWidget(self.course_detail_window)
                break
    def _on_launcher_todo_double_clicked(self, item):
        """Handle double-click on launcher TODO list -> open AutoDetail"""
        todo = item.data(Qt.ItemDataRole.UserRole + 1)
        if todo:
            meta = self.dm.classify_todo(todo)
            if meta.get('is_automatable'):
                self.auto_detail_mgr = AutoDetailManager(todo)
                self.populate_auto_detail_window()
                self._hide_launcher()
                self.stacked_widget.setCurrentWidget(self.auto_detail_window)
    def init_button_bindings(self):
        mw, sw, aw, cdw = self.main_window, self.sitting_window, self.automation_window, self.course_detail_window
        for btn, handler in [('backBtn', self._show_launcher),
                             ('getCookieBtn', lambda: qt_interact.on_get_cookie_clicked(mw.consoleTabWidget, self)),
                             ('getTodoBtn', lambda: qt_interact.on_get_todo_clicked(mw.consoleTabWidget, self)),
                             ('getCourseBtn', lambda: qt_interact.on_get_course_clicked(mw.consoleTabWidget, self)),
                             ('gSyllAllBtn', lambda: qt_interact.on_gsyll_all_clicked(mw.consoleTabWidget)),
                             ('cleanBtn', self._show_clean_dialog),
                             ('automationTopBtn', self.on_automation_top_clicked),
                             ('openFolderBtn', self.on_open_folder_clicked),
                             ('courseDetailBtn', self.on_course_detail_clicked)]:
            getattr(mw, btn).clicked.connect(handler)
        sw.backBtn.clicked.connect(lambda: qt_interact.on_back_clicked(self.stacked_widget, mw))
        sw.submitBtn.clicked.connect(lambda: qt_interact.on_submit_clicked(sw.accountInput, sw.passwordInput, sw.keyInput, self.stacked_widget, mw))
        sw.saveApiBtn.clicked.connect(self._save_api_key)
        sw.savePrefBtn.clicked.connect(lambda: self._save_preference(sw.baseUrlInput.text()))
        original_gemini_focus = sw.geminiApiInput.focusInEvent
        def gemini_focus_wrapper(event):
            self._on_gemini_api_focus()
            original_gemini_focus(event)
        sw.geminiApiInput.focusInEvent = gemini_focus_wrapper
        original_claude_focus = sw.claudeApiInput.focusInEvent
        def claude_focus_wrapper(event):
            self._on_claude_api_focus()
            original_claude_focus(event)
        sw.claudeApiInput.focusInEvent = claude_focus_wrapper
        aw.backBtn.clicked.connect(lambda: qt_interact.on_back_clicked(self.stacked_widget, mw))
        aw.getTodoBtn.clicked.connect(lambda: qt_interact.on_get_todo_clicked(aw.consoleTabWidget, self))
        aw.cleanBtn.clicked.connect(lambda: qt_interact.on_clean_clicked(aw.consoleTabWidget))
        cdw.backBtn.clicked.connect(lambda: qt_interact.on_back_clicked(self.stacked_widget, mw))
        cdw.openSyllabusFolderBtn.clicked.connect(self.on_open_syllabus_folder_clicked)
        cdw.openTextbookFolderBtn.clicked.connect(self.on_open_textbook_folder_clicked)
        cdw.deconTextbookBtn.clicked.connect(self.on_decon_textbook_clicked)
        cdw.loadFromDeconBtn.clicked.connect(lambda: qt_interact.on_load_from_decon_clicked(self))
        cdw.learnMaterialBtn.clicked.connect(lambda: qt_interact.on_learn_material_clicked(self))
        cdw.itemList.itemDoubleClicked.connect(self.on_course_detail_item_double_clicked)
        adw = self.auto_detail_window
        adw.backBtn.clicked.connect(lambda: qt_interact.on_back_clicked(self.stacked_widget, mw))
        adw.hwFolderBtn.clicked.connect(self.on_auto_folder_clicked)
        adw.quizFolderBtn.clicked.connect(self.on_auto_folder_clicked)
        adw.hwDebugBtn.clicked.connect(self.on_hw_debug_clicked)
        adw.quizDebugBtn.clicked.connect(self.on_quiz_debug_clicked)
        adw.hwAgainBtn.clicked.connect(self.on_hw_again_clicked)
        adw.quizAgainBtn.clicked.connect(self.on_quiz_again_clicked)
        adw.hwUploadPreviewBtn.clicked.connect(self.on_hw_preview_clicked)
        adw.quizStartPreviewBtn.clicked.connect(self.on_quiz_preview_clicked)
        adw.hwSubmitBtn.clicked.connect(self.on_hw_submit_clicked)
        adw.quizSubmitBtn.clicked.connect(self.on_quiz_submit_clicked)
        adw.viewDetailBtn.clicked.connect(self.on_view_detail_clicked)
        adw.productComboBox.addItems(['Gemini', 'Claude'])
        adw.productComboBox.currentTextChanged.connect(self.on_product_changed)
        adw.modelComboBox.currentTextChanged.connect(self.on_model_changed)
        self._init_model_selection()
        self.thinking_toggle = IOSToggle(width=50, height=24)
        self.thinking_toggle.setChecked(True)  # Default: thinking mode ON
        placeholder = adw.thinkingTogglePlaceholder; layout = placeholder.parent().layout()
        idx = layout.indexOf(placeholder)
        layout.removeWidget(placeholder)
        placeholder.deleteLater()
        layout.insertWidget(idx, self.thinking_toggle)
        self._load_current_login_info()
        self._load_api_settings()
        for toggle in [self.ios_toggle_main, self.ios_toggle_course_detail] + self.ios_toggles_auto:
            toggle.stateChanged.connect(self.on_toggle_console_clicked)
        self.history_toggle.stateChanged.connect(self.on_history_toggle_clicked)
        mw.consoleTabWidget.tabCloseRequested.connect(self.close_tab)
        aw.consoleTabWidget.tabCloseRequested.connect(self.close_automation_tab)
        for w in [mw.consoleTabWidget, aw.consoleTabWidget]:
            w.setVisible(False)
        for t in [self.ios_toggle_main, self.ios_toggle_course_detail] + self.ios_toggles_auto:
            t.setChecked(False)
    def check_status(self):
        mt = self.main_window.consoleTabWidget.widget(0)
        console = mt.findChild(self.main_window.consoleOutput.__class__) if mt else None
        if os.path.exists(config.COOKIES_FILE) and datetime.now() - datetime.fromtimestamp(os.path.getmtime(config.COOKIES_FILE)) > timedelta(hours=24):
            if console: console.append("[INFO] Cookies expired, auto-refreshing...")
            qt_interact.on_get_cookie_clicked(self.main_window.consoleTabWidget)
        self.update_status()
        self.update_user_info()
        status = checkStatus.get_all_status()
        if status['cookie'] == 1:
            if console: console.append("[INFO] Cookie valid, checking data...")
            if status['courses'] == 0:
                if console: console.append("[INFO] Fetching courses...")
                qt_interact.on_get_course_clicked(self.main_window.consoleTabWidget, self)
            # Always fetch TODOs on startup (both upcoming and historical)
            if console: console.append("[INFO] Auto-fetching todos...")
            qt_interact.on_get_todo_clicked(self.main_window.consoleTabWidget, self)
    def show_toast(self, message, msg_type='success', duration=3000):
        """显示Toast通知 (线程安全 - 从右上角滑入→停留→滑出)"""
        self.toast_signal.show.emit(message, msg_type, duration)
    def _show_toast_slot(self, message, msg_type, duration):
        """Slot: 在主线程中创建Toast"""
        toast_notification.show_toast(self, message, msg_type, duration)
    def update_status(self):
        qt_interact.update_status_indicators(self.status_widgets, checkStatus)
    def update_user_info(self):
        qt_interact.update_user_info_labels(self.main_window.emailLabel, self.main_window.nameLabel, self.main_window.idLabel)
    def init_data_viewer(self):
        mw = self.main_window
        mw.categoryList.addItems(["Courses", "TODOs", "Files"])
        mw.categoryList.currentRowChanged.connect(self.on_category_changed)
        mw.itemList.currentRowChanged.connect(self.on_item_changed)
        mw.itemList.itemChanged.connect(self.on_main_checkbox_changed)
        mw.itemList.itemDoubleClicked.connect(self.on_main_item_double_clicked)
        for f in [mw.filterHomework, mw.filterQuiz, mw.filterDiscussion, mw.filterAutomatable]:
            f.stateChanged.connect(self.apply_filters)
        mw.courseDetailBtn.setVisible(False)
        self.dm.load_all()
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'func'))
            from history_manager import archive_past_todos
            archive_past_todos()
        except: pass
        self._show_launcher()
    def load_data(self):
        self.dm.load_all()
        self.done_mgr.load()
    def on_category_changed(self, index):
        il = self.main_window.itemList
        il.clear()
        self.main_window.courseDetailBtn.setVisible(index == 0)
        if index == 0:
            for c in self.dm.get('courses'): il.addItem(c.get('name', 'Unknown'))
            il.setItemDelegate(QStyledItemDelegate())
        elif index == 1:
            if self.history_mode:
                try:
                    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'func'))
                    from history_manager import load_history
                    todos = load_history()
                except:
                    todos = []
            else:
                todos = self.dm.get('todos')
            for todo in todos:
                item = QListWidgetItem(f"{todo.get('course_name', '')} - {todo.get('name', '')}")
                item.setData(Qt.ItemDataRole.UserRole, self.dm.classify_todo(todo))
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                redirect_url = todo.get('redirect_url', ''); is_done = self.done_mgr.is_done(redirect_url)
                item.setCheckState(Qt.CheckState.Checked if is_done else Qt.CheckState.Unchecked)
                item.setForeground(Qt.GlobalColor.gray if is_done else Qt.GlobalColor.white)
                item.setData(Qt.ItemDataRole.UserRole + 1, todo)
                il.addItem(item)
            il.setItemDelegate(delegates.TodoItemDelegate(il, history_mode=self.history_mode))
        elif index == 2:
            il.addItems(self.dm.get('files'))
            il.setItemDelegate(QStyledItemDelegate())
    def apply_filters(self):
        if self.main_window.categoryList.currentRow() != 1: return
        il, mw = self.main_window.itemList, self.main_window
        filters = [mw.filterHomework.isChecked(), mw.filterQuiz.isChecked(), mw.filterDiscussion.isChecked(), mw.filterAutomatable.isChecked()]
        show_all = not any(filters)
        for i in range(il.count()):
            item, m = il.item(i), il.item(i).data(Qt.ItemDataRole.UserRole)
            if m:
                matches = [m.get('is_homework'), m.get('is_quiz'), m.get('is_discussion'), m.get('is_automatable')]
                item.setHidden(not (show_all or any(f and v for f, v in zip(filters, matches))))
    def on_item_changed(self, index):
        if index < 0: return
        ci = self.main_window.categoryList.currentRow()
        if ci == 1 and self.history_mode:
            try:
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'func'))
                from history_manager import load_history
                data = load_history()
            except:
                data = []
        else:
            data = self.dm.get(['courses', 'todos', 'files'][ci])
        if index < len(data):
            self.main_window.detailView.setHtml([formatters.format_course, formatters.format_todo, formatters.format_folder][ci](data[index]))
    def _update_checkbox(self, item, is_checked):
        todo = item.data(Qt.ItemDataRole.UserRole + 1 if hasattr(item.data(Qt.ItemDataRole.UserRole + 1), 'get') else Qt.ItemDataRole.UserRole)
        if not todo or not todo.get('redirect_url'): return
        (self.done_mgr.mark_done if is_checked else self.done_mgr.mark_undone)(todo['redirect_url'])
        item.setForeground(Qt.GlobalColor.gray if is_checked else Qt.GlobalColor.white)
    def on_main_checkbox_changed(self, item):
        self._update_checkbox(item, item.checkState() == Qt.CheckState.Checked)
    def on_main_item_double_clicked(self, item):
        ci = self.main_window.categoryList.currentRow()
        if ci == 0:
            ii = self.main_window.itemList.currentRow()
            if ii >= 0:
                courses = self.dm.get('courses')
                if ii < len(courses):
                    self.course_detail_mgr = CourseDetailManager(courses[ii], self.dm.get('todos'), self.dm.get('history_todos'))
                    self.populate_course_detail_window()
                    self.stacked_widget.setCurrentWidget(self.course_detail_window)
        elif ci == 1:
            todo = item.data(Qt.ItemDataRole.UserRole + 1)
            if todo:
                meta = self.dm.classify_todo(todo)
                if meta.get('is_automatable'):
                    self.auto_detail_mgr = AutoDetailManager(todo)
                    self.populate_auto_detail_window()
                    self.stacked_widget.setCurrentWidget(self.auto_detail_window)
    def on_toggle_console_clicked(self, state):
        visible = (state == Qt.CheckState.Checked.value)
        self.main_window.consoleTabWidget.setVisible(visible)
        self.automation_window.consoleTabWidget.setVisible(visible)
        for toggle in [self.ios_toggle_main, self.ios_toggle_course_detail] + self.ios_toggles_auto:
            toggle.blockSignals(True)
            toggle.setChecked(visible)
            toggle.blockSignals(False)
    def on_history_toggle_clicked(self, state):
        self.history_mode = (state == Qt.CheckState.Checked.value)
        if self.main_window.categoryList.currentRow() == 1:
            self.on_category_changed(1)
    def on_open_folder_clicked(self):
        ci, ii = self.main_window.categoryList.currentRow(), self.main_window.itemList.currentRow()
        if ci < 0 or ii < 0: return
        fp = None
        if ci == 1 and ii < len(self.dm.get('todos')):
            fn = self.dm.get('todos')[ii].get('assignment_details', {}).get('folder'); fp = os.path.join(config.TODO_DIR, fn) if fn else None
        elif ci == 2 and ii < len(self.dm.get('files')):
            fp = os.path.join(config.TODO_DIR, self.dm.get('files')[ii])
        if fp and os.path.exists(fp):
            self._open_folder(fp)
    def on_automation_clicked(self):
        ci, ii = self.main_window.categoryList.currentRow(), self.main_window.itemList.currentRow()
        if ci != 1: return QMessageBox.warning(self, "Invalid", "Select a TODO first.")
        if ii < 0: return QMessageBox.warning(self, "No Selection", "Select a TODO first.")
        if not (self.main_window.itemList.item(ii).data(Qt.ItemDataRole.UserRole) or {}).get('is_automatable'):
            return QMessageBox.warning(self, "Not Automatable", "Only online submission types can be automated.")
        todos = self.dm.get('todos')
        if ii < len(todos):
            self.populate_automation_window(selected_todo=todos[ii])
            self.stacked_widget.setCurrentWidget(self.automation_window)
    def on_automation_top_clicked(self):
        self.populate_automation_window()
        self.stacked_widget.setCurrentWidget(self.automation_window)
    def populate_automation_window(self, selected_todo=None):
        aw = self.automation_window
        lists = [[aw.automatableOpenCategoryList, aw.automatableOpenItemList, aw.automatableOpenDetailView],
                 [aw.automatableCloseCategoryList, aw.automatableCloseItemList, aw.automatableCloseDetailView],
                 [aw.automatableCategoryList, aw.automatableItemList, aw.automatableDetailView],
                 [aw.allItemsCategoryList, aw.allItemsItemList, aw.allItemsDetailView]]
        for lst_group in lists:
            for lst in lst_group: lst.clear()
            lst_group[0].addItems(["Homework", "Quiz", "Discussion", "All"])
            try:
                for lst in lst_group[:2]:
                    lst.currentRowChanged.disconnect()
                    lst.itemChanged.disconnect()
            except: pass
        for idx, lst_group in enumerate(lists):
            lst_group[0].currentRowChanged.connect(lambda i, t=idx: self.on_automation_category_changed(i, t))
            lst_group[1].currentRowChanged.connect(lambda i, t=idx: self.on_automation_item_changed(i, t))
            lst_group[1].itemChanged.connect(self.on_automation_checkbox_changed)
            lst_group[1].itemDoubleClicked.connect(self.on_automation_item_double_clicked)
        if selected_todo:
            url = selected_todo.get('redirect_url', '').lower(); ci = 1 if 'quiz' in url else 2 if 'discussion' in url else 0
            aw.mainTabWidget.setCurrentIndex(0)
            lists[0][0].setCurrentRow(ci)
            for i in range(lists[0][1].count()):
                if lists[0][1].item(i).data(Qt.ItemDataRole.UserRole).get('redirect_url') == selected_todo.get('redirect_url'):
                    lists[0][1].setCurrentRow(i)
                    break
        else:
            lists[0][0].setCurrentRow(0)
    def on_automation_category_changed(self, index, tab_index=3):
        if index < 0: return
        aw = self.automation_window
        il = [aw.automatableOpenItemList, aw.automatableCloseItemList, aw.automatableItemList, aw.allItemsItemList][tab_index]
        il.clear()
        for todo in self.dm.get('todos'):
            meta = self.dm.classify_todo(todo)
            if tab_index == 0 and not (meta['is_automatable'] and meta['is_open']): continue
            if tab_index == 1 and not (meta['is_automatable'] and not meta['is_open']): continue
            if tab_index == 2 and not meta['is_automatable']: continue
            if index != 3 and not [meta['is_homework'], meta['is_quiz'], meta['is_discussion']][index]: continue
            item = QListWidgetItem(f"{todo.get('course_name', '')} - {todo.get('name', '')}")
            item.setData(Qt.ItemDataRole.UserRole, todo)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            redirect_url = todo.get('redirect_url', ''); is_done = self.done_mgr.is_done(redirect_url)
            item.setCheckState(Qt.CheckState.Checked if is_done else Qt.CheckState.Unchecked)
            item.setForeground(Qt.GlobalColor.gray if is_done else Qt.GlobalColor.white)
            il.addItem(item)
    def on_automation_item_changed(self, index, tab_index=3):
        if index < 0: return
        aw = self.automation_window
        il = [aw.automatableOpenItemList, aw.automatableCloseItemList, aw.automatableItemList, aw.allItemsItemList][tab_index]
        dv = [aw.automatableOpenDetailView, aw.automatableCloseDetailView, aw.automatableDetailView, aw.allItemsDetailView][tab_index]
        todo = il.item(index).data(Qt.ItemDataRole.UserRole)
        if todo: dv.setHtml(formatters.format_todo(todo))
    def on_automation_checkbox_changed(self, item):
        self._update_checkbox(item, item.checkState() == Qt.CheckState.Checked)
    def on_automation_item_double_clicked(self, item):
        """Handle double-click on automation window TODO item -> jump to autoDetail"""
        todo = item.data(Qt.ItemDataRole.UserRole)
        if todo:
            self.auto_detail_mgr = AutoDetailManager(todo)
            self.populate_auto_detail_window()
            self.stacked_widget.setCurrentWidget(self.auto_detail_window)
    def on_course_detail_clicked(self):
        ci, ii = self.main_window.categoryList.currentRow(), self.main_window.itemList.currentRow()
        if ci != 0: return QMessageBox.warning(self, "Invalid", "Please select a Course first.")
        if ii < 0: return QMessageBox.warning(self, "No Selection", "Please select a course first.")
        courses = self.dm.get('courses')
        if ii >= len(courses): return QMessageBox.warning(self, "Error", "Invalid course selection.")
        self.course_detail_mgr = CourseDetailManager(courses[ii], self.dm.get('todos'), self.dm.get('history_todos'))
        self.populate_course_detail_window()
        self.stacked_widget.setCurrentWidget(self.course_detail_window)
    def _course_item_drag_enter(self, event):
        """Handle drag enter event for course detail itemList"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    def _course_item_drag_move(self, event):
        """Handle drag move event for course detail itemList"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    def _course_item_drop(self, event):
        """Handle drop event for course detail itemList (for Textbook and Learn categories)"""
        if not self.course_detail_mgr:
            return

        # Check if current category is Textbook or Learn
        current_category = self.course_detail_window.categoryList.currentItem()
        if not current_category:
            return

        category_text = current_category.text()

        if category_text not in ['Textbook', 'Learn']:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self.course_detail_window, "Invalid Drop",
                              "Files can only be dropped in the Textbook or Learn category.")
            return

        if event.mimeData().hasUrls():
            import shutil

            # Get target directory based on category
            if category_text == 'Textbook':
                target_dir = self.course_detail_mgr.get_textbook_dir()
            else:  # Learn
                target_dir = self.course_detail_mgr.get_learn_dir()

            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if os.path.isfile(file_path):
                    filename = os.path.basename(file_path)
                    dest_path = os.path.join(target_dir, filename)
                    try:
                        shutil.copy2(file_path, dest_path)
                        print(f"[DRAG-DROP] Copied: {filename} → {target_dir}")
                    except Exception as e:
                        print(f"[DRAG-DROP] Error copying {filename}: {e}")

            # Refresh the category view
            event.acceptProposedAction()
            self.on_course_detail_category_changed(self.course_detail_window.categoryList.currentRow())
    def populate_course_detail_window(self):
        if not self.course_detail_mgr: return
        cdw = self.course_detail_window
        try:
            cdw.categoryList.currentRowChanged.disconnect()
            cdw.itemList.currentRowChanged.disconnect()
        except: pass
        cdw.courseNameLabel.setText(self.course_detail_mgr.get_course_name())
        for w in [cdw.categoryList, cdw.itemList, cdw.detailView]: w.clear()
        categories = self.course_detail_mgr.get_categories()
        cdw.categoryList.addItems(categories)
        cdw.categoryList.currentRowChanged.connect(self.on_course_detail_category_changed)
        cdw.itemList.currentRowChanged.connect(self.on_course_detail_item_changed)
        self._prefetch_all_tabs()
        if categories:
            cdw.categoryList.setCurrentRow(0)
            cdw.categoryList.setFocus()  # Default focus for full keyboard navigation
    def populate_auto_detail_window(self):
        """Populate autoDetail window with TODO data"""
        if not self.auto_detail_mgr: return
        adw = self.auto_detail_window
        info = self.auto_detail_mgr.get_identification_info()
        adw.courseNameLabel.setText(f"Course: {info['course']}")
        adw.assignmentNameLabel.setText(f"Assignment: {info['assignment']}")
        adw.typeLabel.setText(f"Type: {info['type']}")
        adw.dueDateLabel.setText(f"Due: {info['due_date']}")
        adw.assignmentDetailView.setHtml(self.auto_detail_mgr.get_assignment_detail_html())
        adw.refFilesView.setHtml(self.auto_detail_mgr.get_reference_files_html())
        is_quiz = self.auto_detail_mgr.is_quiz; is_homework = self.auto_detail_mgr.is_homework
        adw.quizControlWidget.setVisible(is_quiz)
        adw.hwControlWidget.setVisible(is_homework)
        adw.consoleTitle.setText(f"{info['type']} Automation Console")
        preview_html = self._load_auto_detail_preview()
        adw.aiPreviewView.setHtml(preview_html if preview_html else self.auto_detail_mgr.get_preview_placeholder_html())
        adw.previewStatusLabel.setText("Status: Preview loaded" if preview_html else "Status: No preview generated yet")
        config.ensure_dirs()
        if not self.auto_detail_mgr.todo.get('assignment_details', {}).get('assignment_folder'):
            from func.getTodos import create_assignment_folder, sanitize_folder_name
            assignment_name = self.auto_detail_mgr.todo.get('name', 'Unknown'); due_date = self.auto_detail_mgr.todo.get('due_date')
            assignment_folder = create_assignment_folder(config.TODO_DIR, assignment_name, due_date)
            if 'assignment_details' not in self.auto_detail_mgr.todo:
                self.auto_detail_mgr.todo['assignment_details'] = {}
            self.auto_detail_mgr.todo['assignment_details']['assignment_folder'] = assignment_folder
            try:
                todos_data = json.load(open(os.path.join(config.ROOT_DIR, 'todos.json')))
                for todo in todos_data:
                    if (todo.get('name') == self.auto_detail_mgr.todo.get('name') and
                        todo.get('due_date') == self.auto_detail_mgr.todo.get('due_date')):
                        if 'assignment_details' not in todo:
                            todo['assignment_details'] = {}; todo['assignment_details']['assignment_folder'] = assignment_folder
                        break
                json.dump(todos_data, open(os.path.join(config.ROOT_DIR, 'todos.json'), 'w'), indent=2)
            except Exception as e:
                print(f"Warning: Failed to save assignment_folder to todos.json: {e}")
        prompt_type = 'quiz' if is_quiz else 'homework'
        adw.promptEditBox.setPlainText(config.DEFAULT_PROMPTS.get(prompt_type, ''))
    def _load_auto_detail_preview(self):
        """Load AI preview (quiz or homework) if files exist"""
        if not self.auto_detail_mgr: return None
        assignment_folder = self.auto_detail_mgr.todo.get('assignment_details', {}).get('assignment_folder')
        if not assignment_folder: return None
        output_dir = os.path.join(assignment_folder, 'auto', 'output')
        if not os.path.exists(output_dir): return None
        if self.auto_detail_mgr.is_quiz:
            return self.auto_detail_mgr.load_quiz_preview(output_dir)
        elif self.auto_detail_mgr.is_homework:
            return self.auto_detail_mgr.load_homework_preview(output_dir)
        return None
    def _update_auto_detail_status(self, status_text):
        """Slot function to update AutoDetail status label from background thread"""
        if self.auto_detail_window:
            self.auto_detail_window.previewStatusLabel.setText(status_text)
    def on_course_detail_category_changed(self, index):
        if index < 0 or not self.course_detail_mgr: return
        cdw = self.course_detail_window
        cdw.itemList.clear()
        cdw.detailView.clear()
        category = cdw.categoryList.item(index).text()
        cdw.openTextbookFolderBtn.setVisible(category == 'Textbook')
        cdw.deconTextbookBtn.setVisible(category == 'Textbook')
        cdw.loadFromDeconBtn.setVisible(category == 'Learn')
        cdw.learnMaterialBtn.setVisible(category == 'Learn')
        items = self.course_detail_mgr.get_items_for_category(category)
        for item_data in items:
            item = QListWidgetItem(item_data['name'])
            item.setData(Qt.ItemDataRole.UserRole, item_data.get('has_file', False))
            item.setData(Qt.ItemDataRole.UserRole + 1, item_data)
            if item_data.get('is_done', False): item.setForeground(Qt.GlobalColor.gray)
            cdw.itemList.addItem(item)
        cdw.itemList.setItemDelegate(delegates.FileItemDelegate(cdw.itemList) if category in ['Syllabus', 'Textbook', 'Learn'] else QStyledItemDelegate())
        cdw.itemList.viewport().update()
    def on_course_detail_item_changed(self, index):
        if index < 0 or not self.course_detail_mgr: return
        cdw = self.course_detail_window; item_data = cdw.itemList.item(index).data(Qt.ItemDataRole.UserRole + 1)
        if not item_data: return
        item_type, data = item_data.get('type'), item_data.get('data')
        if item_type == 'tab':
            tab_name, url = data.get('tab_name'), data.get('url')
            if tab_name and url:
                self._load_or_fetch_tab(tab_name, url)
            return
        html_map = {
            'intro': lambda: formatters.format_course(data),
            'todo': lambda: formatters.format_todo(data),
            'syllabus': lambda: f"<h2 style='color: #22c55e;'>Syllabus</h2><p><a href='{data['url']}'>{data['url']}</a></p><p>Folder: {data['local_dir']}</p>",
            'textbook_file': lambda: f"<h2>{data['filename']}</h2><p>{data['path']}</p>",
            'learn_file': lambda: f"<h2 style='color: #3b82f6;'>📚 {data['filename']}</h2><p><strong>Path:</strong> {data['path']}</p>" +
                                 (f"<p><strong>Report:</strong> <a href='file://{data['report_path']}'>{os.path.basename(data['report_path'])}</a> ✅</p>" if data.get('report_path') else
                                  "<p><strong>Report:</strong> Not generated yet. Click 'Learn This Material' to generate.</p>"),
            'placeholder': lambda: f"<p>No files</p><p>Folder: {data['folder']}</p>"
        }
        cdw.detailView.setHtml(html_map.get(item_type, lambda: "<p>No details</p>")())
    def on_open_syllabus_folder_clicked(self):
        if not self.course_detail_mgr: return
        self._open_folder(self.course_detail_mgr.get_syll_dir())
    def on_open_textbook_folder_clicked(self):
        if not self.course_detail_mgr: return
        self._open_folder(self.course_detail_mgr.get_textbook_dir())
    def on_decon_textbook_clicked(self):
        """Decon textbook PDFs using LLM - analyze chapters and split PDF"""
        if not self.course_detail_mgr:
            return QMessageBox.warning(self.course_detail_window, "Error", "No course selected.")

        textbook_dir = self.course_detail_mgr.get_textbook_dir()
        if not os.path.exists(textbook_dir):
            return QMessageBox.warning(self.course_detail_window, "Error", "Textbook folder does not exist.")

        # Get all PDF files
        pdf_files = [f for f in os.listdir(textbook_dir) if f.lower().endswith('.pdf')]
        if not pdf_files:
            return QMessageBox.warning(self.course_detail_window, "Error", "No PDF files found in Textbook folder.")

        # Show file selection dialog
        from PyQt6.QtWidgets import QInputDialog
        selected_file, ok = QInputDialog.getItem(
            self.course_detail_window,
            "Select Textbook",
            "Choose a PDF to decon:",
            pdf_files,
            0,
            False
        )
        if not ok or not selected_file:
            return

        # Confirm action
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self.course_detail_window,
            "Decon Textbook",
            f"This will:\n"
            f"1. Analyze chapter structure using Gemini AI\n"
            f"2. Split PDF into individual chapter files\n"
            f"3. Save to: {textbook_dir}/decon/\n\n"
            f"Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Run decon in background thread
        file_path = os.path.join(textbook_dir, selected_file)

        def run_decon(console, progress):
            try:
                progress.update_progress(1, 7, "Step 1/7: Selecting model...")

                sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'func'))
                from upPromptFiles import upload_files, call_ai
                from model_selector import get_best_gemini_model, get_model_display_name
                from pdf_splitter import split_pdf_by_chapters
                from pdf_bookmark_extractor import extract_chapters_from_bookmarks, format_bookmark_chapters, repair_pdf_references
                from PyPDF2 import PdfReader, PdfWriter
                import json
                import tempfile

                # Step 1: Select best Gemini model
                try:
                    best_model = get_best_gemini_model()
                    model_name = get_model_display_name(best_model)
                    console.append(f"✓ Model: {model_name}")
                except Exception as e:
                    model_name = 'gemini-2.0-flash-exp'
                    console.append(f"! Fallback model: {model_name}")

                # Step 2: Load PDF and try bookmark extraction first
                progress.update_progress(2, 7, "Step 2/7: Loading PDF...")
                reader = PdfReader(file_path)
                total_pages = len(reader.pages)
                console.append(f"✓ PDF has {total_pages} pages")

                # Track repaired PDF path for cleanup
                repaired_pdf_path = None

                # PRIORITY: Try bookmark extraction first
                console.append("\n📖 Checking for embedded bookmarks...")
                all_chapters = extract_chapters_from_bookmarks(file_path, total_pages)

                if all_chapters:
                    # SUCCESS: Found valid continuous chapters from bookmarks
                    console.append("✓ Found valid chapter bookmarks (continuous from Chapter 1)")
                    console.append(format_bookmark_chapters(all_chapters))
                    console.append("\n⚡ Skipping AI analysis - using bookmark data")

                    # CRITICAL: Repair PDF references before splitting
                    # This prevents thousands of "Object ID X,0 ref repaired" warnings
                    console.append("")
                    repaired_pdf_path = repair_pdf_references(file_path, console)

                    # Update reader to use repaired PDF for splitting
                    if repaired_pdf_path and repaired_pdf_path != file_path:
                        reader = PdfReader(repaired_pdf_path)
                        # Use repaired PDF for splitting
                        pdf_to_split = repaired_pdf_path
                    else:
                        pdf_to_split = file_path

                    # Convert to expected format
                    all_chapters = [
                        {
                            'chapter': ch['chapter_number'],
                            'name': ch['chapter_name'],
                            'start_page': ch['start_page'],
                            'end_page': ch['end_page']
                        }
                        for ch in all_chapters
                    ]

                else:
                    # FALLBACK: No bookmarks found, use AI analysis
                    console.append("! No valid bookmarks found - falling back to AI analysis")
                    pdf_to_split = file_path  # Use original PDF for AI path

                    # Extract first 200 pages for TOC + chapter 1 analysis
                    TOC_PAGES = min(200, total_pages)
                    writer = PdfWriter()
                    for i in range(TOC_PAGES):
                        writer.add_page(reader.pages[i])

                    temp_toc_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='_toc.pdf')
                    writer.write(temp_toc_pdf)
                    temp_toc_pdf.close()
                    console.append(f"✓ Extracted first {TOC_PAGES} pages")

                    # Step 3: Analyze TOC and calculate delta
                    progress.update_progress(3, 7, "Step 3/7: Analyzing TOC...")
                    uploaded_info = upload_files([temp_toc_pdf.name], 'Gemini')

                    toc_prompt = """Analyze this textbook PDF (first 200 pages) and extract the Table of Contents.

Your task has TWO CRITICAL STEPS:

STEP 1: Read the Table of Contents
- Find all chapter entries with page numbers
- Record what page number the TOC says each chapter starts on

STEP 2: Find the ACTUAL start of Chapter 1
- Scroll through the PDF to find where Chapter 1 ACTUALLY begins
- Look for the actual chapter title page (e.g., "Chapter 1: Introduction")
- Note which PDF page number this is (count from the start of THIS file)
- This is critical because the book may have covers, prefaces, etc. before Chapter 1

STEP 3: Calculate delta
- delta = (book_page_of_chapter_1 - pdf_page_where_chapter_1_actually_starts)
- Example: If TOC says "Chapter 1, Page 1" but Chapter 1 title appears on PDF page 17:
  delta = 1 - 17 = -16

Return ONLY a valid JSON object:
{
  "delta": -16,
  "chapter_1_pdf_page": 17,
  "chapter_1_book_page": 1,
  "chapters": [
    {"chapter": 1, "name": "Introduction", "book_page": 1},
    {"chapter": 2, "name": "Cell Biology", "book_page": 25}
  ]
}

CRITICAL RULES:
1. "delta" MUST be calculated from the ACTUAL Chapter 1 title page, NOT just the TOC entry
2. "chapter_1_pdf_page": The PDF page number where Chapter 1 ACTUALLY starts (for verification)
3. "chapter_1_book_page": What page number the TOC says Chapter 1 starts on (usually 1)
4. "chapters": ONLY include chapters with actual page numbers. Skip "online", "web", or numberless entries
5. Return ONLY the JSON object, no markdown, no explanations"""

                    result = call_ai(toc_prompt, 'Gemini', model_name, uploaded_info=uploaded_info)
                    os.unlink(temp_toc_pdf.name)

                    # Step 4: Parse TOC
                    progress.update_progress(4, 7, "Step 4/7: Parsing TOC...")
                    result_clean = result.strip()
                    if result_clean.startswith('```'):
                        lines = result_clean.split('\n')
                        result_clean = '\n'.join(lines[1:-1]) if len(lines) > 2 else result_clean

                    try:
                        toc_data = json.loads(result_clean)
                    except json.JSONDecodeError as e:
                        console.append(f"[ERROR] JSON parse failed: {e}")
                        console.append(f"Raw: {result_clean[:300]}...")
                        raise

                    delta = toc_data.get('delta', 0)
                    toc_chapters = toc_data.get('chapters', [])

                    # Verify delta calculation (new fields for validation)
                    ch1_pdf = toc_data.get('chapter_1_pdf_page')
                    ch1_book = toc_data.get('chapter_1_book_page')

                    if ch1_pdf and ch1_book:
                        expected_delta = ch1_book - ch1_pdf
                        if expected_delta != delta:
                            console.append(f"! Delta verification failed:")
                            console.append(f"  AI reported delta={delta}")
                            console.append(f"  But Chapter 1: book_page={ch1_book}, pdf_page={ch1_pdf}")
                            console.append(f"  Expected delta={expected_delta}")
                            console.append(f"  → Auto-correcting to delta={expected_delta}")
                            delta = expected_delta
                        else:
                            console.append(f"✓ Delta verified: {delta} (Ch1: book_p{ch1_book} = pdf_p{ch1_pdf})")
                        console.append(f"✓ Found {len(toc_chapters)} chapters from TOC")
                    else:
                        # Fallback: Try to verify by checking first chapter's calculated position
                        console.append(f"✓ Found {len(toc_chapters)} chapters from TOC, delta={delta}")
                        if toc_chapters:
                            first_ch = toc_chapters[0]
                            if first_ch.get('chapter') == 1:
                                predicted_pdf_page = first_ch.get('book_page', 1) - delta
                                console.append(f"  → Predicted Chapter 1 at PDF page {predicted_pdf_page}")
                                console.append(f"  ! Please verify this is correct (check if off by ~16-17 pages)")

                    # Step 5: Convert book pages to PDF pages
                    progress.update_progress(5, 7, "Step 5/7: Converting to PDF pages...")
                    all_chapters = []
                    last_toc_book_page = 0

                    for ch in toc_chapters:
                        book_page = ch.get('book_page', 0)
                        pdf_start = book_page - delta
                        last_toc_book_page = max(last_toc_book_page, book_page)

                        all_chapters.append({
                            'chapter': ch.get('chapter'),
                            'name': ch.get('name'),
                            'start_page': pdf_start,
                            'end_page': None  # Will be filled later
                        })

                    # Calculate where to start scanning (after last TOC chapter)
                    # Estimate: last chapter likely ~50 pages, so start from last_book_page + 50
                    scan_start_book_page = last_toc_book_page + 50
                    scan_start_pdf_page = scan_start_book_page - delta

                    console.append(f"✓ Converted {len(all_chapters)} chapters")
                    console.append(f"  Last TOC book page: {last_toc_book_page} → PDF page {last_toc_book_page - delta}")

                    # Step 5.5: Scan remaining pages if < 500 pages left
                    remaining_pages = total_pages - scan_start_pdf_page
                    if remaining_pages > 0 and remaining_pages < 500:
                        console.append(f"\n! Scanning {remaining_pages} remaining pages (from PDF page {scan_start_pdf_page})...")
                        progress.update_progress(5, 7, f"Step 5/7: Scanning {remaining_pages} remaining pages...")

                        # Extract remaining pages
                        writer = PdfWriter()
                        for i in range(scan_start_pdf_page - 1, total_pages):  # -1 for 0-based indexing
                            writer.add_page(reader.pages[i])

                        temp_tail_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='_tail.pdf')
                        writer.write(temp_tail_pdf)
                        temp_tail_pdf.close()

                        # Analyze remaining section
                        tail_uploaded = upload_files([temp_tail_pdf.name], 'Gemini')
                        tail_prompt = f"""Analyze this PDF section (pages {scan_start_pdf_page}-{total_pages} of the full textbook).
Identify all formal chapters that START in this section, and find where each chapter ENDS.

Return ONLY a valid JSON array:
[
  {{"chapter": 16, "name": "First-Order Differential Equations", "start_page": 1, "end_page": 34}},
  {{"chapter": 17, "name": "Second-Order Differential Equations", "start_page": 35, "end_page": 60}}
]

IMPORTANT:
- start_page and end_page are relative to THIS section (1 = first page = PDF page {scan_start_pdf_page})
- end_page should be the LAST page of the chapter (before practice exercises, or next chapter, or appendix)
- ONLY include formal numbered chapters with format "Chapter NN: Title"
- DO NOT include: Appendices (Appendix A/B/C), Index, Answers, Table of Contents, or any unnumbered sections
- Return ONLY the JSON array"""

                        tail_result = call_ai(tail_prompt, 'Gemini', model_name, uploaded_info=tail_uploaded)
                        os.unlink(temp_tail_pdf.name)

                        # Parse tail chapters
                        tail_clean = tail_result.strip()
                        if tail_clean.startswith('```'):
                            lines = tail_clean.split('\n')
                            tail_clean = '\n'.join(lines[1:-1]) if len(lines) > 2 else tail_clean

                        try:
                            tail_chapters = json.loads(tail_clean)
                            if isinstance(tail_chapters, list):
                                for ch in tail_chapters:
                                    relative_start = ch.get('start_page', 1)
                                    relative_end = ch.get('end_page')

                                    pdf_start = scan_start_pdf_page + relative_start - 1
                                    pdf_end = scan_start_pdf_page + relative_end - 1 if relative_end else None

                                    all_chapters.append({
                                        'chapter': ch.get('chapter'),
                                        'name': ch.get('name'),
                                        'start_page': pdf_start,
                                        'end_page': pdf_end
                                    })
                                console.append(f"  ✓ Found {len(tail_chapters)} additional chapters")
                        except:
                            console.append(f"  ! Failed to parse tail chapters, skipping")

                    # Deduplicate by chapter number (keep first occurrence)
                    seen_chapters = set()
                    unique_chapters = []
                    for ch in all_chapters:
                        ch_num = ch.get('chapter')
                        if ch_num not in seen_chapters:
                            seen_chapters.add(ch_num)
                            unique_chapters.append(ch)
                    all_chapters = unique_chapters

                    # Sort and fill end_page
                    all_chapters.sort(key=lambda x: x['start_page'])
                    for i in range(len(all_chapters)):
                        if all_chapters[i]['end_page'] is None:
                            if i < len(all_chapters) - 1:
                                all_chapters[i]['end_page'] = all_chapters[i + 1]['start_page'] - 1
                            else:
                                all_chapters[i]['end_page'] = total_pages

                    console.append(f"✓ Total: {len(all_chapters)} chapters")

                # Step 6: Validate and fix boundaries
                progress.update_progress(6, 7, "Step 6/7: Validating boundaries...")
                for i in range(len(all_chapters) - 1):
                    current = all_chapters[i]
                    next_ch = all_chapters[i + 1]
                    if current.get('end_page', 0) >= next_ch.get('start_page', 0):
                        current['end_page'] = next_ch['start_page'] - 1
                console.append(f"✓ Validated {len(all_chapters)} chapters")

                # Step 7: Save and split
                progress.update_progress(7, 7, f"Step 7/7: Splitting into {len(all_chapters)} PDFs...")
                decon_dir = os.path.join(textbook_dir, 'decon')
                os.makedirs(decon_dir, exist_ok=True)

                metadata_file = os.path.join(decon_dir, f"{os.path.splitext(selected_file)[0]}_chapters.json")
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(all_chapters, f, indent=2, ensure_ascii=False)

                # Use repaired PDF if available (bookmark path), otherwise original (AI path)
                created_files = split_pdf_by_chapters(pdf_to_split, all_chapters, decon_dir)

                progress.update_progress(7, 7, f"✓ Complete: {len(created_files)} chapters")
                console.append(f"\n✓ Decon complete: {len(created_files)} chapter PDFs")
                console.append(f"  Output: {decon_dir}")

                # Cleanup: Remove temporary repaired PDF
                if repaired_pdf_path and repaired_pdf_path != file_path and os.path.exists(repaired_pdf_path):
                    try:
                        os.unlink(repaired_pdf_path)
                        console.append("✓ Cleaned up temporary repaired PDF")
                    except:
                        pass  # Ignore cleanup errors

            except Exception as e:
                import traceback
                progress.set_text_only(f"✗ Failed: {str(e)[:50]}")
                console.append(f"\n[ERROR] {e}")
                console.append(traceback.format_exc())

                # Cleanup on error too
                if 'repaired_pdf_path' in locals() and repaired_pdf_path and repaired_pdf_path != file_path:
                    try:
                        os.unlink(repaired_pdf_path)
                    except:
                        pass

        from gui import qt_interact
        console, progress = qt_interact._create_console_tab(self.main_window.consoleTabWidget, f"Decon: {selected_file}", with_progress=True)

        def run_with_progress(c):
            run_decon(c, progress)

        qt_interact._run_in_thread(run_with_progress, console, "Decon Textbook")
    def on_course_detail_item_double_clicked(self, item):
        if not self.course_detail_mgr: return
        item_data = item.data(Qt.ItemDataRole.UserRole + 1)
        if not item_data: return
        item_type, data = item_data.get('type'), item_data.get('data')
        if item_type == 'syllabus' and item_data.get('has_file'):
            syll_dir = data.get('local_dir')
            if syll_dir and os.path.exists(syll_dir):
                self._open_folder(syll_dir)
        elif item_type == 'textbook_file':
            file_path = data.get('path')
            if file_path and os.path.exists(file_path):
                self._open_folder(os.path.dirname(file_path))
    def _prefetch_all_tabs(self):
        """Prefetch all missing tabs in background"""
        def worker():
            tabs = self.course_detail_mgr.course.get('tabs', {}); tabs_dir = os.path.join(self.course_detail_mgr.course_dir, 'Tabs')
            os.makedirs(tabs_dir, exist_ok=True); s = self._create_session()
            for name, path in tabs.items():
                safe = "".join(c if c.isalnum() or c in (' ','_') else '_' for c in name); md_path = os.path.join(tabs_dir, f"{safe}.md")
                if os.path.exists(md_path): continue
                try:
                    url = f"{config.CANVAS_BASE_URL}{path}"; r = s.get(url, timeout=10)
                    soup = BeautifulSoup(r.text, 'html.parser')
                    md = self._parse_special_page(name, r.text, soup) if 'grades' in name.lower() or self._is_modules_page(r.text, soup) else self._html_to_md(soup)
                    if md:
                        with open(md_path, 'w', encoding='utf-8') as f:
                            f.write(f"# {name}\n\nSource: {url}\n\n---\n\n{md}")
                        print(f"[INFO] Prefetched {name}")
                except: pass
        threading.Thread(target=worker, daemon=True).start()
    def _load_or_fetch_tab(self, tab_name, url):
        safe_tab_name = "".join(c if c.isalnum() or c in (' ', '_') else '_' for c in tab_name)
        md_path = os.path.join(self.course_detail_mgr.course_dir, 'Tabs', f"{safe_tab_name}.md")
        if os.path.exists(md_path):
            try:
                with open(md_path, 'r', encoding='utf-8') as f:
                    self.tab_content_signal.update_html.emit(f"MARKDOWN:{f.read()}")
            except Exception as e:
                self.course_detail_window.detailView.setHtml(f"<h2 style='color: #ef4444;'>Error</h2><p>{e}</p>")
        else:
            self.course_detail_window.detailView.setHtml(f"<h2 style='color: #eab308;'>Loading...</h2><p>Fetching {tab_name}...</p>")
            self._fetch_tab_content(tab_name, url)
    def _update_course_detail_html(self, html):
        if html.startswith("MARKDOWN:"):
            md_content = html[9:]; lines = md_content.split('\n', 1)
            title = lines[0].strip('# '); body = lines[1] if len(lines) > 1 else ''
            html_body = md_lib.markdown(body, extensions=['extra', 'nl2br', 'tables']); styled_html = f"""<style>
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;line-height:1.6;color:#e0e0e0}}
h1{{color:#3b82f6;border-bottom:2px solid #3b82f6;padding-bottom:8px}}
h2{{color:#60a5fa;margin-top:24px}}h3{{color:#93c5fd;margin-top:20px}}
a{{color:#60a5fa;text-decoration:none}}a:hover{{text-decoration:underline}}
table{{border-collapse:collapse;width:100%;margin:16px 0;background-color:#1a1a1a;border-radius:8px;overflow:hidden}}
th{{background-color:#2563eb;color:white;font-weight:600;padding:12px 16px;text-align:left;border-bottom:2px solid #3b82f6}}
td{{padding:10px 16px;border-bottom:1px solid #333}}
tr:hover{{background-color:#262626}}tr:last-child td{{border-bottom:none}}
code{{background-color:#2a2a2a;padding:2px 6px;border-radius:4px;font-family:'Consolas','Monaco',monospace;color:#22c55e}}
pre{{background-color:#1a1a1a;padding:16px;border-radius:8px;overflow-x:auto;border-left:4px solid #3b82f6}}
blockquote{{border-left:4px solid #3b82f6;padding-left:16px;margin:16px 0;color:#9ca3af}}
ul,ol{{padding-left:24px}}li{{margin:4px 0}}
</style><h1>{title}</h1>{html_body}"""
            self.course_detail_window.detailView.setHtml(styled_html)
        else:
            self.course_detail_window.detailView.setHtml(html)
    def _fetch_tab_content(self, tab_name, url):
        def fetch_worker():
            try:
                session = self._create_session()
                print(f"[INFO] Fetching {tab_name} from {url}")
                response = session.get(url, timeout=10)
                response.raise_for_status()
                if response.history:
                    print(f"[INFO] Server redirects detected for {tab_name}")
                if "window.location.href" in response.text:
                    js_redirect = re.search(r"window\.location\.href\s*=\s*['\"]([^'\"]+)['\"]", response.text)
                    if js_redirect:
                        redirect_url = js_redirect.group(1)
                        if redirect_url.startswith('/'): redirect_url = f"https://psu.instructure.com{redirect_url}"
                        print(f"[INFO] Following JS redirect to: {redirect_url}")
                        response = session.get(redirect_url, timeout=10)
                        response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                markdown = self._parse_special_page(tab_name, response.text, soup) if ('grades' in url.lower() or 'Grades' in tab_name or self._is_modules_page(response.text, soup)) else self._html_to_md(soup)
                if markdown:
                    safe_tab_name = "".join(c if c.isalnum() or c in (' ', '_') else '_' for c in tab_name)
                    tabs_dir = os.path.join(self.course_detail_mgr.course_dir, 'Tabs'); os.makedirs(tabs_dir, exist_ok=True)
                    save_path = os.path.join(tabs_dir, f"{safe_tab_name}.md"); full_markdown = f"# {tab_name}\n\nSource: {url}\n\n---\n\n{markdown}"
                    with open(save_path, 'w', encoding='utf-8') as f:
                        f.write(full_markdown)
                    self.tab_content_signal.update_html.emit(f"MARKDOWN:{full_markdown}")
                    print(f"[INFO] Saved {tab_name} to {save_path}")
                else:
                    self.tab_content_signal.update_html.emit(f"<h2 style='color: #ef4444;'>Error</h2><p>No content found for {tab_name}</p>")
            except Exception as e:
                self.tab_content_signal.update_html.emit(f"<h2 style='color: #ef4444;'>Error</h2><p>Failed to fetch {tab_name}: {str(e)}</p>")
                print(f"[ERROR] Failed to fetch {tab_name}: {e}")
        threading.Thread(target=fetch_worker, daemon=True).start()
    def _create_session(self):
        with open(config.COOKIES_FILE) as f:
            cookies = {c['name']: c['value'] for c in json.load(f)}; s = requests.Session()
        s.cookies.update(cookies)
        s.headers['User-Agent'] = 'Mozilla/5.0'
        return s
    def _html_to_md(self, soup):
        content = soup.find('div', id='content') or soup.body
        if not content: return None
        h = html2text.HTML2Text(); h.ignore_links = h.ignore_images = False
        h.body_width = 0
        return h.handle(str(content))
    def _is_modules_page(self, html_text, soup):
        has_modules_keyword = 'modules' in html_text.lower()
        if not has_modules_keyword:
            return False
        has_modules_dom = soup.find('div', id='context_modules') or soup.find('div', class_=lambda x: x and 'context_modules' in x)
        has_modules_env = 'ENV.MODULES_PATH' in html_text or '"modules_path"' in html_text
        has_modules_url = '/courses/' in html_text and '/modules' in html_text and 'context_modules' in html_text
        return bool(has_modules_dom or has_modules_env or has_modules_url)
    def _parse_special_page(self, name, html_text, soup):
        if 'grades' in name.lower():
            return self._parse_grades_page(html_text, soup)
        elif self._is_modules_page(html_text, soup):
            return self._parse_modules_page(html_text, soup)
        return None
    def _parse_grades_page(self, html_text, soup):
        try:
            start = html_text.find('ENV = {')
            if start == -1: return "**Error:** No ENV found"
            bc, pos = 0, html_text.find('{', start)
            for i, c in enumerate(html_text[pos:], pos):
                if c == '{': bc += 1
                elif c == '}':
                    bc -= 1
                    if bc == 0:
                        env = json.loads(html_text[pos:i+1])
                        break
            else: return "**Error:** Incomplete ENV"
            subs = env.get('submissions', [])
            if not subs: return "**No grades**"
            md = ["## Grades\n", "| Assignment | Score | Status |", "|------------|-------|--------|"]
            for s in subs:
                aid = s.get('assignment_id', ''); link = soup.find('a', href=re.compile(f'/assignments/{aid}'))
                name = link.get_text(strip=True) if link else f"Assignment {aid}"; score = s.get('score')
                if s.get('excused'): md.append(f"| {name} | Excused | Excused |")
                elif score: md.append(f"| {name} | {score:.1f} | ✅ Graded |")
                else: md.append(f"| {name} | - | ⏳ Not submitted |")
            return '\n'.join(md)
        except Exception as e:
            return f"**Error:** {e}"
    def _parse_modules_page(self, html_text, soup):
        try:
            cid = re.search(r'/courses/(\d+)/', html_text)
            if not cid: return "**Error:** No course ID"
            s = self._create_session(); s.headers['Accept'] = 'application/json+canvas-string-ids'
            r = s.get(f'https://psu.instructure.com/api/v1/courses/{cid.group(1)}/modules', params={'include[]': ['items']}, timeout=10)
            r.raise_for_status()
            md = [f"## Modules ({len(r.json())} total)\n"]
            for m in r.json():
                state = {'completed':'✅','started':'🔄','locked':'🔒'}.get(m.get('state'),'📦')
                md.append(f"\n### {state} {m.get('name','?')}")
                items = m.get('items', [])
                if items:
                    md.append("| Item | Type | Local |")
                    md.append("|------|------|-------|")
                    for i in items:
                        title, typ = i.get('title','?'), i.get('type','?'); local = '🟢' if os.path.exists(os.path.join(config.TODO_DIR, title)) else '-'
                        md.append(f"| {title} | {typ} | {local} |")
            return '\n'.join(md)
        except Exception as e:
            return f"**Error:** {e}"
    def _init_model_selection(self):
        """Initialize model selection from default.json"""
        cfg = model_config.load_default_config()
        product, model = cfg.get('product', 'Gemini'), cfg.get('model', 'gemini-2.5-pro')
        idx = self.auto_detail_window.productComboBox.findText(product)
        if idx >= 0: self.auto_detail_window.productComboBox.setCurrentIndex(idx)
        all_models = model_config.get_all_models()
        self.auto_detail_window.modelComboBox.clear()
        self.auto_detail_window.modelComboBox.addItems(all_models.get(product, []))
        idx = self.auto_detail_window.modelComboBox.findText(model)
        if idx >= 0: self.auto_detail_window.modelComboBox.setCurrentIndex(idx)
    def on_product_changed(self, product):
        """Handle product selection change"""
        all_models = model_config.get_all_models()
        self.auto_detail_window.modelComboBox.clear()
        self.auto_detail_window.modelComboBox.addItems(all_models.get(product, []))
        self.auto_detail_window.thinkingToggleWidget.setVisible(product == 'Claude')
    def on_model_changed(self, model):
        """Handle model selection change"""
        product = self.auto_detail_window.productComboBox.currentText()
        model_config.save_default_config(product, model)
    def on_auto_folder_clicked(self):
        """Open assignment folder from AutoDetail"""
        if not self.auto_detail_mgr: return
        folder = self.auto_detail_mgr.todo.get('assignment_details', {}).get('folder')
        if folder:
            fp = os.path.join(config.TODO_DIR, folder)
            if os.path.exists(fp): self._open_folder(fp)
    def on_hw_debug_clicked(self):
        """Debug homework (run CLI with current settings)"""
        if not self.auto_detail_mgr: return
        adw = self.auto_detail_window
        url = self.auto_detail_mgr.todo.get('redirect_url') or self.auto_detail_mgr.todo.get('assignment', {}).get('html_url')
        if not url: return
        if url.startswith('/'):
            url = f"{config.CANVAS_BASE_URL}{url}"
        product = adw.productComboBox.currentText(); model = adw.modelComboBox.currentText()
        import subprocess, sys
        subprocess.Popen([sys.executable, os.path.join(config.ROOT_DIR, 'func/getHomework.py'),
                         '--url', url, '--product', product, '--model', model],
                        cwd=config.ROOT_DIR)
    def on_quiz_debug_clicked(self):
        """Debug quiz (run CLI with current settings)"""
        if not self.auto_detail_mgr: return
        adw = self.auto_detail_window
        url = self.auto_detail_mgr.todo.get('redirect_url') or self.auto_detail_mgr.todo.get('assignment', {}).get('html_url')
        if not url: return
        if url.startswith('/'):
            url = f"{config.CANVAS_BASE_URL}{url}"
        product = adw.productComboBox.currentText(); model = adw.modelComboBox.currentText()
        import subprocess, sys
        subprocess.Popen([sys.executable, os.path.join(config.ROOT_DIR, 'func/getQuiz_ultra.py'),
                         '--url', url, '--product', product, '--model', model],
                        cwd=config.ROOT_DIR)
    def on_hw_again_clicked(self):
        """Regenerate homework with current settings"""
        if not self.auto_detail_mgr: return
        adw = self.auto_detail_window
        url = self.auto_detail_mgr.todo.get('redirect_url') or self.auto_detail_mgr.todo.get('assignment', {}).get('html_url')
        if not url: return
        if url.startswith('/'):
            url = f"{config.CANVAS_BASE_URL}{url}"
        product = adw.productComboBox.currentText(); model = adw.modelComboBox.currentText()
        prompt = adw.promptEditBox.toPlainText().strip() or config.DEFAULT_PROMPTS['homework']
        from pathlib import Path
        ref_files = []
        todo_files = (self.auto_detail_mgr.todo.get('assignment_details') or {}).get('files') or []
        for f in todo_files:
            if fp := f.get('local_path'):
                if os.path.exists(fp): ref_files.append(fp)
        assignment_folder = self.auto_detail_mgr.todo.get('assignment_details', {}).get('assignment_folder')
        if not assignment_folder:
            adw.previewStatusLabel.setText("Status: Error - No assignment folder")
            return
        def run():
            try:
                from func import getHomework
                result = getHomework.run_gui(url, product, model, prompt, ref_files, assignment_folder)
                self.auto_detail_signal.status_update.emit("Status: Preview generated")
                self.auto_detail_signal.preview_refresh.emit()
            except Exception as e:
                import traceback
                traceback.print_exc()  # Print full traceback to terminal
                self.auto_detail_signal.status_update.emit(f"Status: Error - {str(e)}")
        threading.Thread(target=run, daemon=True).start()
        adw.previewStatusLabel.setText("Status: Generating...")
    def on_quiz_again_clicked(self):
        """Regenerate quiz answers with current settings"""
        if not self.auto_detail_mgr: return
        adw = self.auto_detail_window
        url = self.auto_detail_mgr.todo.get('redirect_url') or self.auto_detail_mgr.todo.get('assignment', {}).get('html_url')
        if not url: return
        if url.startswith('/'):
            url = f"{config.CANVAS_BASE_URL}{url}"
        product = adw.productComboBox.currentText(); model = adw.modelComboBox.currentText()
        prompt = adw.promptEditBox.toPlainText().strip() or config.DEFAULT_PROMPTS['quiz']
        thinking = self.thinking_toggle.isChecked() if product == 'Claude' else False
        assignment_folder = self.auto_detail_mgr.todo.get('assignment_details', {}).get('assignment_folder')
        if not assignment_folder:
            adw.previewStatusLabel.setText("Status: Error - No assignment folder")
            return
        def run():
            try:
                from func import getQuiz_ultra
                result = getQuiz_ultra.run_gui(url, product, model, prompt, assignment_folder, thinking=thinking)
                self._last_quiz_result = result  # 保存结果用于提交
                self.auto_detail_signal.status_update.emit("Status: Preview generated")
                self.auto_detail_signal.preview_refresh.emit()
            except Exception as e:
                import traceback
                traceback.print_exc()  # Print full traceback to terminal
                self.auto_detail_signal.status_update.emit(f"Status: Error - {str(e)}")
        threading.Thread(target=run, daemon=True).start()
        adw.previewStatusLabel.setText("Status: Generating...")
    def on_hw_preview_clicked(self):
        """Generate homework preview (same as Again)"""
        self.on_hw_again_clicked()
    def on_quiz_preview_clicked(self):
        """Generate quiz preview (same as Again)"""
        self.on_quiz_again_clicked()
    def _refresh_auto_detail_preview(self):
        """Refresh preview panel in AutoDetail window"""
        if not self.auto_detail_mgr: return
        adw = self.auto_detail_window
        preview_html = self._load_auto_detail_preview()
        if preview_html:
            adw.aiPreviewView.setHtml(preview_html)
            adw.previewStatusLabel.setText("Status: Preview loaded")
    def _refresh_current_category(self):
        """Refresh current category in CourseDetail window"""
        if not self.course_detail_mgr: return
        cdw = self.course_detail_window
        current_row = cdw.categoryList.currentRow()
        if current_row >= 0:
            self.on_course_detail_category_changed(current_row)
    def on_hw_submit_clicked(self):
        """Submit homework to Canvas"""
        if not self.auto_detail_mgr: return
        adw = self.auto_detail_window
        url = self.auto_detail_mgr.todo.get('redirect_url') or self.auto_detail_mgr.todo.get('assignment', {}).get('html_url')
        if not url: return
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(adw, 'Confirm Submission',
                                     'Submit homework to Canvas?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes: return
        def run():
            try:
                from func import getHomework
                success = getHomework.submit_to_canvas(url)
                if success:
                    adw.previewStatusLabel.setText("Status: Submitted successfully")
                    self.show_toast("Homework 提交成功！", 'success')
                else:
                    adw.previewStatusLabel.setText("Status: Submission failed")
                    self.show_toast("Homework 提交失败", 'error')
            except Exception as e:
                adw.previewStatusLabel.setText(f"Status: Error - {str(e)}")
                self.show_toast(f"提交错误: {str(e)}", 'error')
        threading.Thread(target=run, daemon=True).start()
        adw.previewStatusLabel.setText("Status: Submitting...")
    def on_quiz_submit_clicked(self):
        """Submit quiz to Canvas"""
        if not self.auto_detail_mgr: return
        adw = self.auto_detail_window
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(adw, 'Confirm Submission',
                                     'Submit quiz answers to Canvas?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes: return
        def run():
            try:
                from func import getQuiz_ultra
                import json
                if not hasattr(self, '_last_quiz_result'):
                    self.auto_detail_signal.status_update.emit("Status: No preview data - generate first")
                    self.show_toast("需要先生成预览", 'warning')
                    return
                result = self._last_quiz_result; s = result['session']
                doc = result['doc']; url = result['url']
                qs = result['questions']; ans = result['answers']
                getQuiz_ultra.submit(s, url, doc, qs, ans, skip_confirm=True)
                self.auto_detail_signal.status_update.emit("Status: Submitted successfully")
                self.show_toast("Quiz 提交成功！", 'success')
            except Exception as e:
                self.auto_detail_signal.status_update.emit(f"Status: Error - {str(e)}")
                self.show_toast(f"提交错误: {str(e)}", 'error')
        threading.Thread(target=run, daemon=True).start()
        adw.previewStatusLabel.setText("Status: Submitting...")
    def on_view_detail_clicked(self):
        """Open output folder to view details"""
        if not self.auto_detail_mgr: return
        assignment_folder = self.auto_detail_mgr.todo.get('assignment_details', {}).get('assignment_folder')
        if not assignment_folder: return
        output_dir = os.path.join(assignment_folder, 'auto', 'output')
        if os.path.exists(output_dir):
            self._open_folder(output_dir)
    def _open_folder(self, path):
        if path and os.path.exists(path):
            {'Windows': lambda: os.startfile(path), 'Darwin': lambda: subprocess.run(['open', path]), 'Linux': lambda: subprocess.run(['xdg-open', path])}.get(platform.system(), lambda: None)()
    def close_tab(self, index):
        if index > 0: self.main_window.consoleTabWidget.removeTab(index)
    def close_automation_tab(self, index):
        if index > 0: self.automation_window.consoleTabWidget.removeTab(index)
    def _install_list_event_filters(self):
        for lst in [self.main_window.categoryList, self.main_window.itemList,
                    self.automation_window.automatableOpenCategoryList, self.automation_window.automatableOpenItemList,
                    self.automation_window.automatableCloseCategoryList, self.automation_window.automatableCloseItemList,
                    self.automation_window.automatableCategoryList, self.automation_window.automatableItemList,
                    self.automation_window.allItemsCategoryList, self.automation_window.allItemsItemList,
                    self.course_detail_window.categoryList, self.course_detail_window.itemList]:
            lst.installEventFilter(self)
    def eventFilter(self, obj, event):
        if obj == self.main_window and event.type() == QEvent.Type.Resize:
            self._update_launcher_geometry()
            return False
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            modifiers = event.modifiers(); current_widget = self.stacked_widget.currentWidget()
            if self.launcher_overlay.isVisible() and isinstance(obj, QListWidget):
                if key in [Qt.Key.Key_W, Qt.Key.Key_A, Qt.Key.Key_S, Qt.Key.Key_D]:
                    self._handle_launcher_wasd(key, obj)
                    return True
                elif key == Qt.Key.Key_Space:
                    item = obj.currentItem()
                    if item:
                        if obj == self.launcher_overlay.courseList:
                            self._on_launcher_course_double_clicked(item)
                        elif obj == self.launcher_overlay.todoList:
                            self._on_launcher_todo_double_clicked(item)
                        return True
                return False
            if key in [Qt.Key.Key_W, Qt.Key.Key_A, Qt.Key.Key_S, Qt.Key.Key_D] and isinstance(obj, QListWidget):
                self._handle_wasd_navigation(key, current_widget)
                return True
            if key == Qt.Key.Key_Space:
                if current_widget == self.main_window and self.main_window.categoryList.currentRow() == 0:
                    ii = self.main_window.itemList.currentRow()
                    if ii >= 0:
                        courses = self.dm.get('courses')
                        if ii < len(courses):
                            self.course_detail_mgr = CourseDetailManager(courses[ii], self.dm.get('todos'), self.dm.get('history_todos'))
                            self.populate_course_detail_window()
                            self.stacked_widget.setCurrentWidget(self.course_detail_window)
                            return True
                elif current_widget == self.course_detail_window:
                    ii = self.course_detail_window.itemList.currentRow()
                    if ii >= 0:
                        item_data = self.course_detail_window.itemList.item(ii).data(Qt.ItemDataRole.UserRole + 1)
                        if item_data and item_data.get('type') == 'tab':
                            url = item_data.get('data', {}).get('url')
                            if url:
                                webbrowser.open(url)
                                return True
            if key == Qt.Key.Key_F and current_widget == self.course_detail_window and self.course_detail_mgr:
                category = self.course_detail_window.categoryList.currentItem()
                if category:
                    folder_map = {'Syllabus': self.course_detail_mgr.syll_dir, 'Textbook': self.course_detail_mgr.textbook_dir, 'Tabs': os.path.join(self.course_detail_mgr.course_dir, 'Tabs')}
                    folder = folder_map.get(category.text())
                    if folder:
                        os.makedirs(folder, exist_ok=True)
                        self._open_folder(folder)
                        return True
            if key == Qt.Key.Key_Space and (modifiers & Qt.KeyboardModifier.ShiftModifier):
                todo = None
                if current_widget == self.main_window and self.main_window.categoryList.currentRow() == 1:
                    ii = self.main_window.itemList.currentRow()
                    if ii >= 0:
                        item = self.main_window.itemList.item(ii)
                        if item:
                            todo = item.data(Qt.ItemDataRole.UserRole + 1)
                elif current_widget == self.automation_window:
                    tab_idx = self.automation_window.mainTabWidget.currentIndex()
                    item_lists = [self.automation_window.automatableOpenItemList, self.automation_window.automatableCloseItemList,
                                  self.automation_window.automatableItemList, self.automation_window.allItemsItemList]
                    ii = item_lists[tab_idx].currentRow()
                    if ii >= 0:
                        item = item_lists[tab_idx].item(ii)
                        if item:
                            todo = item.data(Qt.ItemDataRole.UserRole)
                if todo:
                    meta = self.dm.classify_todo(todo)
                    if meta.get('is_automatable'):
                        self.auto_detail_mgr = AutoDetailManager(todo)
                        self.populate_auto_detail_window()
                        self.stacked_widget.setCurrentWidget(self.auto_detail_window)
                        return True
            if current_widget == self.main_window and not (modifiers & ~Qt.KeyboardModifier.ShiftModifier):
                if key == Qt.Key.Key_A and (modifiers & Qt.KeyboardModifier.ShiftModifier):
                    self.on_automation_top_clicked()
                    return True
                elif key == Qt.Key.Key_C and (modifiers & Qt.KeyboardModifier.ShiftModifier):
                    self._show_clean_dialog()
                    return True
                elif key == Qt.Key.Key_C and not (modifiers & Qt.KeyboardModifier.ShiftModifier):
                    self.main_window.categoryList.setCurrentRow(0)
                    self.main_window.categoryList.setFocus()
                    if self.main_window.itemList.count() > 0: self.main_window.itemList.setCurrentRow(0)
                    return True
                elif key == Qt.Key.Key_T:
                    self.main_window.categoryList.setCurrentRow(1)
                    self.main_window.categoryList.setFocus()
                    if self.main_window.itemList.count() > 0: self.main_window.itemList.setCurrentRow(0)
                    return True
                elif key == Qt.Key.Key_F:
                    self.main_window.categoryList.setCurrentRow(2)
                    self.main_window.categoryList.setFocus()
                    if self.main_window.itemList.count() > 0: self.main_window.itemList.setCurrentRow(0)
                    return True
        return super().eventFilter(obj, event)
    def _handle_launcher_wasd(self, key, obj):
        """Handle WASD navigation for launcher overlay"""
        lists = [self.launcher_overlay.todoList, self.launcher_overlay.courseList]; current_idx = 0 if obj == lists[0] else 1 if obj == lists[1] else -1
        if current_idx == -1: return
        if key == Qt.Key.Key_W:
            row = obj.currentRow()
            if row > 0: obj.setCurrentRow(row - 1)
        elif key == Qt.Key.Key_S:
            row = obj.currentRow()
            if row < obj.count() - 1: obj.setCurrentRow(row + 1)
        elif key == Qt.Key.Key_A:
            if current_idx > 0:
                lists[current_idx - 1].setFocus()
                if lists[current_idx - 1].count() > 0:
                    lists[current_idx - 1].setCurrentRow(0)
        elif key == Qt.Key.Key_D:
            if current_idx < len(lists) - 1:
                lists[current_idx + 1].setFocus()
                if lists[current_idx + 1].count() > 0:
                    lists[current_idx + 1].setCurrentRow(0)
    def _handle_wasd_navigation(self, key, current_widget):
        if current_widget == self.main_window:
            lists = [self.main_window.categoryList, self.main_window.itemList, None]
        elif current_widget == self.automation_window:
            tab_idx = self.automation_window.mainTabWidget.currentIndex()
            lists_map = [
                [self.automation_window.automatableOpenCategoryList, self.automation_window.automatableOpenItemList, None],
                [self.automation_window.automatableCloseCategoryList, self.automation_window.automatableCloseItemList, None],
                [self.automation_window.automatableCategoryList, self.automation_window.automatableItemList, None],
                [self.automation_window.allItemsCategoryList, self.automation_window.allItemsItemList, None]
            ]
            lists = lists_map[tab_idx]
        elif current_widget == self.course_detail_window:
            lists = [self.course_detail_window.categoryList, self.course_detail_window.itemList, None]
        else:
            return
        focused_list = None
        for i, lst in enumerate(lists):
            if lst and lst.hasFocus():
                focused_list = (i, lst)
                break
        if not focused_list:
            if lists[0]: lists[0].setFocus()
            return
        idx, current_list = focused_list
        if key == Qt.Key.Key_W:
            current_row = current_list.currentRow()
            if current_row > 0: current_list.setCurrentRow(current_row - 1)
        elif key == Qt.Key.Key_S:
            current_row = current_list.currentRow()
            if current_row < current_list.count() - 1: current_list.setCurrentRow(current_row + 1)
        elif key == Qt.Key.Key_A:
            if idx > 0 and lists[idx - 1]:
                lists[idx - 1].setFocus()
                if lists[idx - 1].count() > 0: lists[idx - 1].setCurrentRow(0)
        elif key == Qt.Key.Key_D:
            if idx < len(lists) - 1 and lists[idx + 1]:
                lists[idx + 1].setFocus()
                if lists[idx + 1].count() > 0: lists[idx + 1].setCurrentRow(0)
    def _show_clean_dialog(self):
        from clean import preview_deletion, clean_directory, build_tree, print_tree
        to_delete = preview_deletion()
        if not to_delete: return QMessageBox.information(self, "Clean", "No files to clean!")
        tree_output = StringIO(); old_stdout = sys.stdout
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
        button_layout = QHBoxLayout(); yes_btn, cancel_btn = QPushButton("Yes"), QPushButton("Cancel")
        yes_btn.clicked.connect(lambda: (clean_directory(to_delete), QMessageBox.information(self, "Clean", "Files cleaned successfully!"), dialog.accept()))
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(yes_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        dialog.exec()
def init_qt_window():
    window = CanvasApp()
    def status_update_thread():
        while True:
            time.sleep(30)
            window.status_signal.update.emit()
    def archive_thread():
        while True:
            time.sleep(300)  # 5 minutes
            try:
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'func'))
                from history_manager import archive_past_todos
                archive_past_todos()
            except: pass
    threading.Thread(target=status_update_thread, daemon=True).start(); threading.Thread(target=archive_thread, daemon=True).start()
    return window
def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_THEME)
    window = init_qt_window()
    window.show()
    sys.exit(app.exec())
if __name__ == '__main__':
    main()
