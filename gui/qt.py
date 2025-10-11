import sys
import os
import time
import threading
from datetime import datetime, timedelta

from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PyQt6.QtCore import QTimer, pyqtSignal, QObject
from PyQt6.uic import loadUi

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
import checkStatus
from gui import qt_interact
from gui.styles import DARK_THEME


class StatusUpdateSignal(QObject):
    """Signal for thread-safe status updates"""
    update = pyqtSignal()


class CanvasApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # Initialize signal
        self.status_signal = StatusUpdateSignal()
        self.status_signal.update.connect(self.update_status)

        # Qt initialization
        self.init_qt()

        # Button bindings
        self.init_button_bindings()

        # Data viewer bindings
        self.init_data_viewer()

        # Status check
        self.check_status()

        # Window settings
        self.setWindowTitle("Canvas LMS Automation")
        self.resize(1400, 800)

    def init_qt(self):
        """Qt UI initialization"""
        # Setup stacked widget for navigation
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # Load UI files
        ui_dir = os.path.join(os.path.dirname(__file__), 'ui')

        # Load main window
        self.main_window = loadUi(os.path.join(ui_dir, 'main.ui'))
        self.stacked_widget.addWidget(self.main_window)

        # Load login window
        self.login_window = loadUi(os.path.join(ui_dir, 'login.ui'))
        self.stacked_widget.addWidget(self.login_window)

        # Load automation window
        self.automation_window = loadUi(os.path.join(ui_dir, 'automation.ui'))
        self.stacked_widget.addWidget(self.automation_window)

        # Setup status indicators
        self.status_widgets = {
            'account': self.main_window.accountIndicator,
            'cookie': self.main_window.cookieIndicator,
            'todos': self.main_window.todosIndicator,
            'network': self.main_window.networkIndicator,
            'courses': self.main_window.coursesIndicator
        }

        # Set initial window
        self.stacked_widget.setCurrentWidget(self.main_window)

    def init_button_bindings(self):
        """Initialize button bindings"""
        mw = self.main_window
        lw = self.login_window
        tab_widget = mw.consoleTabWidget

        # Main window buttons
        mw.loginBtn.clicked.connect(lambda: qt_interact.on_login_clicked(mw, self.stacked_widget, lw))
        mw.getCookieBtn.clicked.connect(lambda: qt_interact.on_get_cookie_clicked(tab_widget, self))
        mw.getTodoBtn.clicked.connect(lambda: qt_interact.on_get_todo_clicked(tab_widget, self))
        mw.getCourseBtn.clicked.connect(lambda: qt_interact.on_get_course_clicked(tab_widget, self))
        mw.cleanBtn.clicked.connect(lambda: qt_interact.on_clean_clicked(tab_widget))
        mw.automationTopBtn.clicked.connect(self.on_automation_top_clicked)

        # Login window buttons
        lw.backBtn.clicked.connect(lambda: qt_interact.on_back_clicked(self.stacked_widget, mw))
        lw.submitBtn.clicked.connect(lambda: qt_interact.on_submit_clicked(
            lw.accountInput, lw.passwordInput, lw.keyInput, self.stacked_widget, mw
        ))

        # Automation window buttons
        aw = self.automation_window
        aw.backBtn.clicked.connect(lambda: qt_interact.on_back_clicked(self.stacked_widget, mw))

        # Tab close handler
        tab_widget.tabCloseRequested.connect(self.close_tab)

        # New action buttons (left sidebar)
        mw.openFolderBtn.clicked.connect(self.on_open_folder_clicked)
        mw.automationBtn.clicked.connect(self.on_automation_clicked)

    def check_status(self):
        """Status check - auto-refresh cookies if expired, auto-fetch data if empty"""
        # Get console for logging
        main_tab = self.main_window.consoleTabWidget.widget(0)
        console = main_tab.findChild(self.main_window.consoleOutput.__class__) if main_tab else None

        # Check cookie expiry
        if os.path.exists(config.COOKIES_FILE):
            file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(config.COOKIES_FILE))
            if file_age > timedelta(hours=24):
                if console:
                    console.append("[INFO] Cookies expired (>24h), auto-refreshing...")
                qt_interact.on_get_cookie_clicked(self.main_window.consoleTabWidget)

        # Update status indicators
        self.update_status()
        self.update_user_info()

        # Auto-fetch Course and TODO if cookie is valid (green) and data is empty (red)
        status = checkStatus.get_all_status()

        if status['cookie'] == 1:  # Cookie is green (valid)
            if console:
                console.append("[INFO] Cookie valid, checking data files...")

            # Auto-fetch courses if empty
            if status['courses'] == 0:  # Red (empty/missing)
                if console:
                    console.append("[INFO] Course list empty, auto-fetching...")
                qt_interact.on_get_course_clicked(self.main_window.consoleTabWidget, self)

            # Auto-fetch todos if empty
            if status['todos'] == 0:  # Red (empty/missing)
                if console:
                    console.append("[INFO] TODO list empty, auto-fetching...")
                qt_interact.on_get_todo_clicked(self.main_window.consoleTabWidget, self)

    def update_status(self):
        """Update all status indicators"""
        qt_interact.update_status_indicators(self.status_widgets, checkStatus)

    def update_user_info(self):
        """Update user info labels"""
        mw = self.main_window
        qt_interact.update_user_info_labels(mw.emailLabel, mw.nameLabel, mw.idLabel)

    def init_data_viewer(self):
        """Initialize data viewer (3-column layout)"""
        # Get widgets
        category_list = self.main_window.categoryList
        item_list = self.main_window.itemList
        detail_view = self.main_window.detailView

        # Populate categories
        category_list.addItems(["Courses", "TODOs", "Files"])

        # Connect signals
        category_list.currentRowChanged.connect(self.on_category_changed)
        item_list.currentRowChanged.connect(self.on_item_changed)

        # Connect filter checkboxes
        self.main_window.filterHomework.stateChanged.connect(self.apply_filters)
        self.main_window.filterQuiz.stateChanged.connect(self.apply_filters)
        self.main_window.filterDiscussion.stateChanged.connect(self.apply_filters)
        self.main_window.filterAutomatable.stateChanged.connect(self.apply_filters)

        # Load initial data
        self.current_data = {'courses': [], 'todos': [], 'files': []}
        self.load_data()

    def load_data(self):
        """Load data from JSON files"""
        import json

        # Load courses
        if os.path.exists(config.COURSE_FILE):
            try:
                with open(config.COURSE_FILE, 'r') as f:
                    data = json.load(f)
                    self.current_data['courses'] = data.get('courses', [])
            except:
                pass

        # Load todos
        todos_file = os.path.join(config.ROOT_DIR, 'todos.json')
        if os.path.exists(todos_file):
            try:
                with open(todos_file, 'r') as f:
                    self.current_data['todos'] = json.load(f)
            except:
                pass

        # Load folders from todo_files directory
        todo_files_dir = os.path.join(config.ROOT_DIR, 'todo_files')
        if os.path.exists(todo_files_dir):
            self.current_data['files'] = [
                f for f in os.listdir(todo_files_dir)
                if os.path.isdir(os.path.join(todo_files_dir, f))
            ]

    def on_category_changed(self, index):
        """Handle category selection change"""
        from PyQt6.QtWidgets import QListWidgetItem, QWidget, QHBoxLayout, QLabel
        from PyQt6.QtCore import Qt

        item_list = self.main_window.itemList
        item_list.clear()

        if index == 0:  # Courses
            for course in self.current_data['courses']:
                item_list.addItem(course.get('name', 'Unknown'))

        elif index == 1:  # TODOs - with indicator dots
            for todo in self.current_data['todos']:
                assignment_details = todo.get('assignment_details', {})
                redirect_url = todo.get('redirect_url', '')
                submission_types = assignment_details.get('type', [])

                # Determine item type and automation capability
                is_quiz = 'quiz' in redirect_url.lower()
                is_discussion = 'discussion' in redirect_url.lower()
                is_automatable = (
                    'online_quiz' in submission_types or
                    'online_upload' in submission_types or
                    'online_text_entry' in submission_types or
                    'discussion_topic' in submission_types
                )

                # Build display text
                display_text = f"{todo.get('course_name', '')} - {todo.get('name', '')}"

                # Create list item
                item = QListWidgetItem(display_text)

                # Store metadata for filtering
                item.setData(Qt.ItemDataRole.UserRole, {
                    'is_quiz': is_quiz,
                    'is_discussion': is_discussion,
                    'is_automatable': is_automatable,
                    'is_homework': not (is_quiz or is_discussion),
                    'dots': {
                        'homework': not (is_quiz or is_discussion),
                        'quiz': is_quiz,
                        'discussion': is_discussion,
                        'automatable': is_automatable
                    }
                })

                item_list.addItem(item)

            # Set custom delegate for rendering dots
            from PyQt6.QtWidgets import QStyledItemDelegate
            from PyQt6.QtGui import QPainter, QColor
            from PyQt6.QtCore import QRect, QPoint

            class TodoItemDelegate(QStyledItemDelegate):
                def paint(self, painter, option, index):
                    # Draw default item (text + background)
                    super().paint(painter, option, index)

                    # Get metadata
                    metadata = index.data(Qt.ItemDataRole.UserRole)
                    if not metadata or 'dots' not in metadata:
                        return

                    dots = metadata['dots']

                    # Draw dots on the right
                    painter.save()
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

                    dot_size = 10
                    dot_spacing = 6
                    right_margin = 10
                    x = option.rect.right() - right_margin

                    # Draw dots from right to left
                    # Automatable (red)
                    if dots.get('automatable'):
                        x -= dot_size
                        painter.setBrush(QColor(239, 68, 68))  # #ef4444
                        painter.setPen(QColor(239, 68, 68))
                        painter.drawEllipse(QPoint(x + dot_size // 2, option.rect.center().y()), dot_size // 2, dot_size // 2)
                        x -= dot_spacing

                    # Discussion (blue)
                    if dots.get('discussion'):
                        x -= dot_size
                        painter.setBrush(QColor(59, 130, 246))  # #3b82f6
                        painter.setPen(QColor(59, 130, 246))
                        painter.drawEllipse(QPoint(x + dot_size // 2, option.rect.center().y()), dot_size // 2, dot_size // 2)
                        x -= dot_spacing

                    # Quiz (purple)
                    if dots.get('quiz'):
                        x -= dot_size
                        painter.setBrush(QColor(168, 85, 247))  # #a855f7
                        painter.setPen(QColor(168, 85, 247))
                        painter.drawEllipse(QPoint(x + dot_size // 2, option.rect.center().y()), dot_size // 2, dot_size // 2)
                        x -= dot_spacing

                    # Homework (yellow)
                    if dots.get('homework'):
                        x -= dot_size
                        painter.setBrush(QColor(234, 179, 8))  # #eab308
                        painter.setPen(QColor(234, 179, 8))
                        painter.drawEllipse(QPoint(x + dot_size // 2, option.rect.center().y()), dot_size // 2, dot_size // 2)

                    painter.restore()

                def sizeHint(self, option, index):
                    size = super().sizeHint(option, index)
                    size.setHeight(max(size.height(), 36))
                    return size

            item_list.setItemDelegate(TodoItemDelegate(item_list))

        elif index == 2:  # Files
            item_list.addItems(self.current_data['files'])

    def apply_filters(self):
        """Apply filters to TODO list items (OR logic)"""
        from PyQt6.QtCore import Qt

        # Only apply filters if TODOs category is selected
        if self.main_window.categoryList.currentRow() != 1:
            return

        item_list = self.main_window.itemList

        # Get filter states
        filter_homework = self.main_window.filterHomework.isChecked()
        filter_quiz = self.main_window.filterQuiz.isChecked()
        filter_discussion = self.main_window.filterDiscussion.isChecked()
        filter_automatable = self.main_window.filterAutomatable.isChecked()

        # If no filters are selected, show all items
        show_all = not (filter_homework or filter_quiz or filter_discussion or filter_automatable)

        # Apply filter to each item
        for i in range(item_list.count()):
            item = item_list.item(i)
            metadata = item.data(Qt.ItemDataRole.UserRole)

            if not metadata:
                continue

            # OR logic: show if matches ANY selected filter
            should_show = show_all or (
                (filter_homework and metadata.get('is_homework', False)) or
                (filter_quiz and metadata.get('is_quiz', False)) or
                (filter_discussion and metadata.get('is_discussion', False)) or
                (filter_automatable and metadata.get('is_automatable', False))
            )

            item.setHidden(not should_show)

    def on_item_changed(self, index):
        """Handle item selection change - display details"""
        if index < 0:
            return

        category_index = self.main_window.categoryList.currentRow()
        detail_view = self.main_window.detailView

        if category_index == 0:  # Course details
            if index < len(self.current_data['courses']):
                course = self.current_data['courses'][index]
                detail_view.setHtml(self._format_course_details(course))
        elif category_index == 1:  # TODO details
            if index < len(self.current_data['todos']):
                todo = self.current_data['todos'][index]
                detail_view.setHtml(self._format_todo_details(todo))
        elif category_index == 2:  # File details
            if index < len(self.current_data['files']):
                filename = self.current_data['files'][index]
                detail_view.setHtml(self._format_file_details(filename))

    def _format_course_details(self, course):
        """Format course data as HTML (dynamic - shows all fields)"""
        html = f"<h2 style='color: #3b82f6;'>{course.get('name', 'Unknown Course')}</h2>"
        html += "<div style='font-family: monospace; font-size: 13px;'>"

        for key, value in course.items():
            if key == 'name':
                continue
            if isinstance(value, dict):
                html += f"<p><strong>{key}:</strong></p><ul>"
                for sub_key, sub_value in value.items():
                    html += f"<li>{sub_key}: <span style='color: #22c55e;'>{sub_value}</span></li>"
                html += "</ul>"
            else:
                html += f"<p><strong>{key}:</strong> {value}</p>"

        html += "</div>"
        return html

    def _format_todo_details(self, todo):
        """Format TODO data as HTML (dynamic - shows all fields)"""
        assignment_details = todo.get('assignment_details', {})
        redirect_url = todo.get('redirect_url', '')
        submission_types = assignment_details.get('type', [])

        # Determine type and color
        is_quiz = 'quiz' in redirect_url.lower()
        is_discussion = 'discussion' in redirect_url.lower()
        is_automatable = (
            'online_quiz' in submission_types or
            'online_upload' in submission_types or
            'online_text_entry' in submission_types or
            'discussion_topic' in submission_types
        )

        # Choose title color
        if is_automatable:
            title_color = '#ef4444'  # Red
            type_label = '🤖 AUTOMATABLE'
        elif is_quiz:
            title_color = '#a855f7'  # Purple
            type_label = '📝 QUIZ'
        elif is_discussion:
            title_color = '#3b82f6'  # Blue
            type_label = '💬 DISCUSSION'
        else:
            title_color = '#eab308'  # Yellow
            type_label = '📚 HOMEWORK'

        html = f"<h2 style='color: {title_color};'>{todo.get('name', 'Unknown TODO')} <span style='font-size: 14px;'>[{type_label}]</span></h2>"
        html += f"<h3 style='color: #aaa;'>{todo.get('course_name', '')}</h3>"

        # Add color legend
        html += "<div style='background: #1a1a1a; padding: 10px; border-radius: 6px; margin-bottom: 10px;'>"
        html += "<strong>Legend:</strong> "
        html += "<span style='color: #ef4444;'>🤖 Automatable</span> | "
        html += "<span style='color: #a855f7;'>📝 Quiz</span> | "
        html += "<span style='color: #3b82f6;'>💬 Discussion</span> | "
        html += "<span style='color: #eab308;'>📚 Homework</span>"
        html += "</div>"

        html += "<div style='font-family: monospace; font-size: 13px;'>"

        # Top-level fields
        for key, value in todo.items():
            if key in ['name', 'course_name', 'assignment_details']:
                continue
            html += f"<p><strong>{key}:</strong> {value}</p>"

        # Assignment details
        if 'assignment_details' in todo:
            html += "<hr><h3>Assignment Details:</h3>"
            details = todo['assignment_details']
            for key, value in details.items():
                if key == 'files' and value:
                    html += "<p><strong>Files:</strong></p><ul>"
                    for file in value:
                        html += f"<li>{file.get('filename', 'Unknown')}</li>"
                    html += "</ul>"
                elif isinstance(value, list):
                    html += f"<p><strong>{key}:</strong> {', '.join(str(v) for v in value)}</p>"
                else:
                    html += f"<p><strong>{key}:</strong> {value}</p>"

        html += "</div>"
        return html

    def _format_file_details(self, foldername):
        """Format folder details as HTML (shows files inside)"""
        folder_path = os.path.join(config.ROOT_DIR, 'todo_files', foldername)

        html = f"<h2 style='color: #22c55e;'>{foldername}</h2>"
        html += "<div style='font-family: monospace; font-size: 13px;'>"
        html += f"<p><strong>Path:</strong> {folder_path}</p>"

        # List files in folder
        if os.path.exists(folder_path):
            files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
            if files:
                html += f"<p><strong>Files ({len(files)}):</strong></p><ul>"
                for file in sorted(files):
                    file_path = os.path.join(folder_path, file)
                    size = os.path.getsize(file_path)
                    html += f"<li>{file} <span style='color: #aaa;'>({size:,} bytes)</span></li>"
                html += "</ul>"
            else:
                html += "<p><em>No files in folder</em></p>"

        html += "</div>"
        return html

    def on_open_folder_clicked(self):
        """Open the folder for selected item"""
        category_index = self.main_window.categoryList.currentRow()
        item_index = self.main_window.itemList.currentRow()

        if category_index < 0 or item_index < 0:
            return

        folder_path = None

        if category_index == 1:  # TODOs - open assignment folder
            if item_index < len(self.current_data['todos']):
                todo = self.current_data['todos'][item_index]
                folder_name = todo.get('assignment_details', {}).get('folder')
                if folder_name:
                    folder_path = os.path.join(config.ROOT_DIR, 'todo_files', folder_name)

        elif category_index == 2:  # Files - open selected folder
            if item_index < len(self.current_data['files']):
                folder_name = self.current_data['files'][item_index]
                folder_path = os.path.join(config.ROOT_DIR, 'todo_files', folder_name)

        # Open folder in file explorer
        if folder_path and os.path.exists(folder_path):
            import subprocess
            import platform
            system = platform.system()
            if system == 'Windows':
                os.startfile(folder_path)
            elif system == 'Darwin':  # macOS
                subprocess.run(['open', folder_path])
            else:  # Linux
                subprocess.run(['xdg-open', folder_path])

    def on_automation_clicked(self):
        """Automation button (left sidebar) - check if selected TODO is automatable"""
        from PyQt6.QtWidgets import QMessageBox
        from PyQt6.QtCore import Qt

        # Check if TODO is selected
        category_index = self.main_window.categoryList.currentRow()
        item_index = self.main_window.itemList.currentRow()

        if category_index != 1:  # Not TODOs category
            QMessageBox.warning(self, "Invalid Selection", "Please select a TODO item first.")
            return

        if item_index < 0:
            QMessageBox.warning(self, "No Selection", "Please select a TODO item first.")
            return

        # Get selected item metadata
        item = self.main_window.itemList.item(item_index)
        metadata = item.data(Qt.ItemDataRole.UserRole)

        if not metadata or not metadata.get('is_automatable'):
            QMessageBox.warning(
                self,
                "Not Automatable",
                "This TODO item is not automatable.\n\nOnly items with online submission types can be automated."
            )
            return

        # Find the actual TODO data by matching the visible item index
        # We need to count visible items to get the correct TODO
        visible_count = 0
        selected_todo = None
        for todo in self.current_data['todos']:
            # Check if this item would be visible (apply same logic as on_category_changed)
            assignment_details = todo.get('assignment_details', {})
            redirect_url = todo.get('redirect_url', '')

            is_quiz = 'quiz' in redirect_url.lower()
            is_discussion = 'discussion' in redirect_url.lower()

            if visible_count == item_index:
                selected_todo = todo
                break
            visible_count += 1

        if selected_todo:
            # Navigate to automation page with selected item
            self.populate_automation_window(selected_todo=selected_todo)
            self.stacked_widget.setCurrentWidget(self.automation_window)

    def on_automation_top_clicked(self):
        """Automation button (top bar) - navigate to automation page"""
        self.populate_automation_window()
        self.stacked_widget.setCurrentWidget(self.automation_window)

    def populate_automation_window(self, selected_todo=None):
        """Populate automation window with categorized TODOs"""
        from PyQt6.QtCore import Qt

        aw = self.automation_window

        # Clear all lists
        aw.allItemsCategoryList.clear()
        aw.allItemsItemList.clear()
        aw.allItemsDetailView.clear()
        aw.automatableCategoryList.clear()
        aw.automatableItemList.clear()
        aw.automatableDetailView.clear()

        # Add categories to both tabs
        aw.allItemsCategoryList.addItems(["Homework", "Quiz", "Discussion"])
        aw.automatableCategoryList.addItems(["Homework", "Quiz", "Discussion"])

        # Disconnect all signals first
        try:
            aw.allItemsCategoryList.currentRowChanged.disconnect()
            aw.allItemsItemList.currentRowChanged.disconnect()
            aw.automatableCategoryList.currentRowChanged.disconnect()
            aw.automatableItemList.currentRowChanged.disconnect()
        except:
            pass

        # Connect signals for Tab1 (All Items)
        aw.allItemsCategoryList.currentRowChanged.connect(
            lambda idx: self.on_automation_category_changed(idx, automatable_only=False)
        )
        aw.allItemsItemList.currentRowChanged.connect(
            lambda idx: self.on_automation_item_changed(idx, automatable_only=False)
        )

        # Connect signals for Tab2 (Automatable Only)
        aw.automatableCategoryList.currentRowChanged.connect(
            lambda idx: self.on_automation_category_changed(idx, automatable_only=True)
        )
        aw.automatableItemList.currentRowChanged.connect(
            lambda idx: self.on_automation_item_changed(idx, automatable_only=True)
        )

        # If a specific TODO is selected, navigate to it
        if selected_todo:
            redirect_url = selected_todo.get('redirect_url', '')
            is_quiz = 'quiz' in redirect_url.lower()
            is_discussion = 'discussion' in redirect_url.lower()

            # Determine category index
            if is_quiz:
                category_idx = 1  # Quiz
            elif is_discussion:
                category_idx = 2  # Discussion
            else:
                category_idx = 0  # Homework

            # Switch to Automatable tab and select category
            aw.mainTabWidget.setCurrentIndex(1)  # Tab2: Automatable Only
            aw.automatableCategoryList.setCurrentRow(category_idx)

            # Find and select the item in the list
            item_list = aw.automatableItemList
            for i in range(item_list.count()):
                item = item_list.item(i)
                todo_data = item.data(Qt.ItemDataRole.UserRole)
                if todo_data and todo_data.get('redirect_url') == selected_todo.get('redirect_url'):
                    item_list.setCurrentRow(i)
                    break
        else:
            # Default: select first category in Tab1
            aw.allItemsCategoryList.setCurrentRow(0)

    def on_automation_category_changed(self, index, automatable_only=False):
        """Handle automation category selection change"""
        from PyQt6.QtWidgets import QListWidgetItem
        from PyQt6.QtCore import Qt

        aw = self.automation_window

        # Select the appropriate lists based on tab
        if automatable_only:
            item_list = aw.automatableItemList
        else:
            item_list = aw.allItemsItemList

        item_list.clear()

        if index < 0:
            return

        # Filter TODOs based on category
        for todo in self.current_data['todos']:
            assignment_details = todo.get('assignment_details', {})
            redirect_url = todo.get('redirect_url', '')
            submission_types = assignment_details.get('type', [])

            # Determine item type
            is_quiz = 'quiz' in redirect_url.lower()
            is_discussion = 'discussion' in redirect_url.lower()
            is_homework = not (is_quiz or is_discussion)
            is_automatable = (
                'online_quiz' in submission_types or
                'online_upload' in submission_types or
                'online_text_entry' in submission_types or
                'discussion_topic' in submission_types
            )

            # Skip non-automatable items if in automatable-only mode
            if automatable_only and not is_automatable:
                continue

            # Filter by category
            should_show = False
            if index == 0:  # Homework
                should_show = is_homework
            elif index == 1:  # Quiz
                should_show = is_quiz
            elif index == 2:  # Discussion
                should_show = is_discussion

            if should_show:
                # Build display text
                display_text = f"{todo.get('course_name', '')} - {todo.get('name', '')}"
                item = QListWidgetItem(display_text)

                # Store full TODO data for detail view
                item.setData(Qt.ItemDataRole.UserRole, todo)
                item_list.addItem(item)

    def on_automation_item_changed(self, index, automatable_only=False):
        """Handle automation item selection change - display details"""
        from PyQt6.QtCore import Qt

        if index < 0:
            return

        aw = self.automation_window

        # Select the appropriate widgets based on tab
        if automatable_only:
            item_list = aw.automatableItemList
            detail_view = aw.automatableDetailView
        else:
            item_list = aw.allItemsItemList
            detail_view = aw.allItemsDetailView

        # Get selected item data
        item = item_list.item(index)
        todo = item.data(Qt.ItemDataRole.UserRole)

        if todo:
            # Reuse the existing format method
            detail_view.setHtml(self._format_todo_details(todo))

    def close_tab(self, index):
        """Close a tab (but keep first Main tab)"""
        if index > 0:
            self.main_window.consoleTabWidget.removeTab(index)


def init_qt_window():
    """Initialize Qt window with status update thread"""
    window = CanvasApp()

    # Background status update thread
    def status_update_thread():
        """Update status every 30 seconds"""
        while True:
            time.sleep(30)
            window.status_signal.update.emit()

    thread = threading.Thread(target=status_update_thread, daemon=True)
    thread.start()

    return window


def main():
    """Standalone entry point (for running gui/qt.py directly)"""
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_THEME)

    window = init_qt_window()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
