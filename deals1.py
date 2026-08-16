import asyncio
import hashlib
import html
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus, urlparse
import aiohttp
import feedparser
from .utils import clean_text, env_list, extract_domain, safe_html
log = logging.getLogger('skidkivilki.deals')
DATA_DIR = Path(os.getenv('DATA_DIR', 'data'))
SEEN_FILE = DATA_DIR / 'seen_deals.json'
DEFAULT_QUERIES = ['скидка промокод цена', 'скидка акция распродажа', 'deal discount promo code', 'sale discount price']
GOOGLE_NEWS_TEMPLATE = 'https://news.google.com/rss/search?q={query}&hl=ru&gl=RU&ceid=RU:ru'
@dataclass
class Deal:
    title: str
    url: str
    description: str = ''
    source: str = ''
    published: str = ''
    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(f'{self.title}|{self.url}'.lower().strip().encode('utf-8')).hexdigest()
    def to_telegram_html(self) -> str:
        title = safe_html(self.title[:220])
        description = safe_html(clean_text(self.description)[:500])
        source = safe_html(self.source or extract_domain(self.url))
        text = f'🔥 <b>{title}</b>\n\n'
        if description:
            text += f'{description}\n\n'
        text += f'🏪 {source}\n\n👉 <a href="{html.escape(self.url, quote=True)}">ЗАБРАТЬ СКИДКУ</a>\n\n#скидка #акция'
        return text
class DealCollector:
    def __init__(self):
        self.feed_urls = self._build_feed_list()
        self.seen = self._load_seen()
    @property
    def feed_count(self):
        return len(self.feed_urls)
    def _build_feed_list(self):
        custom = env_list('DEAL_FEEDS')
        if custom:
            return custom
        queries = env_list('DEAL_QUERIES') or DEFAULT_QUERIES
        return [GOOGLE_NEWS_TEMPLATE.format(query=quote_plus(query)) for query in queries]
    def _load_seen(self):
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            if SEEN_FILE.exists():
                data = json.loads(SEEN_FILE.read_text('utf-8'))
                return set(str(x) for x in data) if isinstance(data, list) else set()
        except Exception:
            log.exception('Не удалось загрузить базу опубликованных скидок')
        return set()
    def _save_seen(self):
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            SEEN_FILE.write_text(json.dumps(list(self.seen)[-5000:], ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception:
            log.exception('Не удалось сохранить базу скидок')
    async def _fetch_feed(self, session, url):
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=20), headers={'User-Agent': 'SkidkiVilkiBot/1.0'}) as response:
                if response.status != 200:
                    log.warning('Источник вернул HTTP %s: %s', response.status, url)
                    return []
                parsed = feedparser.parse(await response.read())
                return parsed.entries or []
        except Exception:
            log.exception('Ошибка источника: %s', url)
            return []
    def _entry_to_deal(self, entry):
        title = clean_text(entry.get('title', ''))
        url = entry.get('link', '').strip()
        if not title or not url or urlparse(url).scheme not in {'http', 'https'}:
            return None
        description = entry.get('summary') or entry.get('description') or ''
        source = clean_text(entry.source.get('title', '')) if entry.get('source') else ''
        return Deal(title=title, url=url, description=clean_text(description), source=source or extract_domain(url), published=entry.get('published', ''))
    async def collect(self, limit=8):
        connector = aiohttp.TCPConnector(limit=8, ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            results = await asyncio.gather(*(self._fetch_feed(session, url) for url in self.feed_urls), return_exceptions=True)
        candidates, local_seen = [], set()
        keywords = re.compile(r'(скидк|распродаж|акци|промокод|sale|deal|discount|coupon|off|price|цена|бесплат)', re.I)
        for result in results:
            if isinstance(result, Exception):
                continue
            for entry in result:
                deal = self._entry_to_deal(entry)
                if not deal or deal.fingerprint in self.seen or deal.fingerprint in local_seen:
                    continue
                local_seen.add(deal.fingerprint)
                candidates.append(deal)
        candidates.sort(key=lambda d: (bool(keywords.search(d.title)), d.published), reverse=True)
        return candidates[:limit]
    def mark_published(self, deal):
        self.seen.add(deal.fingerprint)
        self._save_seen()
