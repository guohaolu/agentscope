# ReAct Agent 示例

这个示例展示了 AgentScope 中的 **ReAct Agent**。在这个例子里，ReAct Agent 会以聊天机器人的方式与用户交互，并借助一组工具来辅助回答问题。

> 提示：你可以尝试按 `Ctrl+C` 中断 Agent 的回复，体验实时接管 / 中断能力。

## 快速开始

请先确保已经安装 `agentscope`，并在环境变量中设置好 `DASHSCOPE_API_KEY`。

运行以下命令启动示例：

```bash
python main.py
```

> 说明：
> - 这个示例基于 DashScope 对话模型构建。如果你要替换成其他模型，记得同时调整 formatter。内置模型与 formatter 的对应关系可以参考[教程](https://doc.agentscope.io/tutorial/task_prompt.html#id1)。
> - 如果使用本地模型，请先确认对应模型服务（例如 Ollama）已经启动。
