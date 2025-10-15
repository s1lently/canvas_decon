"""Automation Window Handler - Manages Automation Window (7 methods)"""
import sys, os
from PyQt6.QtWidgets import QListWidgetItem, QStyledItemDelegate
from PyQt6.QtCore import Qt
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from gui.qt_utils.base_handler import BaseHandler
from gui import utilFormatters as formatters
from gui import rdrDelegates as delegates
from gui.mgrAutoDetail import AutoDetailManager


class AutomationWindowHandler(BaseHandler):
    """Handles Automation Window operations"""

    def open(self, selected_todo):
        """Open Automation window with selected TODO"""
        self.populate_window(selected_todo)
        self.stacked_widget.setCurrentWidget(self.automation_window)

    def open_top(self):
        """Open Automation window without selection"""
        self.populate_window(None)
        self.stacked_widget.setCurrentWidget(self.automation_window)

    def populate_window(self, selected_todo=None):
        """Populate 4 tabs in Automation window"""
        aw = self.automation_window
        todos = self.dm.get('todos')

        # Define 4 tabs
        tabs = [
            ('automatableOpen', lambda t: self.dm.classify_todo(t).get('is_automatable') and self.dm.classify_todo(t).get('is_open')),
            ('automatableClose', lambda t: self.dm.classify_todo(t).get('is_automatable') and not self.dm.classify_todo(t).get('is_open')),
            ('automatable', lambda t: self.dm.classify_todo(t).get('is_automatable')),
            ('allItems', lambda t: True)
        ]

        # Populate each tab
        for tab_prefix, filter_func in tabs:
            category_list = getattr(aw, f'{tab_prefix}CategoryList')
            item_list = getattr(aw, f'{tab_prefix}ItemList')
            detail_view = getattr(aw, f'{tab_prefix}DetailView')

            category_list.clear()
            item_list.clear()

            # Add categories
            category_list.addItems(['Quiz', 'Homework', 'Discussion'])

            # Populate items
            filtered_todos = [t for t in todos if filter_func(t)]
            for todo in filtered_todos:
                item = QListWidgetItem(f"{todo.get('course_name', '')} - {todo.get('name', '')}")
                item.setData(Qt.ItemDataRole.UserRole, self.dm.classify_todo(todo))
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)

                # Check done status
                redirect_url = todo.get('redirect_url', '')
                is_done = self.done_mgr.is_done(redirect_url)
                item.setCheckState(Qt.CheckState.Checked if is_done else Qt.CheckState.Unchecked)
                item.setForeground(Qt.GlobalColor.gray if is_done else Qt.GlobalColor.white)
                item.setData(Qt.ItemDataRole.UserRole + 1, todo)
                item_list.addItem(item)

            # Set delegate
            item_list.setItemDelegate(delegates.TodoItemDelegate(item_list))

            # Select matching item if provided
            if selected_todo and filter_func(selected_todo):
                for i in range(item_list.count()):
                    item = item_list.item(i)
                    if item.data(Qt.ItemDataRole.UserRole + 1) == selected_todo:
                        item_list.setCurrentRow(i)
                        detail_view.setHtml(formatters.format_todo(selected_todo))
                        break

    def on_category_changed(self, index, tab_index=3):
        """Handle category change in Automation window"""
        tab_prefixes = ['automatableOpen', 'automatableClose', 'automatable', 'allItems']
        tab_prefix = tab_prefixes[tab_index]

        item_list = getattr(self.automation_window, f'{tab_prefix}ItemList')
        todos = self.dm.get('todos')

        # Filter by category
        category_map = ['quiz', 'homework', 'discussion']
        if index < len(category_map):
            keyword = category_map[index]
            for i in range(item_list.count()):
                item = item_list.item(i)
                meta = item.data(Qt.ItemDataRole.UserRole)
                if meta:
                    item.setHidden(not meta.get(f'is_{keyword}'))

    def on_item_changed(self, index, tab_index=3):
        """Handle item selection in Automation window"""
        tab_prefixes = ['automatableOpen', 'automatableClose', 'automatable', 'allItems']
        tab_prefix = tab_prefixes[tab_index]

        item_list = getattr(self.automation_window, f'{tab_prefix}ItemList')
        detail_view = getattr(self.automation_window, f'{tab_prefix}DetailView')

        if index >= 0 and index < item_list.count():
            todo = item_list.item(index).data(Qt.ItemDataRole.UserRole + 1)
            if todo:
                detail_view.setHtml(formatters.format_todo(todo))

    def on_checkbox_changed(self, item):
        """Handle checkbox change in Automation window"""
        todo = item.data(Qt.ItemDataRole.UserRole + 1)
        if not todo or not todo.get('redirect_url'):
            return

        is_checked = (item.checkState() == Qt.CheckState.Checked)

        # Mark done/undone
        if is_checked:
            self.done_mgr.mark_done(todo['redirect_url'])
        else:
            self.done_mgr.mark_undone(todo['redirect_url'])

        # Update color
        item.setForeground(Qt.GlobalColor.gray if is_checked else Qt.GlobalColor.white)

    def on_item_double_clicked(self, item):
        """Handle double-click -> open AutoDetail"""
        todo = item.data(Qt.ItemDataRole.UserRole + 1)
        if todo:
            self.app.auto_detail_mgr = AutoDetailManager(todo)
            self.app.auto_detail_handler.populate_window()
            self.stacked_widget.setCurrentWidget(self.auto_detail_window)

    def close_tab(self, index):
        """Close console tab in Automation window"""
        if index > 0:
            self.app.main_handler.stop_task_for_tab(self.automation_window.consoleTabWidget, index)
            self.automation_window.consoleTabWidget.removeTab(index)
