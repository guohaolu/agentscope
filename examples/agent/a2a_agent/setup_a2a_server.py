# -*- coding: utf-8 -*-
"""启动一个由 ReAct Agent 提供服务的 A2A 服务端，用于处理输入请求。"""
import os
import uuid
from typing import AsyncGenerator, Any

from agent_card import agent_card

from a2a.server.events import Event
from a2a.types import (
    TaskStatus,
    TaskState,
    MessageSendParams,
    TaskStatusUpdateEvent,
)
from a2a.server.apps import A2AStarletteApplication

from agentscope.agent import ReActAgent
from agentscope.formatter import DashScopeChatFormatter, A2AChatFormatter
from agentscope.model import DashScopeChatModel
from agentscope.pipeline import stream_printing_messages
from agentscope.session import JSONSession
from agentscope.tool import (
    Toolkit,
    execute_python_code,
    execute_shell_command,
    view_text_file,
)


class SimpleStreamHandler:
    """一个简单的请求处理器，使用 ReAct Agent 处理输入请求。"""

    async def on_message_send_stream(
        self,  # pylint: disable=unused-argument
        params: MessageSendParams,
        *args: Any,
        **kwargs: Any,
    ) -> AsyncGenerator[Event, None]:
        """处理 Agent 发起的 message_send 请求。

        Args:
            params (`MessageSendParams`):
                发送消息时使用的参数。

        Returns:
            `AsyncGenerator[Event, None]`:
                一个异步生成器，用于持续产出任务状态更新事件。
        """
        task_id = params.message.task_id or uuid.uuid4().hex
        context_id = params.message.context_id or "default-context"
        # ============ Agent 逻辑 ============

        # 注册工具函数
        toolkit = Toolkit()
        toolkit.register_tool_function(execute_python_code)
        toolkit.register_tool_function(execute_shell_command)
        toolkit.register_tool_function(view_text_file)

        # 创建 Agent 实例
        agent = ReActAgent(
            name="Friday",
            sys_prompt="You're a helpful assistant named Friday.",
            model=DashScopeChatModel(
                model_name="qwen-max",
                api_key=os.getenv("DASHSCOPE_API_KEY"),
            ),
            formatter=DashScopeChatFormatter(),
            toolkit=toolkit,
        )

        session = JSONSession(save_dir="./sessions")
        await session.load_session_state(
            session_id="test-a2a-agent",
            agent=agent,
        )

        # 将 A2A 消息转换为 AgentScope 的 Msg 对象
        formatter = A2AChatFormatter()
        as_msg = await formatter.format_a2a_message(
            name="Friday",
            message=params.message,
        )

        yield TaskStatusUpdateEvent(
            task_id=task_id,
            context_id=context_id,
            status=TaskStatus(state=TaskState.working),
            final=False,
        )

        async for msg, last in stream_printing_messages(
            agents=[agent],
            coroutine_task=agent(as_msg),
        ):
            # A2A 的流式响应是一条完整的 Message 对象，
            # 而不是逐步累积的文本片段
            if last:
                a2a_message = await formatter.format([msg])

                yield TaskStatusUpdateEvent(
                    task_id=task_id,
                    context_id=context_id,
                    status=TaskStatus(
                        state=TaskState.working,
                        message=a2a_message,
                    ),
                    final=False,
                )

        # 结束任务
        yield TaskStatusUpdateEvent(
            task_id=task_id,
            context_id=context_id,
            status=TaskStatus(state=TaskState.completed),
            final=True,
        )

        await session.save_session_state(
            session_id="test-a2a-agent",
            agent=agent,
        )


handler = SimpleStreamHandler()
app_instance = A2AStarletteApplication(
    agent_card,
    handler,
)
app = app_instance.build()
