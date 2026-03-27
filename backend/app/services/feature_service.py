from __future__ import annotations

import pandas as pd


class FeatureEngineeringService:
    """Builds tabular features for next-day gold price prediction."""

    @staticmethod
    def build_features(frame: pd.DataFrame) -> pd.DataFrame:
        features = frame.copy()
        features["close"] = pd.to_numeric(features["close"], errors="coerce")
        features["date"] = pd.to_datetime(features["date"], errors="coerce")
        features = features.dropna(subset=["date", "close"]).sort_values("date").reset_index(drop=True)

        features["lag_1"] = features["close"].shift(1)
        features["lag_2"] = features["close"].shift(2)
        features["ma7"] = features["close"].rolling(window=7).mean()
        features["ma14"] = features["close"].rolling(window=14).mean()
        features["ma30"] = features["close"].rolling(window=30).mean()
        features["returns"] = features["close"].pct_change()
        features["volatility"] = features["returns"].rolling(window=7).std()
        features["momentum_7"] = features["close"] / features["ma7"] - 1.0
        features["momentum_14"] = features["close"] / features["ma14"] - 1.0
        features["target_return"] = features["close"].shift(-1) / features["close"] - 1.0
        return features.dropna().reset_index(drop=True)
