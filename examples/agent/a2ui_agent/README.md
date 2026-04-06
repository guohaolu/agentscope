# AgentScope 中的 A2UI

[A2UI（Agent-to-Agent UI）](https://github.com/google/A2UI) 是一种允许 Agent 向客户端发送流式、可交互用户界面的协议。它使 LLM 能够生成与平台无关的声明式 UI 定义，客户端再使用原生组件逐步渲染这些界面。

这个示例演示了如何在 AgentScope 中把 A2UI 集成到 ReAct Agent 中。实现方式基于 A2UI 官方示例，并适配到了 AgentScope 的 Agent 框架里。

具体来说，本示例主要做了两件事：

1. **使用 AgentScope 重写 Agent 部分**：A2UI 官方示例中的 Agent 逻辑在这里被改写为 AgentScope 的 `ReActAgent`，这样对 AgentScope 用户来说会更熟悉，也更容易与现有能力集成。
2. **通过 Skills 逐步暴露 Schema 和模板**：为了帮助 Agent 学会生成符合 A2UI 规范的界面，我们使用 AgentScope 的 Skill 系统逐步暴露 A2UI 的 schema 和 UI 模板。Agent 可以通过 `A2UI_response_generator` 技能动态加载这些资源，从而理解组件定义，并参考示例 UI 结构生成结果。

## 关于外部依赖

本示例中的以下目录包含来自 [Google A2UI 仓库](https://github.com/google/A2UI) 的内容：

- `samples/client/`：A2UI 客户端示例应用

**NPM 包状态**：截至目前，A2UI 客户端库（`@a2ui/lit` 和 `@a2ui/angular`）**尚未发布到 NPM**。根据 [A2UI 官方客户端配置文档](https://a2ui.org/guides/client-setup/#renderers) 的说明，Lit 客户端库还没有正式发布到 NPM。

因此，这些依赖当前仍通过本地路径的方式被包含在本示例仓库中，例如 `package.json` 里的 `"@a2ui/lit": "file:../../../../renderers/lit"`。这与 [A2UI 官方仓库](https://github.com/google/A2UI) 的做法一致，官方仓库中的 renderers 和 samples 之间也是通过本地路径互相引用的。此外，`renderers/lit/package.json` 中的 `copy-spec` 任务也会在构建过程中从本地 `specification/` 目录复制文件。

**后续计划**：等这些库正式发布到 NPM 后，我们计划逐步切换到官方 NPM 包，并移除当前仓库里这些本地拷贝目录。

## 快速开始

先把 `a2ui` 和 `agentscope` 克隆到同一级目录：

```bash
git clone https://github.com/google/A2UI.git
git clone -b main https://github.com/agentscope-ai/agentscope.git
# 将 renderers 和 specification 目录复制到 AgentScope/examples/agent/a2ui_agent
cp -r A2UI/renderers AgentScope/examples/agent/a2ui_agent
cp -r A2UI/specification AgentScope/examples/agent/a2ui_agent
```

然后进入客户端目录，启动 restaurant finder 演示：

```bash
cd AgentScope/examples/agent/a2ui_agent/samples/client/lit
npm run demo:restaurant
```

这个命令会完成以下事情：

- 安装依赖并构建 A2UI renderer
- 启动 restaurant finder 对应的 A2A 服务端，也就是 AgentScope Agent
- 在浏览器中打开客户端应用

> 说明：
> - 这个示例基于 DashScope 对话模型，请在运行前先设置 `DASHSCOPE_API_KEY`。
> - 如果你使用的是 Qwen 系列模型，推荐使用 `qwen3-max`，这样生成符合 A2UI 规范的 JSON 响应时效果通常更稳定。
> - 生成 UI JSON 响应通常需要一定时间，一般在 1 到 2 分钟之间，因为 Agent 需要处理 schema、示例以及较复杂的 UI 结构。
> - 当前演示使用的是标准 A2UI catalog。自定义 catalog 和 inline catalog 仍在开发中。

## 路线图

AgentScope 接下来在 A2UI 方向上的重点，会放在持续优化 **How Agents Work**。目标工作流大致如下：

```text
用户输入 -> Agent 逻辑 -> LLM -> A2UI JSON
```

接下来的优化重点主要包括：

- **Agent 逻辑**：改进 Agent 对输入的处理方式，以及生成 A2UI JSON 消息时的编排能力
- **处理来自客户端的用户交互**：让 Agent 能够把按钮点击、表单提交等客户端交互当作新的用户输入处理，从而形成连续的交互闭环

**当前方案**：这个示例里基于 Skill 的实现方式，是我们迈向这一目标的第一步。通过 Skill 系统渐进式暴露 A2UI schema 和模板，Agent 可以逐步学会生成合规 UI 结构。后续会继续简化这个流程，让开发者更容易构建具备 A2UI 能力的 Agent。

**Agent 逻辑的下一步优化方向**

- **Agent Skills 改进**：
  - 支持灵活追加 schema，让开发者无需修改核心 Skill 代码也能扩展 schema
  - 将 schema 和 examples 拆分到独立目录中，提升可维护性和结构清晰度

- **针对 A2UI 长上下文的 Memory 管理**：
  - 当前 A2UI 消息通常非常长，会导致多轮交互效率较低，并影响 Agent 回复质量。后续会重点改进长上下文管理策略。

- **持续跟进 A2UI 协议更新**：
  - 我们会跟进 A2UI 协议演进并同步适配，例如计划支持 A2UI v0.9 引入的流式 UI JSON。
