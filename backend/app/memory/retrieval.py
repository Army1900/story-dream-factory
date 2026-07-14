from __future__ import annotations
import math
from app.models.memory import Memory


class MemoryRetriever:
    """记忆检索：score = α·recency + β·importance + γ·relevance。"""

    ALPHA = 0.4   # recency 权重
    BETA = 0.3    # importance 权重
    GAMMA = 0.3   # relevance 权重

    def retrieve(
        self,
        memories: list[Memory],
        query_vec: list[float] | None = None,
        current_tick: int = 0,
        top_k: int = 5,
    ) -> list[Memory]:
        if not memories:
            return []
        scored = []
        for m in memories:
            recency = self._recency_score(m.tick, current_tick)
            importance = m.importance / 10.0
            relevance = self._relevance_score(m.embedding or [], query_vec or [])
            score = self.ALPHA * recency + self.BETA * importance + self.GAMMA * relevance
            scored.append((score, m))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:top_k]]

    def _recency_score(self, mem_tick: int, current_tick: int) -> float:
        diff = max(0, current_tick - mem_tick)
        return math.exp(-diff / 10.0)  # 指数衰减

    def _relevance_score(self, embedding: list[float], query_vec: list[float]) -> float:
        if not embedding or not query_vec:
            return 0.0
        return self._cosine(embedding, query_vec)

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)
