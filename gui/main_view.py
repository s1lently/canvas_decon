"""Main View - Dashboard + Launcher (merged from handlers/main.py, handlers/launcher.py, core/mgrData.py, core/mgrDone.py)"""
import sys, os, json
from PyQt6.QtWidgets import QListWidgetItem, QStyledItemDelegate, QMessageBox
from PyQt6.QtCore import Qt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from gui.learn import format_course, format_todo, format_folder
from gui.widgets import TodoItemDelegate
from gui._internal.mgrCourseDetail import CourseDetailManager
from gui._internal.mgrAutoDetail import AutoDetailManager


class MainView:
    """Handles Main Dashboard + Launcher overlay"""

    def __init__(self, app):
        self.app = app
        self.mw = app.main_window
        self.lo = app.launcher_overlay

    def load_data(self):
        """Reload data from files"""
        self.app.dm.load_all()

    # === LAUNCHER ===
    def show_launcher(self):
        """Show launcher overlay"""
        self._populate_launcher()
        self.update_launcher_geometry()
        self.app._position_hud_corners()  # Position HUD corners
        self.lo.raise_()
        self.lo.show()

    def hide_launcher(self):
        """Hide launcher overlay"""
        self.lo.hide()

    def update_launcher_geometry(self):
        """Update launcher geometry to match main window"""
        self.lo.setGeometry(0, 0, self.mw.width(), self.mw.height())

    def _populate_launcher(self):
        """Populate launcher with TODOs and Courses"""
        self.lo.todoList.clear()
        self.lo.courseList.clear()

        for todo in self.app.dm.get('todos'):
            item = QListWidgetItem(f"{todo.get('course_name', '')} - {todo.get('name', '')}")
            item.setData(Qt.ItemDataRole.UserRole, self.app.dm.classify_todo(todo))
            item.setData(Qt.ItemDataRole.UserRole + 1, todo)
            self.lo.todoList.addItem(item)

        for course in self.app.dm.get('courses'):
            course_name = course.get('name', 'Unknown')
            # Try to extract course code and section from name
            # Example: "CMPSC 131, Section 005: Programming & Comp I" -> "CMPSC 131 • Section 005"
            details = ''
            display_name = course_name
            if ',' in course_name and ':' in course_name:
                parts = course_name.split(':')
                if len(parts) > 1:
                    details = parts[0].replace(',', ' •')
                    display_name = parts[1].strip()

            item = QListWidgetItem(display_name)
            if details:
                item.setData(Qt.ItemDataRole.UserRole, details)
            item.setData(Qt.ItemDataRole.UserRole + 1, course)  # Store full course object
            self.lo.courseList.addItem(item)

    def on_course_double_clicked(self, item):
        """Launcher: double-click course -> CourseDetail"""
        course = item.data(Qt.ItemDataRole.UserRole + 1)
        if course:
            self.app.course_detail_mgr = CourseDetailManager(
                course, self.app.dm.get('todos'), self.app.dm.get('history_todos'))
            self.app.course_view.populate_window()
            self.hide_launcher()
            self.app.stacked_widget.setCurrentWidget(self.app.course_detail_window)

    def on_todo_double_clicked(self, item):
        """Launcher: double-click todo -> AutoDetail"""
        todo = item.data(Qt.ItemDataRole.UserRole + 1)
        if todo and self.app.dm.classify_todo(todo).get('is_automatable'):
            self.app.auto_detail_mgr = AutoDetailManager(todo)
            self.app.detail_view.populate_window()
            self.app.stacked_widget.setCurrentWidget(self.app.auto_detail_window)
            self.hide_launcher()

    # === MAIN DASHBOARD ===
    def on_category_changed(self, index):
        """Category switch: 0=Courses, 1=TODOs, 2=Files"""
        il = self.mw.itemList
        il.clear()
        self.mw.courseDetailBtn.setVisible(index == 0)
        self.mw.filterWidget.setVisible(index == 1)  # Show filters only for TODOs

        if index == 0:  # Courses
            for c in self.app.dm.get('courses'):
                il.addItem(c.get('name', 'Unknown'))
            il.setItemDelegate(QStyledItemDelegate())

        elif index == 1:  # TODOs
            todos = self._get_todos()
            for todo in todos:
                item = QListWidgetItem(f"{todo.get('course_name', '')} - {todo.get('name', '')}")
                item.setData(Qt.ItemDataRole.UserRole, self.app.dm.classify_todo(todo))
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)

                redirect_url = todo.get('redirect_url', '')
                is_done = self.app.done_mgr.is_done(redirect_url)
                item.setCheckState(Qt.CheckState.Checked if is_done else Qt.CheckState.Unchecked)
                item.setForeground(Qt.GlobalColor.gray if is_done else Qt.GlobalColor.white)
                item.setData(Qt.ItemDataRole.UserRole + 1, todo)
                il.addItem(item)

            il.setItemDelegate(TodoItemDelegate(il, history_mode=self.app.history_mode))

        elif index == 2:  # Files
            il.addItems(self.app.dm.get('files'))
            il.setItemDelegate(QStyledItemDelegate())

    def _get_todos(self):
        """Get todos (history or current)"""
        if self.app.history_mode:
            try:
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'func'))
                from mgrHistory import load_history
                return load_history()
            except Exception:
                return []
        return self.app.dm.get('todos')

    def apply_filters(self):
        """Apply filters to TODO list"""
        if self.mw.categoryList.currentRow() != 1:
            return

        il = self.mw.itemList
        filters = [
            self.mw.filterHomework.isChecked(),
            self.mw.filterQuiz.isChecked(),
            self.mw.filterDiscussion.isChecked(),
            self.mw.filterAutomatable.isChecked()
        ]
        show_all = not any(filters)

        for i in range(il.count()):
            item = il.item(i)
            meta = item.data(Qt.ItemDataRole.UserRole)
            if meta:
                matches = [meta.get('is_homework'), meta.get('is_quiz'),
                          meta.get('is_discussion'), meta.get('is_automatable')]
                item.setHidden(not (show_all or any(f and v for f, v in zip(filters, matches))))

    def on_item_changed(self, index):
        """Item selection -> update detailView"""
        if index < 0:
            return

        ci = self.mw.categoryList.currentRow()
        if ci == 1 and self.app.history_mode:
            data = self._get_todos()
        else:
            data = self.app.dm.get(['courses', 'todos', 'files'][ci])

        if index < len(data):
            fmt = [format_course, format_todo, format_folder][ci]
            self.mw.detailView.setHtml(fmt(data[index]))

    def on_checkbox_changed(self, item):
        """Checkbox toggle -> update Done.txt"""
        todo = item.data(Qt.ItemDataRole.UserRole + 1)
        if not todo or not todo.get('redirect_url'):
            return

        is_checked = item.checkState() == Qt.CheckState.Checked
        if is_checked:
            self.app.done_mgr.mark_done(todo['redirect_url'])
        else:
            self.app.done_mgr.mark_undone(todo['redirect_url'])
        item.setForeground(Qt.GlobalColor.gray if is_checked else Qt.GlobalColor.white)

    def on_item_double_clicked(self, item):
        """Double-click: open CourseDetail or AutoDetail"""
        ci = self.mw.categoryList.currentRow()
        ii = self.mw.itemList.currentRow()

        if ci == 0 and ii >= 0:  # Courses
            courses = self.app.dm.get('courses')
            if ii < len(courses):
                self.app.course_detail_mgr = CourseDetailManager(
                    courses[ii], self.app.dm.get('todos'), self.app.dm.get('history_todos'))
                self.app.course_view.populate_window()
                self.app.stacked_widget.setCurrentWidget(self.app.course_detail_window)

        elif ci == 1:  # TODOs
            todo = item.data(Qt.ItemDataRole.UserRole + 1)
            if todo:
                self.app.auto_detail_mgr = AutoDetailManager(todo)
                self.app.detail_view.populate_window()
                self.app.stacked_widget.setCurrentWidget(self.app.auto_detail_window)

    def on_history_toggle(self, state):
        """Toggle history mode"""
        self.app.history_mode = (state == 2)
        if self.mw.categoryList.currentRow() == 1:
            self.on_category_changed(1)

    def on_open_folder_clicked(self):
        """Open folder for selected item"""
        ci = self.mw.categoryList.currentRow()
        ii = self.mw.itemList.currentRow()
        if ci < 0 or ii < 0:
            return

        path = None
        if ci == 1:  # TODO
            todos = self.app.dm.get('todos')
            if ii < len(todos):
                folder = todos[ii].get('assignment_details', {}).get('folder')
                path = os.path.join(config.TODO_DIR, folder) if folder else None
        elif ci == 2:  # Files
            files = self.app.dm.get('files')
            if ii < len(files):
                path = os.path.join(config.TODO_DIR, files[ii])

        if path and os.path.exists(path):
            self.app.open_folder(path)
