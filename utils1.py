import html
import os
import re
from urllib.parse import urlparse
def env_list(name):
    return [x.strip() for x in os.getenv(name, '').splitlines() if x.strip()]
def get_env_int(name, default):
    try:
        return int(os.getenv(name, '').strip())
    except (TypeError, ValueError):
        return default
def normalize_channel(value):
    value = (value or '').strip()
    if not value:
        return ''
    if value.startswith('https://t.me/'):
        value = '@' + value.rstrip('/').split('/')[-1]
    if not value.startswith('@') and not value.lstrip('-').isdigit():
        value = '@' + value
    return value
def channel_value(value):
    value = normalize_channel(value)
    return int(value) if value.lstrip('-').isdigit() else value
def safe_html(text):
    return html.escape(str(text or ''), quote=False)
def clean_text(text):
    text = re.sub(r'<[^>]+>', ' ', str(text or ''))
    return re.sub(r'\s+', ' ', text).strip()
def extract_domain(url):
    try:
        host = urlparse(url).netloc.lower()
        return host[4:] if host.startswith('www.') else host
    except Exception:
        return 'источник'
def is_admin(user):
    if user is None:
        return False
    allowed = os.getenv('ADMIN_ID', '').strip()
    return True if not allowed else str(user.id) == allowed
