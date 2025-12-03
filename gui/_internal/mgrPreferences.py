"""Preferences Manager - Manages app preferences (auto-fetch settings, etc.)"""
import os
import json
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import config


# Default preferences
DEFAULT_PREFERENCES = {
    'auto_fetch_cookie': True,      # Trigger: after saving valid credentials
    'auto_fetch_todos': True,       # Trigger: on startup if cookie exists
    'auto_fetch_courses': True,     # Trigger: after cookie is fetched
    'auto_fetch_syllabus': False,   # Trigger: after courses are fetched
}


class PreferencesManager:
    """Singleton preferences manager"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._prefs = None
        return cls._instance

    def __init__(self):
        if self._prefs is None:
            self._prefs = self._load()

    def _load(self):
        """Load preferences from file"""
        try:
            if os.path.exists(config.PREFERENCES_FILE):
                with open(config.PREFERENCES_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Merge with defaults to handle new keys
                    prefs = DEFAULT_PREFERENCES.copy()
                    prefs.update(loaded)
                    return prefs
        except Exception as e:
            print(f"[WARN] Failed to load preferences: {e}")
        return DEFAULT_PREFERENCES.copy()

    def _save(self):
        """Save preferences to file"""
        try:
            config.ensure_dirs()
            with open(config.PREFERENCES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._prefs, f, indent=2)
        except Exception as e:
            print(f"[ERROR] Failed to save preferences: {e}")

    def get(self, key, default=None):
        """Get a preference value"""
        return self._prefs.get(key, default)

    def set(self, key, value):
        """Set a preference value and save"""
        self._prefs[key] = value
        self._save()

    def get_all(self):
        """Get all preferences"""
        return self._prefs.copy()


# Singleton accessor
_manager = None

def get_preferences():
    """Get the singleton preferences manager"""
    global _manager
    if _manager is None:
        _manager = PreferencesManager()
    return _manager
