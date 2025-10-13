"""Custom Qt delegates for rendering"""
from PyQt6.QtWidgets import QStyledItemDelegate
from PyQt6.QtGui import QPainter, QColor, QFont
from PyQt6.QtCore import Qt, QPoint, QRect
from datetime import datetime


class FileItemDelegate(QStyledItemDelegate):
    """Green dot indicator for files that exist locally"""
    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        if index.data(Qt.ItemDataRole.UserRole):
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            x, y = option.rect.right() - 15, option.rect.center().y()
            painter.setBrush(QColor(34, 197, 94))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPoint(x, y), 5, 5)
            painter.restore()

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        size.setHeight(max(size.height(), 32))
        return size


class TodoItemDelegate(QStyledItemDelegate):
    """Custom delegate for TODO items with colored indicator dots and type labels"""
    DOTS = [
        ('automatable', QColor(239, 68, 68)),   # Red
        ('discussion', QColor(59, 130, 246)),    # Blue
        ('quiz', QColor(168, 85, 247)),          # Purple
        ('homework', QColor(234, 179, 8))        # Yellow
    ]

    TYPE_LABELS = {
        'homework': 'HW',
        'quiz': 'QZ',
        'discussion': 'DS'
    }

    def __init__(self, parent=None, history_mode=False):
        super().__init__(parent)
        self.history_mode = history_mode

    def paint(self, p, opt, idx):
        # ONLY for TODO tab2: use urgency color instead of default blue/gray selection
        from PyQt6.QtWidgets import QStyle
        is_selected = opt.state & QStyle.StateFlag.State_Selected

        # Calculate urgency color FIRST (needed before painting)
        todo = idx.data(Qt.ItemDataRole.UserRole + 1)
        urgency_color = None
        if todo and isinstance(todo, dict):
            due_date = todo.get('due_date') or todo.get('assignment_details', {}).get('due_at')
            if due_date:
                try:
                    dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                    now = datetime.now(dt.tzinfo)
                    hours_left = (dt - now).total_seconds() / 3600

                    # History mode: past-due = blue * alpha
                    if self.history_mode and hours_left <= 0:
                        alpha = 255 if is_selected else 120
                        urgency_color = QColor(59, 130, 246, alpha)  # Blue
                    # Normal mode: urgency color
                    elif not self.history_mode:
                        if hours_left <= 0:
                            r, g, base_alpha = 100, 0, 150  # OVERDUE
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

        # STEP 1: Draw urgency background FIRST (bottom layer)
        if urgency_color:
            p.fillRect(opt.rect, urgency_color)

        # STEP 2: Draw default content (text, checkbox) ON TOP with disabled default backgrounds
        opt_copy = opt.__class__(opt)
        if is_selected:
            opt_copy.state &= ~QStyle.StateFlag.State_Selected
        opt_copy.state &= ~QStyle.StateFlag.State_MouseOver
        super().paint(p, opt_copy, idx)

        # STEP 3: Draw custom overlays (dots, labels, date) at the front
        m = idx.data(Qt.ItemDataRole.UserRole)
        if not m or 'dots' not in m: return
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Start position for dots (right side)
        x_dot = opt.rect.right() - 10
        y = opt.rect.center().y()

        # Collect active types and their labels
        active_types = [(key, color) for key, color in self.DOTS if m['dots'].get(key)]

        if active_types:
            # Draw dots first (to calculate total width)
            x = x_dot
            for key, color in active_types:
                x -= 10
                # Draw black border
                p.setPen(QColor(0, 0, 0))
                p.setBrush(color)
                p.drawEllipse(QPoint(x + 5, y), 5, 5)
                x -= 6

            # Now draw labels to the left of dots
            label_x = x - 5  # 5px gap from dots

            # Setup small font for labels
            label_font = QFont(p.font())
            label_font.setPointSize(8)
            label_font.setBold(True)
            p.setFont(label_font)

            # Draw labels from right to left (white text for visibility)
            p.setPen(QColor(220, 220, 220))  # Light gray text
            for key, color in active_types:
                label = self.TYPE_LABELS.get(key, '')
                if label:
                    # Calculate label width
                    label_rect = p.fontMetrics().boundingRect(label)
                    label_x -= label_rect.width()

                    # Draw label without color (for readability)
                    p.drawText(QRect(label_x, opt.rect.top(), label_rect.width(), opt.rect.height()),
                              Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, label)

                    label_x -= 4  # 4px gap between labels

            # Draw dueDate to the left of type labels (compact mm/dd format)
            if todo and isinstance(todo, dict):
                due_date = todo.get('due_date') or todo.get('assignment_details', {}).get('due_at')
                if due_date:
                    try:
                        # Parse ISO format and convert to mm/dd
                        dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                        due_text = dt.strftime('%m/%d')

                        # Setup compact font for date
                        date_font = QFont(p.font())
                        date_font.setPointSize(8)
                        p.setFont(date_font)
                        p.setPen(QColor(180, 180, 180))  # Gray for readability

                        # Draw date to the left of type labels with small gap
                        date_text_rect = p.fontMetrics().boundingRect(due_text)
                        date_x = label_x - date_text_rect.width() - 6  # 6px gap from labels
                        p.drawText(QRect(date_x, opt.rect.top(), date_text_rect.width(), opt.rect.height()),
                                  Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, due_text)
                    except: pass

        p.restore()

    def sizeHint(self, opt, idx):
        s = super().sizeHint(opt, idx)
        s.setHeight(max(s.height(), 36))
        return s
