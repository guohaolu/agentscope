# -*- coding: utf-8 -*-
"""规划型 Agent 示例中使用的工具函数。"""
import asyncio
import json
import os
from collections import OrderedDict
from typing import AsyncGenerator

from pydantic import BaseModel, Field

from agentscope.agent import ReActAgent
from agentscope.formatter import DashScopeChatFormatter
from agentscope.mcp import HttpStatelessClient, StdIOStatefulClient
from agentscope.message import Msg, TextBlock
from agentscope.model import DashScopeChatModel
from agentscope.pipeline import stream_printing_messages
from agentscope.tool import (
    ToolResponse,
    Toolkit,
    write_text_file,
    insert_text_file,
    view_text_file,
)


class ResultModel(BaseModel):
    """子 Worker 用于总结任务结果的结构化模型。"""

    success: bool = Field(
        description="Whether the task was successful or not.",
    )
    message: str = Field(
        description=(
            "The specific task result, should include necessary details, "
            "e.g. the file path if any file is generated, the deviation, "
            "and the error message if any."
        ),
    )


def _convert_to_text_block(msgs: list[Msg]) -> list[TextBlock]:
    # 收集全部内容块
    blocks: list = []
    # 将 tool_use 块转换为文本块，便于工具流式输出展示
    for _ in msgs:
        for block in _.get_content_blocks():
            if block["type"] == "text":
                blocks.append(block)

            elif block["type"] == "tool_use":
                blocks.append(
                    TextBlock(
                        type="text",
                        text=f"Calling tool {block['name']} ...",
                    ),
                )

    return blocks


async def create_worker(
    task_description: str,
) -> AsyncGenerator[ToolResponse, None]:
    """创建一个子 Worker 来完成指定任务。

    Args:
        task_description (`str`):
            交给子 Worker 执行的任务描述，应包含所需的全部必要信息。

    Returns:
        `AsyncGenerator[ToolResponse, None]`:
            一个异步生成器，用于持续产出 ToolResponse 对象。
    """
    toolkit = Toolkit()

    # 高德地图 MCP 客户端
    if os.getenv("GAODE_API_KEY"):
        toolkit.create_tool_group(
            group_name="amap_tools",
            description="Map-related tools, including geocoding, routing, and "
            "place search.",
        )
        client = HttpStatelessClient(
            name="amap_mcp",
            transport="streamable_http",
            url=f"https://mcp.amap.com/mcp?key={os.environ['GAODE_API_KEY']}",
        )
        await toolkit.register_mcp_client(client, group_name="amap_tools")
    else:
        print(
            "警告：环境变量中未设置 GAODE_API_KEY，跳过高德 MCP 客户端注册。",
        )

    # 浏览器 MCP 客户端
    toolkit.create_tool_group(
        group_name="browser_tools",
        description="Web browsing related tools.",
    )
    browser_client = StdIOStatefulClient(
        name="playwright-mcp",
        command="npx",
        args=["@playwright/mcp@latest"],
    )
    await browser_client.connect()
    await toolkit.register_mcp_client(
        browser_client,
        group_name="browser_tools",
    )

    # GitHub MCP 客户端
    if os.getenv("GITHUB_TOKEN"):
        toolkit.create_tool_group(
            group_name="github_tools",
            description="GitHub related tools, including repository "
            "search and code file retrieval.",
        )
        github_client = HttpStatelessClient(
            name="github",
            transport="streamable_http",
            url="https://api.githubcopilot.com/mcp/",
            headers={"Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}"},
        )
        await toolkit.register_mcp_client(
            github_client,
            group_name="github_tools",
        )

    else:
        print(
            "警告：环境变量中未设置 GITHUB_TOKEN，跳过 GitHub MCP 客户端注册。",
        )

    # 基础读写工具
    toolkit.register_tool_function(write_text_file)
    toolkit.register_tool_function(insert_text_file)
    toolkit.register_tool_function(view_text_file)

    # 创建新的子 Agent 来完成指定任务
    sub_agent = ReActAgent(
        name="Worker",
        sys_prompt=f"""You're an agent named Worker.

## Your Target
Your target is to finish the given task with your tools.

## IMPORTANT
You MUST use the `{ReActAgent.finish_function_name}` to generate the final answer after finishing the task.
""",  # noqa: E501  # pylint: disable=C0301
        model=DashScopeChatModel(
            model_name="qwen3-max",
            api_key=os.environ["DASHSCOPE_API_KEY"],
        ),
        enable_meta_tool=True,
        formatter=DashScopeChatFormatter(),
        toolkit=toolkit,
        max_iters=20,
    )

    # 关闭子 Agent 的控制台输出
    sub_agent.set_console_output_enabled(False)

    # 收集执行过程中的消息内容
    msgs = OrderedDict()

    # 将子 Agent 封装为协程任务，以便获得最终结构化输出
    result = []

    async def call_sub_agent() -> None:
        msg_res = await sub_agent(
            Msg(
                "user",
                content=task_description,
                role="user",
            ),
            structured_model=ResultModel,
        )
        result.append(msg_res)

    # Use stream_printing_message to get the streaming response as the
    # sub-agent works
    async for msg, _ in stream_printing_messages(
        agents=[sub_agent],
        coroutine_task=call_sub_agent(),
    ):
        msgs[msg.id] = msg

        # 收集当前所有内容块
        yield ToolResponse(
            content=_convert_to_text_block(
                list(msgs.values()),
            ),
            stream=True,
            is_last=False,
        )

        # 向调用方暴露中断信号
        if msg.metadata and msg.metadata.get("_is_interrupted", False):
            raise asyncio.CancelledError()

    # 从协程任务中取回最终结果
    if result:
        yield ToolResponse(
            content=[
                *_convert_to_text_block(
                    list(msgs.values()),
                ),
                TextBlock(
                    type="text",
                    text=json.dumps(
                        result[0].metadata,
                        indent=2,
                        ensure_ascii=False,
                    ),
                ),
            ],
            stream=True,
            is_last=True,
        )

    await browser_client.close()
