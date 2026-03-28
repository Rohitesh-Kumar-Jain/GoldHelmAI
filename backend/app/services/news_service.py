from __future__ import annotations

import logging
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote
from urllib.request import urlopen
from xml.etree import ElementTree

from app.utils.config import get_settings


logger = logging.getLogger(__name__)


class NewsService:
    """Fetches and caches gold-related financial news from RSS with a mock fallback."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.keywords = tuple(self.settings.news_keywords)
        self._cached_articles: list[dict[str, Any]] | None = None
        self._cache_loaded_at: datetime | None = None

    def get_latest_news(self) -> list[dict[str, Any]]:
        if self._is_cache_fresh():
            return [article.copy() for article in self._cached_articles or []]

        try:
            rss_articles = self._fetch_rss_articles()
            articles = self._filter_articles(rss_articles)
            if not articles:
                raise ValueError("RSS feed returned no matching articles.")
            self._update_cache(articles)
            return [article.copy() for article in articles]
        except Exception as exc:
            logger.warning("Falling back to mock news articles: %s", exc)
            fallback = self._build_mock_articles()
            self._update_cache(fallback)
            return [article.copy() for article in fallback]

    def _fetch_rss_articles(self) -> list[dict[str, Any]]:
        query = quote("gold inflation federal reserve interest rates USD")
        rss_url = (
            self.settings.news_rss_url
            or f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
        )

        with urlopen(rss_url, timeout=6) as response:  # noqa: S310 - user-configurable RSS URL
            payload = response.read()

        root = ElementTree.fromstring(payload)
        items = root.findall(".//item")
        articles: list[dict[str, Any]] = []
        for item in items[: self.settings.news_article_limit * 2]:
            title = (item.findtext("title") or "").strip()
            description = (item.findtext("description") or "").strip()
            published_at = self._parse_published_at(item.findtext("pubDate"))
            if not title and not description:
                continue

            articles.append(
                {
                    "title": title,
                    "description": description,
                    "published_at": published_at,
                }
            )

        return articles

    def _filter_articles(self, articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        filtered: list[dict[str, Any]] = []
        for article in articles:
            haystack = f"{article['title']} {article['description']}".lower()
            if any(keyword in haystack for keyword in self.keywords):
                filtered.append(article)
            if len(filtered) >= self.settings.news_article_limit:
                break

        return filtered

    @staticmethod
    def _parse_published_at(raw_value: str | None) -> str:
        if not raw_value:
            return datetime.now(UTC).isoformat()

        parsed = parsedate_to_datetime(raw_value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC).isoformat()

    def _build_mock_articles(self) -> list[dict[str, Any]]:
        now = datetime.now(UTC)
        return [
            {
                "title": "Gold steadies as investors weigh inflation and rate outlook",
                "description": "Markets remain focused on inflation signals and the next Federal Reserve decision.",
                "published_at": now.isoformat(),
            },
            {
                "title": "USD softness supports gold prices ahead of macro data",
                "description": "A softer dollar and cautious risk sentiment keep attention on bullion demand.",
                "published_at": now.isoformat(),
            },
            {
                "title": "Interest-rate uncertainty keeps gold traders defensive",
                "description": "Analysts expect rate guidance to shape near-term moves in gold futures.",
                "published_at": now.isoformat(),
            },
        ]

    def _update_cache(self, articles: list[dict[str, Any]]) -> None:
        self._cached_articles = [article.copy() for article in articles]
        self._cache_loaded_at = datetime.now(UTC)

    def _is_cache_fresh(self) -> bool:
        if self._cached_articles is None or self._cache_loaded_at is None:
            return False

        age_seconds = (datetime.now(UTC) - self._cache_loaded_at).total_seconds()
        return age_seconds < self.settings.news_cache_ttl_seconds
