from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class AppConfig:
    db_path: str
    host: str
    port: int
    backup_dir: str
    export_dir: str

    def to_dict(self) -> dict:
        return asdict(self)


def load_config(
    *,
    db_override: str | None = None,
    host_override: str | None = None,
    port_override: int | None = None,
    root_dir: str | None = None,
) -> AppConfig:
    base = Path(root_dir or os.getcwd())
    db_path = db_override or os.getenv("COGNIMEM_DB_PATH") or str(base / "data" / "memory.db")
    host = host_override or os.getenv("COGNIMEM_HOST") or "127.0.0.1"
    port = port_override or int(os.getenv("COGNIMEM_PORT", "8000"))
    backup_dir = os.getenv("COGNIMEM_BACKUP_DIR") or str(base / "backups")
    export_dir = os.getenv("COGNIMEM_EXPORT_DIR") or str(base / "exports")
    return AppConfig(
        db_path=db_path,
        host=host,
        port=port,
        backup_dir=backup_dir,
        export_dir=export_dir,
    )

