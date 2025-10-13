"""AutoDetail Manager - Handles automation detail window logic"""
import os, json, re
from datetime import datetime
from html import unescape
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config


class AutoDetailManager:
    def __init__(self, todo):
        """Initialize with TODO item data"""
        self.todo = todo
        self.course_name = todo.get('course_name', 'Unknown')
        self.assignment_name = todo.get('name', 'Unknown')
        self.due_date = todo.get('due_date')
        self.redirect_url = todo.get('redirect_url', '')
        self.assignment_details = todo.get('assignment_details', {})

        # Determine type
        self.is_quiz = self._is_quiz()
        self.is_homework = self._is_homework()
        self.type_str = self._get_type_string()

    def _is_quiz(self):
        """Check if assignment is a quiz"""
        types = self.assignment_details.get('type', [])
        return 'online_quiz' in types or 'quiz' in self.redirect_url.lower()

    def _is_homework(self):
        """Check if assignment is homework/upload"""
        types = self.assignment_details.get('type', [])
        return 'online_upload' in types or 'on_paper' in types

    def _get_type_string(self):
        """Get human-readable type"""
        if self.is_quiz:
            return "Quiz"
        elif self.is_homework:
            return "Homework (Upload)"
        elif 'discussion_topic' in self.assignment_details.get('type', []):
            return "Discussion"
        else:
            return "Assignment"

    def get_identification_info(self):
        """Get info for top bar"""
        due_str = "No due date"
        if self.due_date:
            try:
                dt = datetime.fromisoformat(self.due_date.replace('Z', '+00:00'))
                due_str = dt.strftime("%m/%d/%Y %I:%M %p")
            except:
                due_str = self.due_date

        return {
            'course': self.course_name,
            'assignment': self.assignment_name,
            'type': self.type_str,
            'due_date': due_str
        }

    def get_assignment_detail_html(self):
        """Generate HTML for assignment detail view (left panel)"""
        desc = self.assignment_details.get('desc', '') or 'No description available.'

        # Clean HTML description
        clean_desc = desc.strip()
        if not clean_desc or clean_desc == 'null':
            clean_desc = '<p style="color: #9ca3af;">No description provided.</p>'

        # Build metadata
        metadata = []
        if points := self.todo.get('points_possible'):
            metadata.append(f"<strong>Points:</strong> {points}")

        if self.assignment_details.get('submitted'):
            metadata.append('<span style="color: #22c55e;">✅ Submitted</span>')
        else:
            metadata.append('<span style="color: #eab308;">⏳ Not submitted</span>')

        # Quiz metadata
        if self.is_quiz and (quiz_meta := self.assignment_details.get('quiz_metadata')):
            metadata.append(f"<strong>Questions:</strong> {quiz_meta.get('question_count', 'Unknown')}")
            metadata.append(f"<strong>Attempts:</strong> {quiz_meta.get('attempt', 0)}/{quiz_meta.get('allowed_attempts', 'Unlimited')}")
            if time_limit := quiz_meta.get('time_limit'):
                metadata.append(f"<strong>Time Limit:</strong> {time_limit} min")

        meta_html = ' | '.join(metadata) if metadata else ''

        html = f"""
        <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            line-height: 1.6;
            color: #e0e0e0;
        }}
        h2 {{ color: #60a5fa; margin-top: 24px; }}
        h3 {{ color: #93c5fd; margin-top: 20px; }}
        a {{ color: #60a5fa; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .metadata {{
            background-color: #1a1a1a;
            padding: 12px;
            border-radius: 8px;
            border-left: 4px solid #3b82f6;
            margin-bottom: 20px;
            font-size: 13px;
        }}
        .url {{
            background-color: #2a2a2a;
            padding: 8px 12px;
            border-radius: 6px;
            font-family: 'Consolas', monospace;
            font-size: 12px;
            margin-top: 20px;
            word-break: break-all;
        }}
        </style>

        <h2>📋 Assignment Information</h2>
        <div class="metadata">{meta_html}</div>

        <h2>📝 Description</h2>
        {clean_desc}

        <div class="url">
            <strong>URL:</strong> <a href="https://psu.instructure.com{self.redirect_url}" target="_blank">
                {self.redirect_url}
            </a>
        </div>
        """

        return html

    def get_preview_placeholder_html(self):
        """Get placeholder HTML for AI preview (before generation)"""
        if self.is_quiz:
            preview_info = """
            <h3>Quiz Preview will show:</h3>
            <ul style="line-height: 1.8;">
                <li>📊 Parsed questions (text + images)</li>
                <li>🎯 Available answer options with IDs</li>
                <li>🖼️ Downloaded question/answer images</li>
                <li>🤖 AI-generated answers (after processing)</li>
            </ul>
            <p style="color: #9ca3af; margin-top: 20px;">
                Files generated: <code>questions.html</code>, <code>questions.md</code>, <code>QesWA.md</code>
            </p>
            """
        elif self.is_homework:
            preview_info = """
            <h3>Homework Preview will show:</h3>
            <ul style="line-height: 1.8;">
                <li>📄 Assignment description (cleaned)</li>
                <li>📚 Referenced PDFs from bisc_pdfs/</li>
                <li>🤖 AI-generated markdown answer</li>
                <li>🖼️ Generated images (if [gen_img] tags present)</li>
                <li>📦 Final DOCX ready for submission</li>
            </ul>
            <p style="color: #9ca3af; margin-top: 20px;">
                Files generated: <code>answer.md</code>, <code>answer.docx</code>, images (if any)
            </p>
            """
        else:
            preview_info = """
            <h3>Preview information:</h3>
            <p style="color: #9ca3af;">
                This assignment type is not supported for automated preview yet.
            </p>
            """

        html = f"""
        <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            line-height: 1.6;
            color: #e0e0e0;
        }}
        h2 {{ color: #22c55e; margin-bottom: 20px; }}
        h3 {{ color: #86efac; margin-top: 16px; }}
        ul {{ padding-left: 24px; }}
        li {{ margin: 8px 0; }}
        code {{
            background-color: #2a2a2a;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Consolas', monospace;
            color: #22c55e;
        }}
        .info-box {{
            background-color: #1a1a1a;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 20px;
            margin-top: 20px;
        }}
        </style>

        <div style="text-align: center; padding: 40px 20px;">
            <h2>🤖 AI Preview</h2>
            <p style="color: #9ca3af; font-size: 14px;">
                No preview has been generated yet for this assignment.
            </p>
        </div>

        <div class="info-box">
            {preview_info}
        </div>
        """

        return html

    def load_quiz_preview(self, preview_dir):
        """Load quiz preview from questions.md or QesWA.md"""
        # Try QesWA.md first (with answers), then questions.md
        for filename in ['QesWA.md', 'questions.md']:
            filepath = os.path.join(preview_dir, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    return self._markdown_to_html(content, filename)
                except:
                    pass

        return None

    def load_homework_preview(self, output_dir):
        """Load homework preview from answer.md"""
        filepath = os.path.join(output_dir, 'answer.md')
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                return self._markdown_to_html(content, 'answer.md')
            except:
                pass

        return None

    def _markdown_to_html(self, md_content, source_filename):
        """Convert markdown to styled HTML"""
        # Simple markdown parsing (can use markdown library if needed)
        import markdown as md_lib

        html_body = md_lib.markdown(md_content, extensions=['extra', 'nl2br', 'tables'])

        styled_html = f"""
        <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            line-height: 1.6;
            color: #e0e0e0;
        }}
        h1 {{ color: #22c55e; border-bottom: 2px solid #22c55e; padding-bottom: 8px; }}
        h2 {{ color: #86efac; margin-top: 24px; }}
        h3 {{ color: #bbf7d0; margin-top: 20px; }}
        a {{ color: #60a5fa; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        code {{
            background-color: #2a2a2a;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Consolas', monospace;
            color: #22c55e;
        }}
        pre {{
            background-color: #1a1a1a;
            padding: 16px;
            border-radius: 8px;
            overflow-x: auto;
            border-left: 4px solid #22c55e;
        }}
        ul, ol {{ padding-left: 24px; }}
        li {{ margin: 4px 0; }}
        .source {{
            background-color: #1a1a1a;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 12px;
            color: #9ca3af;
            margin-bottom: 20px;
        }}
        </style>

        <div class="source">📄 Source: {source_filename}</div>
        {html_body}
        """

        return styled_html

    def get_reference_files_html(self):
        """Get HTML list of reference files that will be uploaded to AI"""
        if self.is_quiz:
            # Quiz: No reference files needed
            html = """
            <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                color: #e0e0e0;
            }
            .info-box {
                background-color: #1a1a1a;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 20px;
                margin: 20px 0;
                text-align: center;
            }
            </style>
            <div class="info-box">
                <p style="color: #9ca3af; font-size: 14px;">
                    ℹ️ Quiz mode: AI will analyze question images directly from the quiz page.
                </p>
                <p style="color: #6b7280; font-size: 12px; margin-top: 10px;">
                    No additional reference files needed.
                </p>
            </div>
            """
            return html

        elif self.is_homework:
            # Homework: List PDFs from bisc_pdfs/
            pdf_dir = os.path.join(config.ROOT_DIR, 'bisc_pdfs')
            pdf_files = []

            if os.path.exists(pdf_dir):
                for file in os.listdir(pdf_dir):
                    if file.lower().endswith('.pdf'):
                        file_path = os.path.join(pdf_dir, file)
                        file_size = os.path.getsize(file_path)
                        size_str = self._format_size(file_size)
                        pdf_files.append((file, size_str, file_path))

            if not pdf_files:
                html = """
                <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    color: #e0e0e0;
                }
                .warning-box {
                    background-color: #1a1a1a;
                    border: 2px solid #eab308;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 20px 0;
                    text-align: center;
                }
                </style>
                <div class="warning-box">
                    <p style="color: #eab308; font-size: 14px;">
                        ⚠️ No reference PDFs found in bisc_pdfs/
                    </p>
                    <p style="color: #9ca3af; font-size: 12px; margin-top: 10px;">
                        AI will work with assignment description only.
                    </p>
                </div>
                """
                return html

            # Build file list
            files_html = []
            for filename, size, path in pdf_files:
                files_html.append(f"""
                <div class="file-item">
                    <div class="file-icon">📄</div>
                    <div class="file-info">
                        <div class="file-name">{filename}</div>
                        <div class="file-size">{size}</div>
                    </div>
                </div>
                """)

            html = f"""
            <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                color: #e0e0e0;
            }}
            .file-list {{
                margin: 10px 0;
            }}
            .file-item {{
                display: flex;
                align-items: center;
                background-color: #1a1a1a;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 12px;
                margin: 8px 0;
                transition: background-color 0.2s;
            }}
            .file-item:hover {{
                background-color: #262626;
            }}
            .file-icon {{
                font-size: 32px;
                margin-right: 15px;
            }}
            .file-info {{
                flex: 1;
            }}
            .file-name {{
                font-size: 14px;
                color: #e0e0e0;
                font-weight: 500;
            }}
            .file-size {{
                font-size: 12px;
                color: #9ca3af;
                margin-top: 4px;
            }}
            .summary {{
                background-color: #1a1a1a;
                border-left: 4px solid #a78bfa;
                padding: 12px 16px;
                margin-bottom: 15px;
                border-radius: 4px;
            }}
            </style>

            <div class="summary">
                <strong style="color: #a78bfa;">📚 {len(pdf_files)} PDF(s) will be uploaded to AI</strong>
            </div>

            <div class="file-list">
                {''.join(files_html)}
            </div>
            """
            return html

        else:
            html = """
            <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                color: #e0e0e0;
            }
            .info-box {
                background-color: #1a1a1a;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 20px;
                margin: 20px 0;
                text-align: center;
            }
            </style>
            <div class="info-box">
                <p style="color: #9ca3af; font-size: 14px;">
                    ℹ️ This assignment type is not supported for automation yet.
                </p>
            </div>
            """
            return html

    def _format_size(self, size_bytes):
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
