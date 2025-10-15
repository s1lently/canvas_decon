"""Preview Loader - Handles AI preview loading for AutoDetail"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))


class PreviewLoader:
    """Handles preview loading operations for AutoDetail"""

    def __init__(self, app, auto_detail_mgr):
        """
        Args:
            app: CanvasApp instance
            auto_detail_mgr: AutoDetailManager instance
        """
        self.app = app
        self.auto_detail_mgr = auto_detail_mgr

    def load_preview(self):
        """Load AI preview (quiz or homework) if files exist"""
        if not self.auto_detail_mgr:
            return None
        assignment_folder = self.auto_detail_mgr.todo.get('assignment_details', {}).get('assignment_folder')
        if not assignment_folder:
            return None
        output_dir = os.path.join(assignment_folder, 'auto', 'output')
        if not os.path.exists(output_dir):
            return None
        if self.auto_detail_mgr.is_quiz:
            return self.auto_detail_mgr.load_quiz_preview(output_dir)
        elif self.auto_detail_mgr.is_homework:
            return self.auto_detail_mgr.load_homework_preview(output_dir)
        return None

    def refresh_preview(self):
        """Refresh preview panel in AutoDetail window"""
        if not self.auto_detail_mgr:
            return
        adw = self.app.auto_detail_window
        preview_html = self.load_preview()
        if preview_html:
            adw.aiPreviewView.setHtml(preview_html)
            adw.previewStatusLabel.setText("Status: Preview loaded")
