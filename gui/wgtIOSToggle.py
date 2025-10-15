"""
iOS-style toggle switch widget for PyQt6
Smooth animation, rounded design, modern appearance
"""

from PyQt6.QtWidgets import QCheckBox
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen


class IOSToggle(QCheckBox):
    """
    iOS-style animated toggle switch

    Features:
    - Smooth sliding animation
    - Rounded pill shape
    - Color transition (red → green)
    - Clean modern design matching dark theme
    """

    def __init__(self, parent=None, width=60, height=28):
        super().__init__(parent)
        self.setFixedSize(width, height)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Colors
        self._bg_color_off = QColor("#2a2a2a")  # Dark gray (off state)
        self._bg_color_on = QColor("#3b82f6")   # Blue (on state)
        self._circle_color = QColor("#ffffff")  # White circle
        self._border_color = QColor("#1a1a1a")  # Subtle border

        # Animation setup
        self._circle_position = 3  # Starting position (left)
        self._animation = QPropertyAnimation(self, b"circle_position", self)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._animation.setDuration(200)  # 200ms smooth transition

        # Connect state change to animation
        self.stateChanged.connect(self._start_animation)

    @pyqtProperty(float)
    def circle_position(self):
        return self._circle_position

    @circle_position.setter
    def circle_position(self, pos):
        self._circle_position = pos
        self.update()

    def _start_animation(self, state):
        """Animate circle movement when toggled"""
        self._animation.stop()
        if state == Qt.CheckState.Checked.value:
            # Move circle to right
            self._animation.setEndValue(self.width() - self.height() + 3)
        else:
            # Move circle to left
            self._animation.setEndValue(3)
        self._animation.start()

    def paintEvent(self, event):
        """Custom paint for iOS-style appearance"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background (pill shape)
        bg_rect = QRectF(0, 0, self.width(), self.height())

        # Interpolate background color based on state
        if self.isChecked():
            bg_color = self._bg_color_on
        else:
            bg_color = self._bg_color_off

        painter.setBrush(bg_color)
        painter.setPen(QPen(self._border_color, 1))
        painter.drawRoundedRect(bg_rect, self.height() / 2, self.height() / 2)

        # Circle (thumb)
        circle_size = self.height() - 6  # Slightly smaller than height
        circle_rect = QRectF(
            self._circle_position,
            3,
            circle_size,
            circle_size
        )

        painter.setBrush(self._circle_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(circle_rect)

    def sizeHint(self):
        """Recommended size"""
        return self.minimumSize()

    def hitButton(self, pos):
        """Make entire widget clickable"""
        return self.contentsRect().contains(pos)
