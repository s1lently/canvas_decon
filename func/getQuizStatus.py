#!/usr/bin/env python3
"""
Quiz Status Fetcher - Independent Canvas API module for quiz status
Fetches: current score, highest score, attempts used/remaining, time limit
"""
import os
import sys
import re
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config


def create_session():
    """Create authenticated Canvas session"""
    import json
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json'
    })
    # Load cookies from cookies.json
    try:
        cookies = {c['name']: c['value'] for c in json.load(open(config.COOKIES_FILE))}
        s.cookies.update(cookies)
    except Exception as e:
        print(f"[getQuizStatus] Failed to load cookies: {e}")
    return s


def extract_quiz_ids(url):
    """Extract course_id and quiz_id from URL"""
    # Patterns: /courses/123/quizzes/456 or /courses/123/assignments/789
    course_match = re.search(r'/courses/(\d+)', url)
    quiz_match = re.search(r'/quizzes/(\d+)', url)

    course_id = course_match.group(1) if course_match else None
    quiz_id = quiz_match.group(1) if quiz_match else None

    return course_id, quiz_id


def get_quiz_status(url):
    """
    Fetch quiz status from Canvas API

    Args:
        url: Quiz URL (e.g., https://psu.instructure.com/courses/123/quizzes/456)

    Returns:
        dict: {
            'status': 'ok' | 'error',
            'quiz_name': str,
            'points_possible': float,
            'question_count': int,
            'time_limit': int | None (minutes),
            'allowed_attempts': int (-1 = unlimited),
            'attempts_used': int,
            'attempts_left': int | 'Unlimited',
            'scoring_policy': str ('keep_highest', 'keep_latest', etc),
            'current_score': float | None,
            'highest_score': float | None,
            'latest_score': float | None,
            'in_progress': bool,
            'time_remaining': int | None (seconds, if in progress),
            'error': str | None
        }
    """
    result = {
        'status': 'error',
        'quiz_name': None,
        'points_possible': None,
        'question_count': None,
        'time_limit': None,
        'allowed_attempts': 1,
        'attempts_used': 0,
        'attempts_left': 1,
        'scoring_policy': 'keep_highest',
        'current_score': None,
        'highest_score': None,
        'latest_score': None,
        'in_progress': False,
        'time_remaining': None,
        'error': None
    }

    try:
        course_id, quiz_id = extract_quiz_ids(url)
        if not course_id or not quiz_id:
            result['error'] = 'Invalid URL: cannot extract course/quiz ID'
            return result

        s = create_session()

        # 1. Fetch quiz metadata
        quiz_url = f"{config.CANVAS_BASE_URL}/api/v1/courses/{course_id}/quizzes/{quiz_id}"
        quiz_resp = s.get(quiz_url, timeout=10)

        if quiz_resp.status_code != 200:
            result['error'] = f'Quiz API error: {quiz_resp.status_code}'
            return result

        quiz_data = quiz_resp.json()
        result['quiz_name'] = quiz_data.get('title', 'Unknown Quiz')
        result['points_possible'] = quiz_data.get('points_possible')
        result['question_count'] = quiz_data.get('question_count', 0)
        result['time_limit'] = quiz_data.get('time_limit')  # minutes
        result['allowed_attempts'] = quiz_data.get('allowed_attempts', 1)
        result['scoring_policy'] = quiz_data.get('scoring_policy', 'keep_highest')

        # 2. Fetch quiz submissions (user's attempts)
        submissions_url = f"{config.CANVAS_BASE_URL}/api/v1/courses/{course_id}/quizzes/{quiz_id}/submissions"
        sub_resp = s.get(submissions_url, timeout=10)

        if sub_resp.status_code == 200:
            sub_data = sub_resp.json()
            quiz_submissions = sub_data.get('quiz_submissions', [])

            if quiz_submissions:
                # Get latest submission
                latest = quiz_submissions[0]
                result['attempts_used'] = latest.get('attempt', 0)

                # Calculate attempts left
                if result['allowed_attempts'] == -1:
                    result['attempts_left'] = 'Unlimited'
                else:
                    result['attempts_left'] = max(0, result['allowed_attempts'] - result['attempts_used'])

                # Check if in progress
                workflow_state = latest.get('workflow_state', '')
                result['in_progress'] = workflow_state in ['untaken', 'pending_review'] or (
                    workflow_state == 'complete' and latest.get('end_at') is None
                )

                # Time remaining (if in progress and time limited)
                if result['in_progress'] and result['time_limit']:
                    time_spent = latest.get('time_spent', 0)  # seconds
                    total_time = result['time_limit'] * 60  # convert to seconds
                    result['time_remaining'] = max(0, total_time - time_spent)

                # Scores
                result['latest_score'] = latest.get('score')
                result['kept_score'] = latest.get('kept_score')

                # Find highest score across all attempts
                scores = [sub.get('score') for sub in quiz_submissions if sub.get('score') is not None]
                if scores:
                    result['highest_score'] = max(scores)
                    result['current_score'] = result['kept_score'] if result['kept_score'] is not None else result['highest_score']
            else:
                # No submissions yet
                if result['allowed_attempts'] == -1:
                    result['attempts_left'] = 'Unlimited'
                else:
                    result['attempts_left'] = result['allowed_attempts']

        result['status'] = 'ok'
        return result

    except Exception as e:
        result['error'] = str(e)
        return result


def format_status_html(status):
    """
    Format status dict as HTML for display

    Args:
        status: Dict from get_quiz_status()

    Returns:
        HTML string
    """
    if status['status'] == 'error':
        return f'<span style="color:#ef4444;">Error: {status["error"]}</span>'

    parts = []

    # Score display
    if status['current_score'] is not None:
        score_color = '#22c55e' if status['current_score'] == status['points_possible'] else '#60a5fa'
        parts.append(f'<span style="color:{score_color};font-weight:bold;">{status["current_score"]}/{status["points_possible"]}</span>')
    else:
        parts.append('<span style="color:#9ca3af;">--/--</span>')

    # Highest score (if different from current)
    if status['highest_score'] is not None and status['highest_score'] != status['current_score']:
        parts.append(f'<span style="color:#a78bfa;">Best: {status["highest_score"]}</span>')

    # Attempts
    if status['allowed_attempts'] == -1:
        attempts_str = f'{status["attempts_used"]}/∞'
    else:
        attempts_str = f'{status["attempts_used"]}/{status["allowed_attempts"]}'

    if status['attempts_left'] == 0:
        parts.append(f'<span style="color:#ef4444;">Attempts: {attempts_str} (Done)</span>')
    elif status['attempts_left'] == 'Unlimited':
        parts.append(f'<span style="color:#22c55e;">Attempts: {attempts_str}</span>')
    else:
        parts.append(f'<span style="color:#eab308;">Attempts: {attempts_str} ({status["attempts_left"]} left)</span>')

    # In progress indicator
    if status['in_progress']:
        if status['time_remaining'] is not None:
            mins = status['time_remaining'] // 60
            secs = status['time_remaining'] % 60
            parts.append(f'<span style="color:#f59e0b;font-weight:bold;">⏱ {mins}:{secs:02d}</span>')
        else:
            parts.append('<span style="color:#f59e0b;font-weight:bold;">● In Progress</span>')

    # Time limit (if not in progress)
    elif status['time_limit']:
        parts.append(f'<span style="color:#9ca3af;">{status["time_limit"]} min</span>')

    return ' | '.join(parts)


def format_status_text(status):
    """
    Format status dict as plain text

    Args:
        status: Dict from get_quiz_status()

    Returns:
        Plain text string
    """
    if status['status'] == 'error':
        return f'Error: {status["error"]}'

    parts = []

    # Score
    if status['current_score'] is not None:
        parts.append(f'Score: {status["current_score"]}/{status["points_possible"]}')
    else:
        parts.append('Score: --')

    # Highest
    if status['highest_score'] is not None:
        parts.append(f'Best: {status["highest_score"]}')

    # Attempts
    if status['allowed_attempts'] == -1:
        parts.append(f'Attempts: {status["attempts_used"]}/∞')
    else:
        parts.append(f'Attempts: {status["attempts_used"]}/{status["allowed_attempts"]} ({status["attempts_left"]} left)')

    # In progress
    if status['in_progress']:
        if status['time_remaining'] is not None:
            mins = status['time_remaining'] // 60
            secs = status['time_remaining'] % 60
            parts.append(f'Time: {mins}:{secs:02d}')
        else:
            parts.append('In Progress')

    return ' | '.join(parts)


if __name__ == '__main__':
    # Test
    import sys
    if len(sys.argv) < 2:
        print("Usage: python getQuizStatus.py <quiz_url>")
        sys.exit(1)

    url = sys.argv[1]
    status = get_quiz_status(url)

    print("=== Quiz Status ===")
    for k, v in status.items():
        print(f"  {k}: {v}")

    print("\n=== Formatted ===")
    print(f"HTML: {format_status_html(status)}")
    print(f"Text: {format_status_text(status)}")
