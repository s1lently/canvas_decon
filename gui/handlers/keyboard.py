"""Keyboard Handler - Manages keyboard events and WASD navigation (4 methods)"""
import sys, os, webbrowser
from PyQt6.QtWidgets import QListWidget
from PyQt6.QtCore import QEvent, Qt
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
import config
from gui.base_handler import BaseHandler
from gui.details.mgrCourseDetail import CourseDetailManager


class KeyboardHandler(BaseHandler):
    """Handles keyboard events and navigation"""

    def install_list_event_filters(self):
        """Install event filters on all list widgets for keyboard navigation"""
        for lst in [self.main_window.categoryList, self.main_window.itemList,
                    self.automation_window.automatableOpenCategoryList, self.automation_window.automatableOpenItemList,
                    self.automation_window.automatableCloseCategoryList, self.automation_window.automatableCloseItemList,
                    self.automation_window.automatableCategoryList, self.automation_window.automatableItemList,
                    self.automation_window.allItemsCategoryList, self.automation_window.allItemsItemList,
                    self.course_detail_window.categoryList, self.course_detail_window.itemList]:
            lst.installEventFilter(self.app)

    def handle_event(self, obj, event):
        """Main event filter handler (eventFilter)"""
        if obj == self.main_window and event.type() == QEvent.Type.Resize:
            self.app.launcher_handler.update_geometry()
            return False
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            modifiers = event.modifiers()
            current_widget = self.stacked_widget.currentWidget()
            if self.launcher_overlay.isVisible() and isinstance(obj, QListWidget):
                if key in [Qt.Key.Key_W, Qt.Key.Key_A, Qt.Key.Key_S, Qt.Key.Key_D]:
                    self.handle_launcher_wasd(key, obj)
                    return True
                elif key == Qt.Key.Key_Space:
                    item = obj.currentItem()
                    if item:
                        if obj == self.launcher_overlay.courseList:
                            self.app.launcher_handler.on_course_double_clicked(item)
                        elif obj == self.launcher_overlay.todoList:
                            self.app.launcher_handler.on_todo_double_clicked(item)
                        return True
                return False
            if key in [Qt.Key.Key_W, Qt.Key.Key_A, Qt.Key.Key_S, Qt.Key.Key_D] and isinstance(obj, QListWidget):
                self.handle_wasd_navigation(key, current_widget)
                return True
            if key == Qt.Key.Key_Space:
                if current_widget == self.main_window and self.main_window.categoryList.currentRow() == 0:
                    ii = self.main_window.itemList.currentRow()
                    if ii >= 0:
                        courses = self.dm.get('courses')
                        if ii < len(courses):
                            self.app.course_detail_mgr = CourseDetailManager(courses[ii], self.dm.get('todos'), self.dm.get('history_todos'))
                            self.app.course_detail_handler.populate_window()
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
                        self.app._open_folder(folder)
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
                    from gui.details.mgrAutoDetail import AutoDetailManager
                    meta = self.dm.classify_todo(todo)
                    if meta.get('is_automatable'):
                        self.app.auto_detail_mgr = AutoDetailManager(todo)
                        self.app.auto_detail_handler.populate_window()
                        self.stacked_widget.setCurrentWidget(self.auto_detail_window)
                        return True
            if current_widget == self.main_window and not (modifiers & ~Qt.KeyboardModifier.ShiftModifier):
                if key == Qt.Key.Key_A and (modifiers & Qt.KeyboardModifier.ShiftModifier):
                    self.app.automation_handler.open_top()
                    return True
                elif key == Qt.Key.Key_C and (modifiers & Qt.KeyboardModifier.ShiftModifier):
                    self.app._show_clean_dialog()
                    return True
                elif key == Qt.Key.Key_C and not (modifiers & Qt.KeyboardModifier.ShiftModifier):
                    self.main_window.categoryList.setCurrentRow(0)
                    self.main_window.categoryList.setFocus()
                    if self.main_window.itemList.count() > 0:
                        self.main_window.itemList.setCurrentRow(0)
                    return True
                elif key == Qt.Key.Key_T:
                    self.main_window.categoryList.setCurrentRow(1)
                    self.main_window.categoryList.setFocus()
                    if self.main_window.itemList.count() > 0:
                        self.main_window.itemList.setCurrentRow(0)
                    return True
                elif key == Qt.Key.Key_F:
                    self.main_window.categoryList.setCurrentRow(2)
                    self.main_window.categoryList.setFocus()
                    if self.main_window.itemList.count() > 0:
                        self.main_window.itemList.setCurrentRow(0)
                    return True
        return False

    def handle_launcher_wasd(self, key, obj):
        """Handle WASD navigation for launcher overlay"""
        lists = [self.launcher_overlay.todoList, self.launcher_overlay.courseList]
        current_idx = 0 if obj == lists[0] else 1 if obj == lists[1] else -1
        if current_idx == -1:
            return
        if key == Qt.Key.Key_W:
            row = obj.currentRow()
            if row > 0:
                obj.setCurrentRow(row - 1)
        elif key == Qt.Key.Key_S:
            row = obj.currentRow()
            if row < obj.count() - 1:
                obj.setCurrentRow(row + 1)
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

    def handle_wasd_navigation(self, key, current_widget):
        """Handle WASD navigation for main windows"""
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
            if lists[0]:
                lists[0].setFocus()
            return
        idx, current_list = focused_list
        if key == Qt.Key.Key_W:
            current_row = current_list.currentRow()
            if current_row > 0:
                current_list.setCurrentRow(current_row - 1)
        elif key == Qt.Key.Key_S:
            current_row = current_list.currentRow()
            if current_row < current_list.count() - 1:
                current_list.setCurrentRow(current_row + 1)
        elif key == Qt.Key.Key_A:
            if idx > 0 and lists[idx - 1]:
                lists[idx - 1].setFocus()
                if lists[idx - 1].count() > 0:
                    lists[idx - 1].setCurrentRow(0)
        elif key == Qt.Key.Key_D:
            if idx < len(lists) - 1 and lists[idx + 1]:
                lists[idx + 1].setFocus()
                if lists[idx + 1].count() > 0:
                    lists[idx + 1].setCurrentRow(0)
