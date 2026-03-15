from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from cognimem.repository import PostgresMemoryRepository, SQLiteMemoryRepository, create_repository
from cognimem.retrieval import RetrievalCandidate, RetrievalScore
from cognimem.service import MemoryService


class StubRetrievalBackend:
    def score(self, *, repository, query, agent_id, session_id, project_id):
        return [
            RetrievalCandidate(
                id=99,
                summary=f"stub:{query}",
                raw_content="stub-content",
                importance=1.5,
                created_at="2026-03-12T00:00:00+00:00",
                vector_json="{}",
            )
        ], {
            99: RetrievalScore(id=99, score=0.91, why_retrieved="stub-backend")
        }


class MemoryServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "memory.db")
        self.service = MemoryService(self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_add_and_retrieve_returns_best_match(self) -> None:
        self.service.add_memory(
            agent_id="agent-a",
            session_id="s1",
            content="用户长期偏好 Python 自动化脚本，并且希望保留 shell 命令示例。",
        )
        self.service.add_memory(
            agent_id="agent-a",
            session_id="s2",
            content="用户正在准备市场分析报告，更关心图表和摘要。",
        )

        results = self.service.retrieve("用户偏好什么脚本语言", agent_id="agent-a")
        self.assertGreaterEqual(len(results), 1)
        self.assertIn("python", results[0].summary.lower())
        self.assertGreater(results[0].score, 0)

    def test_feedback_changes_importance(self) -> None:
        memory_id = self.service.add_memory(
            agent_id="agent-a",
            session_id="s1",
            content="需要优先给出可执行命令，而不是概念描述。",
        )
        success_result = self.service.give_feedback(memory_id, success=True)
        failure_result = self.service.give_feedback(memory_id, success=False)

        self.assertGreater(success_result["importance"], 1.0)
        self.assertEqual(failure_result["prediction_error_count"], 1)

    def test_decay_archives_old_low_value_memories(self) -> None:
        memory_id = self.service.add_memory(
            agent_id="agent-a",
            session_id="s1",
            content="这是一个几乎不会再使用的低价值记忆。",
        )
        self.service.give_feedback(memory_id, success=False)
        self.service.give_feedback(memory_id, success=False)

        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            UPDATE memories
            SET created_at = '2025-01-01T00:00:00+00:00',
                last_accessed_at = '2025-01-01T00:00:00+00:00'
            WHERE id = ?
            """,
            (memory_id,),
        )
        conn.commit()
        conn.close()

        result = self.service.decay_memories(idle_days=7)
        self.assertEqual(result["archived"], 1)

    def test_reflect_creates_semantic_memory(self) -> None:
        self.service.add_memory(
            agent_id="agent-a",
            session_id="s1",
            content="用户偏好 Python 自动化和脚本化解决方案。",
        )
        self.service.add_memory(
            agent_id="agent-a",
            session_id="s2",
            content="在代码生成任务里，优先使用 Python 工具链处理自动化流程。",
        )
        reflections = self.service.reflect(limit=10, min_group_size=2)
        self.assertEqual(len(reflections), 1)
        self.assertEqual(reflections[0]["topic"], "python")

        semantic = self.service.list_semantic_memories()
        self.assertEqual(len(semantic), 1)
        self.assertEqual(semantic[0]["source_memory_ids"], [2, 1])

    def test_service_accepts_repository_injection(self) -> None:
        repository = SQLiteMemoryRepository(self.db_path)
        service = MemoryService(repository=repository)
        service.add_memory(
            agent_id="agent-b",
            session_id="s9",
            content="用户希望长期记忆系统后续切换到 PostgreSQL 和 Qdrant。",
        )
        stats = service.stats()
        self.assertEqual(stats["total_memories"], 1)

    def test_service_accepts_retrieval_backend_injection(self) -> None:
        repository = SQLiteMemoryRepository(self.db_path)
        service = MemoryService(repository=repository, retrieval_backend=StubRetrievalBackend())
        results = service.retrieve("任意问题")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, 99)
        self.assertEqual(results[0].why_retrieved, "stub-backend")

    def test_repository_factory_selects_sqlite_and_postgres(self) -> None:
        sqlite_repo = create_repository(self.db_path)
        self.assertIsInstance(sqlite_repo, SQLiteMemoryRepository)

        postgres_repo = create_repository("postgresql://user:pass@localhost:5432/cognimem")
        self.assertIsInstance(postgres_repo, PostgresMemoryRepository)
        with self.assertRaises(RuntimeError):
            postgres_repo.stats()
        self.assertIn("psycopg is not installed", str(self._get_error(postgres_repo)))

    def _get_error(self, postgres_repo):
        try:
            postgres_repo.stats()
        except Exception as exc:  # noqa: BLE001
            return exc
        raise AssertionError("expected postgres_repo.stats() to fail")


if __name__ == "__main__":
    unittest.main()
