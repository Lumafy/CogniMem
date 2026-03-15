from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def export_payload(*, memories: list[dict], semantic_memories: list[dict], stats: dict) -> dict:
    return {
        "version": 1,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "stats": stats,
        "memories": memories,
        "semantic_memories": semantic_memories,
    }


def write_export(path: str, payload: dict) -> str:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(output)


def read_export(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def backup_file(source: str, target_dir: str, *, prefix: str = "memory-backup") -> str:
    source_path = Path(source)
    target_base = Path(target_dir)
    target_base.mkdir(parents=True, exist_ok=True)
    target_path = target_base / f"{prefix}-{utc_timestamp()}{source_path.suffix or '.db'}"
    shutil.copy2(source_path, target_path)
    return str(target_path)


def restore_file(backup_path: str, target_path: str) -> str:
    source = Path(backup_path)
    target = Path(target_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return str(target)

