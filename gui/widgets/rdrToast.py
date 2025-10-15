#!/usr/bin/env python3
"""
Toast Notification - Next.js暗黑风格超级帅气Toast
从右上滑入 → 停留 → 向右滑出
"""
from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QPoint, QEasingCurve, QSequentialAnimationGroup, QParallelAnimationGroup
from PyQt6.QtGui import QFont, QColor


class ToastNotification(QWidget):
    """Next.js风格超级帅气Toast"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        # 纯暗黑风格配色 (黑色背景 + 彩色圆点区分类型)
        self.styles = {
            'success': {
                'icon': '●',
                'icon_color': '#10b981',  # emerald-500 (只有圆点是彩色)
                'bg': 'rgba(10, 10, 10, 0.95)',  # 纯黑背景
                'text': '#e5e5e5',  # 浅灰文字
                'glow': QColor(16, 185, 129, 60)
            },
            'info': {
                'icon': '●',
                'icon_color': '#3b82f6',  # blue-500
                'bg': 'rgba(10, 10, 10, 0.95)',
                'text': '#e5e5e5',
                'glow': QColor(59, 130, 246, 60)
            },
            'warning': {
                'icon': '●',
                'icon_color': '#f59e0b',  # amber-500
                'bg': 'rgba(10, 10, 10, 0.95)',
                'text': '#e5e5e5',
                'glow': QColor(245, 158, 11, 60)
            },
            'error': {
                'icon': '●',
                'icon_color': '#ef4444',  # red-500
                'bg': 'rgba(10, 10, 10, 0.95)',
                'text': '#e5e5e5',
                'glow': QColor(239, 68, 68, 60)
            }
        }

        # 容器widget (用于设置背景)
        self.container = QWidget(self)
        self.container_layout = QHBoxLayout(self.container)
        self.container_layout.setContentsMargins(18, 14, 18, 14)
        self.container_layout.setSpacing(14)

        # Icon (现代圆点)
        self.icon_label = QLabel()
        self.icon_label.setFont(QFont('Arial', 16, QFont.Weight.Bold))
        self.icon_label.setFixedSize(24, 24)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Text
        self.text_label = QLabel()
        self.text_label.setFont(QFont('Inter, -apple-system, BlinkMacSystemFont, "Segoe UI"', 13, QFont.Weight.Medium))

        self.container_layout.addWidget(self.icon_label)
        self.container_layout.addWidget(self.text_label)
        self.container_layout.addStretch()

        # 阴影效果 (暗黑风格 - 深色阴影)
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(30)
        self.shadow.setOffset(0, 6)
        self.shadow.setColor(QColor(0, 0, 0, 200))  # 深黑色阴影
        self.container.setGraphicsEffect(self.shadow)

        # 动画组
        self.slide_in_animation = QPropertyAnimation(self, b"pos")
        self.slide_in_animation.setDuration(500)
        self.slide_in_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.slide_out_animation = QPropertyAnimation(self, b"pos")
        self.slide_out_animation.setDuration(400)
        self.slide_out_animation.setEasingCurve(QEasingCurve.Type.InBack)
        self.slide_out_animation.finished.connect(self.deleteLater)

        # 定时器
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.slide_out)

    def show_message(self, message, msg_type='success', duration=3000):
        """
        显示消息

        Args:
            message: 消息文本
            msg_type: 'success', 'info', 'warning', 'error'
            duration: 显示时长(ms)
        """
        style = self.styles.get(msg_type, self.styles['info'])

        # 设置Icon颜色和文本
        self.icon_label.setText(style['icon'])
        self.icon_label.setStyleSheet(f"color: {style['icon_color']};")

        self.text_label.setText(message)
        self.text_label.setStyleSheet(f"color: {style['text']}; font-weight: 500; letter-spacing: 0.3px;")

        # 纯暗黑风格 (黑色圆角卡片，无边框)
        self.container.setStyleSheet(f"""
            QWidget {{
                background: {style['bg']};
                border: none;
                border-radius: 14px;
            }}
        """)

        # 更新阴影 (轻微的彩色发光 + 主要深色阴影)
        self.shadow.setColor(QColor(0, 0, 0, 200))  # 保持深色阴影为主
        self.shadow.setBlurRadius(30)

        # 调整大小
        self.container.adjustSize()
        self.setFixedSize(self.container.size())

        # 计算位置
        parent = self.parent()
        if parent:
            parent_rect = parent.geometry()

            # 起始位置：右侧屏幕外 + 稍微上方
            start_x = parent_rect.width() + 50
            start_y = 24

            # 目标位置：右上角内部
            end_x = parent_rect.width() - self.width() - 24
            end_y = 24

            # 退出位置：右侧屏幕外 (向右上消失)
            exit_x = parent_rect.width() + 50
            exit_y = 10

            self.start_pos = QPoint(start_x, start_y)
            self.end_pos = QPoint(end_x, end_y)
            self.exit_pos = QPoint(exit_x, exit_y)

            # 设置初始位置
            self.move(self.start_pos)

            # 显示窗口
            self.show()

            # 丝滑滑入动画 (从右侧滑入)
            self.slide_in_animation.setStartValue(self.start_pos)
            self.slide_in_animation.setEndValue(self.end_pos)
            self.slide_in_animation.start()

            # 设置定时器
            self.timer.start(duration)

    def slide_out(self):
        """超级丝滑的滑出动画 (向右上消失)"""
        self.slide_out_animation.setStartValue(self.pos())
        self.slide_out_animation.setEndValue(self.exit_pos)
        self.slide_out_animation.start()


def show_toast(parent, message, msg_type='success', duration=3000):
    """
    便捷函数：显示Toast通知

    Args:
        parent: 父窗口
        message: 消息文本
        msg_type: 'success', 'info', 'warning', 'error'
        duration: 显示时长(ms)

    Example:
        show_toast(self, "Todo获取成功！", 'success')
        show_toast(self, "Preview生成完成", 'info')
        show_toast(self, "Learn分析完成", 'success')
    """
    toast = ToastNotification(parent)
    toast.show_message(message, msg_type, duration)
    return toast
