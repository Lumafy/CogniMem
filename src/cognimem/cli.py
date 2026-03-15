from __future__ import annotations

import argparse
import json
from pathlib import Path

from .api import run_server
from .config import load_config
from .repository import initialize_storage
from .service import MemoryService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CogniMem MVP CLI")
    parser.add_argument("--db", default=None, help="SQLite database path")
    subparsers = parser.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", dest="sub_db", default=None, help="SQLite database path")

    subparsers.add_parser("init", parents=[common])

    add = subparsers.add_parser("add", parents=[common])
    add.add_argument("--agent", required=True)
    add.add_argument("--session", required=True)
    add.add_argument("--content", required=True)
    add.add_argument("--project")
    add.add_argument("--user")
    add.add_argument("--event-type", default="interaction")
    add.add_argument("--source")

    retrieve = subparsers.add_parser("retrieve", parents=[common])
    retrieve.add_argument("--query", required=True)
    retrieve.add_argument("--top-k", type=int, default=5)
    retrieve.add_argument("--agent")
    retrieve.add_argument("--session")
    retrieve.add_argument("--project")

    feedback = subparsers.add_parser("feedback", parents=[common])
    feedback.add_argument("--memory-id", type=int, required=True)
    feedback.add_argument("--success", action="store_true")
    feedback.add_argument("--failure", action="store_true")
    feedback.add_argument("--note")

    decay = subparsers.add_parser("decay", parents=[common])
    decay.add_argument("--idle-days", type=int, default=7)

    reflect = subparsers.add_parser("reflect", parents=[common])
    reflect.add_argument("--limit", type=int, default=50)
    reflect.add_argument("--min-group-size", type=int, default=2)

    subparsers.add_parser("semantic", parents=[common])
    subparsers.add_parser("stats", parents=[common])
    subparsers.add_parser("config", parents=[common])

    export_cmd = subparsers.add_parser("export", parents=[common])
    export_cmd.add_argument("--output")

    import_cmd = subparsers.add_parser("import", parents=[common])
    import_cmd.add_argument("--input", required=True)

    backup_cmd = subparsers.add_parser("backup", parents=[common])
    backup_cmd.add_argument("--target-dir")

    restore_cmd = subparsers.add_parser("restore", parents=[common])
    restore_cmd.add_argument("--backup-path", required=True)

    serve = subparsers.add_parser("serve", parents=[common])
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config = load_config(
        db_override=args.sub_db or args.db,
        host_override=getattr(args, "host", None),
        port_override=getattr(args, "port", None),
    )
    db_location = config.db_path
    is_postgres = db_location.startswith("postgresql://") or db_location.startswith("postgres://")
    db_path = Path(db_location) if not is_postgres else None

    if args.command == "init":
        result = initialize_storage(db_location)
        result["status"] = "initialized"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    service = MemoryService(db_location)

    if args.command == "add":
        memory_id = service.add_memory(
            agent_id=args.agent,
            session_id=args.session,
            content=args.content,
            project_id=args.project,
            user_id=args.user,
            event_type=args.event_type,
            source=args.source,
        )
        print(json.dumps({"memory_id": memory_id}, ensure_ascii=False, indent=2))
        return

    if args.command == "retrieve":
        result = service.retrieve(
            args.query,
            top_k=args.top_k,
            agent_id=args.agent,
            session_id=args.session,
            project_id=args.project,
        )
        print(json.dumps([item.__dict__ for item in result], ensure_ascii=False, indent=2))
        return

    if args.command == "feedback":
        if args.success == args.failure:
            parser.error("feedback requires exactly one of --success or --failure")
        result = service.give_feedback(args.memory_id, success=args.success, note=args.note)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command == "decay":
        print(json.dumps(service.decay_memories(idle_days=args.idle_days), ensure_ascii=False, indent=2))
        return

    if args.command == "reflect":
        print(
            json.dumps(
                service.reflect(limit=args.limit, min_group_size=args.min_group_size),
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "semantic":
        print(json.dumps(service.list_semantic_memories(), ensure_ascii=False, indent=2))
        return

    if args.command == "stats":
        print(json.dumps(service.stats(), ensure_ascii=False, indent=2))
        return

    if args.command == "config":
        print(json.dumps(config.to_dict(), ensure_ascii=False, indent=2))
        return

    if args.command == "export":
        output = args.output or str(Path(config.export_dir) / "cognimem-export.json")
        print(json.dumps(service.export_data(output), ensure_ascii=False, indent=2))
        return

    if args.command == "import":
        print(json.dumps(service.import_data(args.input), ensure_ascii=False, indent=2))
        return

    if args.command == "backup":
        target_dir = args.target_dir or config.backup_dir
        print(json.dumps(service.backup_database(target_dir), ensure_ascii=False, indent=2))
        return

    if args.command == "restore":
        print(json.dumps(service.restore_database(args.backup_path), ensure_ascii=False, indent=2))
        return

    if args.command == "serve":
        server = run_server(db_location, host=config.host, port=config.port)
        print(json.dumps({"status": "serving", "host": config.host, "port": config.port}, ensure_ascii=False, indent=2))
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return


if __name__ == "__main__":
    main()
