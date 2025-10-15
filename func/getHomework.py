import requests, json, os, sys, re, mimetypes, time
from urllib.parse import urlparse
from html import unescape
from pathlib import Path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from func import utilPromptFiles
TARGET_ASSIGNMENT_URL = "https://psu.instructure.com/courses/2418560/assignments/17474475"
COOKIES_FILE, OUTPUT_DIR, ANSWER_FILE, PERSONAL_INFO_FILE = config.COOKIES_FILE, config.OUTPUT_DIR, os.path.join(config.OUTPUT_DIR, 'answer.md'), config.PERSONAL_INFO_FILE
def get_homework_details(url=None):
    url = url or TARGET_ASSIGNMENT_URL; path = urlparse(url).path.split('/'); course_id, assignment_id = path[path.index('courses')+1], path[path.index('assignments')+1]
    cookies = {c['name']: c['value'] for c in json.load(open(COOKIES_FILE))}; session = requests.Session(); session.cookies.update(cookies); session.headers.update({'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json+canvas-string-ids'})
    assignment = session.get(f"https://psu.instructure.com/api/v1/courses/{course_id}/assignments/{assignment_id}", timeout=20).json(); submission = session.get(f"https://psu.instructure.com/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions/self", timeout=20).json()
    data = {'assignment': {k: assignment.get(k) for k in ['id', 'name', 'description', 'due_at', 'points_possible', 'submission_types', 'html_url']}, 'submission': {k: submission.get(k) for k in ['id', 'submitted_at', 'workflow_state', 'score', 'grade', 'late', 'missing']}}; print(f"✓ Assignment: {assignment['name']}"); return data
def ask_llm_with_pdfs(description, product, model, prompt, ref_files=[]):
    try: personal_info = json.load(open(PERSONAL_INFO_FILE)); personal_context = f"\n**Your Personal Information (USE THESE EXACT VALUES):**\n- Name: {personal_info['name']}\n- Age: {personal_info['age']} years\n- Weight: {personal_info['weight_kg']} kg ({personal_info['weight_lbs']} lbs)\n- Height: {personal_info['height_cm']} cm ({personal_info['height_inches']} inches)\n- Gender: {personal_info['gender']}\n- Location: {personal_info['location']}\n"
    except: personal_context = ""
    full_prompt = f"{prompt}\n{personal_context}\n\n**Description:**\n{description}"; print(f"\n🤖 Calling {product} {model}..."); return utilPromptFiles.call_ai(full_prompt, product, model, ref_files)
def parse_img_requests(answer_text):
    img_requests = [{'name': m.group(1).strip(), 'description': d.group(1).strip()} for match in re.finditer(r'\[gen_img\]\s*\{([^}]+)\}', answer_text, re.DOTALL) if (m := re.search(r'name:\s*(.+?)(?:\n|$)', (content := match.group(1)))) and (d := re.search(r'des:\s*(.+?)(?:\n|$)', content, re.DOTALL))]
    return re.sub(r'\[gen_img\]\s*\{[^}]+\}', '', answer_text, flags=re.DOTALL).strip(), img_requests
def generate_images(img_requests):
    if not img_requests: return
    print(f"\n🖼️  Generating {len(img_requests)} image(s) with Gemini..."); from google import genai as genai_client; from PIL import Image; from io import BytesIO; client = genai_client.Client(api_key=config.GEMINI_API_KEY)
    for req in img_requests:
        print(f"  - {req['name']}: {req['description'][:50]}...")
        try: response = client.models.generate_content(model="gemini-2.5-flash-image", contents=[req['description']]); [Image.open(BytesIO(part.inline_data.data)).save(img_path := f"{OUTPUT_DIR}/{req['name']}") or print(f"    ✅ Generated: {img_path}") for part in response.candidates[0].content.parts if part.inline_data][:1]
        except Exception as e: print(f"    ❌ Failed: {e}")
def md_to_docx(output_path, answer_file=None):
    from docx import Document; from docx.shared import Inches; doc = Document()
    for line in open(answer_file or ANSWER_FILE, 'r', encoding='utf-8'):
        line = line.rstrip()
        if line.strip() in ['[yes]', '[no]'] or line.startswith('```'): continue
        if line.startswith('### '): doc.add_heading(line[4:], 3)
        elif line.startswith('## '): doc.add_heading(line[3:], 2)
        elif line.startswith('# '): doc.add_heading(line[2:], 1)
        elif line.startswith(('*   ', '- ')): text = line[4:] if line.startswith('*   ') else line[2:]; p = doc.add_paragraph(style='List Bullet'); [(run := p.add_run(part), setattr(run, 'bold', bool(i % 2))) for i, part in enumerate(text.split('**'))] if '**' in text else p.add_run(text)
        elif line.startswith('    '): p = doc.add_paragraph(); [(run := p.add_run(part), setattr(run, 'bold', bool(i % 2))) for i, part in enumerate(line.strip().split('**'))]; p.paragraph_format.left_indent = Inches(0.5)
        elif line.strip(): p = doc.add_paragraph(); [(run := p.add_run(part), setattr(run, 'bold', bool(i % 2))) for i, part in enumerate(line.split('**'))]
    doc.save(output_path); print(f"✅ Converted to: {output_path}")
def submit_to_canvas(url=None, assignment_folder=None):
    print("\n📤 Step 7: Submitting to Canvas..."); url = url or TARGET_ASSIGNMENT_URL; path = urlparse(url).path.split('/'); course_id, assignment_id = path[path.index('courses')+1], path[path.index('assignments')+1]
    cookies_list = json.load(open(COOKIES_FILE)); session = requests.Session(); csrf_token = None
    for c in cookies_list: session.cookies.set(c['name'], c['value'], domain=c['domain'], path=c['path']); csrf_token = requests.utils.unquote(c['value']) if c['name'] == '_csrf_token' else csrf_token
    def update_csrf(): nonlocal csrf_token; csrf_token = requests.utils.unquote(session.cookies['_csrf_token']) if '_csrf_token' in session.cookies and (new := requests.utils.unquote(session.cookies['_csrf_token'])) else csrf_token
    def headers(ct='application/json', csrf=True): h = {'Accept': 'application/json+canvas-string-ids, application/json, text/plain, */*', 'Referer': f'https://psu.instructure.com/courses/{course_id}/assignments/{assignment_id}', 'X-Requested-With': 'XMLHttpRequest', 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}; (ct and h.update({'Content-Type': ct})); (csrf and h.update({'X-CSRF-Token': csrf_token})); return h
    output_dir = os.path.join(assignment_folder, 'auto', 'output') if assignment_folder else OUTPUT_DIR
    files = [f for f in Path(output_dir).iterdir() if f.is_file() and not f.name.startswith('.') and f.suffix in ['.docx', '.pdf', '.png', '.jpg']]
    if not files: return print("❌ No files found") or False
    print(f"Files: {[f.name for f in files]}"); file_ids = []
    for p in files:
        print(f"\n  {'='*50}\n  {p.name} ({os.path.getsize(p)} bytes)")
        try:
            print(f"  [1/4] Request token..."); r = session.post('https://psu.instructure.com/files/pending', data={'name': p.name, 'on_duplicate': 'rename', 'no_redirect': 'true', 'attachment[intent]': 'submit', 'attachment[asset_string]': f'assignment_{assignment_id}', 'attachment[filename]': p.name, 'attachment[size]': str(os.path.getsize(p)), 'attachment[context_code]': f'course_{course_id}', 'attachment[on_duplicate]': 'rename', 'attachment[content_type]': mimetypes.guess_type(str(p))[0] or 'application/octet-stream'}, headers=headers('application/x-www-form-urlencoded')); r.raise_for_status(); update_csrf(); info = r.json(); print(f"  ✓ Got token") or time.sleep(0.5)
            print(f"  [2/4] Upload..."); url = f"{info['upload_url']}?token={info['upload_params'].get('token')}" if info['upload_params'].get('token') else info['upload_url']; f = open(p, 'rb'); r = session.post(url, files={'file': (p.name, f, info['upload_params'].get('content_type'))}, headers=headers(None, False), allow_redirects=False); f.close(); r.raise_for_status(); print(f"  ✓ Uploaded") or time.sleep(0.5)
            print(f"  [3/4] Confirm..."); r = session.get(r.headers.get('location'), headers=headers()); r.raise_for_status(); fid = str(r.json()['id']); update_csrf(); file_ids.append(fid); print(f"  ✓ File ID: {fid}") or time.sleep(1)
        except Exception as e: print(f"  ❌ Failed: {e}")
    if not file_ids: return print("\n❌ No files uploaded") or False
    print(f"\n  [4/4] Submit {len(file_ids)} file(s)..."); data = {'utf8': '✓', 'authenticity_token': csrf_token, 'submission[submission_type]': 'online_upload', 'submission[attachment_ids]': ','.join(file_ids), 'submission[eula_agreement_timestamp]': '', 'submission[comment]': ''}
    for i, fid in enumerate(file_ids): data[f'attachments[{i}][uploaded_data]'] = f'C:\\fakepath\\f{i}.dat'
    try: r = session.post(f"https://psu.instructure.com/courses/{course_id}/assignments/{assignment_id}/submissions", data=data, headers=headers('application/x-www-form-urlencoded; charset=UTF-8')); r.raise_for_status(); print(f"  ✅ Success! ID: {r.json().get('id')}"); return True
    except Exception as e: print(f"  ❌ Failed: {e}") or False
def run_gui(url, product, model, prompt, ref_files=[], assignment_folder=None):
    if not assignment_folder: raise ValueError("assignment_folder is required")
    output_dir = os.path.join(assignment_folder, 'auto', 'output'); os.makedirs(output_dir, exist_ok=True); [f.unlink() for f in Path(output_dir).glob('*') if f.is_file()]
    data = get_homework_details(url); description = unescape(re.sub(r'<[^>]+>', '\n', data['assignment']['description'])).strip(); answer = ask_llm_with_pdfs(description, product, model, prompt, ref_files)
    if '[no]' in answer.lower()[:100]: raise Exception("LLM returned [no]")
    clean_answer, img_requests = parse_img_requests(answer); answer_path = os.path.join(output_dir, 'answer.md'); open(answer_path, 'w', encoding='utf-8').write(clean_answer); generate_images(img_requests); docx_path = os.path.join(output_dir, 'answer.docx'); md_to_docx(docx_path, answer_path); return {'status': 'success', 'answer_path': answer_path, 'docx_path': docx_path}
def main(url=None, product=None, model=None):
    import argparse; parser = argparse.ArgumentParser(description='Homework automation CLI'); parser.add_argument('--url', type=str, help='Assignment URL'); parser.add_argument('--product', type=str, choices=['Gemini', 'Claude'], help='AI product (Gemini/Claude)'); parser.add_argument('--model', type=str, help='Model name'); args = parser.parse_args()
    url = args.url or url or TARGET_ASSIGNMENT_URL; product = args.product or product or 'Gemini'; model = args.model or model or 'gemini-2.5-pro'; print(f"🎯 URL: {url}\n🤖 Product: {product}\n📦 Model: {model}\n"); config.ensure_dirs(); [f.unlink() for f in Path(OUTPUT_DIR).glob('*') if f.is_file()]
    print("Step 1: Fetching assignment details..."); data = get_homework_details(url); print("\nStep 2: Extracting description..."); description = unescape(re.sub(r'<[^>]+>', '\n', data['assignment']['description'])).strip(); print(f"Description:\n{description}\n")
    print("Step 3: Asking LLM..."); answer = ask_llm_with_pdfs(description, product, model, config.DEFAULT_PROMPTS['homework'], ref_files=[]); print("\nStep 4: Validating and parsing answer...")
    if '[no]' in answer.lower()[:100]: sys.exit(print("❌ LLM returned [no] - Exiting..."))
    clean_answer, img_requests = parse_img_requests(answer); open(ANSWER_FILE, 'w', encoding='utf-8').write(clean_answer); print(f"✓ Answer saved to: {ANSWER_FILE}"); print("\nStep 5: Generating requested images..."); generate_images(img_requests); print("\nStep 6: Converting to DOCX..."); md_to_docx(f"{OUTPUT_DIR}/answer.docx", ANSWER_FILE); print(f"\n✅ All steps completed! Files in: {OUTPUT_DIR}/")
    print("\n" + "="*60); user_input = input("📤 Submit to Canvas? (yes/no): ").strip().lower()
    if user_input in ['yes', 'y']: submit_to_canvas(url); print("\n" + "="*60 + "\n🎉 All done!")
    else: print("⏸️  Submission skipped.")
if __name__ == '__main__': main()
