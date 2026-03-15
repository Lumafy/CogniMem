from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any

from .store import connect, initialize

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - depends on local environment
    psycopg = None
    dict_row = None


class PostgresMemoryRepository:
    def __init__(self, dsn: str) -> None:
        self.db_path = dsn
        self.dsn = dsn
        self.driver_available = psycopg is not None

    def initialize_schema(self, schema_path: str | None = None) -> None:
        conn = self._connect()
        try:
            path = Path(schema_path or Path(__file__).resolve().parents[2] / "migrations" / "postgres_schema.sql")
            conn.execute(path.read_text(encoding="utf-8"))
            conn.commit()
        finally:
            conn.close()

    def insert_memory(self, values: tuple[Any, ...]) -> int:
        conn = self._connect()
        try:
            row = conn.execute(
                """
                INSERT INTO memories (
                    agent_id, session_id, project_id, user_id, event_type, summary,
                    raw_content, keywords_json, vector_json, created_at, source
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
                RETURNING id
                """,
                values,
            ).fetchone()
            conn.commit()
            return int(row["id"])
        finally:
            conn.close()

    def fetch_memories_for_retrieval(
        self,
        *,
        agent_id: str | None,
        session_id: str | None,
        project_id: str | None,
        limit: int = 200,
    ) -> tuple[list[dict[str, Any]], str, list[Any]]:
        filters = ["status = 'active'"]
        params: list[Any] = []
        if agent_id:
            filters.append("agent_id = %s")
            params.append(agent_id)
        if session_id:
            filters.append("session_id = %s")
            params.append(session_id)
        if project_id:
            filters.append("project_id = %s")
            params.append(project_id)
        where_clause = " AND ".join(filters)
        rows = self._fetchall(
            f"""
            SELECT id, summary, raw_content, importance, vector_json, created_at
            FROM memories
            WHERE {where_clause}
            ORDER BY importance DESC, id DESC
            LIMIT %s
            """,
            [*params, limit],
        )
        return rows, where_clause, params

    def fetch_fts_scores(self, query: str, where_clause: str, params: list[Any]) -> list[dict[str, Any]]:
        return self._fetchall(
            f"""
            SELECT id, ts_rank_cd(
                to_tsvector('simple', coalesce(summary, '') || ' ' || coalesce(raw_content, '')),
                plainto_tsquery('simple', %s)
            ) AS rank
            FROM memories
            WHERE {where_clause}
              AND to_tsvector('simple', coalesce(summary, '') || ' ' || coalesce(raw_content, ''))
                  @@ plainto_tsquery('simple', %s)
            ORDER BY rank DESC
            LIMIT 50
            """,
            [query, *params, query],
        )

    def bump_access(self, memory_ids: list[int], accessed_at: str) -> None:
        if not memory_ids:
            return
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.executemany(
                    "UPDATE memories SET access_count = access_count + 1, last_accessed_at = %s WHERE id = %s",
                    [(accessed_at, memory_id) for memory_id in memory_ids],
                )
            conn.commit()
        finally:
            conn.close()

    def fetch_feedback_target(self, memory_id: int) -> dict[str, Any] | None:
        return self._fetchone(
            "SELECT importance, prediction_error_count FROM memories WHERE id = %s",
            (memory_id,),
            allow_missing=True,
        )

    def update_feedback(self, memory_id: int, importance: float, error_count: int) -> None:
        self._execute(
            "UPDATE memories SET importance = %s, prediction_error_count = %s WHERE id = %s",
            (importance, error_count, memory_id),
        )

    def fetch_active_memories_for_decay(self) -> list[dict[str, Any]]:
        return self._fetchall(
            """
            SELECT id, importance, created_at, COALESCE(last_accessed_at, created_at) AS anchor
            FROM memories
            WHERE status = 'active'
            """
        )

    def update_memory_lifecycle(self, memory_id: int, importance: float, status: str) -> None:
        self._execute(
            "UPDATE memories SET importance = %s, status = %s WHERE id = %s",
            (importance, status, memory_id),
        )

    def fetch_memories_for_reflection(self, limit: int) -> list[dict[str, Any]]:
        return self._fetchall(
            """
            SELECT id, summary, keywords_json, importance
            FROM memories
            WHERE status = 'active'
            ORDER BY importance DESC, id DESC
            LIMIT %s
            """,
            (limit,),
        )

    def insert_semantic_memory(
        self,
        *,
        topic: str,
        summary: str,
        source_memory_ids: str,
        confidence: float,
        created_at: str,
    ) -> None:
        self._execute(
            """
            INSERT INTO semantic_memories (topic, summary, source_memory_ids, confidence, created_at)
            VALUES (%s, %s, %s::jsonb, %s, %s)
            """,
            (topic, summary, source_memory_ids, confidence, created_at),
        )

    def list_semantic_memories(self) -> list[dict[str, Any]]:
        return self._fetchall(
            "SELECT id, topic, summary, source_memory_ids, confidence, created_at FROM semantic_memories ORDER BY id DESC"
        )

    def list_memories(self, *, limit: int, status: str | None, agent_id: str | None) -> list[dict[str, Any]]:
        filters: list[str] = []
        params: list[Any] = []
        if status:
            filters.append("status = %s")
            params.append(status)
        if agent_id:
            filters.append("agent_id = %s")
            params.append(agent_id)
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        return self._fetchall(
            f"""
            SELECT id, agent_id, session_id, project_id, user_id, event_type, summary, importance,
                   access_count, prediction_error_count, created_at, last_accessed_at, status
            FROM memories
            {where_clause}
            ORDER BY id DESC
            LIMIT %s
            """,
            [*params, limit],
        )

    def stats(self) -> dict[str, Any]:
        memory_stats = self._fetchone(
            """
            SELECT
                COUNT(*) AS total_memories,
                SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS active_memories,
                SUM(CASE WHEN status = 'archived' THEN 1 ELSE 0 END) AS archived_memories,
                COALESCE(AVG(importance), 0) AS avg_importance,
                COALESCE(SUM(access_count), 0) AS total_access_count,
                COALESCE(SUM(prediction_error_count), 0) AS total_prediction_errors
            FROM memories
            """
        )
        semantic_count = self._fetchone("SELECT COUNT(*) AS total_semantic FROM semantic_memories")
        return {
            "total_memories": int(memory_stats["total_memories"]),
            "active_memories": int(memory_stats["active_memories"] or 0),
            "archived_memories": int(memory_stats["archived_memories"] or 0),
            "avg_importance": round(float(memory_stats["avg_importance"] or 0.0), 4),
            "total_access_count": int(memory_stats["total_access_count"] or 0),
            "total_prediction_errors": int(memory_stats["total_prediction_errors"] or 0),
            "total_semantic_memories": int(semantic_count["total_semantic"] or 0),
        }

    def _connect(self):
        if psycopg is None:
            raise RuntimeError(
                "psycopg is not installed. Install `psycopg[binary]` to use PostgreSQL repository support."
            )
        return psycopg.connect(self.dsn, row_factory=dict_row)

    def _execute(self, query: str, params: tuple[Any, ...] | list[Any] = ()) -> None:
        conn = self._connect()
        try:
            conn.execute(query, params)
            conn.commit()
        finally:
            conn.close()

    def _fetchone(
        self,
        query: str,
        params: tuple[Any, ...] | list[Any] = (),
        *,
        allow_missing: bool = False,
    ) -> dict[str, Any] | None:
        conn = self._connect()
        try:
            row = conn.execute(query, params).fetchone()
            if row is None and not allow_missing:
                raise RuntimeError("expected a row but query returned none")
            return row
        finally:
            conn.close()

    def _fetchall(self, query: str, params: tuple[Any, ...] | list[Any] = ()) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            return list(conn.execute(query, params).fetchall())
        finally:
            conn.close()


class SQLiteMemoryRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        initialize(db_path)

    def insert_memory(self, values: tuple[Any, ...]) -> int:
        conn = connect(self.db_path)
        try:
            cur = conn.execute(
                """
                INSERT INTO memories (
                    agent_id, session_id, project_id, user_id, event_type, summary,
                    raw_content, keywords_json, vector_json, created_at, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            conn.commit()
            return int(cur.lastrowid)
        finally:
            conn.close()

    def fetch_memories_for_retrieval(
        self,
        *,
        agent_id: str | None,
        session_id: str | None,
        project_id: str | None,
        limit: int = 200,
    ) -> tuple[list[sqlite3.Row], str, list[Any]]:
        conn = connect(self.db_path)
        try:
            filters = ["status = 'active'"]
            params: list[Any] = []
            if agent_id:
                filters.append("agent_id = ?")
                params.append(agent_id)
            if session_id:
                filters.append("session_id = ?")
                params.append(session_id)
            if project_id:
                filters.append("project_id = ?")
                params.append(project_id)
            where_clause = " AND ".join(filters)
            rows = conn.execute(
                f"""
                SELECT id, summary, raw_content, importance, vector_json, created_at
                FROM memories
                WHERE {where_clause}
                ORDER BY importance DESC, id DESC
                LIMIT ?
                """,
                [*params, limit],
            ).fetchall()
            return rows, where_clause, params
        finally:
            conn.close()

    def fetch_fts_scores(self, query: str, where_clause: str, params: list[Any]) -> list[sqlite3.Row]:
        conn = connect(self.db_path)
        try:
            return conn.execute(
                f"""
                SELECT memories.id AS id, bm25(memories_fts, 2.0, 1.0) AS rank
                FROM memories_fts
                JOIN memories ON memories.id = memories_fts.rowid
                WHERE memories_fts MATCH ? AND {where_clause}
                ORDER BY rank
                LIMIT 50
                """,
                [query, *params],
            ).fetchall()
        finally:
            conn.close()

    def bump_access(self, memory_ids: list[int], accessed_at: str) -> None:
        if not memory_ids:
            return
        conn = connect(self.db_path)
        try:
            conn.executemany(
                "UPDATE memories SET access_count = access_count + 1, last_accessed_at = ? WHERE id = ?",
                [(accessed_at, memory_id) for memory_id in memory_ids],
            )
            conn.commit()
        finally:
            conn.close()

    def fetch_feedback_target(self, memory_id: int) -> sqlite3.Row | None:
        conn = connect(self.db_path)
        try:
            return conn.execute(
                "SELECT importance, prediction_error_count FROM memories WHERE id = ?",
                (memory_id,),
            ).fetchone()
        finally:
            conn.close()

    def update_feedback(self, memory_id: int, importance: float, error_count: int) -> None:
        conn = connect(self.db_path)
        try:
            conn.execute(
                "UPDATE memories SET importance = ?, prediction_error_count = ? WHERE id = ?",
                (importance, error_count, memory_id),
            )
            conn.commit()
        finally:
            conn.close()

    def fetch_active_memories_for_decay(self) -> list[sqlite3.Row]:
        conn = connect(self.db_path)
        try:
            return conn.execute(
                """
                SELECT id, importance, created_at, COALESCE(last_accessed_at, created_at) AS anchor
                FROM memories
                WHERE status = 'active'
                """
            ).fetchall()
        finally:
            conn.close()

    def update_memory_lifecycle(self, memory_id: int, importance: float, status: str) -> None:
        conn = connect(self.db_path)
        try:
            conn.execute(
                "UPDATE memories SET importance = ?, status = ? WHERE id = ?",
                (importance, status, memory_id),
            )
            conn.commit()
        finally:
            conn.close()

    def fetch_memories_for_reflection(self, limit: int) -> list[sqlite3.Row]:
        conn = connect(self.db_path)
        try:
            return conn.execute(
                """
                SELECT id, summary, keywords_json, importance
                FROM memories
                WHERE status = 'active'
                ORDER BY importance DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        finally:
            conn.close()

    def insert_semantic_memory(
        self,
        *,
        topic: str,
        summary: str,
        source_memory_ids: str,
        confidence: float,
        created_at: str,
    ) -> None:
        conn = connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO semantic_memories (topic, summary, source_memory_ids, confidence, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (topic, summary, source_memory_ids, confidence, created_at),
            )
            conn.commit()
        finally:
            conn.close()

    def list_semantic_memories(self) -> list[sqlite3.Row]:
        conn = connect(self.db_path)
        try:
            return conn.execute(
                "SELECT id, topic, summary, source_memory_ids, confidence, created_at FROM semantic_memories ORDER BY id DESC"
            ).fetchall()
        finally:
            conn.close()

    def list_memories(self, *, limit: int, status: str | None, agent_id: str | None) -> list[sqlite3.Row]:
        conn = connect(self.db_path)
        try:
            filters: list[str] = []
            params: list[Any] = []
            if status:
                filters.append("status = ?")
                params.append(status)
            if agent_id:
                filters.append("agent_id = ?")
                params.append(agent_id)
            where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
            return conn.execute(
                f"""
                SELECT id, agent_id, session_id, project_id, user_id, event_type, summary, importance,
                       access_count, prediction_error_count, created_at, last_accessed_at, status
                FROM memories
                {where_clause}
                ORDER BY id DESC
                LIMIT ?
                """,
                [*params, limit],
            ).fetchall()
        finally:
            conn.close()

    def stats(self) -> dict[str, Any]:
        conn = connect(self.db_path)
        try:
            memory_stats = conn.execute(
                """
                SELECT
                    COUNT(*) AS total_memories,
                    SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS active_memories,
                    SUM(CASE WHEN status = 'archived' THEN 1 ELSE 0 END) AS archived_memories,
                    COALESCE(AVG(importance), 0) AS avg_importance,
                    COALESCE(SUM(access_count), 0) AS total_access_count,
                    COALESCE(SUM(prediction_error_count), 0) AS total_prediction_errors
                FROM memories
                """
            ).fetchone()
            semantic_count = conn.execute("SELECT COUNT(*) AS total_semantic FROM semantic_memories").fetchone()
            return {
                "total_memories": int(memory_stats["total_memories"]),
                "active_memories": int(memory_stats["active_memories"] or 0),
                "archived_memories": int(memory_stats["archived_memories"] or 0),
                "avg_importance": round(float(memory_stats["avg_importance"] or 0.0), 4),
                "total_access_count": int(memory_stats["total_access_count"] or 0),
                "total_prediction_errors": int(memory_stats["total_prediction_errors"] or 0),
                "total_semantic_memories": int(semantic_count["total_semantic"] or 0),
            }
        finally:
            conn.close()


def create_repository(location: str):
    if location.startswith("postgresql://") or location.startswith("postgres://"):
        return PostgresMemoryRepository(location)
    return SQLiteMemoryRepository(location)


def initialize_storage(location: str) -> dict[str, str]:
    repository = create_repository(location)
    if isinstance(repository, PostgresMemoryRepository):
        repository.initialize_schema()
        return {"backend": "postgres", "location": location}
    return {"backend": "sqlite", "location": repository.db_path}
