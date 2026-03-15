from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .config import load_config
from .service import MemoryService

ADMIN_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>CogniMem Admin</title>
  <style>
    :root {
      --bg: #f4f1e8;
      --panel: #fffdf7;
      --line: #d7cfc0;
      --ink: #1f2a2e;
      --muted: #66757f;
      --accent: #0d6b57;
      --warn: #a4511e;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Iowan Old Style", "Palatino Linotype", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top right, rgba(13,107,87,.08), transparent 35%),
        linear-gradient(180deg, #f8f5ed 0%, var(--bg) 100%);
    }
    main { max-width: 1180px; margin: 0 auto; padding: 28px 18px 56px; }
    h1, h2, h3 { margin: 0; font-weight: 600; }
    p { margin: 0; color: var(--muted); }
    .hero {
      display: grid;
      gap: 18px;
      padding: 22px;
      border: 1px solid var(--line);
      background: linear-gradient(135deg, rgba(255,253,247,.96), rgba(246,242,231,.92));
      border-radius: 18px;
      box-shadow: 0 12px 36px rgba(31,42,46,.08);
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
      margin-top: 18px;
    }
    .card, .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 16px;
      box-shadow: 0 8px 20px rgba(31,42,46,.05);
    }
    .metric { font-size: 28px; line-height: 1; margin-top: 10px; }
    .stack { display: grid; gap: 14px; margin-top: 18px; }
    .toolbar {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 12px;
    }
    input, select, textarea, button {
      font: inherit;
      border-radius: 10px;
      border: 1px solid var(--line);
      padding: 10px 12px;
      background: #fff;
      color: var(--ink);
    }
    textarea { width: 100%; min-height: 100px; resize: vertical; }
    button {
      background: var(--accent);
      color: #fff;
      border: none;
      cursor: pointer;
    }
    button.alt { background: #24353a; }
    button.warn { background: var(--warn); }
    .memory-list, .semantic-list { display: grid; gap: 12px; margin-top: 14px; }
    .memory-item, .semantic-item {
      padding: 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: #fff;
    }
    .meta {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      color: var(--muted);
      font-size: 13px;
      margin-top: 8px;
    }
    .status { display: inline-flex; align-items: center; gap: 6px; }
    .pill {
      display: inline-block;
      padding: 3px 8px;
      border-radius: 999px;
      background: rgba(13,107,87,.12);
      color: var(--accent);
      font-size: 12px;
    }
    .search-row {
      display: grid;
      grid-template-columns: 1.7fr .8fr .8fr auto;
      gap: 10px;
      margin-top: 12px;
    }
    .actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
    .footer-note { margin-top: 18px; font-size: 13px; }
    @media (max-width: 760px) {
      .search-row { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div>
        <h1>CogniMem Admin</h1>
        <p>零依赖长期记忆控制台，聚焦写入、检索、反馈、反思和遗忘。</p>
      </div>
      <div class="grid" id="stats-grid"></div>
    </section>

    <section class="stack">
      <div class="panel">
        <h2>写入记忆</h2>
        <div class="toolbar">
          <input id="agent-id" placeholder="agent_id" value="demo">
          <input id="session-id" placeholder="session_id" value="session-1">
          <input id="project-id" placeholder="project_id">
        </div>
        <div class="toolbar">
          <input id="user-id" placeholder="user_id">
          <input id="source" placeholder="source">
          <select id="event-type">
            <option value="interaction">interaction</option>
            <option value="decision">decision</option>
            <option value="tool_call">tool_call</option>
          </select>
        </div>
        <div class="toolbar" style="display:block">
          <textarea id="content" placeholder="输入要写入的长期记忆内容"></textarea>
        </div>
        <div class="actions">
          <button id="save-btn">写入记忆</button>
          <button class="alt" id="refresh-btn">刷新面板</button>
        </div>
      </div>

      <div class="panel">
        <h2>检索与反馈</h2>
        <div class="search-row">
          <input id="query" placeholder="输入检索问题，例如：用户偏好什么语言">
          <input id="query-agent" placeholder="agent_id">
          <input id="top-k" type="number" value="5" min="1" max="20">
          <button id="search-btn">检索</button>
        </div>
        <div class="memory-list" id="retrieve-results"></div>
      </div>

      <div class="panel">
        <h2>记忆库</h2>
        <div class="toolbar">
          <select id="memory-status">
            <option value="">全部状态</option>
            <option value="active">active</option>
            <option value="archived">archived</option>
          </select>
          <input id="memory-agent" placeholder="按 agent_id 过滤">
          <button class="alt" id="load-memories-btn">加载记忆</button>
          <button class="warn" id="decay-btn">执行衰减</button>
          <button id="reflect-btn">执行反思</button>
        </div>
        <div class="memory-list" id="memory-list"></div>
      </div>

      <div class="panel">
        <h2>语义记忆</h2>
        <div class="semantic-list" id="semantic-list"></div>
        <p class="footer-note">反思会按关键词主题聚合近期情景记忆，生成语义记忆条目。</p>
      </div>
    </section>
  </main>
  <script>
    async function api(path, options = {}) {
      const response = await fetch(path, {
        headers: { "Content-Type": "application/json" },
        ...options
      });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || response.statusText);
      }
      return response.json();
    }

    function statCard(label, value) {
      return `<div class="card"><div>${label}</div><div class="metric">${value}</div></div>`;
    }

    function memoryCard(item, withFeedback = false) {
      const feedback = withFeedback ? `
        <div class="actions">
          <button onclick="feedback(${item.id}, true)">强化</button>
          <button class="warn" onclick="feedback(${item.id}, false)">降权</button>
        </div>` : "";
      return `
        <article class="memory-item">
          <h3>${item.summary}</h3>
          <div class="meta">
            <span class="pill">#${item.id}</span>
            <span>importance ${Number(item.importance).toFixed(2)}</span>
            ${item.score !== undefined ? `<span>score ${Number(item.score).toFixed(4)}</span>` : ""}
            <span>${item.status || ""}</span>
            ${item.why_retrieved ? `<span>${item.why_retrieved}</span>` : ""}
          </div>
          <p style="margin-top:10px">${item.raw_content || ""}</p>
          ${feedback}
        </article>`;
    }

    function semanticCard(item) {
      return `
        <article class="semantic-item">
          <h3>${item.topic}</h3>
          <div class="meta">
            <span>confidence ${Number(item.confidence).toFixed(2)}</span>
            <span>sources ${item.source_memory_ids.join(", ")}</span>
          </div>
          <p style="margin-top:10px">${item.summary}</p>
        </article>`;
    }

    async function loadStats() {
      const stats = await api("/stats");
      document.getElementById("stats-grid").innerHTML = [
        statCard("总记忆数", stats.total_memories),
        statCard("活跃记忆", stats.active_memories),
        statCard("归档记忆", stats.archived_memories),
        statCard("平均重要性", stats.avg_importance),
        statCard("总访问次数", stats.total_access_count),
        statCard("语义记忆", stats.total_semantic_memories),
      ].join("");
    }

    async function loadMemories() {
      const status = document.getElementById("memory-status").value;
      const agent = document.getElementById("memory-agent").value.trim();
      const query = new URLSearchParams();
      if (status) query.set("status", status);
      if (agent) query.set("agent_id", agent);
      query.set("limit", "30");
      const data = await api(`/memories?${query.toString()}`);
      document.getElementById("memory-list").innerHTML = data.map(item => memoryCard(item)).join("") || "<p>暂无记忆</p>";
    }

    async function loadSemantic() {
      const data = await api("/semantic-memories");
      document.getElementById("semantic-list").innerHTML = data.map(semanticCard).join("") || "<p>暂无语义记忆</p>";
    }

    async function saveMemory() {
      const payload = {
        agent_id: document.getElementById("agent-id").value.trim(),
        session_id: document.getElementById("session-id").value.trim(),
        project_id: document.getElementById("project-id").value.trim() || null,
        user_id: document.getElementById("user-id").value.trim() || null,
        source: document.getElementById("source").value.trim() || null,
        event_type: document.getElementById("event-type").value,
        content: document.getElementById("content").value.trim()
      };
      if (!payload.agent_id || !payload.session_id || !payload.content) {
        alert("agent_id、session_id 和 content 必填");
        return;
      }
      await api("/memories", { method: "POST", body: JSON.stringify(payload) });
      document.getElementById("content").value = "";
      await refreshAll();
    }

    async function search() {
      const payload = {
        query: document.getElementById("query").value.trim(),
        agent_id: document.getElementById("query-agent").value.trim() || null,
        top_k: Number(document.getElementById("top-k").value || 5)
      };
      const data = await api("/retrieve", { method: "POST", body: JSON.stringify(payload) });
      document.getElementById("retrieve-results").innerHTML = data.map(item => memoryCard(item, true)).join("") || "<p>没有命中结果</p>";
    }

    async function feedback(memoryId, success) {
      await api("/feedback", {
        method: "POST",
        body: JSON.stringify({ memory_id: memoryId, success })
      });
      await refreshAll();
    }

    async function decay() {
      await api("/decay", { method: "POST", body: JSON.stringify({ idle_days: 7 }) });
      await refreshAll();
    }

    async function reflect() {
      await api("/reflect", { method: "POST", body: JSON.stringify({ limit: 50, min_group_size: 2 }) });
      await refreshAll();
    }

    async function refreshAll() {
      await Promise.all([loadStats(), loadMemories(), loadSemantic()]);
    }

    document.getElementById("save-btn").addEventListener("click", saveMemory);
    document.getElementById("search-btn").addEventListener("click", search);
    document.getElementById("refresh-btn").addEventListener("click", refreshAll);
    document.getElementById("load-memories-btn").addEventListener("click", loadMemories);
    document.getElementById("decay-btn").addEventListener("click", decay);
    document.getElementById("reflect-btn").addEventListener("click", reflect);
    refreshAll();
    window.feedback = feedback;
  </script>
</body>
</html>"""


class MemoryApi:
    def __init__(self, db_path: str) -> None:
        self.service = MemoryService(db_path)

    def dispatch(self, method: str, path: str, payload: dict | None = None) -> tuple[int, object]:
        payload = payload or {}
        parsed = urlparse(path)

        if method == "GET" and parsed.path == "/health":
            return HTTPStatus.OK, {"status": "ok"}
        if method == "GET" and parsed.path == "/":
            return HTTPStatus.OK, {"html": ADMIN_HTML}
        if method == "GET" and parsed.path == "/stats":
            return HTTPStatus.OK, self.service.stats()
        if method == "GET" and parsed.path == "/config":
            config = load_config(db_override=self.service.db_path)
            return HTTPStatus.OK, config.to_dict()
        if method == "GET" and parsed.path == "/memories":
            params = parse_qs(parsed.query)
            limit = int(params.get("limit", ["50"])[0])
            status = params.get("status", [None])[0]
            agent_id = params.get("agent_id", [None])[0]
            return HTTPStatus.OK, self.service.list_memories(limit=limit, status=status, agent_id=agent_id)
        if method == "GET" and parsed.path == "/semantic-memories":
            return HTTPStatus.OK, self.service.list_semantic_memories()

        if method == "POST" and parsed.path == "/memories":
            memory_id = self.service.add_memory(
                agent_id=payload["agent_id"],
                session_id=payload["session_id"],
                content=payload["content"],
                project_id=payload.get("project_id"),
                user_id=payload.get("user_id"),
                event_type=payload.get("event_type", "interaction"),
                source=payload.get("source"),
            )
            return HTTPStatus.CREATED, {"memory_id": memory_id}

        if method == "POST" and parsed.path == "/retrieve":
            result = self.service.retrieve(
                payload["query"],
                top_k=int(payload.get("top_k", 5)),
                agent_id=payload.get("agent_id"),
                session_id=payload.get("session_id"),
                project_id=payload.get("project_id"),
            )
            return HTTPStatus.OK, [item.__dict__ for item in result]

        if method == "POST" and parsed.path == "/feedback":
            result = self.service.give_feedback(
                int(payload["memory_id"]),
                success=bool(payload["success"]),
                note=payload.get("note"),
            )
            return HTTPStatus.OK, result

        if method == "POST" and parsed.path == "/decay":
            result = self.service.decay_memories(idle_days=int(payload.get("idle_days", 7)))
            return HTTPStatus.OK, result

        if method == "POST" and parsed.path == "/reflect":
            result = self.service.reflect(
                limit=int(payload.get("limit", 50)),
                min_group_size=int(payload.get("min_group_size", 2)),
            )
            return HTTPStatus.OK, result
        if method == "POST" and parsed.path == "/export":
            return HTTPStatus.OK, self.service.export_data(payload["output_path"])
        if method == "POST" and parsed.path == "/import":
            return HTTPStatus.OK, self.service.import_data(payload["input_path"])
        if method == "POST" and parsed.path == "/backup":
            return HTTPStatus.OK, self.service.backup_database(payload["target_dir"])
        if method == "POST" and parsed.path == "/restore":
            return HTTPStatus.OK, self.service.restore_database(payload["backup_path"])

        return HTTPStatus.NOT_FOUND, {"error": "not found"}


class ApiHandler(BaseHTTPRequestHandler):
    api: MemoryApi

    def do_GET(self) -> None:
        status, payload = self.api.dispatch("GET", self.path)
        if self.path == "/" and isinstance(payload, dict) and "html" in payload:
            self._html(status, payload["html"])
            return
        self._json(status, payload)

    def do_POST(self) -> None:
        try:
            payload = self._read_json()
        except ValueError:
            return
        status, response_payload = self.api.dispatch("POST", self.path, payload)
        self._json(status, response_payload)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _read_json(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": f"invalid json: {exc}"})
            raise ValueError("invalid json") from exc

    def _json(self, status: int, payload) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(int(status))
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, status: int, payload: str) -> None:
        body = payload.encode("utf-8")
        self.send_response(int(status))
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def create_app(db_path: str):
    api = MemoryApi(db_path)

    class BoundHandler(ApiHandler):
        pass

    BoundHandler.api = api
    return BoundHandler


def run_server(db_path: str, host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), create_app(db_path))
