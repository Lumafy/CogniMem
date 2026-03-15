from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from cognimem.config import load_config
from cognimem.service import MemoryService


class PortabilityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.db_path = str(self.root / "memory.db")
        self.export_path = str(self.root / "exports" / "snapshot.json")
        self.service = MemoryService(self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_load_config_uses_overrides(self) -> None:
        config = load_config(db_override=self.db_path, host_override="0.0.0.0", port_override=9000, root_dir=str(self.root))
        self.assertEqual(config.db_path, self.db_path)
        self.assertEqual(config.host, "0.0.0.0")
        self.assertEqual(config.port, 9000)

    def test_export_import_and_backup_restore(self) -> None:
        self.service.add_memory(agent_id="agent-a", session_id="s1", content="用户偏好长期记忆中的导出能力。")
        self.service.reflect(limit=10, min_group_size=1)

        exported = self.service.export_data(self.export_path)
        self.assertTrue(Path(exported["export_path"]).exists())

        payload = json.loads(Path(self.export_path).read_text(encoding="utf-8"))
        self.assertEqual(payload["stats"]["total_memories"], 1)

        imported_db = str(self.root / "imported.db")
        imported_service = MemoryService(imported_db)
        imported = imported_service.import_data(self.export_path)
        self.assertEqual(imported["imported_memories"], 1)
        self.assertEqual(imported_service.stats()["total_memories"], 1)

        backup = self.service.backup_database(str(self.root / "backups"))
        self.assertTrue(Path(backup["backup_path"]).exists())

        os.remove(self.db_path)
        restored = self.service.restore_database(backup["backup_path"])
        self.assertTrue(Path(restored["restored_path"]).exists())
        restored_service = MemoryService(self.db_path)
        self.assertEqual(restored_service.stats()["total_memories"], 1)


if __name__ == "__main__":
    unittest.main()
