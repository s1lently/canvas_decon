"""Done.txt manager for tracking completed assignments"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config


class DoneManager:
    """Manages Done.txt file for completed assignments"""

    def __init__(self):
        self.done_urls = set()
        self.load()

    def load(self):
        """Load completed redirect_urls from Done.txt"""
        self.done_urls.clear()
        if os.path.exists(config.DONE_FILE):
            with open(config.DONE_FILE, 'r', encoding='utf-8') as f:
                self.done_urls = {line.strip() for line in f if line.strip()}

    def save(self):
        """Save completed redirect_urls to Done.txt"""
        with open(config.DONE_FILE, 'w', encoding='utf-8') as f:
            for url in sorted(self.done_urls):
                f.write(url + '\n')

    def is_done(self, redirect_url):
        """Check if redirect_url is marked as done"""
        return redirect_url in self.done_urls

    def mark_done(self, redirect_url):
        """Mark redirect_url as done"""
        if redirect_url and redirect_url not in self.done_urls:
            self.done_urls.add(redirect_url)
            self.save()

    def mark_undone(self, redirect_url):
        """Unmark redirect_url as done"""
        if redirect_url in self.done_urls:
            self.done_urls.discard(redirect_url)
            self.save()
