<div align="center">

# 🧠 CogniMem
## 让 AI 不再每次都从零开始

[![Stage](https://img.shields.io/badge/stage-MVP-orange.svg)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Architecture](https://img.shields.io/badge/architecture-long--term%20memory-black.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**一个面向 AI Agent 的长期记忆架构。**  
它不是被动存档聊天记录，而是把记忆变成可检索、可评分、可遗忘、可反思的认知基础设施。

[为什么需要](#为什么需要-cognimem) • [核心思路](#核心思路) • [记忆生命周期](#记忆生命周期) • [快速开始](#快速开始) • [路线图](#路线图) • [边界与限制](#边界与限制)

</div>

---

## 为什么需要 CogniMem

大多数 Agent 的问题，不是不会回答，而是**无法持续记住真正重要的信息**。

常见现象：

- 会话一结束，用户偏好、任务上下文、项目状态就丢失
- 历史越存越多，但真正有价值的内容并不会自动浮出来
- 检索系统只能“找相似”，却不知道哪些记忆真的帮助过后续任务
- 上下文窗口被历史灌满，token 花得很多，效果却不稳定

CogniMem 的目标不是把历史“存起来”，而是让系统逐步学会：

1. **什么值得记住**
2. **什么时候该拿出来**
3. **哪些记忆该强化，哪些该遗忘**
4. **如何从事件沉淀为事实、规则和技能**

---

## 一句话定义

> **CogniMem 是一套基于预测贡献的长期记忆架构。**  
> 它围绕“写入、检索、反馈、遗忘、反思”建立记忆闭环，让 AI Agent 具备可持续演化的长期记忆能力。

---

## 核心思路

CogniMem 的设计核心，不是“多存一点历史”，而是把每条记忆看作一个**对未来任务有帮助的预测器**。

当一条记忆被检索并参与后续回答或行动时：

- 帮上忙，就提高它的权重
- 误导了，就降低它的权重
- 长期没用，就逐步衰减
- 重复出现的有效经验，就继续抽象成事实、规则或技能

这意味着 CogniMem 关注的不是“记住了多少”，而是**记住的东西有没有持续创造价值**。

---

## 它和常见做法有什么不同

| 维度 | 普通聊天记录/向量库存档 | CogniMem |
|---|---|---|
| 目标 | 存住历史 | 让历史对未来任务持续有效 |
| 检索依据 | 相似度为主 | 相似度 + 全文 + 时间 + 重要性 |
| 价值判断 | 基本静态 | 根据真实使用效果动态更新 |
| 上下文注入 | 容易全量堆叠 | 摘要优先，按需展开 |
| 记忆演化 | 基本没有 | 支持强化、衰减、归档、反思 |
| 产出形态 | 事件堆积 | 可进一步沉淀为事实、规则、技能 |

CogniMem 不是“又一个 RAG 包装层”，而是把长期记忆当成 Agent 能力增长的一部分来设计。

---

## 当前定位

为了保持实事求是，当前 README 明确区分了**已聚焦的问题**与**尚未承诺的范围**：

### 当前聚焦

- 情景记忆的写入与存储
- 混合检索与重排
- 基于使用结果的反馈打分
- 记忆衰减、归档与生命周期管理
- 摘要级注入与按需展开
- 周期性反思与知识提炼的架构方向
- 作为外部长期记忆层与 Agent 框架集成

### 不应被误解为

- 不是用来替代 Agent 的人格、系统提示或安全边界
- 不是一个已经覆盖所有企业级治理场景的完成品
- 不是“接上就万能解决 Agent 所有问题”的银弹
- 不是所有收益都已经完成严格 benchmark 的成品系统

---

## 记忆生命周期

CogniMem 的方法可以概括为一条清晰的闭环：

### 1. 写入（Capture）
把用户输入、AI 输出、工具调用和任务状态变化记录成记忆事件。

### 2. 摘要与索引（Compress & Index）
对事件做摘要、向量化、全文索引和元数据标注，形成可检索对象。

### 3. 检索（Retrieve）
根据当前任务，从语义、关键词、时间、重要性等多个信号中混合召回最相关记忆。

### 4. 注入（Inject）
默认只把摘要和少量高价值记忆注入上下文，而不是把历史一股脑塞给模型。

### 5. 按需展开（Expand on Demand）
当模型需要更多细节时，再通过记忆 ID 回取原始内容，降低上下文浪费。

### 6. 反馈（Score）
根据任务是否成功、是否被真正使用、是否造成误导，动态调整记忆权重。

### 7. 衰减与归档（Decay & Archive）
长期无贡献或低价值记忆逐步降权、冷存储或清理，避免记忆库膨胀。

### 8. 反思与提炼（Reflect）
从高频、稳定、重复出现的情景记忆中提炼出语义记忆、规则卡片和技能模板。

这套流程的关键，不在“记得更多”，而在**记忆会自己变得更有用**。

---

## 设计原则

### 预测贡献优先
不是所有历史都值得保留。记忆是否强化、遗忘或抽象，取决于它对后续任务的真实贡献。

### 分层记忆
系统将长期记忆分为多个层次：工作记忆、情景记忆、语义记忆、技能记忆，以及负责调参与监控的元认知层。

### 渐进式披露
默认只注入摘要；细节只在需要时展开，尽量减少 token 浪费。

### 可解释与可修正
不仅要检索结果，还要告诉开发者：为什么检索了它、它为什么重要、它是否应该继续保留。

---

## 核心能力

- **长期事实记忆**：跨会话保留用户偏好、项目背景、任务状态与关键决策
- **混合检索**：组合语义检索、全文检索、时间信息和重要性信号
- **反馈学习**：根据真实使用结果动态强化或降权记忆
- **自然遗忘**：让长期低价值记忆自动冷却，避免系统越用越重
- **渐进式披露**：先给摘要，再按需展开原文，控制上下文成本
- **反思提炼**：从事件沉淀为事实、规则、关系与技能线索
- **可观测性**：为 why_retrieved、importance、freshness 等解释字段预留空间
- **可替换后端**：适合从轻量起步，再按需要切换存储或检索组件

---

## 适合什么场景

### 持续协作型 Agent
需要跨会话记住用户习惯、项目阶段、已完成决策和未完成事项。

### 项目型工作流
需要把任务历史、技术选型、错误修复记录、工具调用结果长期沉淀下来。

### 个性化助手
需要稳定保留偏好、规则、表达风格和禁忌项，而不是让用户反复重说。

### 高上下文成本场景
需要在效果和 token 成本之间做平衡，避免每轮都全量灌入历史。

---

## 架构概览

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

在实现层面，它适合作为 **Agent 的外部长期记忆 sidecar service**：

- 用户输入前先检索相关记忆
- 回答完成后写回本轮交互
- 任务成功或失败后更新反馈分数
- 定期执行衰减、归档与反思任务

---

## 快速开始

> 下面展示的是典型使用方式，用于说明 CogniMem 的工作流与集成形态。

### 初始化

```bash
PYTHONPATH=src python3 -m cognimem.cli init --db ./data/memory.db
```

### 写入一条记忆

```python
from cognimem.service import MemoryService

service = MemoryService(db_path="./data/memory.db")

memory_id = service.add_memory(
    agent_id="my_agent",
    session_id="session_001",
    content="用户偏好使用 Python 进行自动化脚本开发，习惯使用 f-string。"
)
```

### 检索相关记忆

```python
results = service.retrieve(
    query="用户偏好什么编程语言？",
    top_k=3,
    agent_id="my_agent"
)

for item in results:
    print(item.summary, item.importance, item.why_retrieved)
```

### 提供反馈

```python
service.give_feedback(
    memory_id=memory_id,
    success=True,
    note="这条记忆帮助系统正确识别了用户偏好"
)
```

### 启动服务

```bash
PYTHONPATH=src python3 -m cognimem.cli serve --db ./data/memory.db --port 8000
```

---

## 典型 API 形态

| Endpoint | Method | 用途 |
|---|---|---|
| `/memories` | GET / POST | 记录或查看记忆 |
| `/retrieve` | POST | 检索相关记忆 |
| `/feedback` | POST | 回写成功/失败反馈 |
| `/decay` | POST | 触发衰减任务 |
| `/reflect` | POST | 触发反思任务 |
| `/export` | POST | 导出备份 |
| `/import` | POST | 导入备份 |
| `/stats` | GET | 查看统计与状态 |

---

## 为什么这个 README 值得被点 Star

因为它不是在卖一个“听起来很聪明”的名词，而是在明确解决一个真实、反复出现的问题：

> **今天的大多数 Agent 还没有真正可演化的长期记忆。**

如果你也在做下面这些事：

- 想让 Agent 记住用户和项目，而不是每轮都重新认识世界
- 想让检索结果不只是“相关”，而是“有用”
- 想把历史沉淀成事实、规则与技能，而不是堆成日志坟场
- 想控制上下文成本，而不是无限堆 token

那 CogniMem 解决的，正是你迟早要正面面对的问题。

---

## 路线图

### MVP

- [x] 情景记忆写入
- [x] 检索接口与基础召回
- [x] 反馈更新分数
- [x] 衰减与归档机制
- [x] 作为外部服务的集成方向

### Next

- [ ] 混合检索与重排增强
- [ ] 反思任务自动化
- [ ] 语义记忆条目生成
- [ ] 技能模板沉淀
- [ ] 更完善的观测指标与管理界面

### Longer Term

- [ ] 元认知调参
- [ ] 多 Agent 记忆隔离与共享策略
- [ ] 更强的知识图谱与技能固化能力
- [ ] 更大规模部署与治理能力

---

## 边界与限制

为了让项目长期可信，下面这些限制应该直接写清楚：

- 记忆系统无法替代高质量的 Agent 本体设计
- 检索不是越多越好，错误召回同样会污染输出
- 反思与技能沉淀需要更强模型时，会引入额外成本
- 长期记忆必须允许人工修正、回滚和白名单保护
- 没有反馈闭环，长期记忆就很容易重新退化成“日志仓库”

---

## 贡献建议

欢迎围绕以下方向参与：

- 检索与重排策略
- 记忆评分机制
- 反思与抽象流程
- 记忆污染治理
- 观测面板与调试工具
- LangGraph / AutoGen / CrewAI 集成

如果你也认同：

**AI 不该只会回答，它还应该学会记住、筛选、遗忘和进化。**

那这个项目值得你现在就点一个 Star。

---

## License

MIT

---

<div align="center">

**CogniMem**  
把“记忆”从附属功能，做成 Agent 持续进化的基础设施。

</div>
