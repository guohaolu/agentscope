# -*- coding: utf-8 -*-
"""Demonstrate the BookRAG multi-document retrieval pipeline with AgentScope.

This example shows both modes of :class:`~agentscope.middleware.BookRAGMiddleware`:

- **Static mode**: the full 4-step BookRAG pipeline (decompose → retrieve →
  fuse → inject) runs automatically on each new user turn.
- **Agentic mode**: the agent drives the process by calling ``decompose_query``
  and ``search_and_fuse`` tools at its own discretion.

The BookRAG pipeline:

1. **Query decomposition** — an LLM breaks the user's question into
   3–5 focused sub-queries.
2. **Multi-document retrieval** — each sub-query is searched independently
   against all bound knowledge bases.
3. **Answer fusion** — results are merged via :class:`RRFStrategy` (default)
   or :class:`LLMFusionStrategy`.
4. **HintBlock injection** — the fused results are injected into the agent's
   context so the final answer can synthesize across all documents.

Run with::

    DASHSCOPE_API_KEY=sk-... python examples/rag/bookrag_demo.py
"""
import asyncio
import os

from agentscope.agent import Agent
from agentscope.credential import DashScopeCredential
from agentscope.embedding import DashScopeEmbeddingModel
from agentscope.message import UserMsg
from agentscope.middleware import BookRAGMiddleware
from agentscope.model import DashScopeChatModel
from agentscope.rag import (
    ApproxTokenChunker,
    KnowledgeBase,
    LLMFusionStrategy,
    QdrantStore,
    RRFStrategy,
    TextParser,
)
from agentscope.tool import Toolkit


COLLECTION = "bookrag-demo"

# ------------------------------------------------------------------
# Sample knowledge base: a tech company's onboarding & release docs
# ------------------------------------------------------------------

KNOWLEDGE: dict[str, bytes] = {
    "onboarding-guide.md": (
        b"# Acme Corp Onboarding Guide\n\n"
        b"## First Week\n\n"
        b"- Day 1: IT setup (laptop, VPN, 2FA), badge issuance, "
        b"HR paperwork review.\n"
        b"- Day 2: Codebase orientation session with your buddy, "
        b"read the ADRs in `/arch`, set up the local dev environment.\n"
        b"- Day 3-5: Pair programming on a small bug, attend standups, "
        b"join the team's Slack channels.\n\n"
        b"## Equipment\n\n"
        b"Each new hire receives a USD 1,500 one-off stipend for home "
        b"office setup. Receipts must be submitted within 90 days.\n"
        b"MacBook Pro (16-inch) is standard; Linux workstations are "
        b"available on request.\n\n"
        b"## Culture\n\n"
        b"Acme follows async-first communication.  Meetings are "
        b"documentation-driven -- every meeting has a written agenda "
        b"and minutes posted to Notion within 24 hours.\n"
        b"Remote work is allowed up to 3 days per week.  Wednesdays "
        b"are mandatory in-office for cross-team syncs.\n",
    ),
    "release-notes-q1.md": (
        b"# AgentScope 3.0 Release Notes (Q1 2026)\n\n"
        b"## New Features\n\n"
        b"- ``agentscope.rag`` module: pluggable parser, chunker, "
        b"embedding, and vector-store backends.\n"
        b"- ``RAGMiddleware`` ships in two modes: ``static`` for "
        b"automatic injection, ``agentic`` for tool-driven search.\n"
        b"- ``BookRAGMiddleware`` adds multi-document retrieval with "
        b"query decomposition, RRF fusion, and LLM fusion strategies.\n"
        b"- Knowledge base service supports embedded and dedicated "
        b"worker deployments through a single message-bus channel.\n\n"
        b"## Performance\n\n"
        b"- Context compression now uses a 5-field summary schema "
        b"(task overview, current state, discoveries, next steps, "
        b"context to preserve).\n"
        b"- Tool call batching groups concurrent tool calls for "
        b"parallel execution when concurrency-safe.\n\n"
        b"## Breaking Changes\n\n"
        b"- ``Agent`` no longer has a base-class hierarchy; the single "
        b"``Agent`` class uses ``middlewares`` for all customization.\n"
        b"- ``Memory`` abstraction removed; conversation history lives "
        b"in ``AgentState.context``.\n",
    ),
    "api-guidelines.md": (
        b"# API Design Guidelines\n\n"
        b"## Endpoints\n\n"
        b"REST endpoints follow the pattern ``GET /api/v1/{resource} `` "
        b"with JSON request and response bodies.  Pagination uses "
        b"``limit`` and ``offset`` query parameters (not cursor-based).\n\n"
        b"All endpoints return a ``request_id`` field for tracing. "
        b"Error responses follow RFC 7807 (Problem Details) with "
        b"``type``, ``title``, ``status``, ``detail``, and ``instance``.\n\n"
        b"## Authentication\n\n"
        b"Bearer tokens via ``Authorization: Bearer <token>``.  "
        b"Tokens are issued by the identity service and expire after "
        b"15 minutes.  Refresh tokens are valid for 7 days.\n\n"
        b"## Rate Limiting\n\n"
        b"API calls are limited to 100 requests per minute per tenant. "
        b"Rate limit headers (``X-RateLimit-Limit``, "
        b"``X-RateLimit-Remaining``, ``X-RateLimit-Reset``) are "
        b"returned with every response.\n",
    ),
}


async def index_corpus(knowledge: KnowledgeBase) -> None:
    """Index the sample corpus into the knowledge base."""
    parser = TextParser()
    chunker = ApproxTokenChunker(chunk_size=256, overlap=32)
    for filename, file_bytes in KNOWLEDGE.items():
        sections = await parser.parse(file=file_bytes, filename=filename)
        chunks = await chunker.chunk(sections)
        await knowledge.insert_document(
            chunks,
            document_metadata={"filename": filename},
        )


def build_agent(
    name: str,
    *,
    chat_model: DashScopeChatModel,
    rag_mw: BookRAGMiddleware,
) -> Agent:
    return Agent(
        name=name,
        system_prompt=(
            "You are a knowledgeable assistant about Acme Corp's "
            "onboarding, tooling, and API guidelines. Use the retrieved "
            "context when available. If you don't know, say so clearly."
        ),
        model=chat_model,
        toolkit=Toolkit(),
        middlewares=[rag_mw],
    )


async def ask(agent: Agent, question: str) -> None:
    print(f"\n[{agent.name}] user: {question}")
    reply = await agent.reply(UserMsg(name="user", content=question))
    print(f"[{agent.name}] assistant: {reply.get_text_content()}")


async def main() -> None:
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("Set DASHSCOPE_API_KEY before running this example.")

    credential = DashScopeCredential(api_key=api_key)
    chat_model = DashScopeChatModel(
        credential=credential,
        model="qwen-plus",
        stream=False,
    )
    embedding_model = DashScopeEmbeddingModel(
        credential=credential,
        model="text-embedding-v4",
        dimensions=1024,
    )

    store = QdrantStore(location=":memory:")
    async with store:
        knowledge = KnowledgeBase(
            name="acme-handbook",
            description=(
                "Acme Corp onboarding guide, API design guidelines, and "
                "AgentScope 3.0 release notes."
            ),
            embedding_model=embedding_model,
            vector_store=store,
            collection=COLLECTION,
        )

        await index_corpus(knowledge)

        # ---- Mode 1: Static (automatic 4-step pipeline) ----
        static_mw = BookRAGMiddleware(
            knowledge_bases=[knowledge],
            parameters=BookRAGMiddleware.Parameters(
                mode="static",
                top_k=3,
                max_sub_questions=3,
                fusion_strategy=RRFStrategy(),
                emit_hint_event=False,
            ),
        )
        static_agent = build_agent(
            "bookrag-static-agent",
            chat_model=chat_model,
            rag_mw=static_mw,
        )
        await ask(
            static_agent,
            "What should I do in my first week at Acme, and what equipment "
            "stipend is available?",
        )

        # ---- Mode 2: Static with LLM fusion ----
        llm_mw = BookRAGMiddleware(
            knowledge_bases=[knowledge],
            parameters=BookRAGMiddleware.Parameters(
                mode="static",
                top_k=3,
                max_sub_questions=3,
                fusion_strategy=LLMFusionStrategy(),
                emit_hint_event=False,
            ),
        )
        llm_agent = build_agent(
            "bookrag-llm-fusion-agent",
            chat_model=chat_model,
            rag_mw=llm_mw,
        )
        await ask(
            llm_agent,
            "Compare the API design guidelines with the release notes — "
            "what's new in AgentScope 3.0, and how does it affect API "
            "design?",
        )

        # ---- Mode 3: Agentic (agent decides when to decompose & search) ----
        agentic_mw = BookRAGMiddleware(
            knowledge_bases=[knowledge],
            parameters=BookRAGMiddleware.Parameters(
                mode="agentic",
                top_k=3,
                max_sub_questions=4,
                fusion_strategy=RRFStrategy(),
            ),
        )
        agentic_agent = build_agent(
            "bookrag-agentic-agent",
            chat_model=chat_model,
            rag_mw=agentic_mw,
        )
        await ask(
            agentic_agent,
            "I'm a new engineer joining Acme next Monday. What should I "
            "prepare beforehand, and what should I expect in my first "
            "two weeks?",
        )


if __name__ == "__main__":
    asyncio.run(main())