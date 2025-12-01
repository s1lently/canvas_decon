"""Base Handler - Parent class for all handlers"""


class BaseHandler:
    """Base handler with reference to main CanvasApp"""

    def __init__(self, app):
        """
        Args:
            app: CanvasApp instance
        """
        self.app = app

    # Shortcuts to frequently used attributes
    @property
    def dm(self):
        return self.app.dm

    @property
    def done_mgr(self):
        return self.app.done_mgr

    @property
    def course_detail_mgr(self):
        return self.app.course_detail_mgr

    @property
    def auto_detail_mgr(self):
        return self.app.auto_detail_mgr

    @property
    def stacked_widget(self):
        return self.app.stacked_widget

    @property
    def main_window(self):
        return self.app.main_window

    @property
    def sitting_window(self):
        return self.app.sitting_window

    @property
    def automation_window(self):
        return self.app.automation_window

    @property
    def course_detail_window(self):
        return self.app.course_detail_window

    @property
    def auto_detail_window(self):
        return self.app.auto_detail_window

    @property
    def launcher_overlay(self):
        return self.app.launcher_overlay
