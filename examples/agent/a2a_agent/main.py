# -*- coding: utf-8 -*-
"""A2A Agent 示例的主入口。"""
import asyncio

from agent_card import agent_card

from agentscope.agent import UserAgent, A2AAgent


async def main() -> None:
    """示例主函数，用于构造用户与 A2A Agent 之间的简单对话。"""

    user = UserAgent("user")

    agent = A2AAgent(
        agent_card=agent_card,
    )

    msg = None
    while True:
        msg = await user(msg)
        if msg.get_text_content() == "exit":
            break
        msg = await agent(msg)


asyncio.run(main())
