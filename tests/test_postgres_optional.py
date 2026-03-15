from __future__ import annotations

import os
import unittest


@unittest.skipUnless(os.getenv("COGNIMEM_PG_DSN"), "COGNIMEM_PG_DSN not set")
class PostgresIntegrationTest(unittest.TestCase):
    def test_postgres_smoke_flow(self) -> None:
        from cognimem.repository import PostgresMemoryRepository
        from cognimem.service import MemoryService

        dsn = os.environ["COGNIMEM_PG_DSN"]
        repository = PostgresMemoryRepository(dsn)
        repository.initialize_schema()
        service = MemoryService(repository=repository)
        memory_id = service.add_memory(
            agent_id="pg-agent",
            session_id="pg-session",
            content="PostgreSQL 集成测试正在验证长期记忆写入与检索。",
        )
        self.assertGreater(memory_id, 0)
        results = service.retrieve("验证长期记忆写入", agent_id="pg-agent")
        self.assertGreaterEqual(len(results), 1)


if __name__ == "__main__":
    unittest.main()
