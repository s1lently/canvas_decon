"""
Mission Control - Global Task Manager
全局任务管理器，统一管理所有后台任务
设计风格：参考 Toast 的暗黑风格 (黑底 + 彩色圆点)
"""
import threading
import uuid
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QColor, QFont


class TaskCard(QFrame):
    """单个任务卡片"""
    dismissed = pyqtSignal(str)  # task_id

    def __init__(self, task_id, name, parent=None):
        super().__init__(parent)
        self.task_id = task_id
        self.name = name
        self._completed = False
        self._error = False

        self.setObjectName("TaskCard")
        self.setStyleSheet("""
            QFrame#TaskCard {
                background: rgba(20, 20, 20, 0.95);
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }
        """)
        self.setFixedHeight(72)
        self.setMinimumWidth(340)
        self.setMaximumWidth(340)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Status indicator (彩色圆点)
        self.status_dot = QLabel("●")
        self.status_dot.setFixedWidth(20)
        self.status_dot.setFont(QFont("Arial", 14))
        self.status_dot.setStyleSheet("color: #3b82f6; background: transparent;")  # Blue = running
        layout.addWidget(self.status_dot)

        # Content area
        content = QVBoxLayout()
        content.setSpacing(4)

        # Title row
        title_row = QHBoxLayout()
        self.title_label = QLabel(name)
        self.title_label.setFont(QFont("Inter", 11, QFont.Weight.DemiBold))
        self.title_label.setStyleSheet("color: #ffffff; background: transparent;")
        self.title_label.setWordWrap(False)
        title_row.addWidget(self.title_label, 1)

        # Speed badge (fixed width to prevent stretching)
        self.speed_label = QLabel("")
        self.speed_label.setFont(QFont("Inter", 9))
        self.speed_label.setStyleSheet("color: #666666; background: transparent;")
        self.speed_label.setFixedWidth(60)
        self.speed_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        title_row.addWidget(self.speed_label)

        content.addLayout(title_row)

        # Status row
        status_row = QHBoxLayout()
        self.status_label = QLabel("Starting...")
        self.status_label.setFont(QFont("Inter", 10))
        self.status_label.setStyleSheet("color: #888888; background: transparent;")
        self.status_label.setWordWrap(False)
        status_row.addWidget(self.status_label, 1)

        # Progress percentage (fixed width)
        self.progress_label = QLabel("0%")
        self.progress_label.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        self.progress_label.setStyleSheet("color: #3b82f6; background: transparent;")
        self.progress_label.setFixedWidth(45)
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        status_row.addWidget(self.progress_label)

        content.addLayout(status_row)

        # Progress bar (底部细线)
        self.progress_bar = QFrame()
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setStyleSheet("background: #3b82f6; border-radius: 1px;")
        self.progress_bar.setFixedWidth(0)
        content.addWidget(self.progress_bar)

        layout.addLayout(content, 1)

        # Dismiss button (完成后显示)
        self.dismiss_btn = QPushButton("×")
        self.dismiss_btn.setFixedSize(24, 24)
        self.dismiss_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dismiss_btn.setStyleSheet("""
            QPushButton {
                color: #666666;
                background: transparent;
                border: none;
                font-size: 16px;
                font-weight: bold;
                border-radius: 12px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
                color: #ffffff;
            }
        """)
        self.dismiss_btn.clicked.connect(lambda: self.dismissed.emit(self.task_id))
        self.dismiss_btn.hide()
        layout.addWidget(self.dismiss_btn)

    def update_progress(self, data):
        """更新进度"""
        if 'progress' in data:
            pct = data['progress']
            self.progress_label.setText(f"{pct}%")
            # 计算进度条宽��� (最大宽度约 280px)
            bar_width = int((pct / 100) * 280)
            self.progress_bar.setFixedWidth(bar_width)

            if pct >= 100 and not self._error:
                self._completed = True
                self.status_dot.setStyleSheet("color: #10b981; background: transparent;")  # Green
                self.progress_label.setStyleSheet("color: #10b981; background: transparent;")
                self.progress_bar.setStyleSheet("background: #10b981; border-radius: 1px;")
                self.dismiss_btn.show()

        if 'status' in data:
            self.status_label.setText(data['status'])

        if 'speed' in data:
            self.speed_label.setText(data['speed'])

        if 'error' in data:
            self._error = True
            self.status_dot.setStyleSheet("color: #ef4444; background: transparent;")  # Red
            self.progress_label.setStyleSheet("color: #ef4444; background: transparent;")
            self.progress_bar.setStyleSheet("background: #ef4444; border-radius: 1px;")
            self.status_label.setText(f"Error: {data['error']}")
            self.dismiss_btn.show()

    @property
    def is_done(self):
        return self._completed or self._error


class MissionControl(QWidget):
    """全局任务管理器窗口"""

    # Thread-safe signal for updates
    update_signal = pyqtSignal(str, dict)  # task_id, data

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mission Control")
        self.resize(380, 450)

        # Frameless + Translucent
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Task tracking
        self.tasks = {}  # task_id -> TaskCard
        self.callbacks = {}  # task_id -> on_success callback

        # Drag support
        self._drag_pos = None

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Container (for rounded corners + shadow)
        self.container = QFrame()
        self.container.setObjectName("MCContainer")
        self.container.setStyleSheet("""
            QFrame#MCContainer {
                background: rgba(10, 10, 10, 0.98);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
            }
        """)

        # Shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 180))
        self.container.setGraphicsEffect(shadow)

        main_layout.addWidget(self.container)

        # Container layout
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(16, 12, 16, 16)
        container_layout.setSpacing(12)

        # Header
        header = QHBoxLayout()

        title = QLabel("Mission Control")
        title.setFont(QFont("Inter", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: #ffffff; background: transparent;")
        header.addWidget(title)

        header.addStretch()

        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet("""
            QPushButton {
                color: #666666;
                background: transparent;
                border: none;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 8px;
            }
            QPushButton:hover { color: #ffffff; }
        """)
        clear_btn.clicked.connect(self.clear_completed)
        header.addWidget(clear_btn)

        # Close button (更明显)
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                color: #888888;
                background: rgba(255, 255, 255, 0.05);
                border: none;
                font-size: 18px;
                font-weight: bold;
                border-radius: 12px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.15);
                color: #ffffff;
            }
        """)
        close_btn.clicked.connect(self.hide)
        header.addWidget(close_btn)

        container_layout.addLayout(header)

        # Separator
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(255, 255, 255, 0.06);")
        container_layout.addWidget(sep)

        # Scroll area for tasks
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.2);
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)

        # Task container
        self.task_container = QWidget()
        self.task_layout = QVBoxLayout(self.task_container)
        self.task_layout.setContentsMargins(0, 0, 0, 0)
        self.task_layout.setSpacing(8)
        self.task_layout.addStretch()

        scroll.setWidget(self.task_container)
        container_layout.addWidget(scroll)

        # Empty state
        self.empty_label = QLabel("No active tasks")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setFont(QFont("Inter", 11))
        self.empty_label.setStyleSheet("color: #444444; background: transparent;")
        self.task_layout.insertWidget(0, self.empty_label)

        # Hint label at bottom
        import platform
        key = "Cmd" if platform.system() == "Darwin" else "Ctrl"
        hint_label = QLabel(f"{key}+M to toggle")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_label.setFont(QFont("Inter", 9))
        hint_label.setStyleSheet("color: #333333; background: transparent;")
        container_layout.addWidget(hint_label)

        # Connect signal
        self.update_signal.connect(self._handle_update)

    # === Drag Support ===
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def keyPressEvent(self, event):
        """Handle Ctrl+M to hide"""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_M:
            self.hide()
            event.accept()
            return
        super().keyPressEvent(event)

    # === Task Management ===
    def start_task(self, name, func, on_success=None):
        """启动后台任务

        Args:
            name: 任务名称
            func: 任务函数，接受 progress 参数 (TaskProgress instance)
            on_success: 成功后的回调
        """
        task_id = str(uuid.uuid4())

        # Create card
        card = TaskCard(task_id, name)
        card.dismissed.connect(self._remove_task)
        self.tasks[task_id] = card
        self.callbacks[task_id] = on_success

        # Add to layout (before stretch)
        self.task_layout.insertWidget(self.task_layout.count() - 1, card)
        self.empty_label.hide()

        # Show window
        self.show()
        self.raise_()

        # Start thread
        def wrapper():
            from func.utilProgress import TaskProgress
            try:
                progress = TaskProgress(callback=self._create_callback(task_id))
                func(progress=progress)
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.update_signal.emit(task_id, {'error': str(e)})

        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()

        return task_id

    def _create_callback(self, task_id):
        """创建线程安全的回调"""
        def callback(data):
            self.update_signal.emit(task_id, data)
        return callback

    def _handle_update(self, task_id, data):
        """处理更新 (主线程)"""
        if task_id not in self.tasks:
            return

        card = self.tasks[task_id]
        card.update_progress(data)

        # Check completion
        if data.get('progress') == 100 and not data.get('error'):
            on_success = self.callbacks.get(task_id)
            if on_success:
                try:
                    on_success()
                except Exception as e:
                    print(f"[WARN] on_success callback failed: {e}")
                self.callbacks[task_id] = None  # Clear to prevent double-call

    def _remove_task(self, task_id):
        """移除任务"""
        if task_id in self.tasks:
            card = self.tasks.pop(task_id)
            self.callbacks.pop(task_id, None)
            card.setParent(None)
            card.deleteLater()

            # Show empty state if no tasks
            if not self.tasks:
                self.empty_label.show()

    def clear_completed(self):
        """清除已完成/失败的任务"""
        to_remove = [tid for tid, card in self.tasks.items() if card.is_done]
        for tid in to_remove:
            self._remove_task(tid)

    def has_active_tasks(self):
        """是否有活跃任务"""
        return any(not card.is_done for card in self.tasks.values())

    def cleanup(self):
        """Clean up all tasks and callbacks for shutdown"""
        self.callbacks.clear()
        for card in list(self.tasks.values()):
            card.setParent(None)
            card.deleteLater()
        self.tasks.clear()

    def closeEvent(self, event):
        """Handle close event"""
        self.cleanup()
        super().closeEvent(event)
