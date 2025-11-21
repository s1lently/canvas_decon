"""HTML formatters for GUI detail views"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

def make_url_clickable(url):
    """Convert URL to clickable HTML link"""
    if not url:
        return ""
    # If URL doesn't start with http, prepend base URL
    full_url = url if url.startswith('http') else f"{config.CANVAS_BASE_URL}{url}"
    return f"<a href='{full_url}' style='color: #3b82f6; text-decoration: underline;'>{url}</a>"

def format_course(course):
    """Format course as HTML"""
    html = f"<h2 style='color: #3b82f6;'>{course.get('name', 'Unknown Course')}</h2><div style='font-family: monospace; font-size: 13px;'>"
    for k, v in course.items():
        if k == 'name': continue
        if isinstance(v, dict):
            items_html = ''.join(f"<li>{sk}: <span style='color: #22c55e;'>{sv}</span></li>" for sk, sv in v.items())
            html += f"<p><strong>{k}:</strong></p><ul>{items_html}</ul>"
        elif k in ['url', 'html_url', 'calendar_url'] or ('url' in k.lower() and isinstance(v, str)):
            html += f"<p><strong>{k}:</strong> {make_url_clickable(v)}</p>"
        else:
            html += f"<p><strong>{k}:</strong> {v}</p>"
    return html + "</div>"

def format_todo(todo):
    """Format TODO as HTML with type indicators"""
    ad, url, types = todo.get('assignment_details', {}), todo.get('redirect_url', '').lower(), todo.get('assignment_details', {}).get('type', [])
    is_auto = any(t in types for t in ['online_quiz', 'online_upload', 'online_text_entry', 'discussion_topic'])
    color, label = (('#ef4444', '🤖 AUTOMATABLE') if is_auto else ('#a855f7', '📝 QUIZ') if 'quiz' in url else ('#3b82f6', '💬 DISCUSSION') if 'discussion' in url else ('#eab308', '📚 HOMEWORK'))

    html = f"<h2 style='color: {color};'>{todo.get('name', 'Unknown')} <span style='font-size: 14px;'>[{label}]</span></h2><h3 style='color: #aaa;'>{todo.get('course_name', '')}</h3>"
    html += "<div style='background: #1a1a1a; padding: 10px; border-radius: 6px; margin-bottom: 10px;'><strong>Legend:</strong> <span style='color: #ef4444;'>🤖 Automatable</span> | <span style='color: #a855f7;'>📝 Quiz</span> | <span style='color: #3b82f6;'>💬 Discussion</span> | <span style='color: #eab308;'>📚 Homework</span></div>"
    html += "<div style='font-family: monospace; font-size: 13px;'>"

    # Format all fields with clickable URLs
    for k, v in todo.items():
        if k in ['name', 'course_name', 'assignment_details']:
            continue
        # Make URLs clickable
        if k in ['redirect_url', 'html_url'] or ('url' in k.lower() and isinstance(v, str)):
            html += f"<p><strong>{k}:</strong> {make_url_clickable(v)}</p>"
        else:
            html += f"<p><strong>{k}:</strong> {v}</p>"

    if ad:
        html += "<hr><h3>Assignment Details:</h3>"
        for k, v in ad.items():
            if k == 'files' and v:
                html += "<p><strong>Files:</strong></p><ul>" + ''.join(f"<li>{f.get('filename', 'Unknown')}</li>" for f in v) + "</ul>"
            elif isinstance(v, list):
                html += f"<p><strong>{k}:</strong> {', '.join(str(x) for x in v)}</p>"
            elif k in ['url', 'html_url'] or ('url' in k.lower() and isinstance(v, str)):
                html += f"<p><strong>{k}:</strong> {make_url_clickable(v)}</p>"
            else:
                html += f"<p><strong>{k}:</strong> {v}</p>"
    return html + "</div>"

def format_folder(foldername):
    """Format folder contents as HTML"""
    fp = os.path.join(config.TODO_DIR, foldername)
    html = f"<h2 style='color: #22c55e;'>{foldername}</h2><div style='font-family: monospace; font-size: 13px;'><p><strong>Path:</strong> {fp}</p>"
    if os.path.exists(fp):
        files_dir = os.path.join(fp, 'files')
        files = [f for f in os.listdir(files_dir) if os.path.isfile(os.path.join(files_dir, f))] if os.path.exists(files_dir) else []
        if files:
            items_html = ''.join(f"<li>{f} <span style='color: #aaa;'>({os.path.getsize(os.path.join(files_dir, f)):,} bytes)</span></li>" for f in sorted(files))
            html += f"<p><strong>Files ({len(files)}):</strong></p><ul>{items_html}</ul>"
        else:
            html += "<p><em>No files in folder</em></p>"
    return html + "</div>"
