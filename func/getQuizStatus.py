#!/usr/bin/env python3
"""Quiz Status Fetcher - Canvas API for real-time quiz status"""
import os, sys, re, json, requests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

def create_session():
    s = requests.Session()
    s.headers.update({'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
    try: s.cookies.update({c['name']: c['value'] for c in json.load(open(config.COOKIES_FILE))})
    except: pass
    return s

def get_quiz_status(url):
    """Fetch quiz status. Returns dict with status, scores, attempts, in_progress, etc."""
    r = {'status': 'error', 'quiz_name': None, 'points_possible': None, 'question_count': None,
         'time_limit': None, 'allowed_attempts': 1, 'attempts_used': 0, 'attempts_left': 1,
         'scoring_policy': 'keep_highest', 'current_score': None, 'highest_score': None,
         'latest_score': None, 'in_progress': False, 'time_remaining': None, 'error': None}
    try:
        m = re.search(r'/courses/(\d+).*?/quizzes/(\d+)', url)
        if not m: r['error'] = 'Invalid URL'; return r
        cid, qid = m.groups()
        s = create_session()

        # Quiz metadata
        resp = s.get(f"{config.CANVAS_BASE_URL}/api/v1/courses/{cid}/quizzes/{qid}", timeout=10)
        if resp.status_code != 200: r['error'] = f'API error: {resp.status_code}'; return r
        q = resp.json()
        r.update({'quiz_name': q.get('title'), 'points_possible': q.get('points_possible'),
                  'question_count': q.get('question_count', 0), 'time_limit': q.get('time_limit'),
                  'allowed_attempts': q.get('allowed_attempts', 1), 'scoring_policy': q.get('scoring_policy', 'keep_highest')})

        # Submissions
        resp = s.get(f"{config.CANVAS_BASE_URL}/api/v1/courses/{cid}/quizzes/{qid}/submissions", timeout=10)
        if resp.status_code == 200:
            subs = resp.json().get('quiz_submissions', [])
            if subs:
                latest = subs[0]
                r['attempts_used'] = latest.get('attempt', 0)
                r['attempts_left'] = 'Unlimited' if r['allowed_attempts'] == -1 else max(0, r['allowed_attempts'] - r['attempts_used'])
                ws = latest.get('workflow_state', '')
                r['in_progress'] = ws in ['untaken', 'pending_review'] or (ws == 'complete' and not latest.get('end_at'))
                if r['in_progress'] and r['time_limit']:
                    r['time_remaining'] = max(0, r['time_limit'] * 60 - latest.get('time_spent', 0))
                r['latest_score'], r['kept_score'] = latest.get('score'), latest.get('kept_score')
                scores = [x.get('score') for x in subs if x.get('score') is not None]
                if scores: r['highest_score'] = max(scores); r['current_score'] = r['kept_score'] or r['highest_score']
            else:
                r['attempts_left'] = 'Unlimited' if r['allowed_attempts'] == -1 else r['allowed_attempts']
        r['status'] = 'ok'
    except Exception as e: r['error'] = str(e)
    return r

if __name__ == '__main__':
    url = sys.argv[1] if len(sys.argv) > 1 else exit("Usage: python getQuizStatus.py <url>")
    for k, v in get_quiz_status(url).items(): print(f"  {k}: {v}")
