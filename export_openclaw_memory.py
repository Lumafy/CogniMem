#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mirror Cognimem SQLite data into OpenClaw markdown memory files.")
    parser.add_argument("--db", required=True, help="Path to cognimem SQLite database")
    parser.add_argument("--output-dir", required=True, help="OpenClaw memory target directory")
    parser.add_argument(
        "--bootstrap-memory-file",
        default=None,
        help="Optional generated MEMORY.md file injected at bootstrap",
    )
    parser.add_argument("--max-memories", type=int, default=500, help="Max active memories to export")
    parser.add_argument("--max-semantic", type=int, default=200, help="Max semantic memories to export")
    return parser.parse_args()


def fetch_rows(conn: sqlite3.Connection, query: str, params: tuple[object, ...] = ()) -> list[sqlite3.Row]:
    cur = conn.execute(query, params)
    return list(cur.fetchall())


def fmt_ts(value: object) -> str:
    if value is None:
      return "-"
    return str(value)


def sanitize_block(text: object) -> str:
    if text is None:
        return ""
    value = str(text).strip()
    if not value:
        return ""
    return value.replace("\r\n", "\n").replace("\r", "\n")


def render_active(rows: list[sqlite3.Row], generated_at: str) -> str:
    parts = [
        "# Cognimem Active Memories",
        "",
        "> Generated file. Edit the Cognimem database, not this mirror.",
        "",
        f"- Generated at: {generated_at}",
        f"- Exported memories: {len(rows)}",
        ""
    ]
    for row in rows:
        parts.extend(
            [
                f"## Memory {row['id']}",
                "",
                f"- Agent: {row['agent_id']}",
                f"- Session: {row['session_id']}",
                f"- Project: {row['project_id'] or '-'}",
                f"- User: {row['user_id'] or '-'}",
                f"- Event Type: {row['event_type']}",
                f"- Importance: {row['importance']}",
                f"- Access Count: {row['access_count']}",
                f"- Status: {row['status']}",
                f"- Created At: {fmt_ts(row['created_at'])}",
                f"- Last Accessed At: {fmt_ts(row['last_accessed_at'])}",
                f"- Source: {row['source'] or '-'}",
                "",
                "### Summary",
                "",
                sanitize_block(row["summary"]) or "-",
                "",
                "### Raw Content",
                "",
                sanitize_block(row["raw_content"]) or "-",
                ""
            ]
        )
    return "\n".join(parts).strip() + "\n"


def render_semantic(rows: list[sqlite3.Row], generated_at: str) -> str:
    parts = [
        "# Cognimem Semantic Memories",
        "",
        "> Generated file. Edit the Cognimem database, not this mirror.",
        "",
        f"- Generated at: {generated_at}",
        f"- Exported semantic memories: {len(rows)}",
        ""
    ]
    for row in rows:
        parts.extend(
            [
                f"## Semantic Memory {row['id']}",
                "",
                f"- Topic: {row['topic']}",
                f"- Confidence: {row['confidence']}",
                f"- Created At: {fmt_ts(row['created_at'])}",
                f"- Source Memory IDs: {row['source_memory_ids']}",
                "",
                "### Summary",
                "",
                sanitize_block(row["summary"]) or "-",
                ""
            ]
        )
    return "\n".join(parts).strip() + "\n"


def render_bootstrap_memory(rows: list[sqlite3.Row], semantic_rows: list[sqlite3.Row], generated_at: str) -> str:
    parts = [
        "# Cognimem Long-Term Memory",
        "",
        "> Auto-generated from Cognimem for OpenClaw bootstrap injection.",
        f"> Generated at: {generated_at}",
        "",
        "## Durable Facts",
        "",
    ]
    if not rows:
        parts.extend(["- No active Cognimem memories exported yet.", ""])
    else:
        for row in rows[:50]:
            summary = sanitize_block(row["summary"]) or sanitize_block(row["raw_content"]) or "-"
            parts.extend(
                [
                    f"- {summary}",
                    f"  Source: memory {row['id']} | importance={row['importance']} | created={fmt_ts(row['created_at'])}",
                ]
            )
        parts.append("")
    if semantic_rows:
        parts.extend(["## Reflections", ""])
        for row in semantic_rows[:20]:
            parts.extend(
                [
                    f"- {sanitize_block(row['topic'])}: {sanitize_block(row['summary'])}",
                    f"  Confidence: {row['confidence']} | source_ids={row['source_memory_ids']}",
                ]
            )
        parts.append("")
    parts.extend(
        [
            "## Usage",
            "",
            "- Treat this file as read-only mirrored long-term memory.",
            "- Prefer using these facts when they are relevant to the current conversation.",
            "- If a fact conflicts with a newer explicit user instruction, follow the newer instruction.",
            "",
        ]
    )
    return "\n".join(parts).strip() + "\n"


def write_if_changed(path: Path, content: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing == content:
            return False
    path.write_text(content, encoding="utf-8")
    return True


def main() -> int:
    args = parse_args()
    db_path = Path(args.db).expanduser()
    output_dir = Path(args.output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        active_rows = fetch_rows(
            conn,
            """
            SELECT id, agent_id, session_id, project_id, user_id, event_type, summary, raw_content,
                   importance, access_count, last_accessed_at, created_at, status, source
            FROM memories
            WHERE status = 'active'
            ORDER BY importance DESC, id DESC
            LIMIT ?
            """,
            (args.max_memories,),
        )
        semantic_rows = fetch_rows(
            conn,
            """
            SELECT id, topic, summary, source_memory_ids, confidence, created_at
            FROM semantic_memories
            ORDER BY confidence DESC, id DESC
            LIMIT ?
            """,
            (args.max_semantic,),
        )
    finally:
        conn.close()

    generated_at = datetime.now(timezone.utc).isoformat()
    active_path = output_dir / "cognimem-active.md"
    semantic_path = output_dir / "cognimem-semantic.md"
    index_path = output_dir / "README.md"
    bootstrap_path = Path(args.bootstrap_memory_file).expanduser() if args.bootstrap_memory_file else None

    active_changed = write_if_changed(active_path, render_active(active_rows, generated_at))
    semantic_changed = write_if_changed(semantic_path, render_semantic(semantic_rows, generated_at))
    index_changed = write_if_changed(
        index_path,
        "\n".join(
            [
                "# Cognimem Mirror",
                "",
                "> This directory is generated from Cognimem for OpenClaw memory_search.",
                "",
                "- `cognimem-active.md`: active long-term memories",
                "- `cognimem-semantic.md`: reflected semantic memories",
                ""
            ]
        ),
    )
    bootstrap_changed = False
    if bootstrap_path is not None:
        bootstrap_changed = write_if_changed(
            bootstrap_path,
            render_bootstrap_memory(active_rows, semantic_rows, generated_at),
        )

    print(
        f"synced active={len(active_rows)} semantic={len(semantic_rows)} "
        f"changed={'yes' if (active_changed or semantic_changed or index_changed or bootstrap_changed) else 'no'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
