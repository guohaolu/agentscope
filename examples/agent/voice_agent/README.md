# Voice Agent

> 这是 AgentScope 中的实验性功能。

这个示例演示了如何基于 AgentScope 和 Qwen-Omni 模型构建一个语音 Agent，支持文本和音频两种输出形式。

> 说明：
> - 启用音频输出时，Qwen-Omni 可能不会生成工具调用。
> - 这个示例支持 DashScope 的 `Qwen-Omni` 和 OpenAI 的 `GPT-4o Audio` 模型。你可以通过修改 `main.py` 中的 `model` 参数来切换模型。
> - 目前还没有验证过 vLLM，欢迎后续补充和扩展。

## 快速开始

请先确保已经安装 `agentscope`，并在环境变量中设置好 `DASHSCOPE_API_KEY`。

运行以下命令启动示例：

```bash
python main.py
```
