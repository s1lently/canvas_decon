"""Merged widgets: delegates, toast, toggle, progress"""
from PyQt6.QtWidgets import (QStyledItemDelegate, QWidget, QLabel, QHBoxLayout,
                              QVBoxLayout, QGraphicsDropShadowEffect, QCheckBox,
                              QProgressBar, QTextEdit, QSplitter, QTabWidget)
from PyQt6.QtGui import QPainter, QColor, QFont, QPen
from PyQt6.QtCore import (Qt, QPoint, QRect, QSize, QTimer, QPropertyAnimation,
                          QEasingCurve, pyqtProperty, QRectF, QPointF)
from datetime import datetime


# ============== DELEGATES ==============

class FileItemDelegate(QStyledItemDelegate):
    """Green dot indicator for files that exist locally, blue dot for md reports"""
    def paint(self, painter, option, index):
        super().paint(painter, option, index)

        has_file = index.data(Qt.ItemDataRole.UserRole)
        item_data = index.data(Qt.ItemDataRole.UserRole + 1)
        has_report = item_data.get('has_report', False) if isinstance(item_data, dict) else False

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        x_base = option.rect.right() - 15
        y = option.rect.center().y()

        if has_file:
            painter.setBrush(QColor(34, 197, 94))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPoint(x_base, y), 5, 5)

        if has_report:
            x_report = x_base - 14
            painter.setBrush(QColor(59, 130, 246))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPoint(x_report, y), 5, 5)

        painter.restore()

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        size.setHeight(max(size.height(), 32))
        return size


class TodoItemDelegate(QStyledItemDelegate):
    """Custom delegate for TODO items with colored indicator dots and type labels"""
    DOTS = [
        ('automatable', QColor(239, 68, 68)),
        ('discussion', QColor(59, 130, 246)),
        ('quiz', QColor(168, 85, 247)),
        ('homework', QColor(234, 179, 8))
    ]

    TYPE_LABELS = {
        'homework': 'HW',
        'quiz': 'QZ',
        'discussion': 'DS'
    }

    COURSE_COLORS = {
        'CMPSC': QColor(239, 68, 68),    # red
        'MATH': QColor(245, 158, 11),    # orange
        'CHEM': QColor(168, 85, 247),    # purple
        'BISC': QColor(16, 185, 129),    # green
        'A-I': QColor(59, 130, 246),     # blue
    }

    def __init__(self, parent=None, history_mode=False, launcher_mode=False):
        super().__init__(parent)
        self.history_mode = history_mode
        self.launcher_mode = launcher_mode

    def paint(self, p, opt, idx):
        from PyQt6.QtWidgets import QStyle
        is_selected = opt.state & QStyle.StateFlag.State_Selected

        if self.launcher_mode:
            self._paint_launcher_card(p, opt, idx)
            return

        todo = idx.data(Qt.ItemDataRole.UserRole + 1)
        urgency_color = None
        if todo and isinstance(todo, dict):
            due_date = todo.get('due_date') or todo.get('assignment_details', {}).get('due_at')
            if due_date:
                try:
                    dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                    now = datetime.now(dt.tzinfo)
                    hours_left = (dt - now).total_seconds() / 3600

                    if self.history_mode and hours_left <= 0:
                        alpha = 255 if is_selected else 120
                        urgency_color = QColor(59, 130, 246, alpha)
                    elif not self.history_mode:
                        if hours_left <= 0:
                            r, g, base_alpha = 100, 0, 150
                        else:
                            t = min(hours_left / 168, 1.0)
                            import math
                            urgency = math.exp(-3 * t)
                            r = int(urgency ** 0.7 * 100)
                            g = int((1 - urgency ** 1.5) * 100)
                            base_alpha = int(60 + urgency * 90)
                        alpha = 255 if is_selected else base_alpha
                        urgency_color = QColor(r, g, 0, alpha)
                except: pass

        if urgency_color:
            p.fillRect(opt.rect, urgency_color)

        opt_copy = opt.__class__(opt)
        if is_selected:
            opt_copy.state &= ~QStyle.StateFlag.State_Selected
        opt_copy.state &= ~QStyle.StateFlag.State_MouseOver
        super().paint(p, opt_copy, idx)

        m = idx.data(Qt.ItemDataRole.UserRole)
        if not m or 'dots' not in m: return
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        x_dot = opt.rect.right() - 10
        y = opt.rect.center().y()

        active_types = [(key, color) for key, color in self.DOTS if m['dots'].get(key)]

        if active_types:
            x = x_dot
            for key, color in active_types:
                x -= 10
                p.setPen(QColor(0, 0, 0))
                p.setBrush(color)
                p.drawEllipse(QPoint(x + 5, y), 5, 5)
                x -= 6

            label_x = x - 5

            label_font = QFont(p.font())
            label_font.setPointSize(8)
            label_font.setBold(True)
            p.setFont(label_font)

            p.setPen(QColor(220, 220, 220))
            for key, color in active_types:
                label = self.TYPE_LABELS.get(key, '')
                if label:
                    label_rect = p.fontMetrics().boundingRect(label)
                    label_x -= label_rect.width()
                    p.drawText(QRect(label_x, opt.rect.top(), label_rect.width(), opt.rect.height()),
                              Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, label)
                    label_x -= 4

            if todo and isinstance(todo, dict):
                due_date = todo.get('due_date') or todo.get('assignment_details', {}).get('due_at')
                if due_date:
                    try:
                        dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                        due_text = dt.strftime('%m/%d')
                        date_font = QFont(p.font())
                        date_font.setPointSize(8)
                        p.setFont(date_font)
                        p.setPen(QColor(180, 180, 180))
                        date_text_rect = p.fontMetrics().boundingRect(due_text)
                        date_x = label_x - date_text_rect.width() - 6
                        p.drawText(QRect(date_x, opt.rect.top(), date_text_rect.width(), opt.rect.height()),
                                  Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, due_text)
                    except: pass

        p.restore()

    def _paint_launcher_card(self, p, opt, idx):
        """Paint launcher-style card with course code, task name, date, and type tag"""
        from PyQt6.QtWidgets import QStyle
        import math

        is_selected = opt.state & QStyle.StateFlag.State_Selected
        todo = idx.data(Qt.ItemDataRole.UserRole + 1)
        if not todo:
            return

        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Card geometry with margins
        margin = 4
        card_rect = opt.rect.adjusted(margin, margin, -margin, -margin)

        # Background
        bg_color = QColor(34, 27, 33) if is_selected else QColor(24, 27, 33)
        p.setBrush(bg_color)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(card_rect, 12, 12)

        # Left border (course color)
        course_name = todo.get('course_name', '')
        course_prefix = course_name.split()[0] if course_name else ''
        border_color = self.COURSE_COLORS.get(course_prefix, QColor(59, 130, 246))
        border_rect = QRectF(card_rect.left(), card_rect.top(), 4, card_rect.height())
        p.setBrush(border_color)
        p.drawRoundedRect(border_rect, 2, 2)

        # Text area
        text_x = card_rect.left() + 20
        text_y = card_rect.top() + 10
        text_width = card_rect.width() - 140

        # Course code (small, gray, monospace)
        code_font = QFont('SF Mono, Consolas, monospace')
        code_font.setPointSize(9)
        p.setFont(code_font)
        p.setPen(QColor(139, 148, 158))
        p.drawText(QRectF(text_x, text_y, text_width, 16),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                   course_name)

        # Task name (normal size, white)
        task_font = QFont()
        task_font.setPointSize(10)
        task_font.setWeight(QFont.Weight.Medium)
        p.setFont(task_font)
        p.setPen(QColor(224, 224, 224))
        task_name = todo.get('name', '')
        p.drawText(QRectF(text_x, text_y + 20, text_width, 20),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   task_name)

        # Right side: date and type tag
        right_x = card_rect.right() - 10
        right_y = card_rect.center().y()

        # Type tag (small, gray background)
        m = idx.data(Qt.ItemDataRole.UserRole)
        type_label = ''
        if m and 'dots' in m:
            dots = m['dots']
            if dots.get('quiz'):
                type_label = 'QZ'
            elif dots.get('discussion'):
                type_label = 'DB'
            else:
                type_label = 'HW'

        tag_font = QFont()
        tag_font.setPointSize(8)
        p.setFont(tag_font)
        tag_width = 24
        tag_height = 18
        tag_rect = QRectF(right_x - tag_width, right_y - tag_height/2, tag_width, tag_height)
        p.setBrush(QColor(255, 255, 255, 26))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(tag_rect, 4, 4)
        p.setPen(QColor(139, 148, 158))
        p.drawText(tag_rect, Qt.AlignmentFlag.AlignCenter, type_label)

        # Date (colored by urgency) with flame icon for urgent tasks
        due_date = todo.get('due_date') or todo.get('assignment_details', {}).get('due_at')
        if due_date:
            try:
                dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                now = datetime.now(dt.tzinfo)
                hours_left = (dt - now).total_seconds() / 3600

                date_text = dt.strftime('%m/%d')
                show_flame = False

                # Color by urgency levels
                if hours_left <= 0:
                    date_color = QColor(239, 68, 68)  # red (overdue)
                    show_flame = True
                elif hours_left <= 24:
                    date_color = QColor(239, 68, 68)  # red (<24h)
                    show_flame = True
                elif hours_left <= 72:  # 1-3 days
                    date_color = QColor(245, 158, 11)  # orange
                elif hours_left <= 168:  # 3-7 days
                    date_color = QColor(234, 179, 8)  # yellow
                else:
                    date_color = QColor(139, 148, 158)  # gray

                date_font = QFont()
                date_font.setPointSize(9)
                date_font.setBold(True)
                p.setFont(date_font)
                p.setPen(date_color)

                date_rect = p.fontMetrics().boundingRect(date_text)
                flame_width = 12 if show_flame else 0
                total_width = date_rect.width() + flame_width + (3 if show_flame else 0)
                date_x = right_x - tag_width - total_width - 10

                # Draw date text
                p.drawText(QRectF(date_x, right_y - 10, date_rect.width(), 20),
                          Qt.AlignmentFlag.AlignCenter, date_text)

                # Draw flame icon for urgent tasks
                if show_flame:
                    flame_font = QFont()
                    flame_font.setPointSize(11)
                    p.setFont(flame_font)
                    flame_x = date_x + date_rect.width() + 3
                    p.drawText(QRectF(flame_x, right_y - 10, flame_width, 20),
                              Qt.AlignmentFlag.AlignCenter, '🔥')
            except:
                pass

        p.restore()

    def sizeHint(self, opt, idx):
        s = super().sizeHint(opt, idx)
        if self.launcher_mode:
            s.setHeight(max(s.height(), 60))  # Taller cards for launcher
        else:
            s.setHeight(max(s.height(), 36))
        # Use full available width - no width constraint on cards
        if hasattr(opt, 'rect'):
            s.setWidth(opt.rect.width())
        return s


class CourseItemDelegate(QStyledItemDelegate):
    """Delegate for launcher course list - shows course name and code"""
    def paint(self, p, opt, idx):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Get course name
        course_name = idx.data(Qt.ItemDataRole.DisplayRole)
        if not course_name:
            p.restore()
            return

        # Split into name and details (assuming format: "Course Name (CODE 123)")
        # Or just use the full name if no details
        y_base = opt.rect.top() + 18
        x = opt.rect.left()

        # Course name (large, white)
        name_font = QFont()
        name_font.setPointSize(13)
        name_font.setWeight(QFont.Weight.DemiBold)
        p.setFont(name_font)
        p.setPen(QColor(224, 224, 224))
        p.drawText(QRectF(x, y_base, opt.rect.width(), 20),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   course_name)

        # Course details stored in UserRole if available
        details = idx.data(Qt.ItemDataRole.UserRole)
        if details:
            detail_font = QFont('SF Mono, Consolas, monospace')
            detail_font.setPointSize(10)
            p.setFont(detail_font)
            p.setPen(QColor(139, 148, 158))
            p.drawText(QRectF(x, y_base + 22, opt.rect.width(), 18),
                      Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                      details)

        # Bottom border line (subtle divider) - thicker and more spacing
        p.setPen(QPen(QColor(255, 255, 255, 20), 2))  # Thicker line, slightly more opaque
        p.drawLine(QPoint(opt.rect.left(), opt.rect.bottom() - 1),
                   QPoint(opt.rect.right(), opt.rect.bottom() - 1))

        p.restore()

    def sizeHint(self, opt, idx):
        return QSize(opt.rect.width(), 70)  # Increased from 58 for more spacing


# ============== TOAST ==============

class ToastNotification(QWidget):
    """Next.js style toast notification"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.styles = {
            'success': {'icon': '●', 'icon_color': '#10b981', 'bg': 'rgba(10, 10, 10, 0.95)', 'text': '#e5e5e5', 'glow': QColor(16, 185, 129, 60)},
            'info': {'icon': '●', 'icon_color': '#3b82f6', 'bg': 'rgba(10, 10, 10, 0.95)', 'text': '#e5e5e5', 'glow': QColor(59, 130, 246, 60)},
            'warning': {'icon': '●', 'icon_color': '#f59e0b', 'bg': 'rgba(10, 10, 10, 0.95)', 'text': '#e5e5e5', 'glow': QColor(245, 158, 11, 60)},
            'error': {'icon': '●', 'icon_color': '#ef4444', 'bg': 'rgba(10, 10, 10, 0.95)', 'text': '#e5e5e5', 'glow': QColor(239, 68, 68, 60)}
        }

        self.container = QWidget(self)
        self.container_layout = QHBoxLayout(self.container)
        self.container_layout.setContentsMargins(18, 14, 18, 14)
        self.container_layout.setSpacing(14)

        self.icon_label = QLabel()
        self.icon_label.setFont(QFont('Arial', 16, QFont.Weight.Bold))
        self.icon_label.setFixedSize(24, 24)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.text_label = QLabel()
        # Use platform-appropriate font (Segoe UI on Windows, SF Pro on macOS)
        import sys
        if sys.platform == 'win32':
            toast_font = QFont('Segoe UI', 13, QFont.Weight.Medium)
        elif sys.platform == 'darwin':
            toast_font = QFont('.AppleSystemUIFont', 13, QFont.Weight.Medium)
        else:
            toast_font = QFont('Arial', 13, QFont.Weight.Medium)
        self.text_label.setFont(toast_font)

        self.container_layout.addWidget(self.icon_label)
        self.container_layout.addWidget(self.text_label)
        self.container_layout.addStretch()

        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(30)
        self.shadow.setOffset(0, 6)
        self.shadow.setColor(QColor(0, 0, 0, 200))
        self.container.setGraphicsEffect(self.shadow)

        self.slide_in_animation = QPropertyAnimation(self, b"pos")
        self.slide_in_animation.setDuration(500)
        self.slide_in_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.slide_out_animation = QPropertyAnimation(self, b"pos")
        self.slide_out_animation.setDuration(400)
        self.slide_out_animation.setEasingCurve(QEasingCurve.Type.InBack)
        self.slide_out_animation.finished.connect(self.deleteLater)

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.slide_out)

    def show_message(self, message, msg_type='success', duration=3000):
        style = self.styles.get(msg_type, self.styles['info'])

        self.icon_label.setText(style['icon'])
        self.icon_label.setStyleSheet(f"color: {style['icon_color']};")

        self.text_label.setText(message)
        self.text_label.setStyleSheet(f"color: {style['text']}; font-weight: 500; letter-spacing: 0.3px;")

        self.container.setStyleSheet(f"""
            QWidget {{
                background: {style['bg']};
                border: none;
                border-radius: 14px;
            }}
        """)

        self.shadow.setColor(QColor(0, 0, 0, 200))
        self.shadow.setBlurRadius(30)

        self.container.adjustSize()
        self.setFixedSize(self.container.size())

        parent = self.parent()
        if parent:
            parent_rect = parent.geometry()
            start_x = parent_rect.width() + 50
            start_y = 24
            end_x = parent_rect.width() - self.width() - 24
            end_y = 24
            exit_x = parent_rect.width() + 50
            exit_y = 10

            self.start_pos = QPoint(start_x, start_y)
            self.end_pos = QPoint(end_x, end_y)
            self.exit_pos = QPoint(exit_x, exit_y)

            self.move(self.start_pos)
            self.show()

            self.slide_in_animation.setStartValue(self.start_pos)
            self.slide_in_animation.setEndValue(self.end_pos)
            self.slide_in_animation.start()

            self.timer.start(duration)

    def slide_out(self):
        self.slide_out_animation.setStartValue(self.pos())
        self.slide_out_animation.setEndValue(self.exit_pos)
        self.slide_out_animation.start()


def show_toast(parent, message, msg_type='success', duration=3000):
    """Show toast notification"""
    toast = ToastNotification(parent)
    toast.show_message(message, msg_type, duration)
    return toast


# ============== IOS TOGGLE ==============

class IOSToggle(QCheckBox):
    """iOS-style animated toggle switch"""

    def __init__(self, parent=None, width=60, height=28):
        super().__init__(parent)
        self.setFixedSize(width, height)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._bg_color_off = QColor("#2a2a2a")
        self._bg_color_on = QColor("#3b82f6")
        self._circle_color = QColor("#ffffff")
        self._border_color = QColor("#1a1a1a")

        self._circle_position = 3
        self._animation = QPropertyAnimation(self, b"circle_position", self)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._animation.setDuration(200)

        self.stateChanged.connect(self._start_animation)

    @pyqtProperty(float)
    def circle_position(self):
        return self._circle_position

    @circle_position.setter
    def circle_position(self, pos):
        self._circle_position = pos
        self.update()

    def _start_animation(self, state):
        self._animation.stop()
        if state == Qt.CheckState.Checked.value:
            self._animation.setEndValue(self.width() - self.height() + 3)
        else:
            self._animation.setEndValue(3)
        self._animation.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg_rect = QRectF(0, 0, self.width(), self.height())
        bg_color = self._bg_color_on if self.isChecked() else self._bg_color_off

        painter.setBrush(bg_color)
        painter.setPen(QPen(self._border_color, 1))
        painter.drawRoundedRect(bg_rect, self.height() / 2, self.height() / 2)

        circle_size = self.height() - 6
        circle_rect = QRectF(self._circle_position, 3, circle_size, circle_size)

        painter.setBrush(self._circle_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(circle_rect)

    def sizeHint(self):
        return self.minimumSize()

    def hitButton(self, pos):
        return self.contentsRect().contains(pos)


# ============== PROGRESS ==============

class ProgressWidget(QWidget):
    """Compact progress indicator with text and progress bar"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(3)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 12px; color: #ccc;")
        self.layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(15)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555;
                border-radius: 3px;
                background-color: #2a2a2a;
                text-align: center;
                font-size: 10px;
                color: #ccc;
            }
            QProgressBar::chunk {
                background-color: #3a7ca5;
                border-radius: 2px;
            }
        """)
        self.layout.addWidget(self.progress_bar)

    def update_progress(self, current, total, status_text=""):
        if total == 0:
            self.progress_bar.setRange(0, 0)
            self.progress_bar.setFormat("")
        else:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
            self.progress_bar.setFormat(f"{current}/{total}")

        if status_text:
            self.status_label.setText(status_text)

    def set_text_only(self, text):
        self.status_label.setText(text)
        self.progress_bar.hide()


def create_console_with_progress(console_tab_widget, tab_name):
    """Create console tab with embedded progress widget"""
    splitter = QSplitter(Qt.Orientation.Vertical)

    progress_widget = ProgressWidget()
    progress_widget.setMaximumHeight(60)

    console_widget = QTextEdit()
    console_widget.setReadOnly(True)
    console_widget.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: 'Courier New', monospace; font-size: 11px;")

    splitter.addWidget(progress_widget)
    splitter.addWidget(console_widget)
    splitter.setSizes([50, 350])

    console_tab_widget.addTab(splitter, tab_name)
    console_tab_widget.setCurrentWidget(splitter)

    return console_widget, progress_widget
