import requests, json, os, sys
from lxml import html
from urllib.parse import urljoin, unquote, urlparse
from concurrent.futures import ThreadPoolExecutor
import google.generativeai as genai

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

# Config
BASE_QUIZ_URL = "https://psu.instructure.com/courses/2405803/quizzes/5363417"
OUT = config.QUIZ_RES_DIR

def start_quiz(s, url):
    """Start/resume quiz"""
    p = urlparse(url).path.split('/')
    cid, qid = p[p.index('courses')+1], p[p.index('quizzes')+1]
    r = s.get(url, timeout=20)
    if html.fromstring(r.content).xpath('//*[@id="questions"]'): return r
    csrf = next((unquote(c.value) for c in s.cookies if c.name == '_csrf_token'), '')
    uid = (html.fromstring(r.content).xpath('//meta[@name="current-user-id"]/@content') or ['7333037'])[0]
    r = s.post(f"https://psu.instructure.com/courses/{cid}/quizzes/{qid}/take",
               data={'user_id': uid, '_method': 'post', 'authenticity_token': csrf},
               headers={'Referer': url}, timeout=30, allow_redirects=True)
    return r if html.fromstring(r.content).xpath('//*[@id="questions"]') else None

def parse_questions(doc):
    """Parse questions & download images"""
    idir = os.path.join(OUT, 'images')
    os.makedirs(idir, exist_ok=True)
    tasks = []
    def dl(u, p):
        try: open(p, 'wb').write(requests.get(u, timeout=10).content); return p
        except: return None
    qs = []
    for qdiv in doc.xpath('//*[@id="questions"]/div[contains(@class, "question")]'):
        qc = qdiv.xpath('.//div[starts-with(@id, "question_")]')[0]
        qid = qc.get('id')
        qt = qc.xpath('.//div[contains(@class, "question_text")]')[0].text_content().strip()
        qimgs = []
        for img in qc.xpath('.//div[contains(@class, "question_text")]//img'):
            if u := img.get('src'):
                ip = os.path.join(idir, f"q_{qid}_{len(qimgs)}.png")
                tasks.append((urljoin(BASE_QUIZ_URL, u), ip))
                qimgs.append(ip)
        ans = []
        # Only select visible answer divs (exclude hidden short_answer, matching, etc)
        for ael in qc.xpath('.//div[contains(@class, "select_answer") or (contains(@class, "answer") and @class="answer")]'):
            ai = ael.xpath('.//input[@type="radio"]')
            if not ai: continue
            ainp = ai[0].get('id')
            # Extract ID: from value (active quiz) or from id="answer-XXXX" (review page)
            aid = ai[0].get('value') or (ainp.replace('answer-', '') if ainp and ainp.startswith('answer-') else None)
            if not aid: continue
            albl = ael.xpath(f'.//label[@for="{ainp}"]') or ael.xpath('.//label')
            atxt = albl[0].text_content().strip() if albl else ''
            aimgs = []
            for img in ael.xpath('.//img'):
                if u := img.get('src'):
                    ip = os.path.join(idir, f"a_{aid}_{len(aimgs)}.png")
                    tasks.append((urljoin(BASE_QUIZ_URL, u), ip))
                    aimgs.append(ip)
            ans.append({'id': aid, 'txt': atxt, 'imgs': aimgs or None})
        qs.append({'id': qid, 'txt': qt, 'imgs': qimgs or None, 'ans': ans})
    if tasks:
        print(f"⬇️  {len(tasks)} images...")
        with ThreadPoolExecutor(max_workers=20) as ex:
            list(ex.map(lambda x: dl(x[0], x[1]), tasks))
    return qs

def get_answers(qs):
    """Get Gemini answers"""
    genai.configure(api_key=config.GEMINI_API_KEY)
    m = genai.GenerativeModel('gemini-2.5-pro')
    files, imap = [], {}
    print("\n📤 Uploading...")
    for q in qs:
        for ip in (q.get('imgs') or []) + sum([a.get('imgs') or [] for a in q['ans']], []):
            if ip not in imap:
                try: f = genai.upload_file(path=str(ip), display_name=os.path.basename(ip)); imap[ip] = f; files.append(f)
                except: pass
    print(f"✓ Uploaded {len(files)} images\n")
    qd = {}
    for q in qs:
        opts = {}
        for a in q['ans']:
            t = a['txt'] or "[IMAGE]"
            if a.get('imgs'): t += f" [See images: {', '.join([os.path.basename(i) for i in a['imgs']])}]"
            opts[a['id']] = t
        qe = {'question': q['txt'], 'options': opts}
        if q.get('imgs'): qe['question_images'] = [os.path.basename(i) for i in q['imgs']]
        qd[q['id']] = qe
    prompt = f"Analyze the quiz questions and uploaded images carefully. Select the best answer for each question.\nReturn ONLY valid JSON: {{\"question_id\": \"answer_id\", ...}}\n\nQuestions:\n{json.dumps(qd, indent=2)}\n\nExample: {{\"question_97585716\": \"7574\"}}"
    print("Asking Gemini...")
    r = m.generate_content([prompt] + files)
    return json.loads(r.text.strip().replace('```json', '').replace('```', ''))

def save_preview(qs, html_txt):
    """Save HTML & MD for quick preview"""
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, 'questions.html'), 'w', encoding='utf-8').write(html_txt)
    with open(os.path.join(OUT, 'questions.md'), 'w', encoding='utf-8') as f:
        for i, q in enumerate(qs):
            f.write(f"### Q{i+1} ({q['id']})\n{q['txt']}\n\n")
            if q.get('imgs'): f.write("**Q-Imgs:** " + ", ".join([f"`{os.path.basename(i)}`" for i in q['imgs']]) + "\n\n")
            f.write("**Answers:**\n")
            for a in q['ans']:
                f.write(f"- `{a['id']}`: {a['txt'] or '[IMG]'}")
                if a.get('imgs'): f.write(f" (Imgs: {', '.join([os.path.basename(i) for i in a['imgs']])})")
                f.write("\n")
            f.write("\n---\n\n")
    print(f"✓ Preview saved: {OUT}/questions.html & questions.md")

def save_answers(qs, ans):
    """Save answers"""
    with open(os.path.join(OUT, 'QesWA.md'), 'w', encoding='utf-8') as f:
        f.write("# Quiz Answers\n\n")
        for i, q in enumerate(qs):
            f.write(f"### Q{i+1} ({q['id']})\n{q['txt']}\n\n")
            sel = ans.get(q['id'])
            for a in q['ans']:
                m = "✅ " if a['id'] == sel else ""
                f.write(f"- {m}`{a['id']}`: {a['txt'] or '[IMG]'}\n")
            f.write("\n")

def submit(s, url, doc, qs, ans):
    """Submit quiz"""
    un = set(q['id'] for q in qs) - set(ans.keys())
    print(f"\n{'='*60}\nTotal: {len(qs)} | Answered: {len(ans)} | Unanswered: {len(un)}")
    if un:
        if input(f"⚠️  {len(un)} unanswered! Type 'yes confirm': ").strip().lower() != 'yes confirm': return print("❌ Cancelled")
    else:
        if input("✓ All done. Submit? (y/yes/ok): ").strip().lower() not in ['y', 'yes', 'ok']: return print("❌ Cancelled")
    f = doc.xpath('//form[@id="submit_quiz_form"]')[0]
    p = {i.get('name'): i.get('value', '') for i in f.xpath('.//input') if i.get('name')}
    p.update(ans)
    print("Submitting...")
    r = s.post(urljoin(url, f.get('action')), data=p, timeout=30)
    open(os.path.join(OUT, 'quiz_response.html'), 'w', encoding='utf-8').write(r.text)
    print("✅ Done!")

def main():
    config.ensure_dirs()
    c = {x['name']: x['value'] for x in json.load(open(config.COOKIES_FILE))}
    s = requests.Session()
    s.cookies.update(c)
    s.headers.update({'User-Agent': 'Mozilla/5.0'})

    # Direct access to /take page (skip start_quiz for debugging)
    print("Accessing quiz directly...")
    r = s.get(BASE_QUIZ_URL + "/take", timeout=20)
    # r = start_quiz(s, BASE_QUIZ_URL)  # Uncomment if attempts remaining
    if not r: return print("❌ Failed to access")

    d = html.fromstring(r.content)
    print("Parsing...")
    qs = parse_questions(d)
    print(f"✓ {len(qs)} questions")
    save_preview(qs, r.text)
    print("Getting answers...")
    ans = get_answers(qs)
    print(f"✓ {len(ans)} answers")
    save_answers(qs, ans)
    submit(s, r.url, d, qs, ans)

if __name__ == '__main__':
    main()
