# Meta Planner Agent 示例

这个示例主要演示以下内容：

- 如何构建一个规划型 Agent，把复杂任务拆解成可执行的子任务，并协调多个子 Agent 完成任务
- 在多 Agent 系统中，如何妥善处理子 Agent 的输出消息
- 如何将子 Agent 的中断事件传递给主规划 Agent

具体来说，[main.py](./main.py) 中创建了一个带 `PlanNotebook` 的规划 Agent，用来生成和管理计划。它通过 [tool.py](./tool.py) 中的 `create_worker` 工具函数动态创建子 Agent，并让子 Agent 完成分配到的子任务。子 Agent 同时挂载了一些基础工具和预置 MCP 服务，用于增强执行能力。

> 建议配合 AgentScope-Studio 使用，这样更方便观察示例中的 Agent 交互过程。

## 快速开始

如果你还没有安装 `agentscope`，可以先执行：

```bash
pip install agentscope
```

请确认已经在环境变量中设置好 DashScope API Key。

这个示例中的子 Agent 支持以下 MCP 服务。设置对应环境变量后，相关能力会自动启用；如果没有设置，则对应 MCP 会被禁用。工具细节可以参考 [tool.py](./tool.py)，你也可以按需自行扩展。

| MCP | 说明 | 环境变量 |
|---|---|---|
| AMAP MCP | 提供地图相关服务 | `GAODE_API_KEY` |
| GitHub MCP | 检索和访问 GitHub 仓库 | `GITHUB_TOKEN` |
| Microsoft Playwright MCP | 提供浏览器自动化能力 | 无 |

运行示例：

```bash
python main.py
```

启动后，你可以让规划 Agent 帮你处理复杂任务，例如“调研 AgentScope 仓库”。

对于简单问题，规划 Agent 也可能直接回答，而不创建子 Agent。

## 进阶说明

### 处理子 Agent 输出

在这个示例中，子 Agent 不会直接把消息打印到控制台（见 `tool.py` 中的 `sub_agent.set_console_output_enabled(False)`）。相反，它的输出会作为 `create_worker` 工具函数的流式响应回传给规划 Agent。这样用户只需要面对一个主规划 Agent，而不是多个并列 Agent，交互体验会更自然。

但另一方面，如果子 Agent 的推理执行过程过长，`create_worker` 的工具响应也可能占用较多上下文长度。

下面这张图展示了子 Agent 输出在 AgentScope-Studio 中作为工具流式响应显示的效果：

<details>
 <summary>中文界面</summary>
 <p align="center">
  <img src="./assets/screenshot_zh.jpg"/>
 </p>
</details>

<details>
 <summary>英文界面</summary>
 <p align="center">
  <img src="./assets/screenshot_en.jpg"/>
 </p>
</details>

当然，你也可以选择把子 Agent 直接暴露给用户，只把结构化结果作为 `create_worker` 的工具结果返回给规划 Agent。

### 传播中断事件

在 `ReActAgent` 中，如果最终答案来自 `handle_interrupt`，返回消息的 `metadata` 中会包含 `_is_interrupted=True`，用于标记 Agent 被中断。

借助这个字段，我们可以在 `create_worker` 工具函数中把子 Agent 的中断事件传递给主规划 Agent。如果你使用自定义 Agent 类，也可以在自己的 `handle_interrupt` 逻辑里定义相应的传播机制。

### 替换大模型

这个示例基于 DashScope 对话模型构建。如果你要替换模型，记得同时调整 formatter。内置模型与 formatter 的对应关系可以参考[教程](https://doc.agentscope.io/tutorial/task_prompt.html#id1)。

## 延伸阅读

- [Plan](https://doc.agentscope.io/tutorial/task_plan.html)
