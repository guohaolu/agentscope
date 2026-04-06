# agent示例中的AgentScope功能

本文按功能视角整理 `examples/agent` 里的 AgentScope 用法，重点不是列 API，而是解释“这些功能在示例中是怎么被用起来的”。

## 1. 最基础的 Agent 交互

最常见的起点是：

```python
from agentscope.agent import ReActAgent, UserAgent
```

常见组合方式如下：

```python
agent = ReActAgent(...)
user = UserAgent("User")
```

然后进入多轮交互循环：

```python
msg = await user(msg)
msg = await agent(msg)
```

这在 `react_agent`、`voice_agent` 等示例中都出现了。

## 2. 模型与 formatter 的配套使用

示例中通常不是只创建模型，还会显式创建 formatter：

```python
model=DashScopeChatModel(...)
formatter=DashScopeChatFormatter()
```

这里体现了一个重要原则：

- 模型决定“调用哪个大模型服务”
- formatter 决定“消息如何组织成模型需要的格式”

如果替换模型，通常也要一起检查 formatter 是否匹配。

## 3. Memory 的作用

多个示例使用了：

```python
memory=InMemoryMemory()
```

它的作用可以简单理解为“保存上下文”。

常见用途包括：

- 让 Agent 记住前面的对话
- 在复杂任务中保存中间状态
- 在一次调用后手动清空，例如 `browser_agent` 在每轮后会清理 memory

## 4. Toolkit 与工具注册

`Toolkit` 是很多示例的关键。

最基础的写法是：

```python
toolkit = Toolkit()
toolkit.register_tool_function(execute_shell_command)
toolkit.register_tool_function(execute_python_code)
toolkit.register_tool_function(view_text_file)
```

这说明 Agent 不只是“生成文本”，还可以借助工具执行动作。

在这些示例里，工具主要被用来：

- 读文件
- 写文件
- 执行 Python
- 执行 shell 命令
- 访问外部 MCP 服务

## 5. MCP 接入外部能力

MCP 是这些示例中非常重要的一层。

常见写法包括：

```python
browser_client = StdIOStatefulClient(
    name="playwright-mcp",
    command="npx",
    args=["@playwright/mcp@latest"],
)
```

以及：

```python
await toolkit.register_mcp_client(browser_client)
```

这类模式出现在：

- `browser_agent`
- `deep_research_agent`
- `meta_planner_agent`

它背后的设计思路是：

- Agent 本身不直接内置所有能力
- 外部能力通过协议化方式挂接
- 工具层和 Agent 层保持解耦

## 6. 结构化输出

有些示例不是只要一段文本，而是希望模型返回一个结构明确的结果。

例如：

```python
class FinalResult(BaseModel):
    result: str
```

然后：

```python
msg = await agent(msg, structured_model=FinalResult)
```

这种模式在 `browser_agent` 和 `meta_planner_agent` 中都很有代表性。

它的价值在于：

- 结果更稳定
- 上层逻辑更容易消费
- 更适合复杂 Agent 链路

## 7. A2AAgent 与协议式 Agent 通信

`a2a_agent` 展示了另一种交互方式：不是直接在本地运行另一个 Agent，而是通过协议连接远端 Agent。

核心点包括：

- `A2AAgent` 作为客户端
- `A2AStarletteApplication` 作为服务端应用
- `A2AChatFormatter` 负责消息转换

这说明 AgentScope 不只支持“单进程内 Agent 调用”，还支持“跨服务 Agent 通信”。

## 8. RealtimeAgent 与实时语音

`realtime_voice_agent` 展示了 `RealtimeAgent` 的使用方式。

它和普通 `ReActAgent` 的差异在于：

- 输入不只是文本
- 输出也可以是实时音频
- 交互依赖持续连接，而不是一次请求一次响应

这个示例还把 Agent 放进了 WebSocket 会话中，因此也很适合理解“前端实时会话如何接 Agent”。

## 9. BrowserAgent 的定位

`browser_agent` 不是单纯把 `ReActAgent` 换个名字，而是一个更聚焦网页操作场景的 Agent。

你可以把它理解成：

- 目标更明确
- 工具更偏浏览器
- 更依赖 MCP 提供的网页操作能力

它特别适合学习“面向具体场景封装 Agent”的思路。

## 10. 自定义复杂 Agent

`deep_research_agent/deep_research_agent.py` 非常值得学习，因为它展示了如何基于已有 Agent 扩展复杂能力。

这里有几个关键点：

- 通过继承 `ReActAgent` 做定制
- 在类内部维护子任务、工作计划和中间结果
- 把“研究 -> 展开 -> 汇总 -> 写报告”做成完整流程

这说明 AgentScope 并不是只能用现成 Agent，也支持你把一个 Agent 演化成更复杂的任务系统。

## 11. 规划 Agent 与多 Agent 编排

`meta_planner_agent` 体现的是另一条路线：不是把所有能力都塞进一个 Agent，而是拆成：

- Planner 负责规划
- Worker 负责执行

这里的典型组件有：

- `PlanNotebook`
- 动态创建子 Agent 的工具函数
- 流式回传子 Agent 过程

这套设计很适合复杂任务，因为它把“怎么拆任务”和“怎么完成任务”分开了。

## 12. A2UI 与 Skill

`a2ui_agent` 更偏框架扩展示例。

它说明了两件事：

- Agent 可以不只输出文本，也可以输出界面定义
- Skill 可以作为“渐进暴露能力和知识”的机制

这对学习 AgentScope 的设计思想很重要，因为它说明框架并不把 Agent 限制在单一输出形式上。

## 学习 AgentScope 时建议抓住的主线

### 主线一：标准组装方式

很多示例都遵循类似的初始化顺序：

1. 创建模型
2. 创建 formatter
3. 创建 memory
4. 创建 toolkit
5. 创建 agent
6. 启动交互循环

### 主线二：复杂能力如何扩展

当基础组装理解后，再重点看这些扩展方式：

- 通过 `Toolkit` 增加动作能力
- 通过 MCP 接外部系统
- 通过继承扩展 Agent
- 通过 `PlanNotebook` 和 Worker 形成多 Agent 协作
- 通过结构化输出让系统更稳定

<tabs>
    <tab title="适合入门的功能">
        <list type="bullet">
            <li><code>ReActAgent</code></li>
            <li><code>UserAgent</code></li>
            <li><code>Toolkit</code></li>
            <li><code>InMemoryMemory</code></li>
        </list>
    </tab>
    <tab title="适合进阶的功能">
        <list type="bullet">
            <li><code>MCP</code></li>
            <li><code>RealtimeAgent</code></li>
            <li><code>A2AAgent</code></li>
            <li><code>PlanNotebook</code></li>
            <li><code>structured_model</code></li>
        </list>
    </tab>
</tabs>

<seealso>
    <category ref="related">
        <a href="agent示例总览.md">agent示例总览</a>
        <a href="agent示例中的Python语法.md">agent示例中的Python语法</a>
    </category>
</seealso>
