"""Learn Sitting Renderer - Creates 3-tab structure for Textbook in CourseDetail"""
import os
import sys
import shutil
import threading
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                              QListWidget, QPushButton, QLabel, QComboBox,
                              QTextEdit, QTextBrowser, QGroupBox, QFormLayout,
                              QListWidgetItem, QMessageBox, QAbstractItemView,
                              QFrame, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from gui.learn.cfgLearnPrefs import (load_preferences, save_preferences,
                                    get_available_products, get_available_models,
                                    get_resolved_product_model, set_product, set_model,
                                    refresh_available_models)


class DropListWidget(QListWidget):
    """QListWidget with drag-and-drop support for file uploads"""

    def __init__(self, target_dir_callback, refresh_callback, parent=None):
        super().__init__(parent)
        self.target_dir_callback = target_dir_callback
        self.refresh_callback = refresh_callback
        self.setAcceptDrops(True)
        self.setDragEnabled(False)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        # Enable drops on viewport as well
        self.viewport().setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """Also need to handle drag move to show the drop cursor"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            target_dir = self.target_dir_callback()
            if not os.path.exists(target_dir):
                try:
                    os.makedirs(target_dir, exist_ok=True)
                except Exception as e:
                    print(f"[ERROR] Failed to create target dir: {e}")
                    return

            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if os.path.isfile(file_path):
                    filename = os.path.basename(file_path)
                    dest_path = os.path.join(target_dir, filename)
                    try:
                        shutil.copy2(file_path, dest_path)
                        print(f"[DRAG-DROP] Copied: {filename} → {target_dir}")
                    except Exception as e:
                        print(f"[DRAG-DROP] Error copying {filename}: {e}")
            event.acceptProposedAction()
            self.refresh_callback()
        else:
            event.ignore()


class FileLoaderWorker(QObject):
    """Worker to load file lists in background"""
    finished = pyqtSignal(list, list)  # textbook_files, learn_items

    def __init__(self, textbook_dir, learn_dir):
        super().__init__()
        self.textbook_dir = textbook_dir
        self.learn_dir = learn_dir

    def run(self):
        # Load textbook files
        textbook_files = []
        if os.path.exists(self.textbook_dir):
            textbook_files = sorted([f for f in os.listdir(self.textbook_dir)
                                   if os.path.isfile(os.path.join(self.textbook_dir, f))])

        # Load learn files
        learn_items = []
        if os.path.exists(self.learn_dir):
            files = []
            for item in os.listdir(self.learn_dir):
                item_path = os.path.join(self.learn_dir, item)
                if os.path.isfile(item_path):
                    files.append(item)

            # Natural sort
            import re
            def natural_sort_key(s):
                return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', s)]

            reports_dir = os.path.join(self.learn_dir, 'reports')
            
            for filename in sorted(files, key=natural_sort_key):
                base_name = os.path.splitext(filename)[0]
                report_path = os.path.join(reports_dir, f"{base_name}.md")
                has_report = os.path.exists(report_path)
                learn_items.append((filename, has_report))

        self.finished.emit(textbook_files, learn_items)


class LearnSittingWidget(QWidget):
    """3-Tab widget for Textbook: Tab1=Files, Tab2=Advanced/Prompts"""

    files_loaded = pyqtSignal(list, list)

    def __init__(self, canvas_app, course_detail_mgr, parent=None):
        super().__init__(parent)
        self.canvas_app = canvas_app
        self.course_detail_mgr = course_detail_mgr
        self.prefs = load_preferences()
        
        # Loading state
        self.is_loading = False
        
        # Connect signal
        self.files_loaded.connect(self._on_files_loaded)

        self.init_ui()
        
        # Defer data loading to fix UI lag
        QTimer.singleShot(10, self.load_data)

    def init_ui(self):
        """Initialize UI structure"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #444;
                border-radius: 4px;
                background: #1e1e1e;
            }
            QTabBar::tab {
                padding: 8px 16px;
                margin-right: 2px;
                background: #2d2d2d;
                color: #aaa;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #3b82f6;
                color: white;
                font-weight: bold;
            }
        """)

        # Create tabs
        self.tab1 = self.create_tab1_textbook()
        self.tab2 = self.create_tab2_advanced() # Renamed from Tab 3

        self.tab_widget.addTab(self.tab1, "📚 Textbook & Learn")
        self.tab_widget.addTab(self.tab2, "⚙️ Prompt Settings")

        layout.addWidget(self.tab_widget)

    # ========== TAB 1: Textbook Files & Model Selection ==========
    def create_tab1_textbook(self):
        """Create Tab 1: Model Header + Textbook List + Learn List"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # --- 1. Model Selection Header ---
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border-radius: 6px;
                border: 1px solid #3e3e42;
            }
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(10, 10, 10, 10)
        header_layout.setSpacing(15)

        # Product Combo
        prod_layout = QVBoxLayout()
        prod_layout.setSpacing(2)
        prod_label = QLabel("Product")
        prod_label.setStyleSheet("color: #aaa; font-size: 11px;")
        self.header_product_combo = QComboBox()
        self.header_product_combo.setMinimumWidth(100)
        self.header_product_combo.addItems(get_available_products())
        self.header_product_combo.currentTextChanged.connect(self.on_header_product_changed)
        prod_layout.addWidget(prod_label)
        prod_layout.addWidget(self.header_product_combo)
        header_layout.addLayout(prod_layout)

        # Model Combo
        model_layout = QVBoxLayout()
        model_layout.setSpacing(2)
        model_label = QLabel("Model")
        model_label.setStyleSheet("color: #aaa; font-size: 11px;")
        self.header_model_combo = QComboBox()
        self.header_model_combo.setMinimumWidth(200)
        self.header_model_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.header_model_combo.currentTextChanged.connect(self.on_header_model_changed)
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.header_model_combo)
        header_layout.addLayout(model_layout, 1) # Stretch

        # Resolved Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_label = QLabel("Actual Model")
        info_label.setStyleSheet("color: #aaa; font-size: 11px;")
        self.resolved_model_label = QLabel("-")
        self.resolved_model_label.setStyleSheet("color: #10b981; font-weight: bold; font-size: 12px;")
        info_layout.addWidget(info_label)
        info_layout.addWidget(self.resolved_model_label)
        header_layout.addLayout(info_layout)

        # API Settings Button
        btn_api = QPushButton("⚙️ API")
        btn_api.setToolTip("Open API Settings")
        btn_api.setFixedSize(60, 35)
        btn_api.clicked.connect(lambda: self.canvas_app.sitting_handler.show())
        header_layout.addWidget(btn_api)

        # Refresh Models Button
        btn_refresh = QPushButton("🔄")
        btn_refresh.setToolTip("Refresh Model List from API")
        btn_refresh.setFixedSize(40, 35)
        btn_refresh.clicked.connect(self.on_refresh_models)
        header_layout.addWidget(btn_refresh)

        layout.addWidget(header_frame)

        # --- 2. Lists Splitter ---
        # We use a VBox with 2 Groups
        
        # Textbook files group
        textbook_group = QGroupBox("Textbook Files (Drag & Drop PDF here)")
        textbook_group.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #444; margin-top: 6px; padding-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        textbook_layout = QVBoxLayout(textbook_group)

        self.textbook_list = DropListWidget(
            target_dir_callback=lambda: self.course_detail_mgr.get_textbook_dir(),
            refresh_callback=self.reload_files_async
        )
        self.textbook_list.setMinimumHeight(150)
        textbook_layout.addWidget(self.textbook_list)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_open_folder = QPushButton("📂 Open Folder")
        btn_decon = QPushButton("📄 Decon Textbook")
        btn_load_decon = QPushButton("📥 Load From Decon")

        btn_open_folder.clicked.connect(self.on_open_textbook_folder)
        btn_decon.clicked.connect(self.on_decon_textbook)
        btn_load_decon.clicked.connect(self.on_load_from_decon)

        btn_layout.addWidget(btn_open_folder)
        btn_layout.addWidget(btn_decon)
        btn_layout.addWidget(btn_load_decon)
        btn_layout.addStretch()

        textbook_layout.addLayout(btn_layout)
        layout.addWidget(textbook_group)

        # Learn materials group
        learn_group = QGroupBox("Learn Materials (Generated Reports)")
        learn_group.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #444; margin-top: 6px; padding-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        learn_layout = QVBoxLayout(learn_group)

        self.learn_list = QListWidget()
        self.learn_list.setMinimumHeight(150)
        learn_layout.addWidget(self.learn_list)

        # Buttons
        learn_btn_layout = QHBoxLayout()
        btn_open_learn = QPushButton("📂 Open Learn Folder")
        btn_batch = QPushButton("🚀 Batch Generate All")

        btn_open_learn.clicked.connect(self.on_open_learn_folder)
        btn_batch.clicked.connect(self.on_batch_generate)

        learn_btn_layout.addWidget(btn_open_learn)
        learn_btn_layout.addWidget(btn_batch)
        learn_btn_layout.addStretch()

        learn_layout.addLayout(learn_btn_layout)
        layout.addWidget(learn_group)

        return tab

    # ========== TAB 2: Prompt Settings (Formerly Tab 3) ==========
    def create_tab2_advanced(self):
        """Create Tab 2: Advanced settings editor"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Prompt editor group
        prompt_group = QGroupBox("Prompt Template Editor")
        prompt_layout = QVBoxLayout(prompt_group)

        prompt_layout.addWidget(QLabel("Template Type:"))
        self.prompt_type_combo = QComboBox()
        self.prompt_type_combo.setMinimumHeight(30)
        self.prompt_type_combo.addItems([
            "Text Files (Python, JS, etc.)",
            "PDF Documents",
            "CSV Data Files"
        ])
        self.prompt_type_combo.currentIndexChanged.connect(self.on_prompt_type_changed)
        prompt_layout.addWidget(self.prompt_type_combo)

        self.prompt_editor = QTextEdit()
        self.prompt_editor.setMinimumHeight(300)
        self.prompt_editor.setFont(QFont("Consolas, Monaco, monospace", 10))
        prompt_layout.addWidget(self.prompt_editor)

        # Buttons
        prompt_btn_layout = QHBoxLayout()
        btn_save = QPushButton("💾 Save Settings")
        btn_reset_type = QPushButton("🔄 Reset Template")
        
        btn_save.clicked.connect(self.on_save_all)
        btn_reset_type.clicked.connect(self.on_reset_prompt_type)

        prompt_btn_layout.addWidget(btn_save)
        prompt_btn_layout.addWidget(btn_reset_type)
        prompt_btn_layout.addStretch()

        prompt_layout.addLayout(prompt_btn_layout)
        layout.addWidget(prompt_group)

        return tab

    # ========== Data Loading ==========
    def load_data(self):
        """Initial data load"""
        # Load preferences into header
        product = self.prefs.get('product', 'Auto')
        model = self.prefs.get('model', 'Auto')
        
        self.header_product_combo.blockSignals(True)
        self.header_model_combo.blockSignals(True)
        
        self.header_product_combo.setCurrentText(product)
        
        # Populate models based on product
        models = get_available_models(product)
        self.header_model_combo.clear()
        self.header_model_combo.addItems(models)
        self.header_model_combo.setCurrentText(model)
        
        self.header_product_combo.blockSignals(False)
        self.header_model_combo.blockSignals(False)
        
        self.update_resolved_model_display()

        # Load prompt editor (default to first type)
        self.on_prompt_type_changed(0)

        # Load files asynchronously
        self.reload_files_async()

    def reload_files_async(self):
        """Start async worker to load files"""
        self.textbook_list.clear()
        self.learn_list.clear()
        
        self.textbook_list.addItem("Loading...")
        self.learn_list.addItem("Loading...")
        self.textbook_list.setEnabled(False)
        self.learn_list.setEnabled(False)

        # Create thread and worker
        self.thread = threading.Thread(target=self._worker_run, daemon=True)
        self.thread.start()

    def _worker_run(self):
        """Background worker execution"""
        worker = FileLoaderWorker(
            self.course_detail_mgr.get_textbook_dir(),
            self.course_detail_mgr.get_learn_dir()
        )
        # Connect signal in a thread-safe way is tricky without full QThread
        # So we use QMetaObject.invokeMethod or a simpler approach:
        # execute the logic and then use QTimer to schedule update on main thread
        
        # Actually, let's just run the logic here and schedule the update
        textbook_files = []
        textbook_dir = self.course_detail_mgr.get_textbook_dir()
        if os.path.exists(textbook_dir):
            textbook_files = sorted([f for f in os.listdir(textbook_dir)
                                   if os.path.isfile(os.path.join(textbook_dir, f))])

        learn_items = []
        learn_dir = self.course_detail_mgr.get_learn_dir()
        if os.path.exists(learn_dir):
            files = []
            for item in os.listdir(learn_dir):
                if os.path.isfile(os.path.join(learn_dir, item)):
                    files.append(item)

            import re
            def natural_sort_key(s):
                return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', s)]

            reports_dir = os.path.join(learn_dir, 'reports')
            for filename in sorted(files, key=natural_sort_key):
                base_name = os.path.splitext(filename)[0]
                report_path = os.path.join(reports_dir, f"{base_name}.md")
                has_report = os.path.exists(report_path)
                learn_items.append((filename, has_report))

        # Emit signal to update UI on main thread
        self.files_loaded.emit(textbook_files, learn_items)

    def _on_files_loaded(self, textbook_files, learn_items):
        """Update UI with loaded files"""
        self.textbook_list.clear()
        self.learn_list.clear()
        self.textbook_list.setEnabled(True)
        self.learn_list.setEnabled(True)

        for f in textbook_files:
            self.textbook_list.addItem(f)
        
        if not textbook_files:
            self.textbook_list.addItem("(No files found - Drag PDFs here)")

        for filename, has_report in learn_items:
            item_text = f"{'✅' if has_report else '⭕'} {filename}"
            self.learn_list.addItem(item_text)
            
        if not learn_items:
            self.learn_list.addItem("(No materials found)")

    # ========== Event Handlers ==========

    def on_header_product_changed(self, product):
        """Product changed in header"""
        self.header_model_combo.blockSignals(True)
        self.header_model_combo.clear()
        models = get_available_models(product)
        self.header_model_combo.addItems(models)
        self.header_model_combo.blockSignals(False)

        set_product(product)
        
        # Auto select first model
        if models:
            self.header_model_combo.setCurrentIndex(0)
            set_model(models[0])
            
        self.update_resolved_model_display()

    def on_header_model_changed(self, model):
        """Model changed in header"""
        if not model: return
        set_model(model)
        self.update_resolved_model_display()

    def update_resolved_model_display(self):
        """Update the 'Actual Model' label"""
        try:
            product, model = get_resolved_product_model()
            self.resolved_model_label.setText(f"{model}")
        except Exception as e:
            self.resolved_model_label.setText("Error")

    def on_open_textbook_folder(self):
        """Open textbook folder"""
        import subprocess
        folder = self.course_detail_mgr.get_textbook_dir()
        if not os.path.exists(folder): os.makedirs(folder)
        subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', folder])

    def on_decon_textbook(self):
        self.canvas_app.course_detail_handler.on_decon_textbook_clicked()

    def on_load_from_decon(self):
        from gui.core import utilQtInteract as qt_interact
        qt_interact.on_load_from_decon_clicked(self.canvas_app)
        self.reload_files_async()

    def on_open_learn_folder(self):
        import subprocess
        folder = self.course_detail_mgr.get_learn_dir()
        if not os.path.exists(folder): os.makedirs(folder)
        subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', folder])

    def on_refresh_models(self):
        """Refresh models from API"""
        from gui.widgets.rdrToast import show_toast
        
        try:
            # 1. Refresh data
            refresh_available_models()
            
            # 2. Update UI
            current_product = self.header_product_combo.currentText()
            current_model = self.header_model_combo.currentText()
            
            # Reload models for current product
            self.header_model_combo.blockSignals(True)
            self.header_model_combo.clear()
            models = get_available_models(current_product)
            self.header_model_combo.addItems(models)
            
            # Restore selection if possible, else select first
            if current_model in models:
                self.header_model_combo.setCurrentText(current_model)
            elif models:
                self.header_model_combo.setCurrentIndex(0)
                set_model(models[0])
                
            self.header_model_combo.blockSignals(False)
            self.update_resolved_model_display()
            
            show_toast(self.canvas_app, "Model list refreshed!", 'success', 2000)
            
        except Exception as e:
            print(f"Error refreshing models: {e}")
            show_toast(self.canvas_app, "Failed to refresh models", 'error', 3000)

    def on_batch_generate(self):
        # (Logic identical to previous, simplified for brevity)
        # Re-using existing batch logic structure
        from PyQt6.QtWidgets import QMessageBox
        import threading

        learn_dir = self.course_detail_mgr.get_learn_dir()
        reports_dir = os.path.join(learn_dir, 'reports')

        if not os.path.exists(learn_dir):
            QMessageBox.warning(self, "No Files", "Learn directory is empty.")
            return

        files = []
        for item in os.listdir(learn_dir):
            item_path = os.path.join(learn_dir, item)
            if os.path.isfile(item_path):
                base_name = os.path.splitext(item)[0]
                report_path = os.path.join(reports_dir, f"{base_name}.md")
                if not os.path.exists(report_path):
                    files.append((item, item_path))

        if not files:
            QMessageBox.information(self, "All Done", "All files already have learning reports!")
            return

        reply = QMessageBox.question(self, "Batch Generate", f"Generate reports for {len(files)} files?", 
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes: return

        from gui.core.utilQtInteract import _create_console_tab
        console = _create_console_tab(self.canvas_app.main_window.consoleTabWidget, "Batch Learn")

        def run_batch():
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'func'))
            from procLearnMaterial import learn_material
            
            console.append(f"🚀 Batch Learn: {len(files)} files")
            success_count = 0
            failed_files = []

            for i, (filename, file_path) in enumerate(files, 1):
                console.append(f"[{i}/{len(files)}] Processing: {filename}")
                try:
                    if learn_material(file_path, self.course_detail_mgr.course_dir, console, use_preferences=True):
                        success_count += 1
                    else:
                        failed_files.append(filename)
                except Exception as e:
                    failed_files.append(filename)
                    console.append(f"Error: {e}")

            from gui.widgets.rdrToast import show_toast
            show_toast(self.canvas_app, f"Completed: {success_count} success", 'success', 5000)
            
            # Safe UI update
            QTimer.singleShot(0, self.reload_files_async)

        threading.Thread(target=run_batch, daemon=True).start()

    def on_prompt_type_changed(self, index):
        prompt_types = ['text', 'pdf', 'csv']
        prompt_type = prompt_types[index]
        custom_prompt = self.prefs.get('prompts', {}).get(prompt_type)
        
        if custom_prompt:
            self.prompt_editor.setPlainText(custom_prompt)
        else:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'func'))
            from procLearnMaterial import DEFAULT_TEXT_PROMPT, DEFAULT_PDF_PROMPT, DEFAULT_CSV_PROMPT
            defaults = {'text': DEFAULT_TEXT_PROMPT, 'pdf': DEFAULT_PDF_PROMPT, 'csv': DEFAULT_CSV_PROMPT}
            self.prompt_editor.setPlainText(defaults.get(prompt_type, ""))

    def on_save_all(self):
        prompt_types = ['text', 'pdf', 'csv']
        prompt_type = prompt_types[self.prompt_type_combo.currentIndex()]
        prompt_text = self.prompt_editor.toPlainText().strip()
        
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'func'))
        from procLearnMaterial import DEFAULT_TEXT_PROMPT, DEFAULT_PDF_PROMPT, DEFAULT_CSV_PROMPT
        defaults = {'text': DEFAULT_TEXT_PROMPT, 'pdf': DEFAULT_PDF_PROMPT, 'csv': DEFAULT_CSV_PROMPT}

        if prompt_text != defaults.get(prompt_type, ""):
            set_prompt(prompt_type, prompt_text)
        else:
            set_prompt(prompt_type, None)
            
        from gui.widgets.rdrToast import show_toast
        show_toast(self.canvas_app, "Settings Saved", 'success', 2000)

    def on_reset_prompt_type(self):
        self.on_prompt_type_changed(self.prompt_type_combo.currentIndex())
