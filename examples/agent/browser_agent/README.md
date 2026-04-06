# Browser Agent 示例

这个示例演示了如何使用 AgentScope 的 `BrowserAgent` 完成网页自动化任务。`BrowserAgent` 通过 Model Context Protocol（MCP）连接由 Playwright 驱动的浏览器工具，从而实现网页导航、信息提取和自动化操作。

## 前置条件

- Python 3.10 或更高版本
- Node.js 和 npm（用于启动 MCP 服务）
- 阿里云 DashScope API Key

## 安装

### 安装 AgentScope

```bash
# 从源码安装
cd {PATH_TO_AGENTSCOPE}
pip install -e .
```

## 配置

### 1. 环境变量

设置 DashScope API Key：

```bash
export DASHSCOPE_API_KEY="your_dashscope_api_key_here"
```

你可以从 [阿里云 DashScope 控制台](https://dashscope.console.aliyun.com/) 获取 API Key。

### 2. 关于 PlayWright MCP 服务

在运行 Browser Agent 之前，可以先测试本地是否能正常启动 Playwright MCP 服务：

```bash
npx @playwright/mcp@latest
```

## 使用方式

### 基础示例

执行以下命令启动 Browser Agent：

```bash
cd examples/agent/browser_agent
python main.py
```
