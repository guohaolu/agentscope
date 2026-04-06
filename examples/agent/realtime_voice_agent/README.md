# Realtime Voice Agent 示例

这个示例演示了如何使用 AgentScope 的 `RealtimeAgent` 构建一个**实时语音对话 Agent**。它支持双向语音流传输，因此可以实现低延迟、自然的语音交互，并支持实时语音转写。

## 前置条件

- Python 3.10 或更高版本
- 已在环境变量中设置 `DASHSCOPE_API_KEY`

安装依赖：

```bash
uv pip install agentscope fastapi uvicorn websockets
# 或
# pip install agentscope
```

## 使用方式

### 1. 启动服务端

运行 FastAPI 服务：

```bash
cd examples/agent/realtime_voice_agent
python run_server.py
```

默认会启动在 `http://localhost:8000`。

### 2. 打开网页界面

在浏览器中访问：

```text
http://localhost:8000
```

你会看到一个网页界面，其中包含：

- 配置面板（指令和用户名）
- 语音控制按钮（开始录音、停止录音、断开连接）
- 视频录制按钮
- 文本输入框
- 消息显示区域
- 视频预览区域（开启视频录制时显示）

### 3. 开始对话

1. **配置 Agent**（可选）：
   - 修改 “Instructions” 来定制 Agent 行为
   - 在 “User Name” 输入你的名字

2. **开始语音录制**：
   - 点击“开始录音”按钮
   - 按浏览器提示授权麦克风权限
   - 自然地对 Agent 说话
   - Agent 会返回语音和文本响应

3. **停止录音**：
   - 点击“停止录音”暂停语音输入

4. **视频录制**（可选）：
   - 点击“开始视频录制”按钮启动视频采集
   - 按浏览器提示授权摄像头权限
   - 系统会自动以每秒 1 帧（1 fps）的频率采集并上传视频帧
   - 录制时会显示视频预览
   - 点击“停止视频录制”结束采集
   - **注意**：视频录制依赖已经建立的语音会话，请先启动语音对话再开始视频录制

## 切换模型

AgentScope 支持多种实时语音模型。这个示例默认使用 DashScope 的 `qwen3-omni-flash-realtime`，但你也可以很方便地切换到其他提供商。

### 支持的模型

- `GeminiRealtimeModel`
- `OpenAIRealtimeModel`

### 如何切换

编辑 `run_server.py`，替换模型初始化代码即可。

**切换到 OpenAI：**

```python
from agentscope.realtime import OpenAIRealtimeModel

agent = RealtimeAgent(
    name="Friday",
    sys_prompt=sys_prompt,
    model=OpenAIRealtimeModel(
        model_name="gpt-4o-realtime-preview",
        api_key=os.getenv("OPENAI_API_KEY"),
        voice="alloy",  # 可选值："alloy"、"echo"、"marin"、"cedar"
    ),
)
```

**切换到 Gemini：**

```python
from agentscope.realtime import GeminiRealtimeModel

agent = RealtimeAgent(
    name="Friday",
    sys_prompt=sys_prompt,
    model=GeminiRealtimeModel(
        model_name="gemini-2.5-flash-native-audio-preview-09-2025",
        api_key=os.getenv("GEMINI_API_KEY"),
        voice="Puck",  # 可选值："Puck"、"Charon"、"Kore"、"Fenrir"
    ),
)
```

启动服务前不要忘记设置对应的 API Key 环境变量。
