"""
Embedding 向量内存缓存（LRU + 可选 TTL）

用于减少重复的 DashScope TextEmbedding 调用，加速 RAG 检索与用户重复提问。
可通过环境变量调整容量与过期时间。
"""

from __future__ import annotations

import hashlib
import os
import threading
import time
from collections import OrderedDict
from typing import List, Optional

import logging

logger = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


class EmbeddingLRUCache:
    """线程安全的 LRU；可选 TTL（秒），0 表示仅用容量淘汰。"""

    def __init__(self, max_size: int, ttl_seconds: int) -> None:
        self.max_size = max(1, max_size)
        self.ttl_seconds = max(0, ttl_seconds)
        self._store: "OrderedDict[str, tuple[List[float], float]]" = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _make_key(text: str, model: str, dimension: int) -> str:
        raw = f"{model}|{dimension}|{text}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, text: str, model: str, dimension: int) -> Optional[List[float]]:
        key = self._make_key(text, model, dimension)
        now = time.time()
        with self._lock:
            if key not in self._store:
                self._misses += 1
                return None
            vec, ts = self._store[key]
            if self.ttl_seconds > 0 and now - ts > self.ttl_seconds:
                del self._store[key]
                self._misses += 1
                return None
            self._store.move_to_end(key)
            self._hits += 1
            return vec

    def put(self, text: str, model: str, dimension: int, vector: List[float]) -> None:
        key = self._make_key(text, model, dimension)
        now = time.time()
        with self._lock:
            if key in self._store:
                del self._store[key]
            self._store[key] = (vector, now)
            self._store.move_to_end(key)
            while len(self._store) > self.max_size:
                self._store.popitem(last=False)

    def stats(self) -> dict:
        with self._lock:
            return {
                "hits": self._hits,
                "misses": self._misses,
                "size": len(self._store),
                "max_size": self.max_size,
            }


_global_cache: Optional[EmbeddingLRUCache] = None


def get_embedding_cache() -> EmbeddingLRUCache:
    global _global_cache
    if _global_cache is None:
        max_size = _env_int("EMBEDDING_CACHE_MAX_SIZE", 4096)
        ttl = _env_int("EMBEDDING_CACHE_TTL_SECONDS", 0)
        _global_cache = EmbeddingLRUCache(max_size=max_size, ttl_seconds=ttl)
        logger.info(
            "Embedding cache initialized max_size=%s ttl_seconds=%s",
            max_size,
            ttl,
        )
    return _global_cache
