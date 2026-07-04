"""
PATCC Cache Service

Stores and retrieves cached market data.
"""

import pickle
from datetime import datetime, timedelta
from pathlib import Path

from Utils.paths import data_dir


class CacheService:

    def __init__(self):
        self.cache_dir = data_dir() / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_file(self, key: str) -> Path:
        safe_key = key.replace("/", "_").replace(":", "_")
        return self.cache_dir / f"{safe_key}.pkl"

    def save(self, key: str, data) -> None:
        payload = {
            "saved_at": datetime.now(),
            "data": data,
        }

        with open(self._cache_file(key), "wb") as file:
            pickle.dump(payload, file)

    def load(self, key: str):
        file_path = self._cache_file(key)

        if not file_path.exists():
            return None

        with open(file_path, "rb") as file:
            payload = pickle.load(file)

        return payload["data"]

    def is_expired(self, key: str, max_age_minutes: int = 60) -> bool:
        file_path = self._cache_file(key)

        if not file_path.exists():
            return True

        with open(file_path, "rb") as file:
            payload = pickle.load(file)

        saved_at = payload["saved_at"]
        return datetime.now() - saved_at > timedelta(minutes=max_age_minutes)

    def clear(self) -> None:
        for file_path in self.cache_dir.glob("*.pkl"):
            file_path.unlink()
