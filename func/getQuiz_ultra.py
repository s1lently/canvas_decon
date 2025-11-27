import requests, json, os, sys
from lxml import html
from urllib.parse import urljoin, unquote, urlparse
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from func import utilPromptFiles
BASE_QUIZ_URL = "https://psu.instructure.com/courses/2405803/quizzes/5363417"
OUT = config.OUTPUT_DIR
def start_quiz(s, url):
    p = urlparse(url).path.split('/'); cid, qid = p[p.index('courses')+1], p[p.index('quizzes')+1]; r = s.get(url, timeout=20)
    if html.fromstring(r.content).xpath('//*[@id="questions"]'): return r
    csrf = next((unquote(c.value) for c in s.cookies if c.name == '_csrf_token'), ''); uid = (html.fromstring(r.content).xpath('//meta[@name="current-user-id"]/@content') or ['7333037'])[0]
    r = s.post(f"https://psu.instructure.com/courses/{cid}/quizzes/{qid}/take", data={'user_id': uid, '_method': 'post', 'authenticity_token': csrf}, headers={'Referer': url}, timeout=30, allow_redirects=True)
    return r if html.fromstring(r.content).xpath('//*[@id="questions"]') else None
def parse_questions(doc, base_url, output_dir):
    idir = os.path.join(output_dir, 'images'); os.makedirs(idir, exist_ok=True); tasks = []
    def dl(u, p):
        try: open(p, 'wb').write(requests.get(u, timeout=10).content); return p
        except: return None
    qs = []
    for qdiv in doc.xpath('//*[@id="questions"]/div[contains(@class, "question")]'):
        qc = qdiv.xpath('.//div[starts-with(@id, "question_")]')[0]; qid = qc.get('id'); qt = qc.xpath('.//div[contains(@class, "question_text")]')[0].text_content().strip(); qimgs = []
        for img in qc.xpath('.//div[contains(@class, "question_text")]//img'):
            if u := img.get('src'): ip = os.path.join(idir, f"q_{qid}_{len(qimgs)}.png"); tasks.append((urljoin(base_url, u), ip)); qimgs.append(ip)
        ans = []
        for ael in qc.xpath('.//div[contains(@class, "select_answer") or (contains(@class, "answer") and @class="answer")]'):
            ai = ael.xpath('.//input[@type="radio"]')
            if not ai: continue
            ainp = ai[0].get('id'); aid = ai[0].get('value') or (ainp.replace('answer-', '') if ainp and ainp.startswith('answer-') else None)
            if not aid: continue
            albl = ael.xpath(f'.//label[@for="{ainp}"]') or ael.xpath('.//label'); atxt = albl[0].text_content().strip() if albl else ''; aimgs = []
            for img in ael.xpath('.//img'):
                if u := img.get('src'): ip = os.path.join(idir, f"a_{aid}_{len(aimgs)}.png"); tasks.append((urljoin(base_url, u), ip)); aimgs.append(ip)
            ans.append({'id': aid, 'txt': atxt, 'imgs': aimgs or None})
        qs.append({'id': qid, 'txt': qt, 'imgs': qimgs or None, 'ans': ans})
    if tasks: print(f"⬇️  {len(tasks)} images..."); [list(ThreadPoolExecutor(max_workers=20).map(lambda x: dl(x[0], x[1]), tasks))]
    return qs
def get_answers(qs, product, model, prompt, thinking=False):
    files = []; file_map = {}
    for q in qs:
        for img in (q.get('imgs') or []):
            if img not in file_map: file_map[img] = len(files); files.append(img)
        for a in q['ans']:
            for img in (a.get('imgs') or []):
                if img not in file_map: file_map[img] = len(files); files.append(img)
    if files: print(f"📤 Uploading {len(files)} images...")
    uploaded_info = utilPromptFiles.upload_files(files, product); img_desc = []
    if files:
        if product == 'Gemini': img_desc.append("\nUploaded Images (with URIs):"); [img_desc.append(f"  {info['uri']}: {info['filename']}") for idx, info in enumerate(uploaded_info)]
        else: img_desc.append("\nImages are uploaded in order and passed to you sequentially."); img_desc.append("When you see 'Image N' in the questions, it refers to the Nth image in the sequence below:"); [img_desc.append(f"  Image {idx+1}: {info['filename']}") for idx, info in enumerate(uploaded_info)]
        img_desc.append("")
    qd = {}
    for q in qs:
        opts = {}
        for a in q['ans']:
            t = a['txt'] or "No answer text provided."
            if a.get('imgs'): img_refs = [uploaded_info[file_map[i]]['uri'] for i in a['imgs']] if product == 'Gemini' else [f"Image {file_map[i]+1}" for i in a['imgs']]; t += f" [See: {', '.join(img_refs)}]"
            opts[a['id']] = t
        qe = {'question': q['txt'], 'options': opts}
        if q.get('imgs'): img_refs = [uploaded_info[file_map[i]]['uri'] for i in q['imgs']] if product == 'Gemini' else [f"Image {file_map[i]+1}" for i in q['imgs']]; qe['question_images'] = img_refs
        qd[q['id']] = qe
    full_prompt = f"{prompt}{''.join(img_desc)}\n\nQuestions:\n{json.dumps(qd, indent=2)}"; print(f"🤖 Calling {product} {model}..." + (" (thinking mode)" if product == 'Claude' and thinking else "")); result = utilPromptFiles.call_ai(full_prompt, product, model, uploaded_info=uploaded_info, thinking=thinking); cleaned = result.strip()
    if '```json' in cleaned: cleaned = cleaned.split('```json')[1].split('```')[0].strip()
    elif '```' in cleaned: cleaned = cleaned.split('```')[1].split('```')[0].strip()
    try: parsed = json.loads(cleaned); print(f"✅ Got {len(parsed)} answers\n"); return parsed
    except json.JSONDecodeError:
        import re; match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned, re.DOTALL)
        if match:
            try: parsed = json.loads(match.group(0)); print(f"✅ Got {len(parsed)} answers\n"); return parsed
            except: pass
        print(f"❌ Failed to parse JSON from response"); raise ValueError(f"Failed to parse JSON")
def save_preview(qs, html_txt, output_dir):
    os.makedirs(output_dir, exist_ok=True); open(os.path.join(output_dir, 'questions.html'), 'w', encoding='utf-8').write(html_txt)
    with open(os.path.join(output_dir, 'questions.md'), 'w', encoding='utf-8') as f:
        for i, q in enumerate(qs):
            f.write(f"### Q{i+1} ({q['id']})\n{q['txt']}\n\n")
            if q.get('imgs'): f.write("**Q-Imgs:** " + ", ".join([f"`{os.path.basename(i)}`" for i in q['imgs']]) + "\n\n")
            f.write("**Answers:**\n"); [f.write(f"- `{a['id']}`: {a['txt'] or '[IMG]'}") or (a.get('imgs') and f.write(f" (Imgs: {', '.join([os.path.basename(i) for i in a['imgs']])})")) or f.write("\n") for a in q['ans']]
            f.write("\n---\n\n")
    print(f"✓ Preview saved: {output_dir}/questions.html & questions.md")
def save_answers(qs, ans, output_dir):
    with open(os.path.join(output_dir, 'QesWA.md'), 'w', encoding='utf-8') as f:
        f.write("# Quiz Answers\n\n")
        for i, q in enumerate(qs):
            f.write(f"### Q{i+1} ({q['id']})\n{q['txt']}\n\n")
            if q.get('imgs'): f.write("**Q-Imgs:** " + ", ".join([f"`{os.path.basename(i)}`" for i in q['imgs']]) + "\n\n")
            sel = ans.get(q['id']); [f.write(f"- {'✅ ' if a['id'] == sel else ''}`{a['id']}`: {a['txt'] or 'No answer text provided.'}") or (a.get('imgs') and f.write(f" (Imgs: {', '.join([os.path.basename(i) for i in a['imgs']])})")) or f.write("\n") for a in q['ans']]
            f.write("\n")
def submit(s, url, doc, qs, ans, skip_confirm=False):
    un = set(q['id'] for q in qs) - set(ans.keys()); print(f"\n{'='*60}\nTotal: {len(qs)} | Answered: {len(ans)} | Unanswered: {len(un)}")
    if not skip_confirm:
        if un:
            if input(f"⚠️  {len(un)} unanswered! Type 'yes confirm': ").strip().lower() != 'yes confirm': return print("❌ Cancelled")
        else:
            if input("✓ All done. Submit? (y/yes/ok): ").strip().lower() not in ['y', 'yes', 'ok']: return print("❌ Cancelled")
    f = doc.xpath('//form[@id="submit_quiz_form"]')[0]; p = {i.get('name'): i.get('value', '') for i in f.xpath('.//input') if i.get('name')}; p.update(ans); print("Submitting..."); r = s.post(urljoin(url, f.get('action')), data=p, timeout=30); print("✅ Done!"); return r
def check_quiz_status(s, url):
    """Check if quiz is started. Returns (is_started, response, session)"""
    r = s.get(url if '/take' in url else url + '/take', timeout=20)
    if not r: return (False, None, s, 'failed')
    d = html.fromstring(r.content)
    has_questions = bool(d.xpath('//*[@id="questions"]'))
    return (has_questions, r, s, 'started' if has_questions else 'not_started')

def start_quiz_now(s, url):
    """Actually start the quiz by POSTing to Canvas"""
    p = urlparse(url).path.split('/'); cid, qid = p[p.index('courses')+1], p[p.index('quizzes')+1]
    r = s.get(url, timeout=20)
    csrf = next((unquote(c.value) for c in s.cookies if c.name == '_csrf_token'), '')
    uid = (html.fromstring(r.content).xpath('//meta[@name="current-user-id"]/@content') or [''])[0]
    r = s.post(f"https://psu.instructure.com/courses/{cid}/quizzes/{qid}/take",
               data={'user_id': uid, '_method': 'post', 'authenticity_token': csrf},
               headers={'Referer': url}, timeout=30, allow_redirects=True)
    d = html.fromstring(r.content)
    if d.xpath('//*[@id="questions"]'):
        return (True, r, s)
    return (False, r, s)

def run_gui(url, product, model, prompt, assignment_folder=None, thinking=False, auto_start=False):
    if not assignment_folder: raise ValueError("assignment_folder is required")
    output_dir = os.path.join(assignment_folder, 'auto', 'output'); os.makedirs(output_dir, exist_ok=True)
    c = {x['name']: x['value'] for x in json.load(open(config.COOKIES_FILE))}
    s = requests.Session(); s.cookies.update(c); s.headers.update({'User-Agent': 'Mozilla/5.0'})

    # Check quiz status first
    is_started, r, s, status = check_quiz_status(s, url)

    if status == 'failed':
        raise Exception("Failed to access quiz")

    if not is_started:
        if not auto_start:
            # Return special status to let GUI handle the prompt
            return {'status': 'not_started', 'session': s, 'url': url}
        else:
            # Auto start quiz
            print("🚀 Starting quiz...")
            success, r, s = start_quiz_now(s, url)
            if not success:
                raise Exception("Failed to start quiz")

    d = html.fromstring(r.content)
    qs = parse_questions(d, r.url, output_dir)
    if not qs:
        raise Exception("No questions found - quiz may not be properly started")
    save_preview(qs, r.text, output_dir)
    ans = get_answers(qs, product, model, prompt, thinking=thinking)
    save_answers(qs, ans, output_dir)
    return {'status': 'success', 'questions': qs, 'answers': ans, 'output_dir': output_dir, 'session': s, 'doc': d, 'url': r.url}
def main(url=None, product=None, model=None):
    import argparse; parser = argparse.ArgumentParser(description='Quiz automation CLI'); parser.add_argument('--url', type=str, help='Quiz URL'); parser.add_argument('--product', type=str, choices=['Gemini', 'Claude'], help='AI product (Gemini/Claude)'); parser.add_argument('--model', type=str, help='Model name'); args = parser.parse_args()
    url = args.url or url or BASE_QUIZ_URL; product = args.product or product or 'Gemini'; model = args.model or model or 'gemini-2.5-pro'; print(f"🎯 URL: {url}\n🤖 Product: {product}\n📦 Model: {model}\n"); config.ensure_dirs(); c = {x['name']: x['value'] for x in json.load(open(config.COOKIES_FILE))}; s = requests.Session(); s.cookies.update(c); s.headers.update({'User-Agent': 'Mozilla/5.0'})
    print("Accessing quiz directly..."); r = s.get(url if '/take' in url else url + "/take", timeout=20)
    if not r: return print("❌ Failed to access")
    d = html.fromstring(r.content); print("Parsing..."); qs = parse_questions(d, r.url, OUT); print(f"✓ {len(qs)} questions"); save_preview(qs, r.text, OUT); print("Getting answers..."); ans = get_answers(qs, product, model, config.DEFAULT_PROMPTS['quiz']); print(f"✓ {len(ans)} answers"); save_answers(qs, ans, OUT); submit(s, r.url, d, qs, ans)
if __name__ == '__main__': main()
