# -*- coding: utf-8 -*-
"""
一个用于演示音频输出能力的 ReAct Agent 示例。
注意：启用音频输出后，工具调用功能可能会失效。
"""
import asyncio
import os
from agentscope.agent import ReActAgent, UserAgent
from agentscope.formatter import OpenAIChatFormatter

from agentscope.memory import InMemoryMemory
from agentscope.model import OpenAIChatModel


async def main() -> None:
    """ReAct 语音 Agent 示例的主函数。"""

    agent = ReActAgent(
        name="Friday",
        sys_prompt="You are a helpful assistant",
        model=OpenAIChatModel(
            model_name="qwen3-omni-flash",
            client_kwargs={
                "base_url": "https://dashscope.aliyuncs.com/"
                "compatible-mode/v1",
            },
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            stream=True,
            # 更多配置项可参考 DashScope API 文档：
            # https://help.aliyun.com/zh/model-studio/qwen-omni
            generate_kwargs={
                "modalities": ["text", "audio"],
                "audio": {"voice": "Cherry", "format": "wav"},
            },
        ),
        formatter=OpenAIChatFormatter(),
        memory=InMemoryMemory(),
    )

    user = UserAgent("Bob")

    msg = None
    while True:
        msg = await user(msg)
        if msg.get_text_content() == "exit":
            break
        msg = await agent(msg)


asyncio.run(main())
