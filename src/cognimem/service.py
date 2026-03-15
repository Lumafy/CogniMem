from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .portability import export_payload, read_export, restore_file, write_export
from .repository import SQLiteMemoryRepository, create_repository
from .retrieval import HybridRetrievalBackend, RetrievalBackend, parse_json_field
from .text import keyword_scores, summarize_text, tf_vector


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def to_jsonable_timestamp(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


@dataclass
class RetrievalResult:
    id: int
    summary: str
    raw_content: str
    importance: float
    score: float
    why_retrieved: str
    created_at: str


class MemoryService:
    def __init__(
        self,
        db_path: str | None = None,
        *,
        decay_factor_per_day: float = 0.98,
        importance_floor: float = 0.05,
        success_increment: float = 0.25,
        error_decrement: float = 0.35,
        repository: Any | None = None,
        retrieval_backend: RetrievalBackend | None = None,
    ) -> None:
        if repository is None and db_path is None:
            raise ValueError("db_path or repository is required")
        self.db_path = db_path or repository.db_path
        self.decay_factor_per_day = decay_factor_per_day
        self.importance_floor = importance_floor
        self.success_increment = success_increment
        self.error_decrement = error_decrement
        self.repository = repository or create_repository(self.db_path)
        self.retrieval_backend = retrieval_backend or HybridRetrievalBackend()

    def add_memory(
        self,
        *,
        agent_id: str,
        session_id: str,
        content: str,
        project_id: str | None = None,
        user_id: str | None = None,
        event_type: str = "interaction",
        source: str | None = None,
    ) -> int:
        summary = summarize_text(content)
        keywords = keyword_scores(content)
        vector = tf_vector(f"{summary} {content}")
        now = utcnow().isoformat()

        return self.repository.insert_memory(
            (
                agent_id,
                session_id,
                project_id,
                user_id,
                event_type,
                summary,
                content,
                json.dumps(keywords, ensure_ascii=False),
                json.dumps(vector, ensure_ascii=False),
                now,
                source,
            )
        )

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        agent_id: str | None = None,
        session_id: str | None = None,
        project_id: str | None = None,
    ) -> list[RetrievalResult]:
        candidates, scores = self.retrieval_backend.score(
            repository=self.repository,
            query=query,
            agent_id=agent_id,
            session_id=session_id,
            project_id=project_id,
        )
        scored: list[RetrievalResult] = []
        for candidate in candidates:
            score = scores[candidate.id]
            scored.append(
                RetrievalResult(
                    id=candidate.id,
                    summary=candidate.summary,
                    raw_content=candidate.raw_content,
                    importance=candidate.importance,
                    score=score.score,
                    why_retrieved=score.why_retrieved,
                    created_at=to_jsonable_timestamp(candidate.created_at),
                )
            )

        scored.sort(key=lambda item: item.score, reverse=True)
        selected = scored[:top_k]
        if selected:
            self.repository.bump_access([item.id for item in selected], utcnow().isoformat())
        return selected

    def give_feedback(self, memory_id: int, *, success: bool, note: str | None = None) -> dict[str, Any]:
        row = self.repository.fetch_feedback_target(memory_id)
        if row is None:
            raise ValueError(f"memory {memory_id} not found")

        importance = float(row["importance"])
        if success:
            importance += self.success_increment
            error_count = row["prediction_error_count"]
        else:
            importance = max(self.importance_floor, importance - self.error_decrement)
            error_count = int(row["prediction_error_count"]) + 1

        self.repository.update_feedback(memory_id, importance, error_count)
        return {
            "memory_id": memory_id,
            "success": success,
            "importance": round(importance, 4),
            "prediction_error_count": error_count,
            "note": note,
        }

    def decay_memories(self, *, idle_days: int = 7) -> dict[str, int]:
        rows = self.repository.fetch_active_memories_for_decay()

        decayed = 0
        archived = 0
        now = utcnow()
        for row in rows:
            anchor = datetime.fromisoformat(row["anchor"])
            days_idle = max((now - anchor).days, 0)
            if days_idle < idle_days:
                continue

            new_importance = float(row["importance"]) * (self.decay_factor_per_day ** days_idle)
            status = "active"
            if new_importance < self.importance_floor:
                new_importance = self.importance_floor
                status = "archived"
                archived += 1
            decayed += 1
            self.repository.update_memory_lifecycle(row["id"], new_importance, status)
        return {"decayed": decayed, "archived": archived}

    def reflect(self, *, limit: int = 50, min_group_size: int = 2) -> list[dict[str, Any]]:
        rows = self.repository.fetch_memories_for_reflection(limit)
        groups: dict[str, list[sqlite_memory]] = defaultdict(list)
        for row in rows:
            keywords = parse_json_field(row["keywords_json"])
            if not keywords:
                continue
            topic = keywords[0]
            groups[topic].append(row)

        outputs: list[dict[str, Any]] = []
        now = utcnow().isoformat()
        for topic, members in groups.items():
            if len(members) < min_group_size:
                continue
            source_ids = [int(item["id"]) for item in members]
            summary = "；".join(item["summary"] for item in members[:3])
            confidence = round(min(0.99, 0.45 + len(members) * 0.12), 2)
            self.repository.insert_semantic_memory(
                topic=topic,
                summary=summary,
                source_memory_ids=json.dumps(source_ids),
                confidence=confidence,
                created_at=now,
            )
            outputs.append(
                {
                    "topic": topic,
                    "summary": summary,
                    "source_memory_ids": source_ids,
                    "confidence": confidence,
                }
            )
        return outputs

    def list_semantic_memories(self) -> list[dict[str, Any]]:
        rows = self.repository.list_semantic_memories()
        return [
            {
                "id": int(row["id"]),
                "topic": row["topic"],
                "summary": row["summary"],
                "source_memory_ids": parse_json_field(row["source_memory_ids"]),
                "confidence": row["confidence"],
                "created_at": to_jsonable_timestamp(row["created_at"]),
            }
            for row in rows
        ]

    def list_memories(
        self,
        *,
        limit: int = 50,
        status: str | None = None,
        agent_id: str | None = None,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for row in self.repository.list_memories(limit=limit, status=status, agent_id=agent_id):
            item = dict(row)
            item["created_at"] = to_jsonable_timestamp(item.get("created_at"))
            item["last_accessed_at"] = to_jsonable_timestamp(item.get("last_accessed_at"))
            items.append(item)
        return items

    def stats(self) -> dict[str, Any]:
        return self.repository.stats()

    def export_data(self, output_path: str) -> dict[str, Any]:
        payload = export_payload(
            memories=self.list_memories(limit=100000),
            semantic_memories=self.list_semantic_memories(),
            stats=self.stats(),
        )
        path = write_export(output_path, payload)
        return {"export_path": path, "counts": {"memories": len(payload["memories"]), "semantic_memories": len(payload["semantic_memories"])}}

    def import_data(self, input_path: str) -> dict[str, Any]:
        payload = read_export(input_path)
        imported_memories = 0
        imported_semantic = 0

        for item in payload.get("memories", []):
            memory_id = self.add_memory(
                agent_id=item["agent_id"],
                session_id=item["session_id"],
                content=item.get("raw_content") or item["summary"],
                project_id=item.get("project_id"),
                user_id=item.get("user_id"),
                event_type=item.get("event_type", "interaction"),
                source=item.get("source"),
            )
            if item.get("importance") not in (None, 1.0):
                self.repository.update_feedback(
                    memory_id,
                    float(item["importance"]),
                    int(item.get("prediction_error_count", 0)),
                )
            if item.get("status") == "archived":
                self.repository.update_memory_lifecycle(memory_id, float(item.get("importance", 1.0)), "archived")
            imported_memories += 1

        for item in payload.get("semantic_memories", []):
            self.repository.insert_semantic_memory(
                topic=item["topic"],
                summary=item["summary"],
                source_memory_ids=json.dumps(item.get("source_memory_ids", [])),
                confidence=float(item.get("confidence", 0.5)),
                created_at=item.get("created_at", utcnow().isoformat()),
            )
            imported_semantic += 1

        return {
            "imported_memories": imported_memories,
            "imported_semantic_memories": imported_semantic,
            "source": input_path,
        }

    def backup_database(self, target_dir: str) -> dict[str, Any]:
        db_path = Path(self.db_path)
        if not db_path.exists():
            raise FileNotFoundError(f"database not found: {db_path}")
        from .portability import backup_file

        backup_path = backup_file(str(db_path), target_dir, prefix="cognimem-db")
        return {"backup_path": backup_path}

    def restore_database(self, backup_path: str) -> dict[str, Any]:
        restored = restore_file(backup_path, self.db_path)
        return {"restored_path": restored, "source_backup": backup_path}


sqlite_memory = Any
