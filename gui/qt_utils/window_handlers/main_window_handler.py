"""Main Window Handler - Manages Main Dashboard (12 methods)"""
import sys, os
from PyQt6.QtWidgets import QListWidgetItem, QStyledItemDelegate, QMessageBox
from PyQt6.QtCore import Qt
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import config
from gui.qt_utils.base_handler import BaseHandler
from gui import utilFormatters as formatters
from gui import rdrDelegates as delegates
from gui.mgrCourseDetail import CourseDetailManager
from gui.mgrAutoDetail import AutoDetailManager


class MainWindowHandler(BaseHandler):
    """Handles Main Window operations"""

    def load_data(self):
        """Reload all data from JSON files"""
        self.dm.load_all()
        self.done_mgr.load()

    def on_category_changed(self, index):
        """Handle category switch: 0=Courses, 1=TODOs, 2=Files"""
        il = self.main_window.itemList
        il.clear()

        # Show/hide CourseDetail button
        self.main_window.courseDetailBtn.setVisible(index == 0)

        if index == 0:  # Courses
            for c in self.dm.get('courses'):
                il.addItem(c.get('name', 'Unknown'))
            il.setItemDelegate(QStyledItemDelegate())

        elif index == 1:  # TODOs
            # Load history or current todos
            if self.app.history_mode:
                try:
                    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'func'))
                    from history_manager import load_history
                    todos = load_history()
                except:
                    todos = []
            else:
                todos = self.dm.get('todos')

            # Populate TODO list
            for todo in todos:
                item = QListWidgetItem(f"{todo.get('course_name', '')} - {todo.get('name', '')}")
                item.setData(Qt.ItemDataRole.UserRole, self.dm.classify_todo(todo))
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)

                # Check done status
                redirect_url = todo.get('redirect_url', '')
                is_done = self.done_mgr.is_done(redirect_url)
                item.setCheckState(Qt.CheckState.Checked if is_done else Qt.CheckState.Unchecked)
                item.setForeground(Qt.GlobalColor.gray if is_done else Qt.GlobalColor.white)
                item.setData(Qt.ItemDataRole.UserRole + 1, todo)
                il.addItem(item)

            il.setItemDelegate(delegates.TodoItemDelegate(il, history_mode=self.app.history_mode))

        elif index == 2:  # Files
            il.addItems(self.dm.get('files'))
            il.setItemDelegate(QStyledItemDelegate())

    def apply_filters(self):
        """Apply filters to TODO list"""
        if self.main_window.categoryList.currentRow() != 1:
            return

        il = self.main_window.itemList
        mw = self.main_window

        # Get filter states
        filters = [
            mw.filterHomework.isChecked(),
            mw.filterQuiz.isChecked(),
            mw.filterDiscussion.isChecked(),
            mw.filterAutomatable.isChecked()
        ]
        show_all = not any(filters)

        # Apply filters
        for i in range(il.count()):
            item = il.item(i)
            meta = item.data(Qt.ItemDataRole.UserRole)
            if meta:
                matches = [
                    meta.get('is_homework'),
                    meta.get('is_quiz'),
                    meta.get('is_discussion'),
                    meta.get('is_automatable')
                ]
                item.setHidden(not (show_all or any(f and v for f, v in zip(filters, matches))))

    def on_item_changed(self, index):
        """Handle item selection -> update detailView"""
        if index < 0:
            return

        ci = self.main_window.categoryList.currentRow()

        # Load data
        if ci == 1 and self.app.history_mode:
            try:
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'func'))
                from history_manager import load_history
                data = load_history()
            except:
                data = []
        else:
            data = self.dm.get(['courses', 'todos', 'files'][ci])

        # Update detailView
        if index < len(data):
            formatters_map = [formatters.format_course, formatters.format_todo, formatters.format_folder]
            self.main_window.detailView.setHtml(formatters_map[ci](data[index]))

    def update_checkbox(self, item, is_checked):
        """Update checkbox state and save to Done.txt"""
        todo = item.data(Qt.ItemDataRole.UserRole + 1 if hasattr(item.data(Qt.ItemDataRole.UserRole + 1), 'get') else Qt.ItemDataRole.UserRole)
        if not todo or not todo.get('redirect_url'):
            return

        # Mark done/undone
        if is_checked:
            self.done_mgr.mark_done(todo['redirect_url'])
        else:
            self.done_mgr.mark_undone(todo['redirect_url'])

        # Update color
        item.setForeground(Qt.GlobalColor.gray if is_checked else Qt.GlobalColor.white)

    def on_checkbox_changed(self, item):
        """Handle checkbox click in Main window"""
        self.update_checkbox(item, item.checkState() == Qt.CheckState.Checked)

    def on_item_double_clicked(self, item):
        """Handle double-click: Open CourseDetail or AutoDetail"""
        ci = self.main_window.categoryList.currentRow()

        if ci == 0:  # Courses
            ii = self.main_window.itemList.currentRow()
            if ii >= 0:
                courses = self.dm.get('courses')
                if ii < len(courses):
                    self.app.course_detail_mgr = CourseDetailManager(
                        courses[ii],
                        self.dm.get('todos'),
                        self.dm.get('history_todos')
                    )
                    self.app.course_detail_handler.populate_window()
                    self.stacked_widget.setCurrentWidget(self.course_detail_window)

        elif ci == 1:  # TODOs
            todo = item.data(Qt.ItemDataRole.UserRole + 1)
            if todo:
                meta = self.dm.classify_todo(todo)
                if meta.get('is_automatable'):
                    self.app.auto_detail_mgr = AutoDetailManager(todo)
                    self.app.auto_detail_handler.populate_window()
                    self.stacked_widget.setCurrentWidget(self.auto_detail_window)

    def on_toggle_console_clicked(self, state):
        """Toggle console visibility across all windows"""
        visible = (state == Qt.CheckState.Checked.value)
        self.main_window.consoleTabWidget.setVisible(visible)
        self.automation_window.consoleTabWidget.setVisible(visible)

        # Sync all toggle states
        for toggle in [self.app.ios_toggle_main, self.app.ios_toggle_course_detail] + self.app.ios_toggles_auto:
            toggle.blockSignals(True)
            toggle.setChecked(visible)
            toggle.blockSignals(False)

    def on_history_toggle_clicked(self, state):
        """Toggle history mode"""
        self.app.history_mode = (state == Qt.CheckState.Checked.value)
        if self.main_window.categoryList.currentRow() == 1:
            self.on_category_changed(1)

    def on_open_folder_clicked(self):
        """Open folder for selected TODO or File"""
        ci = self.main_window.categoryList.currentRow()
        ii = self.main_window.itemList.currentRow()

        if ci < 0 or ii < 0:
            return

        fp = None

        if ci == 1 and ii < len(self.dm.get('todos')):  # TODO
            fn = self.dm.get('todos')[ii].get('assignment_details', {}).get('folder')
            fp = os.path.join(config.TODO_DIR, fn) if fn else None

        elif ci == 2 and ii < len(self.dm.get('files')):  # File
            fp = os.path.join(config.TODO_DIR, self.dm.get('files')[ii])

        if fp and os.path.exists(fp):
            self.open_folder(fp)

    def open_to_automation(self):
        """Open Automation window with selected TODO"""
        ci = self.main_window.categoryList.currentRow()
        ii = self.main_window.itemList.currentRow()

        if ci != 1:
            return QMessageBox.warning(self.app, "Invalid", "Select a TODO first.")

        if ii < 0:
            return QMessageBox.warning(self.app, "No Selection", "Select a TODO first.")

        if not (self.main_window.itemList.item(ii).data(Qt.ItemDataRole.UserRole) or {}).get('is_automatable'):
            return QMessageBox.warning(self.app, "Not Automatable", "Only online submission types can be automated.")

        # Switch to automation window
        selected_todo = self.dm.get('todos')[ii]
        self.app.automation_handler.populate_window(selected_todo)
        self.stacked_widget.setCurrentWidget(self.automation_window)

    def close_tab(self, index):
        """Close console tab"""
        if index > 0:
            self.stop_task_for_tab(self.main_window.consoleTabWidget, index)
            self.main_window.consoleTabWidget.removeTab(index)

    def stop_task_for_tab(self, tab_widget, index):
        """Stop any task associated with the given tab"""
        from gui.mgrTask import get_task_manager
        from PyQt6.QtWidgets import QTextEdit

        # Get the console widget from the tab
        tab = tab_widget.widget(index)
        if not tab:
            return

        # Find the console widget
        console_widget = tab.findChild(QTextEdit)
        if not console_widget:
            return

        # Find any task with this console
        task_manager = get_task_manager()
        tasks = task_manager.get_all_tasks()

        for task in tasks:
            # Check if this task's console matches
            if task.get('console') and hasattr(task['console'], 'console'):
                # It's a ThreadSafeConsole wrapper
                if task['console'].console == console_widget:
                    task_manager.stop_task(task['id'])
                    print(f"[INFO] Stopped task '{task['name']}' (tab closed)")
                    break

    def open_folder(self, path):
        """Open folder cross-platform"""
        import subprocess
        import platform

        if path and os.path.exists(path):
            system_commands = {
                'Windows': lambda: os.startfile(path),
                'Darwin': lambda: subprocess.run(['open', path]),
                'Linux': lambda: subprocess.run(['xdg-open', path])
            }
            system_commands.get(platform.system(), lambda: None)()
