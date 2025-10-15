import os, sys
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
class AutoDetailManager:
    def __init__(self, todo):
        self.todo, self.course_name, self.assignment_name, self.due_date, self.redirect_url, self.assignment_details = todo, todo.get('course_name', 'Unknown'), todo.get('name', 'Unknown'), todo.get('due_date'), todo.get('redirect_url', ''), todo.get('assignment_details', {})
        types = self.assignment_details.get('type', []); self.is_quiz = 'online_quiz' in types or 'quiz' in self.redirect_url.lower(); self.is_homework = 'online_upload' in types or 'on_paper' in types
        self.type_str = "Quiz" if self.is_quiz else "Homework" if self.is_homework else "Discussion" if 'discussion_topic' in types else "Assignment"
    def get_identification_info(self):
        due_str = "No due date"
        if self.due_date:
            try: dt = datetime.fromisoformat(self.due_date.replace('Z', '+00:00')); due_str = dt.strftime("%m/%d/%Y %I:%M %p")
            except: due_str = self.due_date
        return {'course': self.course_name, 'assignment': self.assignment_name, 'type': self.type_str, 'due_date': due_str}
    def get_assignment_detail_html(self):
        desc = self.assignment_details.get('desc', '') or '<p style="color:#9ca3af;">No description</p>'; desc = '<p style="color:#9ca3af;">No description</p>' if not desc.strip() or desc.strip() == 'null' else desc; m = []
        if pts := self.todo.get('points_possible'): m.append(f"<strong>Points:</strong> {pts}")
        m.append('<span style="color:#22c55e;">✅ Submitted</span>' if self.assignment_details.get('submitted') else '<span style="color:#eab308;">⏳ Not submitted</span>')
        if self.is_quiz and (qm := self.assignment_details.get('quiz_metadata')): m.append(f"<strong>Questions:</strong> {qm.get('question_count','?')}"); m.append(f"<strong>Attempts:</strong> {qm.get('attempt',0)}/{qm.get('allowed_attempts','Unlimited')}"); (tl := qm.get('time_limit')) and m.append(f"<strong>Time:</strong> {tl} min")
        return f"""<style>body{{font-family:-apple-system,sans-serif;line-height:1.6;color:#e0e0e0}}a{{color:#60a5fa;text-decoration:none}}a:hover{{text-decoration:underline}}.m{{background:#1a1a1a;padding:12px;border-radius:8px;border-left:4px solid #3b82f6;margin-bottom:20px;font-size:13px}}</style><div class="m">{' | '.join(m)}</div>{desc}"""
    def get_preview_placeholder_html(self): return '<div style="text-align:center;padding:60px 20px;color:#9ca3af;">No preview generated yet</div>'
    def load_quiz_preview(self, preview_dir):
        for fn in ['QesWA.md', 'questions.md']:
            fp = os.path.join(preview_dir, fn)
            if os.path.exists(fp):
                try: return self._markdown_to_html(open(fp, encoding='utf-8').read(), fn, preview_dir)
                except: pass
        return None
    def load_homework_preview(self, output_dir): fp = os.path.join(output_dir, 'answer.md'); return self._markdown_to_html(open(fp, encoding='utf-8').read(), 'answer.md', output_dir) if os.path.exists(fp) else None
    def _markdown_to_html(self, md_content, source_filename, base_dir=None):
        import markdown as md_lib; import re; import base64; html_body = md_lib.markdown(md_content, extensions=['extra', 'nl2br', 'tables'])
        if base_dir and self.is_quiz:
            images_dir = os.path.join(base_dir, 'images')
            if os.path.exists(images_dir):
                def replace_image_ref(match):
                    filename = match.group(1); img_path = os.path.join(images_dir, filename)
                    if os.path.exists(img_path):
                        try:
                            with open(img_path, 'rb') as f: img_data = base64.b64encode(f.read()).decode()
                            ext = filename.split('.')[-1].lower(); mime = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'gif': 'image/gif', 'webp': 'image/webp'}.get(ext, 'image/png'); return f'<img src="data:{mime};base64,{img_data}" style="max-width:300px;border:1px solid #333;border-radius:4px;margin:8px 4px;display:block;" title="{filename}"/>'
                        except: pass
                    return match.group(0)
                html_body = re.sub(r'\(Imgs:\s*([a-zA-Z0-9_]+\.(?:png|jpg|jpeg|gif|webp))\)', replace_image_ref, html_body, flags=re.IGNORECASE); html_body = re.sub(r'<code>([^<>]+\.(?:png|jpg|jpeg|gif|webp))</code>', replace_image_ref, html_body, flags=re.IGNORECASE)
        return f"""<style>body{{font-family:-apple-system,sans-serif;line-height:1.6;color:#e0e0e0}}h1{{color:#22c55e;border-bottom:2px solid #22c55e;padding-bottom:8px}}h2{{color:#86efac;margin-top:24px}}h3{{color:#bbf7d0;margin-top:20px}}a{{color:#60a5fa;text-decoration:none}}a:hover{{text-decoration:underline}}code{{background:#2a2a2a;padding:2px 6px;border-radius:4px;font-family:Consolas,monospace;color:#22c55e}}pre{{background:#1a1a1a;padding:16px;border-radius:8px;overflow-x:auto;border-left:4px solid #22c55e}}ul,ol{{padding-left:24px}}li{{margin:4px 0}}img{{max-width:100%}}.s{{background:#1a1a1a;padding:8px 12px;border-radius:6px;font-size:12px;color:#9ca3af;margin-bottom:20px}}</style><div class="s">📄 {source_filename}</div>{html_body}"""
    def get_reference_files_html(self):
        if self.is_quiz: return ''
        if not self.is_homework: return '<div style="text-align:center;padding:20px;color:#9ca3af;">Not supported</div>'

        assignment_folder = self.assignment_details.get('assignment_folder')
        if not assignment_folder:
            return '<div style="background:#1a1a1a;border:2px solid #eab308;border-radius:8px;padding:20px;margin:20px 0;text-align:center;color:#eab308;">⚠️ No assignment folder</div>'

        file_items = []

        # Scan auto/input directory
        input_dir = os.path.join(assignment_folder, 'auto', 'input')
        if os.path.exists(input_dir):
            for f in os.listdir(input_dir):
                fp = os.path.join(input_dir, f)
                if os.path.isfile(fp):
                    sz = os.path.getsize(fp)
                    for unit in ['B','KB','MB','GB']:
                        if sz < 1024:
                            break
                        sz /= 1024.0
                    icon = '📄' if f.lower().endswith('.pdf') else '📎'
                    file_items.append(f'<div style="display:flex;align-items:center;background:#1a1a1a;border:1px solid #333;border-radius:8px;padding:12px;margin:8px 0"><div style="font-size:32px;margin-right:15px">{icon}</div><div><div style="font-size:14px;color:#e0e0e0;font-weight:500">{f}</div><div style="font-size:12px;color:#9ca3af;margin-top:4px">{sz:.1f} {unit} • input/</div></div></div>')

        # Scan files directory
        files_dir = os.path.join(assignment_folder, 'files')
        if os.path.exists(files_dir):
            for f in os.listdir(files_dir):
                fp = os.path.join(files_dir, f)
                if os.path.isfile(fp):
                    sz = os.path.getsize(fp)
                    for unit in ['B','KB','MB','GB']:
                        if sz < 1024:
                            break
                        sz /= 1024.0
                    icon = '📄' if f.lower().endswith('.pdf') else '📎'
                    file_items.append(f'<div style="display:flex;align-items:center;background:#1a1a1a;border:1px solid #333;border-radius:8px;padding:12px;margin:8px 0"><div style="font-size:32px;margin-right:15px">{icon}</div><div><div style="font-size:14px;color:#e0e0e0;font-weight:500">{f}</div><div style="font-size:12px;color:#9ca3af;margin-top:4px">{sz:.1f} {unit} • files/</div></div></div>')

        if not file_items:
            return '<div style="background:#1a1a1a;border:2px solid #eab308;border-radius:8px;padding:20px;margin:20px 0;text-align:center;color:#eab308;">⚠️ No reference files</div>'

        return f'<div style="background:#1a1a1a;border-left:4px solid #a78bfa;padding:12px 16px;margin-bottom:15px;border-radius:4px;color:#a78bfa;font-weight:bold">📚 {len(file_items)} File(s)</div>{"".join(file_items)}'
