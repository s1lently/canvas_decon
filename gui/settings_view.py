"""Settings View - Settings Overlay (merged from handlers/sitting.py)"""
import sys, os, json
from io import StringIO
from PyQt6.QtWidgets import QMessageBox, QTableWidgetItem, QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config


class SettingsView:
    """Handles Settings Overlay operations"""

    def __init__(self, app):
        self.app = app
        self.sw = app.settings_overlay

        # Auto-refresh timer for tasks table (300ms)
        self.tasks_refresh_timer = QTimer()
        self.tasks_refresh_timer.timeout.connect(self.refresh_tasks_table)
        self.tasks_refresh_timer.start(300)

    def show(self):
        """Show settings overlay"""
        self._update_geometry()
        self.sw.show()
        self.sw.raise_()
        self.refresh_tasks_table()

    def hide(self):
        """Hide settings overlay"""
        self.sw.hide()

    def _update_geometry(self):
        """Update geometry to match parent"""
        self.sw.setGeometry(self.app.rect())

    # === LOGIN INFO ===
    def load_login_info(self):
        """Load and display current login info"""
        try:
            if os.path.exists(config.ACCOUNT_CONFIG_FILE):
                with open(config.ACCOUNT_CONFIG_FILE) as f:
                    data = json.load(f)
                    account = data.get('account', '--')
                    self.sw.accountDisplayLabel.setText(f"Account: {account}")
        except Exception:
            self.sw.accountDisplayLabel.setText("Account: --")

    # === API SETTINGS ===
    def load_api_settings(self):
        """Load API settings into form"""
        try:
            if os.path.exists(config.ACCOUNT_CONFIG_FILE):
                with open(config.ACCOUNT_CONFIG_FILE) as f:
                    data = json.load(f)

                    # Gemini
                    gemini_key = data.get('gemini_api_key', '')
                    if gemini_key:
                        display = gemini_key[:10] + '...' if len(gemini_key) > 10 else gemini_key
                        self.sw.geminiApiInput.setText(display)
                        self.sw.geminiApiInput.setProperty('full_key', gemini_key)

                    # Claude
                    claude_key = data.get('claude_api_key', '')
                    if claude_key:
                        display = claude_key[:10] + '...' if len(claude_key) > 10 else claude_key
                        self.sw.claudeApiInput.setText(display)
                        self.sw.claudeApiInput.setProperty('full_key', claude_key)
        except Exception:
            pass

    def save_api_key(self):
        """Save API keys"""
        gemini_key = self.sw.geminiApiInput.text()
        claude_key = self.sw.claudeApiInput.text()

        # Handle masked keys
        if gemini_key.endswith('...'):
            full_key = self.sw.geminiApiInput.property('full_key')
            gemini_key = full_key if full_key else ''

        if claude_key.endswith('...'):
            full_key = self.sw.claudeApiInput.property('full_key')
            claude_key = full_key if full_key else ''

        if not gemini_key and not claude_key:
            return QMessageBox.warning(self.app, "Error", "Please enter at least one API key!")

        try:
            data = {}
            if os.path.exists(config.ACCOUNT_CONFIG_FILE):
                with open(config.ACCOUNT_CONFIG_FILE) as f:
                    data = json.load(f)

            if gemini_key:
                data['gemini_api_key'] = gemini_key
            if claude_key:
                data['claude_api_key'] = claude_key

            with open(config.ACCOUNT_CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=2)

            saved = []
            if gemini_key:
                saved.append("Gemini")
            if claude_key:
                saved.append("Claude")

            config.reload_config()
            QMessageBox.information(self.app, "Success", f"{' and '.join(saved)} API Key(s) saved!")
            self.load_api_settings()
        except Exception as e:
            QMessageBox.critical(self.app, "Error", f"Failed to save: {str(e)}")

    def save_preference(self, base_url):
        """Save preference (base_url)"""
        if not base_url:
            return QMessageBox.warning(self.app, "Error", "Please enter a base URL!")

        try:
            data = {}
            if os.path.exists(config.ACCOUNT_CONFIG_FILE):
                with open(config.ACCOUNT_CONFIG_FILE) as f:
                    data = json.load(f)

            if 'preference' not in data:
                data['preference'] = {}
            data['preference']['base_url'] = base_url

            with open(config.ACCOUNT_CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=2)

            QMessageBox.information(self.app, "Success", "Preference saved! Restart to apply.")
            self.sw.baseUrlInput.clear()
        except Exception as e:
            QMessageBox.critical(self.app, "Error", f"Failed to save: {str(e)}")

    # === TASK MANAGEMENT ===
    def refresh_tasks_table(self):
        """Refresh tasks table"""
        if not self.sw.isVisible():
            return

        from gui._internal.mgrTask import get_task_manager

        table = self.sw.tasksTable
        table.setRowCount(0)

        for task in get_task_manager().get_all_tasks():
            row = table.rowCount()
            table.insertRow(row)

            table.setItem(row, 0, QTableWidgetItem(task['name']))
            table.setItem(row, 1, QTableWidgetItem(task['start_time'].strftime('%H:%M:%S')))
            status = 'Running' if task['thread'].is_alive() else 'Completed'
            table.setItem(row, 2, QTableWidgetItem(status))
            table.item(row, 0).setData(Qt.ItemDataRole.UserRole, task['id'])

    def stop_selected_task(self):
        """Stop selected task"""
        from gui._internal.mgrTask import get_task_manager

        table = self.sw.tasksTable
        row = table.currentRow()

        if row < 0:
            return QMessageBox.warning(self.app, "No Selection", "Please select a task to stop.")

        task_id = table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        task_name = table.item(row, 0).text()

        reply = QMessageBox.question(self.app, "Confirm Stop", f"Stop task:\n{task_name}?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            if get_task_manager().stop_task(task_id):
                self.app.show_toast(f"Task '{task_name}' stopped", 'success')
                self.refresh_tasks_table()
            else:
                QMessageBox.warning(self.app, "Error", "Failed to stop task.")

    def stop_all_tasks(self):
        """Stop all tasks"""
        from gui._internal.mgrTask import get_task_manager

        tasks = get_task_manager().get_all_tasks()
        if not tasks:
            return QMessageBox.information(self.app, "No Tasks", "No running tasks.")

        reply = QMessageBox.question(self.app, "Confirm Stop All", f"Stop all {len(tasks)} tasks?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            get_task_manager().stop_all_tasks()
            self.app.show_toast("All tasks stopped", 'success')
            self.refresh_tasks_table()

    # === CLEAN ===
    def show_clean_dialog(self):
        """Show clean dialog with checkboxes for exclusion"""
        from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QCheckBox
        from func.clean import scan_items, clean_items, _rel_path, _format_size

        items = scan_items()
        if not items:
            return QMessageBox.information(self.app, "Clean", "Nothing to clean!")

        # Create dialog
        dialog = QDialog(self.app)
        dialog.setWindowTitle("Clean - Select items to delete")
        dialog.setMinimumSize(700, 500)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("☑ Check items to DELETE (uncheck to keep):"))

        # List with checkboxes
        list_widget = QListWidget()
        list_widget.setStyleSheet("QListWidget { font-family: monospace; }")

        for i, (path, item_type, size_str) in enumerate(items):
            marker = '📁' if item_type == 'dir' else '📄'
            item = QListWidgetItem(f"{marker} {_rel_path(path)} ({size_str})")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)  # Default: will delete
            item.setData(Qt.ItemDataRole.UserRole, i)
            list_widget.addItem(item)

        layout.addWidget(list_widget)

        # Buttons
        button_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_none_btn = QPushButton("Select None")
        clean_btn = QPushButton("🗑️ Clean Selected")
        cancel_btn = QPushButton("Cancel")

        def select_all():
            for i in range(list_widget.count()):
                list_widget.item(i).setCheckState(Qt.CheckState.Checked)

        def select_none():
            for i in range(list_widget.count()):
                list_widget.item(i).setCheckState(Qt.CheckState.Unchecked)

        def do_clean():
            exclude = set()
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                if item.checkState() != Qt.CheckState.Checked:
                    exclude.add(item.data(Qt.ItemDataRole.UserRole))

            to_clean = len(items) - len(exclude)
            if to_clean == 0:
                QMessageBox.information(dialog, "Clean", "No items selected.")
                return

            reply = QMessageBox.question(dialog, "Confirm",
                f"Delete {to_clean} items?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

            if reply == QMessageBox.StandardButton.Yes:
                deleted, skipped = clean_items(items, exclude)
                self.app.show_toast(f"Cleaned {deleted} items", 'success')
                dialog.accept()

        select_all_btn.clicked.connect(select_all)
        select_none_btn.clicked.connect(select_none)
        clean_btn.clicked.connect(do_clean)
        cancel_btn.clicked.connect(dialog.reject)

        button_layout.addWidget(select_all_btn)
        button_layout.addWidget(select_none_btn)
        button_layout.addStretch()
        button_layout.addWidget(clean_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        dialog.setLayout(layout)
        dialog.exec()
