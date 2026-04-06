# Deep Research Agent 示例

## 这个示例展示了什么

这个示例展示了如何基于 AgentScope 实现一个 **DeepResearch Agent**。DeepResearch Agent 擅长执行多步骤研究任务，可以从多个信息源中收集并整合内容，最终生成较完整的报告来解决复杂问题。

## 前置条件

- Python 3.10 或更高版本
- Node.js 和 npm（用于启动 MCP 服务）
- 来自[阿里云](https://dashscope.console.aliyun.com/)的 DashScope API Key
- 来自 [Tavily](https://www.tavily.com/) 的 Tavily Search API Key

## 运行方式

1. **设置环境变量**：

   ```bash
   export DASHSCOPE_API_KEY="your_dashscope_api_key_here"
   export TAVILY_API_KEY="your_tavily_api_key_here"
   export AGENT_OPERATION_DIR="your_own_direction_here"
   ```

2. **测试 Tavily MCP 服务**：

   ```bash
   npx -y tavily-mcp@latest
   ```

3. **运行脚本**：

   ```bash
   python main.py
   ```

如果你希望让 Deep Research Agent 支持多轮对话，可以参考下面的代码方式进行改造：

```python
from agentscope.agent import UserAgent
user = UserAgent("User")
user_msg = None
msg = []
while True:
    user_msg = await user(user_msg)
    if user_msg.get_text_content() == "exit":
        break
    msg.append(user_msg)
    assistant_msg = await agent(user_msg)
    msg.append(assistant_msg)
```

## 连接网页搜索 MCP 客户端

DeepResearch Agent 当前只支持通过 Tavily MCP 客户端进行网页搜索。要启用这个能力，你需要先在本地启动 MCP 服务，并建立连接。

```python
from agentscope.mcp import StdIOStatefulClient

tavily_search_client = StdIOStatefulClient(
    name="tavily_mcp",
    command="npx",
    args=["-y", "tavily-mcp@latest"],
    env={"TAVILY_API_KEY": os.getenv("TAVILY_API_KEY", "")},
)
await tavily_search_client.connect()
```

> 说明：这个示例基于 DashScope 对话模型构建。如果你要替换模型，记得同时更换 formatter。内置模型与 formatter 的对应关系可以参考[教程](https://doc.agentscope.io/tutorial/task_prompt.html#id1)。
