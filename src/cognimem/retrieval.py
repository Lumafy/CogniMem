from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol

from .text import cosine_similarity, tf_vector


def parse_json_field(value):
    if isinstance(value, (dict, list)):
        return value
    if value is None:
        return {}
    return json.loads(value)


def parse_timestamp(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


@dataclass
class RetrievalCandidate:
    id: int
    summary: str
    raw_content: str
    importance: float
    created_at: str
    vector_json: str


@dataclass
class RetrievalScore:
    id: int
    score: float
    why_retrieved: str


class RetrievalRepository(Protocol):
    def fetch_memories_for_retrieval(
        self,
        *,
        agent_id: str | None,
        session_id: str | None,
        project_id: str | None,
        limit: int = 200,
    ) -> tuple[list[Any], str, list[Any]]: ...

    def fetch_fts_scores(self, query: str, where_clause: str, params: list[Any]) -> list[Any]: ...


class RetrievalBackend(Protocol):
    def score(
        self,
        *,
        repository: RetrievalRepository,
        query: str,
        agent_id: str | None,
        session_id: str | None,
        project_id: str | None,
    ) -> tuple[list[RetrievalCandidate], dict[int, RetrievalScore]]: ...


class HybridRetrievalBackend:
    def score(
        self,
        *,
        repository: RetrievalRepository,
        query: str,
        agent_id: str | None,
        session_id: str | None,
        project_id: str | None,
    ) -> tuple[list[RetrievalCandidate], dict[int, RetrievalScore]]:
        query_vector = tf_vector(query)
        rows, where_clause, params = repository.fetch_memories_for_retrieval(
            agent_id=agent_id,
            session_id=session_id,
            project_id=project_id,
        )
        fts_scores = self._fts_scores(repository, query, where_clause, params)

        candidates: list[RetrievalCandidate] = []
        scored: dict[int, RetrievalScore] = {}
        for row in rows:
            candidate = RetrievalCandidate(
                id=int(row["id"]),
                summary=row["summary"],
                raw_content=row["raw_content"],
                importance=float(row["importance"]),
                created_at=row["created_at"],
                vector_json=row["vector_json"],
            )
            semantic_score = cosine_similarity(query_vector, parse_json_field(candidate.vector_json))
            lexical_score = fts_scores.get(candidate.id, 0.0)
            recency_bonus = self._recency_bonus(candidate.created_at)
            importance_bonus = min(candidate.importance, 3.0) / 10.0
            score = semantic_score * 0.55 + lexical_score * 0.25 + recency_bonus * 0.1 + importance_bonus * 0.1
            if score <= 0:
                continue
            candidates.append(candidate)
            scored[candidate.id] = RetrievalScore(
                id=candidate.id,
                score=round(score, 4),
                why_retrieved=self._build_why(semantic_score, lexical_score, recency_bonus, candidate.importance),
            )
        return candidates, scored

    def _fts_scores(
        self,
        repository: RetrievalRepository,
        query: str,
        where_clause: str,
        params: list[Any],
    ) -> dict[int, float]:
        try:
            rows = repository.fetch_fts_scores(query, where_clause, params)
        except Exception:
            return {}

        if not rows:
            return {}
        raw_scores = {int(row["id"]): float(row["rank"]) for row in rows}
        best = min(raw_scores.values())
        worst = max(raw_scores.values())
        if best == worst:
            return {key: 1.0 for key in raw_scores}
        return {key: (worst - value) / (worst - best) for key, value in raw_scores.items()}

    def _recency_bonus(self, created_at: str) -> float:
        created = parse_timestamp(created_at)
        age = datetime.now(created.tzinfo) - created
        if age <= timedelta(days=1):
            return 1.0
        if age <= timedelta(days=7):
            return 0.6
        if age <= timedelta(days=30):
            return 0.3
        return 0.1

    def _build_why(
        self,
        semantic_score: float,
        lexical_score: float,
        recency_bonus: float,
        importance: float,
    ) -> str:
        reasons: list[str] = []
        if semantic_score > 0.2:
            reasons.append("semantic-match")
        if lexical_score > 0.2:
            reasons.append("keyword-match")
        if recency_bonus >= 0.6:
            reasons.append("recent")
        if importance >= 1.2:
            reasons.append("high-importance")
        if not reasons:
            reasons.append("baseline-rank")
        return ", ".join(reasons)
