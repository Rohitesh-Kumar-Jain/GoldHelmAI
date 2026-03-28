from __future__ import annotations

from collections import defaultdict
from datetime import UTC

import pandas as pd


class SentimentService:
    """Scores gold-market news with a lightweight finance-oriented lexicon."""

    POSITIVE_TERMS = {
        "rise",
        "rally",
        "gain",
        "support",
        "strong",
        "optimistic",
        "cooling inflation",
        "rate cut",
        "safe haven",
        "soft usd",
        "weaker dollar",
    }
    NEGATIVE_TERMS = {
        "fall",
        "drop",
        "loss",
        "pressure",
        "weak",
        "hawkish",
        "rate hike",
        "higher yields",
        "strong dollar",
        "selloff",
        "uncertainty",
    }

    def analyze_articles(self, articles: list[dict[str, Any]]) -> dict[str, Any]:
        if not articles:
            return {"sentiment_score": 0.0, "label": "neutral", "article_count": 0}

        article_scores = [self._score_article(article) for article in articles]
        aggregated_score = round(sum(article_scores) / len(article_scores), 4)
        return {
            "sentiment_score": aggregated_score,
            "label": self._label_from_score(aggregated_score),
            "article_count": len(article_scores),
        }

    def build_daily_sentiment_series(
        self,
        articles: list[dict[str, Any]],
        date_index: pd.Series,
    ) -> pd.Series:
        """Aggregates article sentiment by publication date and aligns it to market dates."""

        if date_index.empty:
            return pd.Series(dtype=float)

        daily_scores: dict[pd.Timestamp, list[float]] = defaultdict(list)
        for article in articles:
            published_at = pd.to_datetime(article.get("published_at"), utc=True, errors="coerce")
            if pd.isna(published_at):
                continue
            daily_scores[published_at.tz_convert(UTC).normalize().tz_localize(None)].append(
                self._score_article(article)
            )

        normalized_dates = pd.to_datetime(date_index, errors="coerce").dt.normalize()
        aligned_scores = []
        for date_value in normalized_dates:
            article_scores = daily_scores.get(date_value, [])
            aligned_scores.append(sum(article_scores) / len(article_scores) if article_scores else 0.0)

        return pd.Series(aligned_scores, index=date_index.index, dtype=float)

    def _score_article(self, article: dict[str, Any]) -> float:
        text = f"{article.get('title', '')} {article.get('description', '')}".lower()
        positive_hits = sum(term in text for term in self.POSITIVE_TERMS)
        negative_hits = sum(term in text for term in self.NEGATIVE_TERMS)

        if positive_hits == negative_hits == 0:
            return 0.0

        score = (positive_hits - negative_hits) / max(positive_hits + negative_hits, 1)
        return float(max(-1.0, min(1.0, score)))

    @staticmethod
    def _label_from_score(score: float) -> str:
        if score > 0.15:
            return "positive"
        if score < -0.15:
            return "negative"
        return "neutral"
