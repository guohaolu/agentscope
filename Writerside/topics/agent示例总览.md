# agent示例总览

本文根据 `examples/agent` 目录下已经扫描过的示例整理，目标不是重复 README，而是给学习路径做一个总入口。

## 适合怎么学

如果你的目标是同时学习 Python 和 AgentScope，建议按下面顺序阅读和运行：

1. `react_agent`
2. `voice_agent`
3. `realtime_voice_agent`
4. `a2a_agent`
5. `browser_agent`
6. `deep_research_agent`
7. `meta_planner_agent`
8. `a2ui_agent`

前半部分更适合入门，后半部分更适合理解 Agent 编排、MCP、实时通信和复杂工作流。

## 各示例在学什么

| 示例目录 | 学习重点 | 推荐关注点 |
|---|---|---|
| `react_agent` | 基础 ReAct Agent | `ReActAgent`、`UserAgent`、工具注册、内存 |
| `voice_agent` | 语音输出 Agent | 多模态模型参数、音频输出 |
| `realtime_voice_agent` | 实时语音交互 | `RealtimeAgent`、WebSocket、前后端联动 |
| `a2a_agent` | Agent-to-Agent 协议 | `A2AAgent`、A2A 服务端、消息格式转换 |
| `browser_agent` | 浏览器自动化 | `BrowserAgent`、MCP、命令行参数 |
| `deep_research_agent` | 深度研究流程 | 多步推理、子任务展开、报告生成 |
| `meta_planner_agent` | 规划与子 Agent 编排 | `PlanNotebook`、动态创建 Worker、流式工具输出 |
| `a2ui_agent` | Agent 生成 UI | Skill、Schema 暴露、A2UI 集成思路 |

## 学习时建议重点看什么

### 第一层：先看入口文件

优先看每个目录下的 `main.py` 或 `run_server.py`，因为这些文件最能说明一个示例是如何被组装起来的。

你会反复看到这些模式：

- 创建模型
- 创建 formatter
- 创建 toolkit / memory
- 创建 agent
- 创建用户或前端输入源
- 在循环中交互

### 第二层：再看扩展点

当你理解入口后，再去看这些更有代表性的扩展点：

- `a2a_agent/setup_a2a_server.py`
- `browser_agent/browser_agent.py`
- `deep_research_agent/deep_research_agent.py`
- `meta_planner_agent/tool.py`

这些文件更能体现 AgentScope 的设计思路，而不只是“怎么跑起来”。

## 从设计角度可以学到什么

这些示例背后体现了几个比较稳定的设计思路：

- Agent 负责“决策和对话”，工具负责“执行具体动作”
- 模型、formatter、memory、toolkit 通常被显式组装，而不是完全隐藏
- 复杂任务会逐步拆成“规划 -> 执行 -> 汇总”
- 外部能力通过 MCP 接入，而不是直接把所有能力写死在 Agent 类里
- 多 Agent 场景强调职责分离，例如 Planner 负责分工，Worker 负责执行

## 推荐阅读顺序

<procedure title="建议的学习顺序" id="recommended-learning-order">
    <step>
        <p>先运行 <code>react_agent</code>，理解最基础的 Agent 交互循环。</p>
    </step>
    <step>
        <p>再看 <code>voice_agent</code> 和 <code>realtime_voice_agent</code>，理解多模态和实时会话。</p>
    </step>
    <step>
        <p>接着阅读 <code>a2a_agent</code> 和 <code>browser_agent</code>，理解协议和 MCP 工具接入。</p>
    </step>
    <step>
        <p>最后看 <code>deep_research_agent</code>、<code>meta_planner_agent</code> 和 <code>a2ui_agent</code>，理解复杂任务编排与框架扩展。</p>
    </step>
</procedure>

<seealso>
    <category ref="related">
        <a href="agent示例中的Python语法.md">agent示例中的Python语法</a>
        <a href="agent示例中的AgentScope功能.md">agent示例中的AgentScope功能</a>
    </category>
</seealso>
