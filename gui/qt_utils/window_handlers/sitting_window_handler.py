"""Sitting Window Handler - Manages Settings Window (9 methods)"""
import sys, os, json
from io import StringIO
from PyQt6.QtWidgets import QMessageBox, QTableWidgetItem, QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import config
from gui.qt_utils.base_handler import BaseHandler


class SittingWindowHandler(BaseHandler):
    """Handles Sitting Window operations"""

    def open(self):
        """Open sitting window"""
        self.stacked_widget.setCurrentWidget(self.sitting_window)
        self.refresh_tasks_table()

    def load_current_login_info(self):
        """Load and display current login account info"""
        try:
            if os.path.exists(config.ACCOUNT_CONFIG_FILE):
                with open(config.ACCOUNT_CONFIG_FILE) as f:
                    account_data = json.load(f)
                    account = account_data.get('account', '--')
                    self.sitting_window.accountDisplayLabel.setText(f"Account: {account}")
        except:
            self.sitting_window.accountDisplayLabel.setText("Account: --")

    def load_api_settings(self):
        """Load current API settings into the form"""
        try:
            if os.path.exists(config.ACCOUNT_CONFIG_FILE):
                with open(config.ACCOUNT_CONFIG_FILE) as f:
                    config_data = json.load(f)

                    # Gemini API Key
                    gemini_key = config_data.get('gemini_api_key', '')
                    if gemini_key:
                        display_key = gemini_key[:10] + '...' if len(gemini_key) > 10 else gemini_key
                        self.sitting_window.geminiApiInput.setText(display_key)
                        self.sitting_window.geminiApiInput.setProperty('full_key', gemini_key)

                    # Claude API Key
                    claude_key = config_data.get('claude_api_key', '')
                    if claude_key:
                        display_key = claude_key[:10] + '...' if len(claude_key) > 10 else claude_key
                        self.sitting_window.claudeApiInput.setText(display_key)
                        self.sitting_window.claudeApiInput.setProperty('full_key', claude_key)
        except:
            pass

    def on_gemini_api_focus(self):
        """Clear Gemini API key input if it contains masked value"""
        if self.sitting_window.geminiApiInput.text().endswith('...'):
            self.sitting_window.geminiApiInput.clear()

    def on_claude_api_focus(self):
        """Clear Claude API key input if it contains masked value"""
        if self.sitting_window.claudeApiInput.text().endswith('...'):
            self.sitting_window.claudeApiInput.clear()

    def save_api_key(self):
        """Save both API keys to account_config.json"""
        gemini_key = self.sitting_window.geminiApiInput.text()
        claude_key = self.sitting_window.claudeApiInput.text()

        # Handle masked keys
        if gemini_key.endswith('...'):
            full_key = self.sitting_window.geminiApiInput.property('full_key')
            gemini_key = full_key if full_key else ''

        if claude_key.endswith('...'):
            full_key = self.sitting_window.claudeApiInput.property('full_key')
            claude_key = full_key if full_key else ''

        if not gemini_key and not claude_key:
            QMessageBox.warning(self.app, "Error", "Please enter at least one API key!")
            return

        try:
            config_data = {}
            if os.path.exists(config.ACCOUNT_CONFIG_FILE):
                with open(config.ACCOUNT_CONFIG_FILE) as f:
                    config_data = json.load(f)

            if gemini_key:
                config_data['gemini_api_key'] = gemini_key
            if claude_key:
                config_data['claude_api_key'] = claude_key

            with open(config.ACCOUNT_CONFIG_FILE, 'w') as f:
                json.dump(config_data, f, indent=2)

            saved_keys = []
            if gemini_key:
                saved_keys.append("Gemini")
            if claude_key:
                saved_keys.append("Claude")

            QMessageBox.information(self.app, "Success", f"{' and '.join(saved_keys)} API Key(s) saved successfully!\nRestart the app to apply changes.")
            self.load_api_settings()  # Reload to show masked keys
        except Exception as e:
            QMessageBox.critical(self.app, "Error", f"Failed to save API keys: {str(e)}")

    def save_preference(self, base_url):
        """Save preference (base_url) to account_config.json"""
        if not base_url:
            QMessageBox.warning(self.app, "Error", "Please enter a base URL!")
            return

        try:
            config_data = {}
            if os.path.exists(config.ACCOUNT_CONFIG_FILE):
                with open(config.ACCOUNT_CONFIG_FILE) as f:
                    config_data = json.load(f)

            if 'preference' not in config_data:
                config_data['preference'] = {}

            config_data['preference']['base_url'] = base_url

            with open(config.ACCOUNT_CONFIG_FILE, 'w') as f:
                json.dump(config_data, f, indent=2)

            QMessageBox.information(self.app, "Success", "Preference saved successfully!\nRestart the app to apply changes.")
            self.sitting_window.baseUrlInput.clear()
        except Exception as e:
            QMessageBox.critical(self.app, "Error", f"Failed to save preference: {str(e)}")

    def refresh_tasks_table(self):
        """Refresh tasks table with current running tasks"""
        from gui.mgrTask import get_task_manager
        from datetime import datetime

        table = self.sitting_window.tasksTable
        table.setRowCount(0)

        tasks = get_task_manager().get_all_tasks()
        for task in tasks:
            row = table.rowCount()
            table.insertRow(row)

            # Task name
            table.setItem(row, 0, QTableWidgetItem(task['name']))

            # Start time (formatted)
            start_time = task['start_time'].strftime('%H:%M:%S')
            table.setItem(row, 1, QTableWidgetItem(start_time))

            # Status
            status = 'Running' if task['thread'].is_alive() else 'Completed'
            table.setItem(row, 2, QTableWidgetItem(status))

            # Store task ID in first column for reference
            table.item(row, 0).setData(Qt.ItemDataRole.UserRole, task['id'])

    def stop_selected_task(self):
        """Stop the selected task"""
        from gui.mgrTask import get_task_manager

        table = self.sitting_window.tasksTable
        current_row = table.currentRow()

        if current_row < 0:
            QMessageBox.warning(self.app, "No Selection", "Please select a task to stop.")
            return

        task_id = table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)
        task_name = table.item(current_row, 0).text()

        reply = QMessageBox.question(
            self.app,
            "Confirm Stop",
            f"Are you sure you want to stop task:\n{task_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if get_task_manager().stop_task(task_id):
                self.app.show_toast(f"Task '{task_name}' stopped", 'success')
                self.refresh_tasks_table()
            else:
                QMessageBox.warning(self.app, "Error", "Failed to stop task.")

    def stop_all_tasks(self):
        """Stop all running tasks"""
        from gui.mgrTask import get_task_manager

        tasks = get_task_manager().get_all_tasks()
        if not tasks:
            QMessageBox.information(self.app, "No Tasks", "No running tasks to stop.")
            return

        reply = QMessageBox.question(
            self.app,
            "Confirm Stop All",
            f"Are you sure you want to stop all {len(tasks)} running tasks?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            get_task_manager().stop_all_tasks()
            self.app.show_toast(f"All tasks stopped", 'success')
            self.refresh_tasks_table()

    def show_clean_dialog(self):
        """Show clean dialog with preview"""
        from clean import preview_deletion, clean_directory, build_tree, print_tree

        to_delete = preview_deletion()
        if not to_delete:
            return QMessageBox.information(self.app, "Clean", "No files to clean!")

        # Build tree preview
        tree_output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = tree_output
        print_tree(build_tree(to_delete))
        sys.stdout = old_stdout

        # Create dialog
        dialog = QDialog(self.app)
        dialog.setWindowTitle("Clean Confirmation")
        dialog.setMinimumSize(600, 400)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("The following files will be deleted:"))

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(f"Found {len(to_delete)} files to clean:\n\n{tree_output.getvalue()}")
        layout.addWidget(text_edit)

        # Buttons
        button_layout = QHBoxLayout()
        yes_btn = QPushButton("Yes")
        cancel_btn = QPushButton("Cancel")

        yes_btn.clicked.connect(lambda: (
            clean_directory(to_delete),
            QMessageBox.information(self.app, "Clean", "Files cleaned successfully!"),
            dialog.accept()
        ))
        cancel_btn.clicked.connect(dialog.reject)

        button_layout.addWidget(yes_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        dialog.setLayout(layout)
        dialog.exec()
