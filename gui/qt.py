import sys, os, time, threading, json, re, requests, html2text, webbrowser, subprocess, platform
from datetime import datetime, timedelta
from io import StringIO
from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QListWidgetItem, QListWidget, QMessageBox, QStyledItemDelegate, QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout
from PyQt6.QtCore import pyqtSignal, QObject, Qt, QEvent
from PyQt6.uic import loadUi
from bs4 import BeautifulSoup
import markdown as md_lib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config, checkStatus
from gui import qt_interact, formatters, delegates
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

class CanvasApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.dm, self.done_mgr, self.course_detail_mgr, self.auto_detail_mgr = DataManager(), DoneManager(), None, None
        self.history_mode = False
        self.status_signal = StatusUpdateSignal()
        self.status_signal.update.connect(self.update_status)
        self.tab_content_signal = TabContentSignal()
        self.tab_content_signal.update_html.connect(self._update_course_detail_html)
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
        ui_dir = os.path.join(os.path.dirname(__file__), 'ui')
        self.main_window = loadUi(os.path.join(ui_dir, 'main.ui'))
        self.sitting_window = loadUi(os.path.join(ui_dir, 'sitting.ui'))
        self.automation_window = loadUi(os.path.join(ui_dir, 'automation.ui'))
        self.course_detail_window = loadUi(os.path.join(ui_dir, 'course_detail.ui'))
        self.auto_detail_window = loadUi(os.path.join(ui_dir, 'autoDetail.ui'))
        self.launcher_overlay = loadUi(os.path.join(ui_dir, 'launcher.ui'))
        for w in [self.main_window, self.sitting_window, self.automation_window, self.course_detail_window, self.auto_detail_window]:
            self.stacked_widget.addWidget(w)

        self.status_widgets = {k: getattr(self.main_window, f'{k}Indicator') for k in ['account', 'cookie', 'todos', 'network', 'courses']}
        for dv in [self.main_window.detailView, self.automation_window.automatableOpenDetailView, self.automation_window.automatableCloseDetailView,
                   self.automation_window.automatableDetailView, self.automation_window.allItemsDetailView, self.course_detail_window.detailView,
                   self.auto_detail_window.assignmentDetailView, self.auto_detail_window.refFilesView, self.auto_detail_window.aiPreviewView]:
            dv.setOpenExternalLinks(True)

        # iOS toggles
        self.ios_toggle_main = IOSToggle(width=50, height=24)
        self.main_window.categoryColumnLayout.addWidget(self.ios_toggle_main)
        self.ios_toggles_auto = [IOSToggle(width=50, height=24) for _ in range(4)]
        for toggle, layout in zip(self.ios_toggles_auto, ['automatableOpenCategoryLayout', 'automatableCloseCategoryLayout', 'automatableCategoryLayout', 'allItemsCategoryLayout']):
            getattr(self.automation_window, layout).addWidget(toggle)
        self.ios_toggle_course_detail = IOSToggle(width=50, height=24)
        self.course_detail_window.toggleLayout.addWidget(self.ios_toggle_course_detail)

        # History mode toggle (right of user info)
        self.history_toggle = IOSToggle(width=50, height=24)
        hist_label = QLabel("History")
        hist_label.setStyleSheet("font-size: 11px; color: #aaa;")
        hist_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_window.historyToggleLayout.addWidget(hist_label)
        self.main_window.historyToggleLayout.addWidget(self.history_toggle)
        self.history_toggle.setChecked(False)

        self.stacked_widget.setCurrentWidget(self.main_window)

        # Setup launcher overlay (defer data population)
        self._init_launcher_overlay_ui()

    def _init_launcher_overlay_ui(self):
        """Initialize launcher overlay UI without data (defer data population)"""
        from PyQt6.QtWidgets import QWidget
        from PyQt6.QtCore import Qt as QtCore

        # Make launcher overlay a child of main_window to overlay it
        self.launcher_overlay.setParent(self.main_window)
        self.launcher_overlay.setAttribute(QtCore.WidgetAttribute.WA_StyledBackground, True)

        # Connect buttons
        self.launcher_overlay.dashboardBtn.clicked.connect(self._hide_launcher)
        self.launcher_overlay.automationBtn.clicked.connect(lambda: (self._hide_launcher(), self.on_automation_top_clicked()))
        self.launcher_overlay.settingsBtn.clicked.connect(lambda: qt_interact.on_login_clicked(self.main_window, self.stacked_widget, self.sitting_window))

        # Connect list interactions
        self.launcher_overlay.courseList.itemDoubleClicked.connect(self._on_launcher_course_double_clicked)

        # Apply TodoItemDelegate to todoList
        self.launcher_overlay.todoList.setItemDelegate(delegates.TodoItemDelegate(self.launcher_overlay.todoList))

        # Install event filters
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
        # Clear lists
        self.launcher_overlay.todoList.clear()
        self.launcher_overlay.courseList.clear()

        # Populate TODO list (copy from main window TODO tab)
        for todo in self.dm.get('todos'):
            item = QListWidgetItem(f"{todo.get('course_name', '')} - {todo.get('name', '')}")
            item.setData(Qt.ItemDataRole.UserRole, self.dm.classify_todo(todo))
            item.setData(Qt.ItemDataRole.UserRole + 1, todo)
            self.launcher_overlay.todoList.addItem(item)

        # Populate Course list (copy from main window Courses tab)
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
                    account_data = json.load(f)
                    account = account_data.get('account', '--')
                    self.sitting_window.accountDisplayLabel.setText(f"Account: {account}")
        except:
            self.sitting_window.accountDisplayLabel.setText("Account: --")

    def _save_api_key(self, api_key):
        """Save Gemini API key to account_config.json"""
        if not api_key:
            QMessageBox.warning(self, "Error", "Please enter an API key!")
            return

        try:
            # Load existing config
            config_data = {}
            if os.path.exists(config.ACCOUNT_CONFIG_FILE):
                with open(config.ACCOUNT_CONFIG_FILE) as f:
                    config_data = json.load(f)

            # Update API key
            config_data['gemini_api_key'] = api_key

            # Save back
            with open(config.ACCOUNT_CONFIG_FILE, 'w') as f:
                json.dump(config_data, f, indent=2)

            QMessageBox.information(self, "Success", "API Key saved successfully!\nRestart the app to apply changes.")
            self.sitting_window.geminiApiInput.clear()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save API key: {str(e)}")

    def _save_preference(self, base_url):
        """Save preference (base_url) to account_config.json"""
        if not base_url:
            QMessageBox.warning(self, "Error", "Please enter a base URL!")
            return

        try:
            # Load existing config
            config_data = {}
            if os.path.exists(config.ACCOUNT_CONFIG_FILE):
                with open(config.ACCOUNT_CONFIG_FILE) as f:
                    config_data = json.load(f)

            # Update preference
            if 'preference' not in config_data:
                config_data['preference'] = {}
            config_data['preference']['base_url'] = base_url

            # Save back
            with open(config.ACCOUNT_CONFIG_FILE, 'w') as f:
                json.dump(config_data, f, indent=2)

            QMessageBox.information(self, "Success", "Preference saved successfully!\nRestart the app to apply changes.")
            self.sitting_window.baseUrlInput.clear()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save preference: {str(e)}")

    def _on_launcher_course_double_clicked(self, item):
        """Handle double-click on launcher course list -> open CourseDetail"""
        course_name = item.text()
        courses = self.dm.get('courses')
        for i, course in enumerate(courses):
            if course.get('name') == course_name:
                self.course_detail_mgr = CourseDetailManager(course, self.dm.get('todos'))
                self.populate_course_detail_window()
                self._hide_launcher()
                self.stacked_widget.setCurrentWidget(self.course_detail_window)
                break

    def init_button_bindings(self):
        mw, sw, aw, cdw = self.main_window, self.sitting_window, self.automation_window, self.course_detail_window
        # Main window
        for btn, handler in [('backBtn', self._show_launcher),
                             ('getCookieBtn', lambda: qt_interact.on_get_cookie_clicked(mw.consoleTabWidget, self)),
                             ('getTodoBtn', lambda: qt_interact.on_get_todo_clicked(mw.consoleTabWidget, self)),
                             ('getCourseBtn', lambda: qt_interact.on_get_course_clicked(mw.consoleTabWidget, self)),
                             ('gSyllAllBtn', lambda: qt_interact.on_gsyll_all_clicked(mw.consoleTabWidget)),
                             ('cleanBtn', self._show_clean_dialog),
                             ('automationTopBtn', self.on_automation_top_clicked),
                             ('openFolderBtn', self.on_open_folder_clicked),
                             ('automationBtn', self.on_automation_clicked),
                             ('courseDetailBtn', self.on_course_detail_clicked)]:
            getattr(mw, btn).clicked.connect(handler)

        # Sitting window (Settings)
        sw.backBtn.clicked.connect(lambda: qt_interact.on_back_clicked(self.stacked_widget, mw))
        sw.submitBtn.clicked.connect(lambda: qt_interact.on_submit_clicked(sw.accountInput, sw.passwordInput, sw.keyInput, self.stacked_widget, mw))
        sw.saveApiBtn.clicked.connect(lambda: self._save_api_key(sw.geminiApiInput.text()))
        sw.savePrefBtn.clicked.connect(lambda: self._save_preference(sw.baseUrlInput.text()))

        # Automation window
        aw.backBtn.clicked.connect(lambda: qt_interact.on_back_clicked(self.stacked_widget, mw))
        aw.getTodoBtn.clicked.connect(lambda: qt_interact.on_get_todo_clicked(aw.consoleTabWidget, self))
        aw.cleanBtn.clicked.connect(lambda: qt_interact.on_clean_clicked(aw.consoleTabWidget))

        # Course detail window
        cdw.backBtn.clicked.connect(lambda: qt_interact.on_back_clicked(self.stacked_widget, mw))
        cdw.openTextbookFolderBtn.clicked.connect(self.on_open_textbook_folder_clicked)
        cdw.itemList.itemDoubleClicked.connect(self.on_course_detail_item_double_clicked)

        # Auto detail window
        self.auto_detail_window.backBtn.clicked.connect(lambda: qt_interact.on_back_clicked(self.stacked_widget, mw))

        # Load current login info when sitting window is shown
        self._load_current_login_info()

        # iOS toggles
        for toggle in [self.ios_toggle_main, self.ios_toggle_course_detail] + self.ios_toggles_auto:
            toggle.stateChanged.connect(self.on_toggle_console_clicked)
        self.history_toggle.stateChanged.connect(self.on_history_toggle_clicked)

        # Console tabs
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
            if status['todos'] == 0:
                if console: console.append("[INFO] Fetching todos...")
                qt_interact.on_get_todo_clicked(self.main_window.consoleTabWidget, self)

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

        # Archive past TODOs on startup
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'func'))
            from history_manager import archive_past_todos
            archive_past_todos()
        except: pass

        # Show launcher after data is loaded
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
            # Load history or current todos
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
                redirect_url = todo.get('redirect_url', '')
                is_done = self.done_mgr.is_done(redirect_url)
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

        # Get correct data source based on history mode
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
                    self.course_detail_mgr = CourseDetailManager(courses[ii], self.dm.get('todos'))
                    self.populate_course_detail_window()
                    self.stacked_widget.setCurrentWidget(self.course_detail_window)
        elif ci == 1:
            # TODO double-click: check if Tab2 (automatable), then jump to autoDetail
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
            fn = self.dm.get('todos')[ii].get('assignment_details', {}).get('folder')
            fp = os.path.join(config.ROOT_DIR, 'todo_files', fn) if fn else None
        elif ci == 2 and ii < len(self.dm.get('files')):
            fp = os.path.join(config.ROOT_DIR, 'todo_files', self.dm.get('files')[ii])
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
            url = selected_todo.get('redirect_url', '').lower()
            ci = 1 if 'quiz' in url else 2 if 'discussion' in url else 0
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
            # Filter logic
            if tab_index == 0 and not (meta['is_automatable'] and meta['is_open']): continue
            if tab_index == 1 and not (meta['is_automatable'] and not meta['is_open']): continue
            if tab_index == 2 and not meta['is_automatable']: continue
            if index != 3 and not [meta['is_homework'], meta['is_quiz'], meta['is_discussion']][index]: continue

            item = QListWidgetItem(f"{todo.get('course_name', '')} - {todo.get('name', '')}")
            item.setData(Qt.ItemDataRole.UserRole, todo)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            redirect_url = todo.get('redirect_url', '')
            is_done = self.done_mgr.is_done(redirect_url)
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
        self.course_detail_mgr = CourseDetailManager(courses[ii], self.dm.get('todos'))
        self.populate_course_detail_window()
        self.stacked_widget.setCurrentWidget(self.course_detail_window)

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

        # Populate top bar identification
        info = self.auto_detail_mgr.get_identification_info()
        adw.courseNameLabel.setText(f"Course: {info['course']}")
        adw.assignmentNameLabel.setText(f"Assignment: {info['assignment']}")
        adw.typeLabel.setText(f"Type: {info['type']}")
        adw.dueDateLabel.setText(f"Due: {info['due_date']}")

        # Populate left panel - assignment detail
        adw.assignmentDetailView.setHtml(self.auto_detail_mgr.get_assignment_detail_html())

        # Populate left panel - reference files
        adw.refFilesView.setHtml(self.auto_detail_mgr.get_reference_files_html())

        # Show/hide control console based on type
        is_quiz = self.auto_detail_mgr.is_quiz
        is_homework = self.auto_detail_mgr.is_homework

        adw.quizControlWidget.setVisible(is_quiz)
        adw.hwControlWidget.setVisible(is_homework)

        # Populate right panel (AI preview or placeholder)
        preview_html = self._load_auto_detail_preview()
        adw.aiPreviewView.setHtml(preview_html if preview_html else self.auto_detail_mgr.get_preview_placeholder_html())
        adw.previewStatusLabel.setText("Status: Preview loaded" if preview_html else "Status: No preview generated yet")

        # Clear prompt edit box (can be customized later)
        adw.promptEditBox.clear()

    def _load_auto_detail_preview(self):
        """Load AI preview (quiz or homework) if files exist"""
        if not self.auto_detail_mgr: return None

        if self.auto_detail_mgr.is_quiz:
            # Try to load quiz preview from QUIZ_RES_DIR
            preview_dir = config.QUIZ_RES_DIR
            if os.path.exists(preview_dir):
                return self.auto_detail_mgr.load_quiz_preview(preview_dir)
        elif self.auto_detail_mgr.is_homework:
            # Try to load homework preview from OUTPUT_DIR
            output_dir = config.SUBMISSION_DIR
            if os.path.exists(output_dir):
                return self.auto_detail_mgr.load_homework_preview(output_dir)

        return None

    def on_course_detail_category_changed(self, index):
        if index < 0 or not self.course_detail_mgr: return
        cdw = self.course_detail_window
        cdw.itemList.clear()
        cdw.detailView.clear()
        category = cdw.categoryList.item(index).text()
        cdw.openTextbookFolderBtn.setVisible(category == 'Textbook')
        items = self.course_detail_mgr.get_items_for_category(category)

        for item_data in items:
            item = QListWidgetItem(item_data['name'])
            item.setData(Qt.ItemDataRole.UserRole, item_data.get('has_file', False))
            item.setData(Qt.ItemDataRole.UserRole + 1, item_data)
            if item_data.get('is_done', False): item.setForeground(Qt.GlobalColor.gray)
            cdw.itemList.addItem(item)

        cdw.itemList.setItemDelegate(delegates.FileItemDelegate(cdw.itemList) if category in ['Syllabus', 'Textbook'] else QStyledItemDelegate())
        cdw.itemList.viewport().update()

    def on_course_detail_item_changed(self, index):
        if index < 0 or not self.course_detail_mgr: return
        cdw = self.course_detail_window
        item_data = cdw.itemList.item(index).data(Qt.ItemDataRole.UserRole + 1)
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
            'placeholder': lambda: f"<p>No textbook files</p><p>Folder: {data['folder']}</p>"
        }
        cdw.detailView.setHtml(html_map.get(item_type, lambda: "<p>No details</p>")())

    def on_open_textbook_folder_clicked(self):
        if not self.course_detail_mgr: return
        self._open_folder(self.course_detail_mgr.get_textbook_dir())

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
            tabs = self.course_detail_mgr.course.get('tabs', {})
            tabs_dir = os.path.join(self.course_detail_mgr.course_dir, 'Tabs')
            os.makedirs(tabs_dir, exist_ok=True)
            s = self._create_session()

            for name, path in tabs.items():
                safe = "".join(c if c.isalnum() or c in (' ','_') else '_' for c in name)
                md_path = os.path.join(tabs_dir, f"{safe}.md")
                if os.path.exists(md_path): continue

                try:
                    url = f"{config.CANVAS_BASE_URL}{path}"
                    r = s.get(url, timeout=10)
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
            md_content = html[9:]
            lines = md_content.split('\n', 1)
            title = lines[0].strip('# ')
            body = lines[1] if len(lines) > 1 else ''
            html_body = md_lib.markdown(body, extensions=['extra', 'nl2br', 'tables'])
            styled_html = f"""<style>
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

                # Handle redirects
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
                    tabs_dir = os.path.join(self.course_detail_mgr.course_dir, 'Tabs')
                    os.makedirs(tabs_dir, exist_ok=True)
                    save_path = os.path.join(tabs_dir, f"{safe_tab_name}.md")
                    full_markdown = f"# {tab_name}\n\nSource: {url}\n\n---\n\n{markdown}"
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
            cookies = {c['name']: c['value'] for c in json.load(f)}
        s = requests.Session()
        s.cookies.update(cookies)
        s.headers['User-Agent'] = 'Mozilla/5.0'
        return s

    def _html_to_md(self, soup):
        content = soup.find('div', id='content') or soup.body
        if not content: return None
        h = html2text.HTML2Text()
        h.ignore_links = h.ignore_images = False
        h.body_width = 0
        return h.handle(str(content))

    def _is_modules_page(self, html_text, soup):
        # Must have ALL conditions to be considered modules page
        has_modules_keyword = 'modules' in html_text.lower()
        if not has_modules_keyword:
            return False

        # Check for specific modules indicators (not just keyword)
        has_modules_dom = soup.find('div', id='context_modules') or soup.find('div', class_=lambda x: x and 'context_modules' in x)
        has_modules_env = 'ENV.MODULES_PATH' in html_text or '"modules_path"' in html_text
        has_modules_url = '/courses/' in html_text and '/modules' in html_text and 'context_modules' in html_text

        # Return True only if has specific modules indicators
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
                aid = s.get('assignment_id', '')
                link = soup.find('a', href=re.compile(f'/assignments/{aid}'))
                name = link.get_text(strip=True) if link else f"Assignment {aid}"
                score = s.get('score')
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
            s = self._create_session()
            s.headers['Accept'] = 'application/json+canvas-string-ids'
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
                        title, typ = i.get('title','?'), i.get('type','?')
                        local = '🟢' if os.path.exists(os.path.join(config.ROOT_DIR, 'todo_files', title)) else '-'
                        md.append(f"| {title} | {typ} | {local} |")
            return '\n'.join(md)
        except Exception as e:
            return f"**Error:** {e}"

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
        # Handle main_window resize to update launcher overlay
        if obj == self.main_window and event.type() == QEvent.Type.Resize:
            self._update_launcher_geometry()
            return False

        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            modifiers = event.modifiers()
            current_widget = self.stacked_widget.currentWidget()

            # Launcher overlay WASD + Space navigation
            if self.launcher_overlay.isVisible() and isinstance(obj, QListWidget):
                if key in [Qt.Key.Key_W, Qt.Key.Key_A, Qt.Key.Key_S, Qt.Key.Key_D]:
                    self._handle_launcher_wasd(key, obj)
                    return True
                elif key == Qt.Key.Key_Space:
                    if obj == self.launcher_overlay.courseList:
                        item = obj.currentItem()
                        if item:
                            self._on_launcher_course_double_clicked(item)
                            return True
                return False

            # WASD Navigation
            if key in [Qt.Key.Key_W, Qt.Key.Key_A, Qt.Key.Key_S, Qt.Key.Key_D] and isinstance(obj, QListWidget):
                self._handle_wasd_navigation(key, current_widget)
                return True

            # Space: Open CourseDetail/Tab URL
            if key == Qt.Key.Key_Space:
                if current_widget == self.main_window and self.main_window.categoryList.currentRow() == 0:
                    ii = self.main_window.itemList.currentRow()
                    if ii >= 0:
                        courses = self.dm.get('courses')
                        if ii < len(courses):
                            self.course_detail_mgr = CourseDetailManager(courses[ii], self.dm.get('todos'))
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

            # F: Open folder
            if key == Qt.Key.Key_F and current_widget == self.course_detail_window and self.course_detail_mgr:
                category = self.course_detail_window.categoryList.currentItem()
                if category:
                    folder_map = {'Syllabus': self.course_detail_mgr.syll_dir, 'Textbook': self.course_detail_mgr.textbook_dir, 'Tabs': os.path.join(self.course_detail_mgr.course_dir, 'Tabs')}
                    folder = folder_map.get(category.text())
                    if folder:
                        os.makedirs(folder, exist_ok=True)
                        self._open_folder(folder)
                        return True

            # Shift+Space: Jump to autoDetail (main window + automation window)
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

            # Main window shortcuts
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
        lists = [self.launcher_overlay.todoList, self.launcher_overlay.courseList]
        current_idx = 0 if obj == lists[0] else 1 if obj == lists[1] else -1
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
    threading.Thread(target=status_update_thread, daemon=True).start()
    threading.Thread(target=archive_thread, daemon=True).start()
    return window

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_THEME)
    window = init_qt_window()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
