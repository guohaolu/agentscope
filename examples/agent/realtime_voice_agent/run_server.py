# -*- coding: utf-8 -*-
"""实时语音 Agent 示例服务端。"""
import asyncio
import os
import traceback
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse

from agentscope import logger
from agentscope.agent import RealtimeAgent
from agentscope.realtime import (
    DashScopeRealtimeModel,
    GeminiRealtimeModel,
    OpenAIRealtimeModel,
    ClientEvents,
    ServerEvents,
    ClientEventType,
)
from agentscope.tool import (
    Toolkit,
    execute_python_code,
    execute_shell_command,
    view_text_file,
)

app = FastAPI()


@app.get("/")
async def get() -> FileResponse:
    """返回前端测试页面。"""
    html_path = Path(__file__).parent / "chatbot.html"
    return FileResponse(html_path)


@app.get("/api/check-models")
async def check_models() -> dict:
    """检查环境变量中哪些模型 API Key 可用。"""
    return {
        "dashscope": bool(os.getenv("DASHSCOPE_API_KEY")),
        "gemini": bool(os.getenv("GEMINI_API_KEY")),
        "openai": bool(os.getenv("OPENAI_API_KEY")),
    }


async def frontend_receive(
    websocket: WebSocket,
    frontend_queue: asyncio.Queue,
) -> None:
    """将 Agent 返回的消息转发到前端。"""
    try:
        while True:
            msg: ServerEvents.EventBase = await frontend_queue.get()

            # 以 JSON 形式发送消息
            await websocket.send_json(msg.model_dump())

    except Exception as e:
        print(f"[ERROR] frontend_receive error: {e}")
        traceback.print_exc()


@app.websocket("/ws/{user_id}/{session_id}")
async def single_agent_endpoint(
    websocket: WebSocket,
    user_id: str,
    session_id: str,
) -> None:
    """单个实时 Agent 的 WebSocket 接口。"""
    try:
        await websocket.accept()

        logger.info(
            "Connected to WebSocket: user_id=%s, session_id=%s",
            user_id,
            session_id,
        )

        # 创建用于转发前端消息的队列
        frontend_queue = asyncio.Queue()
        asyncio.create_task(
            frontend_receive(websocket, frontend_queue),
        )

        # 创建实时 Agent
        agent = None

        while True:
            # 处理前端传入的消息，也就是 ClientEvents
            data = await websocket.receive_json()

            client_event = ClientEvents.from_json(data)

            if isinstance(
                client_event,
                ClientEvents.ClientSessionCreateEvent,
            ):
                # 根据会话参数创建 Agent
                instructions = client_event.config.get(
                    "instructions",
                    "You're a helpful assistant.",
                )
                agent_name = client_event.config.get("agent_name", "Friday")
                model_provider = client_event.config.get(
                    "model_provider",
                    "dashscope",
                )

                sys_prompt = instructions

                # 为支持工具调用的模型创建工具箱
                toolkit = None
                if model_provider in ["gemini", "openai"]:
                    toolkit = Toolkit()
                    toolkit.register_tool_function(execute_python_code)
                    toolkit.register_tool_function(execute_shell_command)
                    toolkit.register_tool_function(view_text_file)

                # 根据模型提供商创建对应模型
                if model_provider == "dashscope":
                    model = DashScopeRealtimeModel(
                        model_name="qwen3-omni-flash-realtime",
                        api_key=os.getenv("DASHSCOPE_API_KEY"),
                    )
                elif model_provider == "gemini":
                    model = GeminiRealtimeModel(
                        model_name=(
                            "gemini-2.5-flash-native-audio-preview-09-2025"
                        ),
                        api_key=os.getenv("GEMINI_API_KEY"),
                    )
                elif model_provider == "openai":
                    model = OpenAIRealtimeModel(
                        model_name="gpt-4o-realtime-preview",
                        api_key=os.getenv("OPENAI_API_KEY"),
                    )
                else:
                    raise ValueError(
                        f"Unsupported model provider: {model_provider}",
                    )

                # 创建 Agent
                agent = RealtimeAgent(
                    name=agent_name,
                    sys_prompt=sys_prompt,
                    model=model,
                    toolkit=toolkit,
                )

                await agent.start(frontend_queue)

                # 向前端发送 session_created 事件
                await websocket.send_json(
                    ServerEvents.ServerSessionCreatedEvent(
                        session_id=session_id,
                    ).model_dump(),
                )
                print(
                    f"Session created successfully: {session_id}",
                )

            elif client_event.type == ClientEventType.CLIENT_SESSION_END:
                # 结束当前 Agent 会话
                if agent:
                    await agent.stop()
                    agent = None

            else:
                await agent.handle_input(client_event)

    except Exception as e:
        print(f"[ERROR] WebSocket endpoint error: {e}")
        traceback.print_exc()
        raise


if __name__ == "__main__":
    uvicorn.run(
        "run_server:app",
        host="localhost",
        port=8000,
        reload=True,
        log_level="info",
    )
