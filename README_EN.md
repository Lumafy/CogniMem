<div align="center">

<img src="assets/logo.png" alt="CogniMem logo" width="720" />

[中文](README.md) | English

# 🧠 CogniMem
## Stop Shipping Amnesiac Agents

[![Stage](https://img.shields.io/badge/stage-MVP-orange.svg)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Architecture](https://img.shields.io/badge/architecture-long--term%20memory-black.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**A long-term memory architecture for AI agents.**  
Not a passive chat archive, but a memory layer that can be retrieved, scored, decayed, reflected on, and improved over time.

[Why It Exists](#why-cognimem) • [Core Idea](#core-idea) • [Memory Lifecycle](#memory-lifecycle) • [Quick Start](#quick-start) • [Roadmap](#roadmap) • [Limits](#limits)

</div>

---

## Why CogniMem

Most agents do not fail because they cannot answer. They fail because they **cannot keep the right things alive across time**.

Common symptoms:

- user preferences disappear after the session ends
- project context has to be re-explained again and again
- retrieval systems return “similar” history, not necessarily *useful* history
- context windows get flooded with stale logs while token costs keep rising

CogniMem is built to answer four practical questions:

1. **What is worth remembering?**
2. **When should memory be retrieved?**
3. **What should be reinforced, and what should be forgotten?**
4. **How do repeated events become facts, rules, and reusable skills?**

---

## One-Line Definition

> **CogniMem is a prediction-contribution-driven long-term memory architecture.**  
> It closes the loop between writing, retrieving, feedback, decay, and reflection so an AI agent can evolve instead of merely accumulating logs.

---

## Core Idea

CogniMem does not treat memory as “more history.” It treats memory as a **future-useful predictor**.

When a memory is retrieved and used in a later task:

- if it helps, its value should increase
- if it misleads, its value should drop
- if it remains unused for too long, it should decay
- if a pattern keeps proving useful, it should be abstracted into facts, rules, or skills

That is the key distinction: CogniMem is not optimized for storing the most data. It is optimized for **retaining the most useful memory over time**.

---

## How It Differs from Typical Setups

| Dimension | Chat logs / Vector storage | CogniMem |
|---|---|---|
| Primary goal | keep history | make history useful for future tasks |
| Retrieval basis | mostly similarity | similarity + full-text + time + importance |
| Memory value | largely static | updated from real usage outcomes |
| Context injection | easy to overstuff | summary-first, details on demand |
| Evolution | minimal | reinforce, decay, archive, reflect |
| Output shape | event pile | facts, rules, skill candidates |

CogniMem is not just another RAG wrapper. It treats long-term memory as part of the agent’s capability stack.

---

## Current Positioning

To stay credible, this README separates **what the project is focused on now** from **what it should not be mistaken for**.

### Current focus

- episodic memory capture and storage
- hybrid retrieval and reranking
- feedback-driven memory scoring
- decay, archiving, and memory lifecycle control
- summary-first injection with on-demand expansion
- reflection and knowledge extraction as an architectural direction
- external memory-layer integration with agent frameworks

### What it is not

- not a replacement for agent identity, system prompts, or safety boundaries
- not a finished enterprise platform covering every governance scenario
- not a magic plug-in that fixes every agent problem overnight
- not a product where every claimed gain has already been benchmarked at scale

---

## Memory Lifecycle

CogniMem follows a simple but disciplined loop:

### 1. Capture
Store user input, model output, tool calls, and task-state transitions as memory events.

### 2. Compress & Index
Summarize events, vectorize them, add full-text indexing, and attach metadata.

### 3. Retrieve
Recall the most relevant memories using a mix of semantic signals, keywords, time, and importance.

### 4. Inject
Inject summaries and a small set of high-value memories first instead of dumping full history into the context window.

### 5. Expand on Demand
When more detail is actually needed, fetch the raw content by memory ID.

### 6. Score
Update memory value based on whether it was used, whether it helped, and whether it caused confusion.

### 7. Decay & Archive
Let low-value and stale memories cool down, move to cold storage, or get cleaned up.

### 8. Reflect
Turn repeated, stable episodic patterns into semantic memories, rules, and skill templates.

The point is not to remember more. The point is to make memory **more useful, more selective, and more adaptive**.

---

## Design Principles

### Prediction contribution first
Not all history deserves to survive. Memory should be reinforced, forgotten, or abstracted according to its contribution to later tasks.

### Layered memory
The architecture distinguishes working memory, episodic memory, semantic memory, skill memory, and a meta-cognitive layer for monitoring and adjustment.

### Progressive disclosure
Start with summaries. Pull details only when they are actually needed.

### Explainable and correctable
A serious memory layer should answer: why was this retrieved, why is it important, and should it continue to live?

---

## Core Capabilities

- **Long-term factual memory** for user preferences, project context, task progress, and important decisions
- **Hybrid retrieval** combining semantic retrieval, full-text lookup, time cues, and importance signals
- **Feedback learning** that reinforces or downranks memory based on actual outcomes
- **Natural forgetting** so low-value memory does not bloat the system forever
- **Progressive disclosure** to balance retrieval quality and token efficiency
- **Reflection pipelines** that turn events into facts, rules, relationships, and skill candidates
- **Observability hooks** for fields such as `why_retrieved`, `importance`, and `freshness`
- **Swappable backends** so the system can start light and scale when needed

---

## Where It Fits Best

### Persistent collaboration agents
Agents that need to remember preferences, project phase, previous decisions, and unfinished work across sessions.

### Project-centric workflows
Systems that need to retain debugging history, architectural choices, tool outputs, and task state over time.

### Personalized assistants
Assistants that should stop asking the same questions and start behaving as if they actually know the user.

### High-context-cost environments
Teams that need better memory quality without paying for full-history injection on every turn.

---

## Architecture Overview

```text
Agent / Workflow Framework
        |
        v
Long-Term Memory Service
  - write
  - retrieve
  - feedback
  - reflect
  - decay
  - observe
        |
        +-------------------+
        |                   |
        v                   v
Relational Store      Vector / Retrieval Index
  - metadata          - semantic recall
  - scores            - similarity search
  - timeline          - clustering input
  - full-text index
        |
        v
File / Object Storage
  - raw logs
  - archived content
  - reflection outputs
  - skill templates
```

In practice, it fits naturally as an **external sidecar memory service** for an agent stack:

- retrieve before response generation
- write back after the turn completes
- score memory after success or failure
- run decay, archive, and reflection jobs on a schedule

---

## Quick Start

> The commands below illustrate the intended developer workflow and integration shape.

### Initialize

```bash
PYTHONPATH=src python3 -m cognimem.cli init --db ./data/memory.db
```

### Add a memory

```python
from cognimem.service import MemoryService

service = MemoryService(db_path="./data/memory.db")

memory_id = service.add_memory(
    agent_id="my_agent",
    session_id="session_001",
    content="The user prefers Python for automation and likes f-strings."
)
```

### Retrieve relevant memories

```python
results = service.retrieve(
    query="What programming language does the user prefer?",
    top_k=3,
    agent_id="my_agent"
)

for item in results:
    print(item.summary, item.importance, item.why_retrieved)
```

### Send feedback

```python
service.give_feedback(
    memory_id=memory_id,
    success=True,
    note="This memory helped the agent identify the user's preference"
)
```

### Start the service

```bash
PYTHONPATH=src python3 -m cognimem.cli serve --db ./data/memory.db --port 8000
```

---

## Typical API Shape

| Endpoint | Method | Purpose |
|---|---|---|
| `/memories` | GET / POST | write or inspect memories |
| `/retrieve` | POST | retrieve relevant memory |
| `/feedback` | POST | write back success/failure signals |
| `/decay` | POST | trigger decay |
| `/reflect` | POST | trigger reflection |
| `/export` | POST | export backup |
| `/import` | POST | import backup |
| `/stats` | GET | inspect system state |

---

## Why This Project Is Worth a Star

Because it addresses a problem that nearly every serious agent team eventually hits:

> **most agents today do not have a truly evolvable long-term memory layer.**

If you are trying to build agents that:

- remember users and projects across sessions
- retrieve not just relevant history, but useful history
- turn repeated events into rules and reusable workflows
- reduce context waste instead of endlessly injecting logs

then CogniMem is working on a problem you will eventually have to solve anyway.

---

## Roadmap

### MVP

- [x] episodic memory capture
- [x] retrieval interface and basic recall loop
- [x] feedback-based score updates
- [x] decay and archive mechanisms
- [x] external-service integration direction

### Next

- [ ] stronger hybrid retrieval and reranking
- [ ] automated reflection jobs
- [ ] semantic memory extraction
- [ ] skill-template consolidation
- [ ] better observability and management surfaces

### Longer Term

- [ ] meta-cognitive parameter tuning
- [ ] multi-agent memory isolation and sharing policies
- [ ] stronger knowledge-graph and skill solidification
- [ ] larger-scale deployment and governance tooling

---

## Limits

A trustworthy memory system should state its limits clearly:

- memory does not replace good agent design
- retrieval quality can be damaged by false positives, not just low recall
- reflection and skill extraction may add model cost when stronger reasoning is required
- long-term memory must support manual correction, rollback, and protected records
- without a feedback loop, memory quickly collapses back into a log warehouse

---

## Contributing

Contributions are especially valuable around:

- retrieval and reranking
- scoring logic
- reflection and abstraction pipelines
- memory-pollution control
- observability and debugging tools
- LangGraph / AutoGen / CrewAI integrations

If you believe AI should do more than answer —
if it should **remember, filter, forget, and improve** —
this project deserves your attention now.

---

## License

MIT

---

<div align="center">

**CogniMem**  
Turn memory from an accessory into infrastructure for agent evolution.

</div>
