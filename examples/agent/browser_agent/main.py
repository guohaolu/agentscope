# -*- coding: utf-8 -*-
# pylint: disable=too-many-lines
"""Browser Agent 示例的主入口。"""
import asyncio
import os
import sys
import argparse
import traceback
from pydantic import BaseModel, Field
from browser_agent import BrowserAgent
from agentscope.formatter import DashScopeChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.model import DashScopeChatModel
from agentscope.tool import Toolkit
from agentscope.mcp import StdIOStatefulClient
from agentscope.agent import UserAgent


class FinalResult(BaseModel):
    """用于结构化输出的结果模型。"""

    result: str = Field(
        description="The final result to the initial user query",
    )


async def main(
    start_url_param: str = "https://www.google.com",
    max_iters_param: int = 50,
) -> None:
    """Browser Agent 示例主函数。"""
    # 使用 MCP 服务提供的浏览器工具初始化工具箱
    toolkit = Toolkit()
    browser_client = StdIOStatefulClient(
        name="playwright-mcp",
        command="npx",
        args=["@playwright/mcp@latest"],
    )

    try:
        # 连接浏览器客户端
        await browser_client.connect()
        await toolkit.register_mcp_client(browser_client)

        agent = BrowserAgent(
            name="Browser-Use Agent",
            model=DashScopeChatModel(
                api_key=os.environ.get("DASHSCOPE_API_KEY"),
                model_name="qwen3-max",
                stream=False,
            ),
            formatter=DashScopeChatFormatter(),
            memory=InMemoryMemory(),
            toolkit=toolkit,
            max_iters=max_iters_param,
            start_url=start_url_param,
        )
        user = UserAgent("User")

        msg = None
        while True:
            msg = await user(msg)
            if msg.get_text_content() == "exit":
                break
            msg = await agent(msg, structured_model=FinalResult)
            await agent.memory.clear()

    except Exception as e:
        traceback.print_exc()
        print(f"发生错误：{e}")
        print("正在清理浏览器客户端资源...")
    finally:
        # 无论执行成功还是失败，都确保浏览器客户端被关闭
        try:
            await browser_client.close()
            print("浏览器客户端已成功关闭。")
        except Exception as cleanup_error:
            print(f"关闭浏览器客户端时出错：{cleanup_error}")


def parse_arguments() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="支持自定义参数的 Browser Agent 示例",
    )
    parser.add_argument(
        "--start-url",
        type=str,
        default="https://www.google.com",
        help=(
            "Browser Agent 的起始网址 "
            "（默认值：https://www.google.com）"
        ),
    )
    parser.add_argument(
        "--max-iters",
        type=int,
        default=50,
        help="最大迭代次数（默认值：50）",
    )
    return parser.parse_args()


if __name__ == "__main__":
    print("正在启动 Browser Agent 示例...")
    print(
        "该示例将使用 "
        "playwright-mcp（https://github.com/microsoft/playwright-mcp）。"
        "请先通过 `npx @playwright/mcp@latest` 确认 MCP 服务可用。",
    )
    print("\n使用示例：")
    print("  python main.py                           # 使用默认参数启动")
    print("  python main.py --start-url https://example.com --max-iters 100")
    print("  python main.py --help                   # 查看全部参数说明")
    print()

    # 解析命令行参数
    args = parse_arguments()

    # 读取参数
    start_url = args.start_url
    max_iters = args.max_iters

    # 校验参数
    if max_iters <= 0:
        print("错误：max-iters 必须为正整数")
        sys.exit(1)

    if not start_url.startswith(("http://", "https://")):
        print("错误：start-url 必须是合法的 HTTP/HTTPS URL")
        sys.exit(1)

    print(f"起始 URL：{start_url}")
    print(f"最大迭代次数：{max_iters}")

    asyncio.run(main(start_url, max_iters))
