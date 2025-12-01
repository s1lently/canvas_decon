"""Launcher Handler - Manages Launcher overlay (8 methods)"""
import sys, os
from PyQt6.QtWidgets import QListWidgetItem
from PyQt6.QtCore import Qt
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from gui.base_handler import BaseHandler
from gui.details.mgrCourseDetail import CourseDetailManager
from gui.details.mgrAutoDetail import AutoDetailManager
from gui.widgets import rdrDelegates as delegates


class LauncherHandler(BaseHandler):
    """Handles Launcher overlay operations"""

    def init_ui(self):
        """Initialize launcher overlay UI without data (defer data population)"""
        from PyQt6.QtCore import Qt as QtCore
        self.launcher_overlay.setParent(self.main_window)
        self.launcher_overlay.setAttribute(QtCore.WidgetAttribute.WA_StyledBackground, True)
        self.launcher_overlay.dashboardBtn.clicked.connect(self.hide)
        self.launcher_overlay.automationBtn.clicked.connect(lambda: (self.hide(), self.app.automation_handler.open_top()))
        self.launcher_overlay.courseList.itemDoubleClicked.connect(self.on_course_double_clicked)
        self.launcher_overlay.todoList.itemDoubleClicked.connect(self.on_todo_double_clicked)
        self.launcher_overlay.todoList.setItemDelegate(delegates.TodoItemDelegate(self.launcher_overlay.todoList))
        self.main_window.installEventFilter(self.app)
        self.launcher_overlay.todoList.installEventFilter(self.app)
        self.launcher_overlay.courseList.installEventFilter(self.app)

    def show(self):
        """Show launcher overlay with updated data and geometry"""
        self.populate_data()
        self.update_geometry()
        self.launcher_overlay.raise_()
        self.launcher_overlay.show()

    def hide(self):
        """Hide the launcher overlay"""
        self.launcher_overlay.hide()

    def update_geometry(self):
        """Update launcher overlay geometry to match main window size"""
        if hasattr(self.app, 'launcher_overlay') and self.launcher_overlay:
            self.launcher_overlay.setGeometry(0, 0, self.main_window.width(), self.main_window.height())

    def populate_data(self):
        """Populate launcher overlay with TODO and Course data"""
        self.launcher_overlay.todoList.clear()
        self.launcher_overlay.courseList.clear()

        # Populate TODOs
        for todo in self.dm.get('todos'):
            item = QListWidgetItem(f"{todo.get('course_name', '')} - {todo.get('name', '')}")
            item.setData(Qt.ItemDataRole.UserRole, self.dm.classify_todo(todo))
            item.setData(Qt.ItemDataRole.UserRole + 1, todo)
            self.launcher_overlay.todoList.addItem(item)

        # Populate Courses
        for course in self.dm.get('courses'):
            item = QListWidgetItem(course.get('name', 'Unknown'))
            self.launcher_overlay.courseList.addItem(item)

    def on_course_double_clicked(self, item):
        """Handle double-click on launcher course list -> open CourseDetail"""
        course_name = item.text()
        courses = self.dm.get('courses')

        for course in courses:
            if course.get('name') == course_name:
                self.app.course_detail_mgr = CourseDetailManager(
                    course,
                    self.dm.get('todos'),
                    self.dm.get('history_todos')
                )
                self.app.course_detail_handler.populate_window()
                self.hide()
                self.stacked_widget.setCurrentWidget(self.course_detail_window)
                break

    def on_todo_double_clicked(self, item):
        """Handle double-click on launcher todo list -> open AutoDetail"""
        todo = item.data(Qt.ItemDataRole.UserRole + 1)
        if todo:
            classification = self.dm.classify_todo(todo)
            if classification.get('is_automatable'):
                self.app.auto_detail_mgr = AutoDetailManager(todo)
                self.app.auto_detail_handler.populate_window()
                self.stacked_widget.setCurrentWidget(self.auto_detail_window)
                self.hide()
