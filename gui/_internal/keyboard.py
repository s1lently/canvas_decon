"""Keyboard Handler - WASD navigation and shortcuts"""
import sys, os, webbrowser
from PyQt6.QtWidgets import QListWidget
from PyQt6.QtCore import QEvent, Qt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import config
from gui._internal.mgrCourseDetail import CourseDetailManager
from gui._internal.mgrAutoDetail import AutoDetailManager


class KeyboardHandler:
    """Handles keyboard events and navigation"""

    def __init__(self, app):
        self.app = app

    @property
    def mw(self):
        return self.app.main_window

    @property
    def aw(self):
        return self.app.automation_window

    @property
    def cdw(self):
        return self.app.course_detail_window

    @property
    def lo(self):
        return self.app.launcher_overlay

    def install_list_event_filters(self):
        """Install event filters on all list widgets"""
        lists = [
            self.mw.categoryList, self.mw.itemList,
            self.aw.automatableOpenCategoryList, self.aw.automatableOpenItemList,
            self.aw.automatableCloseCategoryList, self.aw.automatableCloseItemList,
            self.aw.automatableCategoryList, self.aw.automatableItemList,
            self.aw.allItemsCategoryList, self.aw.allItemsItemList,
            self.cdw.categoryList, self.cdw.itemList
        ]
        for lst in lists:
            lst.installEventFilter(self.app)

    def handle_event(self, obj, event):
        """Main event filter handler"""
        if obj == self.mw and event.type() == QEvent.Type.Resize:
            self.app.main_view.update_launcher_geometry()
            return False

        if event.type() != QEvent.Type.KeyPress:
            return False

        key = event.key()
        modifiers = event.modifiers()
        current = self.app.stacked_widget.currentWidget()

        # Launcher WASD
        if self.lo.isVisible() and isinstance(obj, QListWidget):
            if key in [Qt.Key.Key_W, Qt.Key.Key_A, Qt.Key.Key_S, Qt.Key.Key_D]:
                self._handle_launcher_wasd(key, obj)
                return True
            elif key == Qt.Key.Key_Space:
                item = obj.currentItem()
                if item:
                    if obj == self.lo.courseList:
                        self.app.main_view.on_course_double_clicked(item)
                    elif obj == self.lo.todoList:
                        self.app.main_view.on_todo_double_clicked(item)
                    return True
            return False

        # WASD navigation
        if key in [Qt.Key.Key_W, Qt.Key.Key_A, Qt.Key.Key_S, Qt.Key.Key_D] and isinstance(obj, QListWidget):
            self._handle_wasd(key, current)
            return True

        # Space - open course detail
        if key == Qt.Key.Key_Space:
            if current == self.mw and self.mw.categoryList.currentRow() == 0:
                ii = self.mw.itemList.currentRow()
                if ii >= 0:
                    courses = self.app.dm.get('courses')
                    if ii < len(courses):
                        self.app.course_detail_mgr = CourseDetailManager(courses[ii], self.app.dm.get('todos'), self.app.dm.get('history_todos'))
                        self.app.course_view.populate_window()
                        self.app.stacked_widget.setCurrentWidget(self.cdw)
                        return True
            elif current == self.cdw:
                ii = self.cdw.itemList.currentRow()
                if ii >= 0:
                    item_data = self.cdw.itemList.item(ii).data(Qt.ItemDataRole.UserRole + 1)
                    if item_data and item_data.get('type') == 'tab':
                        url = item_data.get('data', {}).get('url')
                        if url:
                            webbrowser.open(url)
                            return True

        # F - open folder
        if key == Qt.Key.Key_F and current == self.cdw and self.app.course_detail_mgr:
            category = self.cdw.categoryList.currentItem()
            if category:
                folder_map = {
                    'Syllabus': self.app.course_detail_mgr.syll_dir,
                    'Textbook': self.app.course_detail_mgr.textbook_dir,
                    'Tabs': os.path.join(self.app.course_detail_mgr.course_dir, 'Tabs')
                }
                folder = folder_map.get(category.text())
                if folder:
                    os.makedirs(folder, exist_ok=True)
                    self.app.open_folder(folder)
                    return True

        # Shift+Space - open auto detail
        if key == Qt.Key.Key_Space and (modifiers & Qt.KeyboardModifier.ShiftModifier):
            todo = None
            if current == self.mw and self.mw.categoryList.currentRow() == 1:
                ii = self.mw.itemList.currentRow()
                if ii >= 0:
                    item = self.mw.itemList.item(ii)
                    if item:
                        todo = item.data(Qt.ItemDataRole.UserRole + 1)
            elif current == self.aw:
                tab_idx = self.aw.mainTabWidget.currentIndex()
                lists = [self.aw.automatableOpenItemList, self.aw.automatableCloseItemList,
                        self.aw.automatableItemList, self.aw.allItemsItemList]
                ii = lists[tab_idx].currentRow()
                if ii >= 0:
                    item = lists[tab_idx].item(ii)
                    if item:
                        todo = item.data(Qt.ItemDataRole.UserRole)

            if todo:
                meta = self.app.dm.classify_todo(todo)
                if meta.get('is_automatable'):
                    self.app.auto_detail_mgr = AutoDetailManager(todo)
                    self.app.detail_view.populate_window()
                    self.app.stacked_widget.setCurrentWidget(self.app.auto_detail_window)
                    return True

        # Main window shortcuts
        if current == self.mw and not (modifiers & ~Qt.KeyboardModifier.ShiftModifier):
            if key == Qt.Key.Key_A and (modifiers & Qt.KeyboardModifier.ShiftModifier):
                self.app.auto_view.open()
                return True
            elif key == Qt.Key.Key_C and (modifiers & Qt.KeyboardModifier.ShiftModifier):
                self.app.settings_view.show_clean_dialog()
                return True
            elif key == Qt.Key.Key_C and not (modifiers & Qt.KeyboardModifier.ShiftModifier):
                self.mw.categoryList.setCurrentRow(0)
                self.mw.categoryList.setFocus()
                if self.mw.itemList.count() > 0:
                    self.mw.itemList.setCurrentRow(0)
                return True
            elif key == Qt.Key.Key_T:
                self.mw.categoryList.setCurrentRow(1)
                self.mw.categoryList.setFocus()
                if self.mw.itemList.count() > 0:
                    self.mw.itemList.setCurrentRow(0)
                return True
            elif key == Qt.Key.Key_F:
                self.mw.categoryList.setCurrentRow(2)
                self.mw.categoryList.setFocus()
                if self.mw.itemList.count() > 0:
                    self.mw.itemList.setCurrentRow(0)
                return True

        return False

    def _handle_launcher_wasd(self, key, obj):
        """Handle WASD for launcher"""
        lists = [self.lo.todoList, self.lo.courseList]
        idx = 0 if obj == lists[0] else 1 if obj == lists[1] else -1
        if idx == -1:
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
            if idx > 0:
                lists[idx - 1].setFocus()
                if lists[idx - 1].count() > 0:
                    lists[idx - 1].setCurrentRow(0)
        elif key == Qt.Key.Key_D:
            if idx < len(lists) - 1:
                lists[idx + 1].setFocus()
                if lists[idx + 1].count() > 0:
                    lists[idx + 1].setCurrentRow(0)

    def _handle_wasd(self, key, current):
        """Handle WASD for main windows"""
        if current == self.mw:
            lists = [self.mw.categoryList, self.mw.itemList, None]
        elif current == self.aw:
            tab_idx = self.aw.mainTabWidget.currentIndex()
            lists_map = [
                [self.aw.automatableOpenCategoryList, self.aw.automatableOpenItemList, None],
                [self.aw.automatableCloseCategoryList, self.aw.automatableCloseItemList, None],
                [self.aw.automatableCategoryList, self.aw.automatableItemList, None],
                [self.aw.allItemsCategoryList, self.aw.allItemsItemList, None]
            ]
            lists = lists_map[tab_idx]
        elif current == self.cdw:
            lists = [self.cdw.categoryList, self.cdw.itemList, None]
        else:
            return

        focused = None
        for i, lst in enumerate(lists):
            if lst and lst.hasFocus():
                focused = (i, lst)
                break

        if not focused:
            if lists[0]:
                lists[0].setFocus()
            return

        idx, current_list = focused
        if key == Qt.Key.Key_W:
            row = current_list.currentRow()
            if row > 0:
                current_list.setCurrentRow(row - 1)
        elif key == Qt.Key.Key_S:
            row = current_list.currentRow()
            if row < current_list.count() - 1:
                current_list.setCurrentRow(row + 1)
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
