from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

from cognimem.api import MemoryApi


class ApiDispatchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "memory.db")
        self.api = MemoryApi(self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_dispatch_flow(self) -> None:
        status, health = self.api.dispatch("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(health["status"], "ok")

        status, root = self.api.dispatch("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("CogniMem Admin", root["html"])

        status, created = self.api.dispatch(
            "POST",
            "/memories",
            {
                "agent_id": "agent-api",
                "session_id": "s1",
                "content": "用户偏好 Python 自动化脚本，并且喜欢直接给出命令。",
            },
        )
        self.assertEqual(status, 201)
        self.assertIn("memory_id", created)

        status, retrieved = self.api.dispatch(
            "POST",
            "/retrieve",
            {"query": "用户喜欢什么脚本", "agent_id": "agent-api"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(retrieved), 1)
        self.assertIn("Python", retrieved[0]["summary"])

        memory_id = created["memory_id"]
        status, feedback = self.api.dispatch("POST", "/feedback", {"memory_id": memory_id, "success": True})
        self.assertEqual(status, 200)
        self.assertGreater(feedback["importance"], 1.0)

        status, stats = self.api.dispatch("GET", "/stats")
        self.assertEqual(status, 200)
        self.assertEqual(stats["total_memories"], 1)
        self.assertEqual(stats["total_access_count"], 1)


if __name__ == "__main__":
    unittest.main()
