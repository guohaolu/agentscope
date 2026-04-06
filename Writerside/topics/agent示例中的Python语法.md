# agent示例中的Python语法

本文只讲 `examples/agent` 这些示例里实际出现过、并且最值得初学时掌握的 Python 语法点。

## 异步编程是这些示例的基础

很多示例都不是普通的同步函数，而是异步函数：

```python
async def main() -> None:
    ...
```

这里有三个要点：

- `async def` 表示定义异步函数
- `await` 表示等待一个异步操作完成
- `asyncio.run(main())` 表示启动整个异步程序

例如在 `react_agent/main.py`、`voice_agent/main.py`、`a2a_agent/main.py`、`browser_agent/main.py` 中，都采用了这种写法。

## 无限循环与交互式输入

很多示例都使用了下面这种模式：

```python
msg = None
while True:
    msg = await user(msg)
    if msg.get_text_content() == "exit":
        break
    msg = await agent(msg)
```

这段代码体现了几个基础语法：

- `while True` 表示持续循环
- `if ...: break` 表示满足条件后退出循环
- 变量 `msg` 会在每轮循环中被更新

这种写法很适合聊天机器人、命令行 Agent 和多轮对话。

## 类型标注

示例里大量使用了类型标注，例如：

```python
async def main() -> None:
```

```python
start_url_param: str = "https://www.google.com"
```

```python
) -> AsyncGenerator[Event, None]:
```

类型标注的价值不是“让 Python 才能运行”，而是：

- 增强代码可读性
- 让 IDE 更容易补全
- 帮助静态检查工具发现问题

在这些示例里，最常见的类型有：

- `str`
- `int`
- `dict`
- `list`
- `Any`
- `AsyncGenerator`
- `BaseModel`

## 类定义与继承

在 `browser_agent/main.py`、`meta_planner_agent/tool.py`、`deep_research_agent/deep_research_agent.py` 中都能看到类定义：

```python
class FinalResult(BaseModel):
    result: str
```

```python
class DeepResearchAgent(ReActAgent):
    ...
```

这说明两个常见用法：

- `class A(B)` 表示类继承
- 可以把公共行为放进父类，子类只扩展自己的特性

在 AgentScope 示例中，继承常用于“基于已有 Agent 做更复杂的定制”。

## Pydantic 模型

多个示例通过 `BaseModel` 定义结构化输出：

```python
class ResultModel(BaseModel):
    success: bool
    message: str
```

这类结构非常适合：

- 约束模型输出格式
- 让工具返回结果更稳定
- 让上层 Agent 更容易消费结果

你可以把它理解成“带校验能力的数据结构”。

## 异常处理

`browser_agent/main.py` 和 `realtime_voice_agent/run_server.py` 中都有类似写法：

```python
try:
    ...
except Exception as e:
    ...
finally:
    ...
```

这表示：

- `try` 中放可能出错的逻辑
- `except` 负责捕获异常
- `finally` 无论成功失败都会执行

在 Agent 场景里，`finally` 很常用来关闭 MCP 客户端、网络连接或其他资源。

## 命令行参数解析

`browser_agent/main.py` 使用了 `argparse`：

```python
parser = argparse.ArgumentParser(...)
parser.add_argument("--start-url", type=str, default="https://www.google.com")
```

这让脚本具备“命令行可配置”的能力。

适合学习的语法点有：

- 默认参数
- 命名参数
- 参数类型限制
- 帮助信息

## 环境变量读取

这些示例大量依赖 API Key，因此经常出现：

```python
os.getenv("DASHSCOPE_API_KEY")
```

或者：

```python
os.environ["DASHSCOPE_API_KEY"]
```

它们的区别可以简单理解为：

- `os.getenv(...)` 读取不到时通常返回 `None`
- `os.environ[...]` 读取不到时会直接报错

前者更温和，后者更严格。

## f-string

示例里经常用 f-string 组装字符串：

```python
print(f"起始 URL：{start_url}")
```

或者：

```python
f"{self.report_path_based}_detailed_report.md"
```

这是一种最常见、也最推荐的字符串插值方式。

## 生成器与异步生成器

在 `a2a_agent/setup_a2a_server.py` 和 `meta_planner_agent/tool.py` 中，你会看到：

```python
async def create_worker(...) -> AsyncGenerator[ToolResponse, None]:
    yield ToolResponse(...)
```

这里的重点是：

- `yield` 不是一次性返回最终结果
- 它是“边生成边返回”
- 异步生成器很适合做流式输出

这也是为什么这些示例能逐步把中间过程回传给上层 Agent 或前端。

## 学这些语法时的建议

- 不要孤立背语法，要和示例中的真实用途一起看
- 优先理解 `async/await`、类、类型标注、异常处理
- 等你理解 `main.py` 后，再去看自定义 Agent 类和工具函数

<seealso>
    <category ref="related">
        <a href="agent示例总览.md">agent示例总览</a>
        <a href="agent示例中的AgentScope功能.md">agent示例中的AgentScope功能</a>
    </category>
</seealso>
