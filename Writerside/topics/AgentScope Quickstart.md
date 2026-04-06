# AgentScope Quickstart

This page is a Writerside sample written for the current repository layout.
It uses the same `Writerside/topics/*.md` organization as your existing sample and combines Markdown with Writerside semantic markup.

## What you will do

- Install AgentScope
- Create a minimal example
- Preview a realistic quickstart page in Writerside

## Before you begin

Prepare the following:

- Python `3.10+`
- A virtual environment such as `venv` or `conda`
- A model API key if you want to run the example against a real provider

> This page is intentionally small so you can focus on the writing style and structure rather than a full documentation migration.

## Install AgentScope

<tabs>
    <tab title="PyPI">
        <p>Use the published package if you only want to try AgentScope:</p>
        <code-block lang="bash">
pip install agentscope
        </code-block>
    </tab>
    <tab title="Repository source">
        <p>Use editable installation if you are working inside this repository:</p>
        <code-block lang="bash">
pip install -e .
        </code-block>
    </tab>
</tabs>

## Run a minimal example

<procedure title="Create and run a sample agent" id="create-and-run-a-sample-agent">
    <step>
        <p>Create a file named <path>hello_agentscope.py</path>.</p>
    </step>
    <step>
        <p>Paste the following code:</p>
        <code-block lang="python">
from agentscope.agent import ReActAgent
from agentscope.model import ChatModel

model = ChatModel(
    model_name="gpt-4o-mini",
    api_key="YOUR_API_KEY",
)

agent = ReActAgent(
    name="assistant",
    sys_prompt="You are a concise assistant.",
    model=model,
)

response = agent("Introduce AgentScope in one sentence.")
print(response.text)
        </code-block>
    </step>
    <step>
        <p>Run the script:</p>
        <code-block lang="bash">
python hello_agentscope.py
        </code-block>
    </step>
</procedure>

<note>
    <p>The model configuration above is meant as documentation sample content. If you want this page to be runnable as-is, I should align it with one concrete example already present in this repository.</p>
</note>

## Why this is a good Writerside sample

- It keeps the page mostly in Markdown, which is easier to maintain
- It injects XML only for structures that benefit from semantic markup, such as tabs and procedures
- It fits the kind of quickstart page this project would realistically need

### Suggested next step {collapsible="true" default-state="expanded"}

If you want to continue, the natural next move is to convert one real page from `docs/tutorial/` into:

- a landing page
- one quickstart page
- one feature page

That gives you a representative Writeside skeleton for the rest of the migration.

<seealso>
    <category ref="wrs">
        <a href="https://www.jetbrains.com/help/writerside/markup-reference.html">Writerside markup reference</a>
        <a href="https://www.jetbrains.com/help/writerside/manage-table-of-contents.html">Manage the table of contents</a>
    </category>
</seealso>
