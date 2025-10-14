"""Login module for Canvas authentication"""
from .getCookie import get_cookies
from .getTotp import generate_token

__all__ = ['get_cookies', 'generate_token']
