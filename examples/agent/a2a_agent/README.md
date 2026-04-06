# Agent-to-Agent 协议示例

AgentScope 中的 `A2AAgent` 是一个 A2A 客户端，它通过 Agent-to-Agent（A2A）协议连接到外部 Agent 服务端。
这个示例演示了如何配置并使用 `A2AAgent`，与部署在 A2A 服务端上的 Agent 进行交互。

需要注意的是，A2A 功能目前仍属于实验性能力，未来可能会调整。并且由于 A2A 协议本身的限制，`A2AAgent` 当前存在以下约束：

1. 仅支持聊天机器人场景，也就是只包含用户和单个 Agent 的对话
2. 不支持会话过程中的实时接管或中断
3. 不支持 Agent 风格的结构化输出
4. 会将已观察到的消息保存在本地，并在调用 `reply` 函数时与新的输入消息一起发送

## 文件说明

本示例包含以下文件：

```text
examples/agent/a2a_agent
├── main.py                  # 运行 A2A Agent 示例的主脚本
├── setup_a2a_server.py      # 启动一个简单 A2A 服务端的脚本
├── agent_card.py            # A2A Agent 的 agent card 定义
└── README.md                # 当前说明文档
```

## 环境准备

这个示例提供了一个最小可运行配置，用来展示如何在 AgentScope 中使用 `A2AAgent`。
首先安装依赖：

```bash
uv pip install a2a-sdk[http-server] agentscope[a2a]
# 或
pip install a2a-sdk[http-server] agentscope[a2a]
```

然后启动一个承载 ReAct Agent 的简单 A2A 服务端：

```bash
uvicorn setup_a2a_server:app --host 0.0.0.0 --port 8000
```

这会在本地 `8000` 端口启动 A2A 服务。

之后运行下面的命令，即可通过 A2A Agent 与服务端上的 Agent 进行聊天：

```bash
python main.py
```
