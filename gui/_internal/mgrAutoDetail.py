"""AutoDetail Manager - Modern GitHub Dark themed HTML generation"""
import os, sys, re, base64
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

# Mission Control Dark theme colors (matching wgtAutoDetailModern.py)
C = {
    'bg': '#0a0a0a', 'bg2': '#111111', 'bg3': '#1a1a1a', 'card': '#1e1e1e',
    'border': '#2a2a2a', 'text': '#ffffff', 'muted': '#b0b0b0', 'dim': '#707070',
    'blue': '#58a6ff', 'green': '#22c55e', 'purple': '#a371f7', 'orange': '#f59e0b', 'red': '#ef4444'
}

class AutoDetailManager:
    def __init__(self, todo):
        self.todo = todo
        self.course_name = todo.get('course_name', 'Unknown')
        self.assignment_name = todo.get('name', 'Unknown')
        self.due_date = todo.get('due_date')
        self.redirect_url = todo.get('redirect_url', '')
        self.assignment_details = todo.get('assignment_details', {})
        types = self.assignment_details.get('type', [])
        self.is_quiz = 'online_quiz' in types or 'quiz' in self.redirect_url.lower()
        self.is_homework = 'online_upload' in types or 'on_paper' in types
        self.type_str = "Quiz" if self.is_quiz else "Homework" if self.is_homework else "Discussion" if 'discussion_topic' in types else "Assignment"

    def get_identification_info(self):
        due_str = "No due date"
        if self.due_date:
            try:
                dt = datetime.fromisoformat(self.due_date.replace('Z', '+00:00'))
                due_str = dt.strftime("%m/%d/%Y %I:%M %p")
            except:
                due_str = self.due_date
        return {'course': self.course_name, 'assignment': self.assignment_name, 'type': self.type_str, 'due_date': due_str}

    def get_assignment_detail_html(self):
        desc = self.assignment_details.get('desc', '') or ''
        desc = '' if not desc.strip() or desc.strip() == 'null' else desc
        if not desc:
            desc = f'<p style="color:{C["muted"]};">No description available</p>'
        return f"""<div style="color:{C['text']};font-family:-apple-system,sans-serif;font-size:14px;line-height:1.6;">{desc}</div>"""

    def get_preview_placeholder_html(self):
        return f'''<div style="text-align:center;padding:80px 20px;">
            <div style="font-size:32px;margin-bottom:16px;color:{C['dim']};">[ Preview ]</div>
            <div style="color:{C['muted']};font-size:14px;">No preview generated yet</div>
            <div style="color:{C['dim']};font-size:12px;margin-top:8px;">Click "Again" to generate answers</div>
        </div>'''

    def load_quiz_preview(self, preview_dir, prefer_questions=False):
        """Load quiz preview, optionally preferring questions.md over QesWA.md"""
        if prefer_questions:
            files = ['questions.md', 'QesWA.md']
        else:
            files = ['QesWA.md', 'questions.md']
        for fn in files:
            fp = os.path.join(preview_dir, fn)
            if os.path.exists(fp):
                try:
                    return self._markdown_to_html(open(fp, encoding='utf-8').read(), fn, preview_dir)
                except:
                    pass
        return None

    def load_homework_preview(self, output_dir):
        fp = os.path.join(output_dir, 'answer.md')
        return self._markdown_to_html(open(fp, encoding='utf-8').read(), 'answer.md', output_dir) if os.path.exists(fp) else None

    def _markdown_to_html(self, md_content, source_filename, base_dir=None):
        import markdown as md_lib
        html_body = md_lib.markdown(md_content, extensions=['extra', 'nl2br', 'tables'])

        # Embed images for quiz
        if base_dir and self.is_quiz:
            images_dir = os.path.join(base_dir, 'images')
            if os.path.exists(images_dir):
                def replace_image_ref(match):
                    filename = match.group(1)
                    img_path = os.path.join(images_dir, filename)
                    if os.path.exists(img_path):
                        try:
                            with open(img_path, 'rb') as f:
                                img_data = base64.b64encode(f.read()).decode()
                            ext = filename.split('.')[-1].lower()
                            mime = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'gif': 'image/gif', 'webp': 'image/webp'}.get(ext, 'image/png')
                            return f'<img src="data:{mime};base64,{img_data}" style="max-width:280px;border:1px solid {C["border"]};border-radius:8px;margin:8px 0;"/>'
                        except:
                            pass
                    return match.group(0)
                html_body = re.sub(r'\(Imgs:\s*([a-zA-Z0-9_]+\.(?:png|jpg|jpeg|gif|webp))\)', replace_image_ref, html_body, flags=re.IGNORECASE)
                html_body = re.sub(r'<code>([^<>]+\.(?:png|jpg|jpeg|gif|webp))</code>', replace_image_ref, html_body, flags=re.IGNORECASE)

        # QTextBrowser has limited CSS support, so we use <div> instead of <li>
        html_body = html_body.replace('<ul>', '<div class="answer-list">').replace('</ul>', '</div>')
        html_body = html_body.replace('<ol>', '<div class="answer-list">').replace('</ol>', '</div>')

        # First pass: Replace any ✅ emoji with [*] marker in the raw HTML
        html_body = html_body.replace('✅', '<span class="selected-marker">[*]</span>')

        # Selected answers - has [*] marker
        html_body = re.sub(
            r'<li>\s*<span class="selected-marker">\[\*\]</span>\s*<code>([^<]+)</code>:\s*(.*?)</li>',
            rf'<div style="background:rgba(34,197,94,0.15);border-left:3px solid {C["green"]};padding:8px 12px;margin:8px 0;border-radius:0 6px 6px 0;"><span style="color:{C["green"]};font-weight:bold;">[*]</span> <code style="background:{C["bg3"]};color:{C["orange"]};padding:2px 6px;border-radius:4px;font-size:11px;">\g<1></code>: \g<2></div>',
            html_body
        )
        # Non-selected answers (no marker)
        html_body = re.sub(
            r'<li>\s*<code>([^<]+)</code>:\s*(.*?)</li>',
            rf'<div style="padding:8px 12px;margin:8px 0;color:{C["muted"]};"><span style="color:{C["dim"]};">[ ]</span> <code style="background:{C["bg3"]};color:{C["orange"]};padding:2px 6px;border-radius:4px;font-size:11px;">\g<1></code>: \g<2></div>',
            html_body
        )
        # Handle answers with [*] marker that weren't caught above
        html_body = re.sub(
            r'<li>\s*\[\*\]\s*<code>([^<]+)</code>:\s*(.*?)</li>',
            rf'<div style="background:rgba(34,197,94,0.15);border-left:3px solid {C["green"]};padding:8px 12px;margin:8px 0;border-radius:0 6px 6px 0;"><span style="color:{C["green"]};font-weight:bold;">[*]</span> <code style="background:{C["bg3"]};color:{C["orange"]};padding:2px 6px;border-radius:4px;font-size:11px;">\g<1></code>: \g<2></div>',
            html_body
        )
        # Clean up any remaining <li> tags
        html_body = re.sub(r'<li>(.*?)</li>', r'<div style="padding:4px 0;">\1</div>', html_body)
        # Replace any remaining [*] markers with styled version
        html_body = re.sub(
            r'<span class="selected-marker">\[\*\]</span>',
            rf'<span style="color:{C["green"]};font-weight:bold;">[*]</span>',
            html_body
        )

        css = f'''
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: {C['text']}; background: {C['bg2']}; }}
            h1 {{ color: {C['green']}; font-size: 22px; font-weight: 600; margin: 0 0 20px 0; padding-bottom: 12px; border-bottom: 2px solid {C['green']}; }}
            h2 {{ color: {C['blue']}; font-size: 16px; font-weight: 600; margin: 24px 0 12px 0; padding: 12px; background: {C['bg3']}; border-radius: 8px; border-left: 3px solid {C['purple']}; }}
            h3 {{ color: {C['purple']}; font-size: 14px; font-weight: 600; margin: 16px 0 8px 0; }}
            p {{ margin: 8px 0; color: {C['text']}; }}
            code {{ background: {C['bg3']}; padding: 2px 6px; border-radius: 4px; font-family: 'SF Mono', Consolas, monospace; font-size: 12px; color: {C['orange']}; }}
            pre {{ background: {C['bg']}; padding: 16px; border-radius: 8px; border: 1px solid {C['border']}; overflow-x: auto; }}
            ul, ol {{ padding-left: 0; list-style: none; margin: 12px 0; }}
            li {{ display: block; margin: 6px 0; }}
            a {{ color: {C['blue']}; text-decoration: none; }}
            strong {{ color: {C['text']}; }}
            em {{ color: {C['blue']}; font-style: italic; }}
            hr {{ border: none; border-top: 1px solid {C['border']}; margin: 20px 0; }}
            img {{ max-width: 100%; border-radius: 8px; }}
            table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
            th, td {{ border: 1px solid {C['border']}; padding: 8px 12px; text-align: left; }}
            th {{ background: {C['bg3']}; font-weight: 600; }}
        '''

        return f'<style>{css}</style>{html_body}'

    def get_reference_files_html(self):
        if self.is_quiz:
            return ''
        if not self.is_homework:
            return f'<div style="text-align:center;padding:20px;color:{C["muted"]};">Not supported for this type</div>'

        assignment_folder = self.assignment_details.get('assignment_folder')
        if not assignment_folder:
            return f'''<div style="background:{C['bg3']};border:1px solid {C['orange']};border-radius:8px;padding:16px;text-align:center;color:{C['orange']};">
                <div style="font-weight:600;margin-bottom:4px;">Warning</div>
                <div style="font-size:12px;">No assignment folder found</div>
            </div>'''

        file_items = []

        def scan_dir(dir_path):
            if not os.path.exists(dir_path):
                return
            for f in os.listdir(dir_path):
                fp = os.path.join(dir_path, f)
                if os.path.isfile(fp):
                    sz = os.path.getsize(fp)
                    for unit in ['B', 'KB', 'MB', 'GB']:
                        if sz < 1024:
                            break
                        sz /= 1024.0
                    ext = f.lower().split('.')[-1] if '.' in f else ''
                    # Use text indicators instead of emojis
                    type_labels = {'pdf': 'PDF', 'xlsx': 'XLS', 'xls': 'XLS', 'doc': 'DOC', 'docx': 'DOC', 'txt': 'TXT', 'png': 'IMG', 'jpg': 'IMG', 'jpeg': 'IMG'}
                    type_label = type_labels.get(ext, 'FILE')
                    file_items.append(f'''
                        <div style="background:{C['bg3']};border:1px solid {C['border']};border-radius:8px;padding:10px 14px;margin:6px 0;">
                            <span style="background:{C['purple']};color:white;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;margin-right:10px;">{type_label}</span>
                            <span style="color:{C['text']};font-size:13px;">{f}</span>
                            <span style="color:{C['dim']};font-size:11px;margin-left:8px;">{sz:.1f} {unit}</span>
                        </div>
                    ''')

        scan_dir(os.path.join(assignment_folder, 'auto', 'input'))
        scan_dir(os.path.join(assignment_folder, 'files'))

        if not file_items:
            return f'''<div style="background:{C['bg3']};border:1px solid {C['border']};border-radius:8px;padding:16px;text-align:center;">
                <div style="color:{C['muted']};font-size:13px;">No reference files</div>
                <div style="font-size:11px;color:{C['dim']};margin-top:4px;">Drop files into auto/input/</div>
            </div>'''

        return ''.join(file_items)
