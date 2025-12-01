"""Auto View - Automation Window with 4 tabs (merged from handlers/automation.py)"""
import sys, os
from PyQt6.QtWidgets import QListWidgetItem, QStyledItemDelegate
from PyQt6.QtCore import Qt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from gui.learn import format_todo
from gui.widgets import TodoItemDelegate
from gui._internal.mgrAutoDetail import AutoDetailManager


class AutoView:
    """Handles Automation Window with 4 tabs"""

    TAB_PREFIXES = ['automatableOpen', 'automatableClose', 'automatable', 'allItems']

    def __init__(self, app):
        self.app = app
        self.aw = app.automation_window

    def open(self, selected_todo=None):
        """Open Automation window"""
        self.populate_window(selected_todo)
        self.app.stacked_widget.setCurrentWidget(self.aw)

    def populate_window(self, selected_todo=None):
        """Populate all 4 tabs"""
        todos = self.app.dm.get('todos')

        # Tab filters
        filters = [
            lambda t: self.app.dm.classify_todo(t).get('is_automatable') and self.app.dm.classify_todo(t).get('is_open'),
            lambda t: self.app.dm.classify_todo(t).get('is_automatable') and not self.app.dm.classify_todo(t).get('is_open'),
            lambda t: self.app.dm.classify_todo(t).get('is_automatable'),
            lambda t: True
        ]

        for i, prefix in enumerate(self.TAB_PREFIXES):
            cat_list = getattr(self.aw, f'{prefix}CategoryList')
            item_list = getattr(self.aw, f'{prefix}ItemList')
            detail_view = getattr(self.aw, f'{prefix}DetailView')

            cat_list.clear()
            item_list.clear()
            cat_list.addItems(['Quiz', 'Homework', 'Discussion'])

            filtered = [t for t in todos if filters[i](t)]
            for todo in filtered:
                item = QListWidgetItem(f"{todo.get('course_name', '')} - {todo.get('name', '')}")
                item.setData(Qt.ItemDataRole.UserRole, self.app.dm.classify_todo(todo))
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)

                redirect_url = todo.get('redirect_url', '')
                is_done = self.app.done_mgr.is_done(redirect_url)
                item.setCheckState(Qt.CheckState.Checked if is_done else Qt.CheckState.Unchecked)
                item.setForeground(Qt.GlobalColor.gray if is_done else Qt.GlobalColor.white)
                item.setData(Qt.ItemDataRole.UserRole + 1, todo)
                item_list.addItem(item)

            item_list.setItemDelegate(TodoItemDelegate(item_list))

            # Select matching item
            if selected_todo and filters[i](selected_todo):
                for j in range(item_list.count()):
                    if item_list.item(j).data(Qt.ItemDataRole.UserRole + 1) == selected_todo:
                        item_list.setCurrentRow(j)
                        detail_view.setHtml(format_todo(selected_todo))
                        break

    def on_category_changed(self, index, tab_index=3):
        """Category filter within tab"""
        prefix = self.TAB_PREFIXES[tab_index]
        item_list = getattr(self.aw, f'{prefix}ItemList')

        category_keys = ['is_quiz', 'is_homework', 'is_discussion']
        if index < len(category_keys):
            key = category_keys[index]
            for i in range(item_list.count()):
                item = item_list.item(i)
                meta = item.data(Qt.ItemDataRole.UserRole)
                if meta:
                    item.setHidden(not meta.get(key))

    def on_item_changed(self, index, tab_index=3):
        """Item selection -> update detail"""
        prefix = self.TAB_PREFIXES[tab_index]
        item_list = getattr(self.aw, f'{prefix}ItemList')
        detail_view = getattr(self.aw, f'{prefix}DetailView')

        if 0 <= index < item_list.count():
            todo = item_list.item(index).data(Qt.ItemDataRole.UserRole + 1)
            if todo:
                detail_view.setHtml(format_todo(todo))

    def on_checkbox_changed(self, item):
        """Checkbox toggle"""
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
        """Double-click -> AutoDetail"""
        todo = item.data(Qt.ItemDataRole.UserRole + 1)
        if todo:
            self.app.auto_detail_mgr = AutoDetailManager(todo)
            self.app.detail_view.populate_window()
            self.app.stacked_widget.setCurrentWidget(self.app.auto_detail_window)
