import math
import uuid

class UrlShortener:
    _store = {}

    @classmethod
    def shorten(cls, url):
        short_id = str(uuid.uuid4())[:8]
        cls._store[short_id] = url
        return short_id

    @classmethod
    def get_url(cls, short_id):
        return cls._store.get(short_id)

shortener = UrlShortener()

def format_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])

def format_duration(seconds):
    if not seconds:
        return "00:00"
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def sanitize_filename(filename):
    return "".join([c for c in filename if c.isalpha() or c.isdigit() or c in " .-_"]).rstrip()

from urllib.parse import urlparse

def extract_platform(url):
    domain = urlparse(url).netloc.lower()
    if 'youtube.com' in domain or 'youtu.be' in domain:
        return 'youtube'
    elif 'instagram.com' in domain:
        return 'instagram'
    elif 'twitter.com' in domain or 'x.com' in domain:
        return 'twitter'
    elif 'reddit.com' in domain:
        return 'reddit'
    elif 'tiktok.com' in domain:
        return 'tiktok'
    elif 'facebook.com' in domain or 'fb.watch' in domain:
        return 'facebook'
    return None
