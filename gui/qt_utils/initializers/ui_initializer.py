"""UI Initializer - Handles all UI initialization"""
import sys, os
from PyQt6.QtWidgets import QStackedWidget, QLabel, QWidget, QHBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.uic import loadUi
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from gui.widgets.wgtIOSToggle import IOSToggle
from gui.widgets.wgtSidebar import GlobalSidebar
from gui.widgets import rdrDelegates as delegates


class UIInitializer:
    """Handles UI initialization for CanvasApp"""

    @staticmethod
    def init_qt(app):
        """Initialize Qt UI: Load 6 windows + create widgets"""
        # Create stacked widget (full width, no sidebar in layout)
        app.stacked_widget = QStackedWidget()
        app.setCentralWidget(app.stacked_widget)

        # Load UI files
        ui_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'ui')
        app.main_window = loadUi(os.path.join(ui_dir, 'main.ui'))
        app.sitting_window = loadUi(os.path.join(ui_dir, 'sitting.ui'))
        app.automation_window = loadUi(os.path.join(ui_dir, 'automation.ui'))
        app.course_detail_window = loadUi(os.path.join(ui_dir, 'course_detail.ui'))
        app.auto_detail_window = loadUi(os.path.join(ui_dir, 'autoDetail.ui'))
        app.launcher_overlay = loadUi(os.path.join(ui_dir, 'launcher.ui'))

        # Add windows to stacked widget
        for w in [app.main_window, app.sitting_window, app.automation_window,
                  app.course_detail_window, app.auto_detail_window]:
            app.stacked_widget.addWidget(w)

        # Status widgets
        app.status_widgets = {
            k: getattr(app.main_window, f'{k}Indicator')
            for k in ['account', 'cookie', 'todos', 'network', 'courses']
        }

        # Enable external links in detail views
        for dv in [app.main_window.detailView,
                   app.automation_window.automatableOpenDetailView,
                   app.automation_window.automatableCloseDetailView,
                   app.automation_window.automatableDetailView,
                   app.automation_window.allItemsDetailView,
                   app.course_detail_window.detailView,
                   app.auto_detail_window.assignmentDetailView,
                   app.auto_detail_window.refFilesView,
                   app.auto_detail_window.aiPreviewView]:
            dv.setOpenExternalLinks(True)

        # Create IOSToggle widgets
        app.ios_toggle_main = IOSToggle(width=50, height=24)
        app.main_window.categoryColumnLayout.addWidget(app.ios_toggle_main)

        app.ios_toggles_auto = [IOSToggle(width=50, height=24) for _ in range(4)]
        for toggle, layout in zip(app.ios_toggles_auto, [
            'automatableOpenCategoryLayout', 'automatableCloseCategoryLayout',
            'automatableCategoryLayout', 'allItemsCategoryLayout'
        ]):
            getattr(app.automation_window, layout).addWidget(toggle)

        # Removed: ios_toggle_course_detail (console toggle moved to sidebar)

        # Enable drag-and-drop for course detail
        app.course_detail_window.itemList.setAcceptDrops(True)
        app.course_detail_window.itemList.setDragEnabled(False)

        # History toggle
        app.history_toggle = IOSToggle(width=50, height=24)
        hist_label = QLabel("History")
        hist_label.setStyleSheet("font-size: 11px; color: #aaa;")
        hist_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        app.main_window.historyToggleLayout.addWidget(hist_label)
        app.main_window.historyToggleLayout.addWidget(app.history_toggle)
        app.history_toggle.setChecked(False)

        # Thinking toggle (for AutoDetail)
        app.thinking_toggle = IOSToggle(width=50, height=24)
        app.thinking_toggle.setChecked(True)
        placeholder = app.auto_detail_window.thinkingTogglePlaceholder
        layout = placeholder.parent().layout()
        idx = layout.indexOf(placeholder)
        layout.removeWidget(placeholder)
        placeholder.deleteLater()
        layout.insertWidget(idx, app.thinking_toggle)

        # Manual 2FA mode toggle (for Sitting)
        app.manual_mode_toggle = IOSToggle(width=50, height=24)
        app.manual_mode_toggle.setChecked(False)
        placeholder = app.sitting_window.manualModeTogglePlaceholder
        layout = placeholder.parent().layout()
        idx = layout.indexOf(placeholder)
        layout.removeWidget(placeholder)
        placeholder.deleteLater()
        layout.insertWidget(idx, app.manual_mode_toggle)

        # Hide old action buttons (replaced by sidebar)
        old_buttons = ['getCookieBtn', 'getTodoBtn', 'getCourseBtn', 'gSyllAllBtn',
                       'cleanBtn', 'automationTopBtn', 'sittingBtn']
        for btn_name in old_buttons:
            if hasattr(app.main_window, btn_name):
                getattr(app.main_window, btn_name).setVisible(False)

        # Set current widget
        app.stacked_widget.setCurrentWidget(app.main_window)

        # Init launcher overlay
        UIInitializer._init_launcher_overlay(app)

        # Init floating sidebar
        UIInitializer._init_sidebar(app)

    @staticmethod
    def _init_launcher_overlay(app):
        """Initialize launcher overlay UI"""
        from PyQt6.QtCore import Qt as QtCore

        app.launcher_overlay.setParent(app.main_window)
        app.launcher_overlay.setAttribute(QtCore.WidgetAttribute.WA_StyledBackground, True)
        app.launcher_overlay.todoList.setItemDelegate(
            delegates.TodoItemDelegate(app.launcher_overlay.todoList)
        )

        # Install event filters
        app.main_window.installEventFilter(app)
        app.launcher_overlay.todoList.installEventFilter(app)
        app.launcher_overlay.courseList.installEventFilter(app)

    @staticmethod
    def _init_sidebar(app):
        """Initialize floating sidebar (overlays on top, doesn't occupy space)"""
        from PyQt6.QtCore import Qt as QtCore

        # Create floating sidebar
        app.sidebar = GlobalSidebar(app, parent=app)
        app.sidebar.setAttribute(QtCore.WidgetAttribute.WA_StyledBackground, True)

        # Position at top-right corner
        app.sidebar.raise_()  # Bring to front
        UIInitializer._position_sidebar(app)

    @staticmethod
    def _position_sidebar(app):
        """Position sidebar at right edge"""
        # Get window size
        window_width = app.width()
        window_height = app.height()

        # Get current sidebar width (might be animating)
        current_width = app.sidebar.width()
        if current_width == 0:  # First time positioning
            current_width = app.sidebar.collapsed_width

        # Position at top-right, don't force width (let animation control it)
        app.sidebar.move(window_width - current_width, 0)
        app.sidebar.setFixedHeight(window_height)

    @staticmethod
    def init_data_viewer(app):
        """Initialize data viewer: Load data + show launcher"""
        mw = app.main_window

        # Setup category list
        mw.categoryList.addItems(["Courses", "TODOs", "Files"])

        # Hide course detail button initially
        mw.courseDetailBtn.setVisible(False)

        # Load data
        app.dm.load_all()

        # Archive past todos
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'func'))
            from mgrHistory import archive_past_todos
            archive_past_todos()
        except:
            pass

        # Show launcher
        app.launcher_handler.show()
