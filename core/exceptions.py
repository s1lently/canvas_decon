"""Unified exception hierarchy for Canvas LMS Automation

Usage:
    from core.exceptions import APIError, CookieExpiredError

    try:
        response = api.get_assignment(...)
    except APIError as e:
        logger.error(f"API failed: {e.status_code} - {e}")
    except CookieExpiredError:
        # Trigger re-authentication
        pass
"""
from typing import Optional


class CanvasError(Exception):
    """Base exception for all Canvas operations"""
    pass


class ConfigError(CanvasError):
    """Configuration error (missing keys, invalid values)"""
    pass


class AuthError(CanvasError):
    """Authentication failed"""
    pass


class CookieExpiredError(AuthError):
    """Cookie expired or invalid (24h limit)"""
    def __init__(self, message: str = "Cookie expired. Please re-authenticate."):
        super().__init__(message)


class NetworkError(CanvasError):
    """Network-level error (timeout, connection refused)"""
    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(message)
        self.cause = cause


class APIError(CanvasError):
    """Canvas API returned error response"""
    def __init__(self, status_code: int, message: str, url: Optional[str] = None):
        self.status_code = status_code
        self.url = url
        super().__init__(f"[{status_code}] {message}")

    @classmethod
    def from_response(cls, response, url: Optional[str] = None):
        """Create from requests.Response"""
        try:
            detail = response.json().get('errors', [{}])[0].get('message', response.text[:200])
        except Exception:
            detail = response.text[:200] if response.text else 'Unknown error'
        return cls(response.status_code, detail, url or response.url)


class ParseError(CanvasError):
    """Data parsing error (invalid URL, malformed JSON)"""
    def __init__(self, message: str, data: Optional[str] = None):
        super().__init__(message)
        self.data = data


class RateLimitError(APIError):
    """API rate limit exceeded (429)"""
    def __init__(self, retry_after: Optional[int] = None):
        self.retry_after = retry_after
        super().__init__(429, f"Rate limited. Retry after {retry_after}s" if retry_after else "Rate limited")


# Exception handler decorator for clean error handling
def handle_api_errors(func):
    """Decorator to convert common exceptions to CanvasError types

    Usage:
        @handle_api_errors
        def fetch_data(url):
            response = session.get(url)
            ...
    """
    import functools
    import requests

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.Timeout as e:
            raise NetworkError(f"Request timeout: {e}", cause=e)
        except requests.ConnectionError as e:
            raise NetworkError(f"Connection failed: {e}", cause=e)
        except requests.HTTPError as e:
            if e.response is not None:
                if e.response.status_code == 429:
                    retry = e.response.headers.get('Retry-After')
                    raise RateLimitError(int(retry) if retry else None)
                raise APIError.from_response(e.response)
            raise NetworkError(str(e), cause=e)
        except (ValueError, KeyError, IndexError) as e:
            raise ParseError(f"Parse error: {e}")
    return wrapper
