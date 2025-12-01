"""Initializers - UI setup and signal bindings"""
import sys, os
from PyQt6.QtWidgets import QStackedWidget, QLabel, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.uic import loadUi

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from gui.widgets.wgtIOSToggle import IOSToggle
from gui.widgets.wgtSidebar import GlobalSidebar
from gui.widgets.wgtAutoDetailModern import ModernAutoDetailWidget
from gui.widgets import rdrDelegates as delegates
from gui.core import utilQtInteract as qt_interact


def _resource_path(relative_path):
    """Get absolute path to resource (dev + PyInstaller)"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class UIInitializer:
    """UI initialization"""

    @staticmethod
    def init_qt(app):
        """Initialize Qt UI: Load windows + create widgets"""
        # Container with sidebar margin
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 70, 0)
        layout.setSpacing(0)

        app.stacked_widget = QStackedWidget()
        layout.addWidget(app.stacked_widget)
        app.setCentralWidget(container)

        # Load UI files
        app.main_window = loadUi(_resource_path('gui/ui/main.ui'))
        app.automation_window = loadUi(_resource_path('gui/ui/automation.ui'))
        app.course_detail_window = loadUi(_resource_path('gui/ui/course_detail.ui'))
        app.auto_detail_window = ModernAutoDetailWidget()
        app.launcher_overlay = loadUi(_resource_path('gui/ui/launcher.ui'))
        app.settings_overlay = loadUi(_resource_path('gui/ui/settings_overlay.ui'))

        # Add to stack
        for w in [app.main_window, app.automation_window, app.course_detail_window, app.auto_detail_window]:
            app.stacked_widget.addWidget(w)

        # Status widgets
        app.status_widgets = {k: getattr(app.main_window, f'{k}Indicator') for k in ['account', 'cookie', 'todos', 'network', 'courses']}

        # Enable external links
        for dv in [app.main_window.detailView, app.automation_window.automatableOpenDetailView,
                   app.automation_window.automatableCloseDetailView, app.automation_window.automatableDetailView,
                   app.automation_window.allItemsDetailView, app.course_detail_window.detailView]:
            dv.setOpenExternalLinks(True)

        # Drag-drop for course detail
        app.course_detail_window.itemList.setAcceptDrops(True)
        app.course_detail_window.itemList.setDragEnabled(False)
        from PyQt6.QtWidgets import QAbstractItemView
        app.course_detail_window.itemList.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)

        # Toggles
        app.history_toggle = IOSToggle(width=50, height=24)
        hist_label = QLabel("History")
        hist_label.setStyleSheet("font-size: 11px; color: #aaa;")
        hist_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        app.main_window.historyToggleLayout.addWidget(hist_label)
        app.main_window.historyToggleLayout.addWidget(app.history_toggle)

        app.thinking_toggle = IOSToggle(width=50, height=24)
        app.thinking_toggle.setChecked(True)
        UIInitializer._replace_placeholder(app.auto_detail_window.thinkingTogglePlaceholder, app.thinking_toggle)

        app.manual_mode_toggle = IOSToggle(width=50, height=24)
        UIInitializer._replace_placeholder(app.settings_overlay.manualModeTogglePlaceholder, app.manual_mode_toggle)

        # Hide old buttons (replaced by sidebar)
        for btn in ['getCookieBtn', 'getTodoBtn', 'getCourseBtn', 'gSyllAllBtn', 'cleanBtn', 'automationTopBtn', 'sittingBtn']:
            if hasattr(app.main_window, btn):
                getattr(app.main_window, btn).setVisible(False)

        app.stacked_widget.setCurrentWidget(app.main_window)
        UIInitializer._init_launcher(app)
        UIInitializer._init_settings(app)
        app.sitting_window = app.settings_overlay  # Alias
        UIInitializer._init_sidebar(app)

    @staticmethod
    def _replace_placeholder(placeholder, widget):
        """Replace placeholder widget"""
        if placeholder and placeholder.parent():
            layout = placeholder.parent().layout()
            if layout:
                idx = layout.indexOf(placeholder)
                layout.removeWidget(placeholder)
                placeholder.deleteLater()
                layout.insertWidget(idx, widget)

    @staticmethod
    def _init_launcher(app):
        """Initialize launcher overlay"""
        app.launcher_overlay.setParent(app.main_window)
        app.launcher_overlay.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        app.launcher_overlay.todoList.setItemDelegate(delegates.TodoItemDelegate(app.launcher_overlay.todoList))
        app.main_window.installEventFilter(app)
        app.launcher_overlay.todoList.installEventFilter(app)
        app.launcher_overlay.courseList.installEventFilter(app)

    @staticmethod
    def _init_settings(app):
        """Initialize settings overlay"""
        app.settings_overlay.setParent(app)
        app.settings_overlay.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        app.settings_overlay.hide()

    @staticmethod
    def _init_sidebar(app):
        """Initialize floating sidebar"""
        app.sidebar = GlobalSidebar(app, parent=app)
        app.sidebar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        app.sidebar.raise_()
        UIInitializer._position_sidebar(app)

    @staticmethod
    def _position_sidebar(app):
        """Position sidebar at right edge"""
        w = app.sidebar.width() or app.sidebar.collapsed_width
        app.sidebar.move(app.width() - w, 0)
        app.sidebar.setFixedHeight(app.height())

    @staticmethod
    def init_data_viewer(app):
        """Initialize data viewer"""
        app.main_window.categoryList.addItems(["Courses", "TODOs", "Files"])
        app.main_window.courseDetailBtn.setVisible(False)
        app.dm.load_all()
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'func'))
            from mgrHistory import archive_past_todos
            archive_past_todos()
        except Exception:
            pass
        app.launcher_handler.show()


class SignalInitializer:
    """Signal/slot bindings"""

    @staticmethod
    def init_button_bindings(app):
        """Initialize all button bindings"""
        mw, sw, aw, cdw, adw = app.main_window, app.settings_overlay, app.automation_window, app.course_detail_window, app.auto_detail_window

        # === MAIN WINDOW ===
        mw.backBtn.clicked.connect(app.launcher_handler.show)
        mw.getCookieBtn.clicked.connect(lambda: qt_interact.on_get_cookie_clicked(None, app))
        mw.getTodoBtn.clicked.connect(lambda: qt_interact.on_get_todo_clicked(None, app))
        mw.getCourseBtn.clicked.connect(lambda: qt_interact.on_get_course_clicked(None, app))
        mw.gSyllAllBtn.clicked.connect(lambda: qt_interact.on_gsyll_all_clicked(None, app))
        mw.cleanBtn.clicked.connect(app.sitting_handler.show_clean_dialog)
        mw.automationTopBtn.clicked.connect(app.automation_handler.open_top)
        mw.sittingBtn.clicked.connect(app.sitting_handler.show)
        mw.openFolderBtn.clicked.connect(app.main_handler.on_open_folder_clicked)
        mw.courseDetailBtn.clicked.connect(app.course_detail_handler.open)
        mw.categoryList.currentRowChanged.connect(app.main_handler.on_category_changed)
        mw.itemList.currentRowChanged.connect(app.main_handler.on_item_changed)
        mw.itemList.itemChanged.connect(app.main_handler.on_checkbox_changed)
        mw.itemList.itemDoubleClicked.connect(app.main_handler.on_item_double_clicked)
        for f in [mw.filterHomework, mw.filterQuiz, mw.filterDiscussion, mw.filterAutomatable]:
            f.stateChanged.connect(app.main_handler.apply_filters)

        # === SETTINGS OVERLAY ===
        sw.backBtn.clicked.connect(app.sitting_handler.hide)
        sw.submitBtn.clicked.connect(lambda: qt_interact.on_submit_clicked(sw.accountInput, sw.passwordInput, sw.keyInput, app.stacked_widget, mw, app.manual_mode_toggle))
        sw.saveApiBtn.clicked.connect(app.sitting_handler.save_api_key)
        sw.savePrefBtn.clicked.connect(lambda: app.sitting_handler.save_preference(sw.baseUrlInput.text()))

        # API key focus handlers
        def wrap_focus(widget, handler):
            orig = widget.focusInEvent
            def wrapper(e): handler(); orig(e)
            widget.focusInEvent = wrapper
        wrap_focus(sw.geminiApiInput, app.sitting_handler.on_gemini_api_focus)
        wrap_focus(sw.claudeApiInput, app.sitting_handler.on_claude_api_focus)

        sw.refreshTasksBtn.clicked.connect(app.sitting_handler.refresh_tasks_table)
        sw.stopTaskBtn.clicked.connect(app.sitting_handler.stop_selected_task)
        sw.stopAllTasksBtn.clicked.connect(app.sitting_handler.stop_all_tasks)

        def on_manual_mode_changed(state):
            is_manual = (state == 2)
            sw.keyInput.setEnabled(not is_manual)
            sw.keyInput.setPlaceholderText("TOTP Key (Disabled)" if is_manual else "TOTP Key")
        app.manual_mode_toggle.stateChanged.connect(on_manual_mode_changed)

        # === AUTOMATION WINDOW ===
        aw.backBtn.clicked.connect(lambda: qt_interact.on_back_clicked(app.stacked_widget, mw))
        aw.getTodoBtn.clicked.connect(lambda: qt_interact.on_get_todo_clicked(None, app))
        aw.cleanBtn.clicked.connect(lambda: qt_interact.on_clean_clicked(None, app))

        for tab_idx, prefix in enumerate(['automatableOpen', 'automatableClose', 'automatable', 'allItems']):
            cat_list = getattr(aw, f'{prefix}CategoryList')
            item_list = getattr(aw, f'{prefix}ItemList')
            cat_list.currentRowChanged.connect(lambda idx, ti=tab_idx: app.automation_handler.on_category_changed(idx, ti))
            item_list.currentRowChanged.connect(lambda idx, ti=tab_idx: app.automation_handler.on_item_changed(idx, ti))
            item_list.itemChanged.connect(app.automation_handler.on_checkbox_changed)
            item_list.itemDoubleClicked.connect(app.automation_handler.on_item_double_clicked)

        # === COURSE DETAIL WINDOW ===
        cdw.backBtn.clicked.connect(lambda: qt_interact.on_back_clicked(app.stacked_widget, mw))
        cdw.openSyllabusFolderBtn.clicked.connect(app.course_detail_handler.on_open_syllabus_folder_clicked)
        cdw.openTextbookFolderBtn.clicked.connect(app.course_detail_handler.on_open_textbook_folder_clicked)
        cdw.deconTextbookBtn.clicked.connect(app.course_detail_handler.on_decon_textbook_clicked)
        cdw.loadFromDeconBtn.clicked.connect(lambda: qt_interact.on_load_from_decon_clicked(app))
        cdw.learnMaterialBtn.clicked.connect(lambda: qt_interact.on_learn_material_clicked(app))
        cdw.itemList.itemDoubleClicked.connect(app.course_detail_handler.on_item_double_clicked)
        cdw.categoryList.currentRowChanged.connect(app.course_detail_handler.on_category_changed)
        cdw.itemList.currentRowChanged.connect(app.course_detail_handler.on_item_changed)
        cdw.itemList.dragEnterEvent = app.course_detail_handler.drag_enter
        cdw.itemList.dragMoveEvent = app.course_detail_handler.drag_move
        cdw.itemList.dropEvent = app.course_detail_handler.drag_drop

        # === AUTO DETAIL WINDOW ===
        def on_back():
            app.auto_detail_handler.stop_quiz_status_timer()
            qt_interact.on_back_clicked(app.stacked_widget, mw)

        adw.back_clicked.connect(on_back)
        adw.folder_clicked.connect(app.auto_detail_handler.on_auto_folder_clicked)
        adw.debug_clicked.connect(app.auto_detail_handler.on_debug_clicked)
        adw.again_clicked.connect(app.auto_detail_handler.on_again_clicked)
        adw.preview_clicked.connect(app.auto_detail_handler.on_preview_clicked)
        adw.submit_clicked.connect(app.auto_detail_handler.on_submit_clicked)
        adw.viewDetailBtn.clicked.connect(app.auto_detail_handler.on_view_detail_clicked)
        adw.product_changed.connect(app.auto_detail_handler.on_product_changed)
        adw.model_changed.connect(app.auto_detail_handler.on_model_changed)
        adw.tab_changed.connect(app.auto_detail_handler.on_tab_changed)
        app.auto_detail_handler.init_model_selection()

        # === LAUNCHER OVERLAY ===
        app.launcher_overlay.dashboardBtn.clicked.connect(app.launcher_handler.hide)
        app.launcher_overlay.automationBtn.clicked.connect(lambda: (app.launcher_handler.hide(), app.automation_handler.open_top()))
        app.launcher_overlay.settingsBtn.clicked.connect(app.sitting_handler.show)
        app.launcher_overlay.courseList.itemDoubleClicked.connect(app.launcher_handler.on_course_double_clicked)
        app.launcher_overlay.todoList.itemDoubleClicked.connect(app.launcher_handler.on_todo_double_clicked)

        # === TOGGLES ===
        app.history_toggle.stateChanged.connect(app.main_handler.on_history_toggle_clicked)

        # === SIDEBAR ===
        def navigate(page_id):
            if page_id == 'launch':
                app.stacked_widget.setCurrentWidget(mw)
                app.launcher_handler.show()
            elif page_id == 'main':
                app.stacked_widget.setCurrentWidget(mw)
                app.launcher_handler.hide()
            elif page_id == 'auto':
                app.automation_handler.open_top()
            elif page_id == 'sitting':
                app.sitting_handler.show()
        app.sidebar.navigate.connect(navigate)

        # === INITIAL STATE ===
        app.sitting_handler.load_current_login_info()
        app.sitting_handler.load_api_settings()
