"""Unified Canvas API client

Provides centralized API access with:
- Session management & cookie handling
- Automatic retry with backoff
- Connection pooling
- Consistent error handling

Usage:
    from core.canvas_api import CanvasAPI

    api = CanvasAPI()  # Auto-loads cookies from config
    courses = api.get_courses()
    assignment = api.get_assignment(course_id, assignment_id)
"""
import json
import os
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Import config at module level for paths
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

from .exceptions import (
    APIError, AuthError, CookieExpiredError, NetworkError,
    ParseError, RateLimitError, handle_api_errors
)


class CanvasAPI:
    """Canvas LMS API client with session management"""

    COOKIE_MAX_AGE_HOURS = 24
    DEFAULT_TIMEOUT = 10
    DEFAULT_PER_PAGE = 100

    def __init__(
        self,
        base_url: Optional[str] = None,
        cookies_file: Optional[str] = None,
        auto_validate: bool = True
    ):
        """Initialize Canvas API client

        Args:
            base_url: Canvas instance URL (default: from config)
            cookies_file: Path to cookies JSON (default: from config)
            auto_validate: Validate cookies on init (default: True)
        """
        self.base_url = (base_url or config.CANVAS_BASE_URL).rstrip('/')
        self.cookies_file = cookies_file or config.COOKIES_FILE
        self.session = self._create_session()

        if auto_validate:
            self._load_and_validate_cookies()

    def _create_session(self) -> requests.Session:
        """Create session with connection pooling and retry"""
        session = requests.Session()

        # Retry strategy for transient failures
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=['GET', 'HEAD', 'POST']
        )

        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=retry
        )
        session.mount('https://', adapter)
        session.mount('http://', adapter)

        session.headers.update({
            'Accept': 'application/json+canvas-string-ids',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        return session

    def _load_and_validate_cookies(self) -> None:
        """Load cookies and validate freshness"""
        if not os.path.exists(self.cookies_file):
            raise CookieExpiredError(f"Cookies file not found: {self.cookies_file}")

        # Check file age
        file_age = datetime.now() - datetime.fromtimestamp(
            os.path.getmtime(self.cookies_file)
        )
        if file_age > timedelta(hours=self.COOKIE_MAX_AGE_HOURS):
            raise CookieExpiredError(
                f"Cookies expired ({file_age.total_seconds()/3600:.1f}h old). "
                "Please re-authenticate."
            )

        # Load cookies
        try:
            with open(self.cookies_file, 'r') as f:
                cookies_list = json.load(f)
        except json.JSONDecodeError as e:
            raise ParseError(f"Invalid cookies JSON: {e}")

        if not isinstance(cookies_list, list):
            raise ParseError("Cookies file should contain a list")

        cookies = {c['name']: c['value'] for c in cookies_list if 'name' in c and 'value' in c}
        if not cookies:
            raise CookieExpiredError("No valid cookies found")

        self.session.cookies.update(cookies)

    # ─────────────────────────────────────────────────────────────────
    # Core API Methods
    # ─────────────────────────────────────────────────────────────────

    @handle_api_errors
    def _get(self, endpoint: str, params: Optional[Dict] = None, timeout: int = None) -> Any:
        """Make GET request to Canvas API"""
        url = f"{self.base_url}/api/v1{endpoint}"
        response = self.session.get(url, params=params, timeout=timeout or self.DEFAULT_TIMEOUT)

        if response.status_code == 401:
            raise CookieExpiredError("Session expired (401)")
        if response.status_code == 429:
            retry_after = response.headers.get('Retry-After')
            raise RateLimitError(int(retry_after) if retry_after else 60)
        if response.status_code >= 400:
            raise APIError.from_response(response, endpoint)

        return response.json()

    @handle_api_errors
    def _get_paginated(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        max_pages: int = 10
    ) -> List[Any]:
        """Fetch all pages of a paginated endpoint"""
        params = params or {}
        params.setdefault('per_page', self.DEFAULT_PER_PAGE)

        all_items = []
        for page in range(1, max_pages + 1):
            params['page'] = page
            items = self._get(endpoint, params)
            if not items:
                break
            all_items.extend(items)
            if len(items) < params['per_page']:
                break

        return all_items

    # ─────────────────────────────────────────────────────────────────
    # Courses
    # ─────────────────────────────────────────────────────────────────

    def get_courses(self, enrollment_state: str = 'active') -> List[Dict]:
        """Get user's courses"""
        return self._get_paginated('/courses', {'enrollment_state': enrollment_state})

    def get_course(self, course_id: str) -> Dict:
        """Get single course details"""
        return self._get(f'/courses/{course_id}')

    def get_course_tabs(self, course_id: str) -> List[Dict]:
        """Get course navigation tabs"""
        return self._get(f'/courses/{course_id}/tabs')

    # ─────────────────────────────────────────────────────────────────
    # Assignments
    # ─────────────────────────────────────────────────────────────────

    def get_assignment(self, course_id: str, assignment_id: str) -> Dict:
        """Get assignment details"""
        return self._get(f'/courses/{course_id}/assignments/{assignment_id}')

    def get_assignments(self, course_id: str) -> List[Dict]:
        """Get all assignments for a course"""
        return self._get_paginated(f'/courses/{course_id}/assignments')

    # ─────────────────────────────────────────────────────────────────
    # Quizzes
    # ─────────────────────────────────────────────────────────────────

    def get_quiz(self, course_id: str, quiz_id: str) -> Dict:
        """Get quiz details"""
        return self._get(f'/courses/{course_id}/quizzes/{quiz_id}')

    def get_quiz_submissions(self, course_id: str, quiz_id: str) -> List[Dict]:
        """Get quiz submissions for current user"""
        result = self._get(f'/courses/{course_id}/quizzes/{quiz_id}/submissions')
        return result.get('quiz_submissions', [])

    def get_quiz_status(self, course_id: str, quiz_id: str) -> Dict:
        """Get comprehensive quiz status"""
        quiz = self.get_quiz(course_id, quiz_id)
        submissions = self.get_quiz_submissions(course_id, quiz_id)

        status = {
            'quiz_name': quiz.get('title'),
            'points_possible': quiz.get('points_possible'),
            'question_count': quiz.get('question_count', 0),
            'time_limit': quiz.get('time_limit'),
            'allowed_attempts': quiz.get('allowed_attempts', 1),
            'scoring_policy': quiz.get('scoring_policy', 'keep_highest'),
            'attempts_used': 0,
            'attempts_left': quiz.get('allowed_attempts', 1),
            'in_progress': False,
            'current_score': None,
            'highest_score': None,
        }

        if submissions:
            latest = submissions[0]
            status['attempts_used'] = latest.get('attempt', 0)

            allowed = status['allowed_attempts']
            if allowed == -1:
                status['attempts_left'] = 'Unlimited'
            else:
                status['attempts_left'] = max(0, allowed - status['attempts_used'])

            ws = latest.get('workflow_state', '')
            status['in_progress'] = ws in ['untaken', 'pending_review']

            scores = [s.get('score') for s in submissions if s.get('score') is not None]
            if scores:
                status['highest_score'] = max(scores)
                status['current_score'] = latest.get('kept_score') or status['highest_score']

        return status

    # ─────────────────────────────────────────────────────────────────
    # Discussions
    # ─────────────────────────────────────────────────────────────────

    def get_discussion(self, course_id: str, topic_id: str) -> Dict:
        """Get discussion topic details"""
        return self._get(f'/courses/{course_id}/discussion_topics/{topic_id}')

    # ─────────────────────────────────────────────────────────────────
    # Planner (TODOs)
    # ─────────────────────────────────────────────────────────────────

    def get_planner_items(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days: int = 365
    ) -> List[Dict]:
        """Get planner items (todos)

        Args:
            start_date: ISO date string (default: today)
            end_date: ISO date string (default: start + days)
            days: Days to look ahead if end_date not specified
        """
        if not start_date:
            start_date = datetime.now().date().isoformat()
        if not end_date:
            end = datetime.now() + timedelta(days=days)
            end_date = end.date().isoformat()

        return self._get_paginated(
            '/planner/items',
            {'start_date': start_date, 'end_date': end_date},
            max_pages=10
        )

    # ─────────────────────────────────────────────────────────────────
    # Submissions
    # ─────────────────────────────────────────────────────────────────

    def get_graded_submissions(self, max_pages: int = 5) -> List[Dict]:
        """Get user's graded submissions"""
        return self._get_paginated('/users/self/graded_submissions', max_pages=max_pages)

    # ─────────────────────────────────────────────────────────────────
    # URL Parsing Utilities
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def parse_canvas_url(url: str) -> Dict[str, Optional[str]]:
        """Parse Canvas URL to extract IDs

        Args:
            url: Canvas URL (assignment, quiz, discussion)

        Returns:
            Dict with course_id, resource_type, resource_id

        Raises:
            ParseError: If URL format is invalid
        """
        # Clean URL
        url = url.split('#')[0].split('?')[0]
        parts = urlparse(url).path.split('/')

        result = {'course_id': None, 'resource_type': None, 'resource_id': None}

        try:
            if 'courses' not in parts:
                raise ParseError(f"No 'courses' in URL: {url}")

            course_idx = parts.index('courses')
            if course_idx + 1 >= len(parts):
                raise ParseError(f"Missing course_id in URL: {url}")
            result['course_id'] = parts[course_idx + 1]

            # Find resource type
            for rtype in ['assignments', 'quizzes', 'discussion_topics']:
                if rtype in parts:
                    idx = parts.index(rtype)
                    if idx + 1 < len(parts):
                        result['resource_type'] = rtype
                        result['resource_id'] = parts[idx + 1]
                        break

            if not result['resource_type']:
                raise ParseError(f"Unknown resource type in URL: {url}")

        except (ValueError, IndexError) as e:
            raise ParseError(f"Failed to parse URL '{url}': {e}")

        return result


def create_session(validate: bool = True) -> CanvasAPI:
    """Factory function to create CanvasAPI instance

    Args:
        validate: Whether to validate cookies on creation

    Returns:
        Configured CanvasAPI instance
    """
    return CanvasAPI(auto_validate=validate)


# ─────────────────────────────────────────────────────────────────────────────
# Standalone functions for backward compatibility
# ─────────────────────────────────────────────────────────────────────────────

def load_cookies() -> Dict[str, str]:
    """Load cookies from file (backward compatible)

    Returns:
        Dict of cookie name -> value

    Raises:
        CookieExpiredError: If cookies missing or expired
    """
    api = CanvasAPI(auto_validate=True)
    return dict(api.session.cookies)
