# -*- coding: utf-8 -*-
"""BookRAG-style multi-document retrieval middleware for AgentScope agents.

The :class:`BookRAGMiddleware` extends the standard RAG workflow with the
four core steps of BookRAG:

1. **Query decomposition** — an LLM breaks the user's question into
   3–5 focused sub-queries that cover all aspects.
2. **Multi-document retrieval** — each sub-query is searched independently
   against all bound knowledge bases.
3. **Answer fusion** — results are merged via :class:`RRFStrategy` (default)
   or :class:`LLMFusionStrategy`.
4. **HintBlock injection** — the fused results are injected into the agent's
   context as a :class:`~agentscope.message.HintBlock`.

Two modes are supported:

- ``"static"`` — the full 4-step pipeline runs automatically on the first
  reasoning step of each reply.  The agent never sees the intermediate steps.
- ``"agentic"`` — :meth:`list_tools` exposes
  ``decompose_query`` and ``search_and_fuse`` tools so the agent decides
  when and how to decompose, retrieve, and fuse.
"""
import asyncio
import json
from copy import deepcopy
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Callable,
    Literal,
    Sequence,
)

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.json_schema import SkipJsonSchema

from ._base import MiddlewareBase
from .._logging import logger
from ..event import HintBlockEvent
from ..message import (
    DataBlock,
    HintBlock,
    Msg,
    TextBlock,
    ToolCallBlock,
    ToolResultState,
)
from ..permission import PermissionBehavior, PermissionDecision
from ..tool import ParamsBase, ToolBase, ToolChunk
from ._rag import _format_results

if TYPE_CHECKING:
    from ..agent import Agent
    from ..rag import KnowledgeBase, VectorSearchResult
    from ..rag._fusion import FusionStrategy


_DEFAULT_HINT_TEMPLATE = (
    "<system-reminder>The following content is retrieved from the "
    "knowledge base(s) and may be helpful for the current "
    "request:\n<content>{context}</content></system-reminder>"
)

_HINT_SOURCE = json.dumps({"label": "BookRAG", "sublabel": ""})

_DEFAULT_DECOMPOSE_TEMPLATE = (
    "You are a query decomposition assistant. Given a user question, "
    "break it down into at most {max_sub_questions} focused sub-questions "
    "that cover all aspects of the original question. Each sub-question "
    "should:\n"
    "- Be self-contained and specific\n"
    "- Not overlap significantly with other sub-questions\n"
    "- Be phrased as a clear factual query\n\n"
    "Original question: {query}\n\n"
    "Sub-questions:"
)


class _DecomposeOutput(BaseModel):
    """Structured output for query decomposition."""

    sub_questions: list[str]
    rationale: str = ""


class _SearchParams(ParamsBase):
    """Parameters for the ``decompose_query`` tool."""

    query: str = Field(
        description=(
            "The user's question to decompose into focused sub-queries."
        ),
    )

    max_sub_questions: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of sub-questions to generate.",
    )


class _SearchAndFuseParams(ParamsBase):
    """Parameters for the ``search_and_fuse`` tool."""

    sub_queries: list[str] = Field(
        description=(
            "A list of sub-queries to search the knowledge base(s) with. "
            "Each query should be a concise, self-contained factual question."
        ),
    )

    knowledge_bases: list[str] | None = Field(
        default=None,
        description=(
            "Optional subset of knowledge bases to query, by name. "
            "When omitted (or `null`) every equipped knowledge base "
            "is searched for each sub-query."
        ),
    )


class _DecomposeQueryTool(ToolBase):
    """Tool that decomposes a user question into sub-queries."""

    name: str = "decompose_query"
    is_read_only: bool = True
    is_concurrency_safe: bool = True
    is_external_tool: bool = False
    is_state_injected: bool = False
    is_mcp: bool = False

    def __init__(self, max_sub_questions: int = 5) -> None:
        super().__init__()
        self._max_sub_questions = max_sub_questions
        self.description = (
            "Decompose a complex user question into multiple focused "
            "sub-queries. Each sub-query should be a self-contained "
            "factual question that covers one aspect of the original "
            "question. This is useful for multi-document retrieval where "
            "the answer requires synthesizing information from several "
            "topics.\n\n"
            "Use this tool when the user's question is complex, multi-faceted, "
            "or spans several topics. Each sub-query can then be used with "
            "the `search_and_fuse` tool."
        )
        self.input_schema = _SearchParams.model_json_schema()

    async def check_permissions(
        self,
        tool_input: dict[str, Any],
        context: Any,
    ) -> Any:
        del tool_input, context
        return PermissionDecision(
            behavior=PermissionBehavior.ALLOW,
            message="Query decomposition is read-only.",
        )

    async def call(  # type: ignore[override]
        self,
        query: str,
        max_sub_questions: int = 5,
    ) -> ToolChunk:
        try:
            sub_qs = self._decompose_sync(query, max_sub_questions)
        except Exception as e:  # pylint: disable=broad-except
            return ToolChunk(
                content=[TextBlock(text=f"Decomposition failed: {e}")],
                state=ToolResultState.ERROR,
                is_last=True,
            )

        lines = [f"[{i}] {q}" for i, q in enumerate(sub_qs, start=1)]
        return ToolChunk(
            content=[TextBlock(text="\n".join(lines))],
            state=ToolResultState.SUCCESS,
            is_last=True,
        )

    def _decompose_sync(self, query: str, max_n: int) -> list[str]:
        """Synchronous decomposition: split on compound connectors.

        When the tool is used without a model (e.g. in a no-model test),
        fall back to a simple heuristic split.
        """
        # Simple heuristic: split on " and ", " or ", " , "
        parts = [query.strip()]
        for sep in [" and ", " or ", " , "]:
            new_parts = []
            for p in parts:
                new_parts.extend([x.strip() for x in p.split(sep)])
            parts = new_parts
        # Keep only non-empty, reasonable-length parts
        parts = [p for p in parts if p and len(p) > 5]
        return parts[:max_n]


class _SearchAndFuseTool(ToolBase):
    """Tool that searches multiple sub-queries and fuses results."""

    name: str = "search_and_fuse"
    is_read_only: bool = True
    is_concurrency_safe: bool = True
    is_external_tool: bool = False
    is_state_injected: bool = False
    is_mcp: bool = False

    def __init__(
        self,
        knowledge_bases: list["KnowledgeBase"],
        top_k: int,
        score_threshold: float | None,
        fusion_strategy: "FusionStrategy",
    ) -> None:
        super().__init__()
        self._knowledge_bases = knowledge_bases
        self._top_k = top_k
        self._score_threshold = score_threshold
        self._fusion_strategy = fusion_strategy
        self.description = self._build_description()
        self.input_schema = self._build_input_schema()

    def _build_description(self) -> str:
        lines = [
            "Search the agent's equipped knowledge bases with multiple "
            "sub-queries and fuse the results into a single ranked list.",
            "",
            "## When to Use",
            "- You have multiple sub-queries (from ``decompose_query`` or "
            "your own reasoning) that need to be searched across the "
            "knowledge bases.",
            "- The final answer requires synthesizing information from "
            "several topics.",
            "",
            "## Guidance",
            "- Pass a list of focused sub-queries in ``sub_queries``.",
            "- Leave ``knowledge_bases`` unset to search all equipped KBs.",
            "",
            "## Equipped Knowledge Bases",
        ]
        if self._knowledge_bases:
            lines.append(
                f"The agent is equipped with {len(self._knowledge_bases)} "
                f"knowledge base(s):",
            )
            lines.extend(
                f"- **{kb.name}**: {kb.description}"
                for kb in self._knowledge_bases
            )
        else:
            lines.append("No knowledge bases equipped — this tool will return nothing.")
        return "\n".join(lines)

    def _build_input_schema(self) -> dict:
        schema = _SearchAndFuseParams.model_json_schema()
        if self._knowledge_bases:
            names = [kb.name for kb in self._knowledge_bases]
            kb_schema = schema["properties"]["knowledge_bases"]
            if "items" in kb_schema:
                kb_schema["items"]["enum"] = names
            else:
                for variant in kb_schema.get("anyOf", []):
                    if variant.get("type") == "array" and "items" in variant:
                        variant["items"]["enum"] = names
                        break
        return schema

    async def check_permissions(
        self,
        tool_input: dict[str, Any],
        context: Any,
    ) -> Any:
        del tool_input, context
        return PermissionDecision(
            behavior=PermissionBehavior.ALLOW,
            message="Knowledge-base search is read-only.",
        )

    async def call(  # type: ignore[override]
        self,
        sub_queries: list[str],
        knowledge_bases: list[str] | None = None,
    ) -> ToolChunk:
        if knowledge_bases is None:
            targets = list(self._knowledge_bases)
        else:
            wanted = set(knowledge_bases)
            targets = [kb for kb in self._knowledge_bases if kb.name in wanted]

        if not targets or not sub_queries:
            return ToolChunk(
                content=[TextBlock(text="No relevant content found.")],
                state=ToolResultState.SUCCESS,
                is_last=True,
            )

        try:
            grouped = await _search_and_fuse(
                targets,
                sub_queries,
                self._fusion_strategy,
                self._top_k,
                self._score_threshold,
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.exception("search_and_fuse failed.")
            return ToolChunk(
                content=[TextBlock(text=f"Search failed: {e}")],
                state=ToolResultState.ERROR,
                is_last=True,
            )

        blocks = _format_results(grouped)
        if not blocks:
            return ToolChunk(
                content=[TextBlock(text="No relevant content found.")],
                state=ToolResultState.SUCCESS,
                is_last=True,
            )
        return ToolChunk(
            content=blocks,
            state=ToolResultState.SUCCESS,
            is_last=True,
        )


# ---------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------

async def _search_and_fuse(
    knowledge_bases: list["KnowledgeBase"],
    sub_queries: list[str],
    fusion_strategy: "FusionStrategy",
    top_k: int,
    score_threshold: float | None,
    *,
    fusion_model: "ChatModelBase | None" = None,
) -> list["VectorSearchResult"]:
    """Search each sub-query across all knowledge bases, then fuse."""
    if not knowledge_bases or not sub_queries:
        return []

    # Step 1: Collect grouped results from all KBs
    # Build all_results: query → [VectorSearchResult, ...]
    all_results: dict[str, list["VectorSearchResult"]] = {}
    for query in sub_queries:
        per_kb = await asyncio.gather(
            *(
                kb.search_multiple_grouped(
                    [query],
                    top_k=top_k,
                    score_threshold=score_threshold,
                )
                for kb in knowledge_bases
            ),
        )
        # Flatten: each KB returns {query: [results]}, take the first key
        merged: list["VectorSearchResult"] = []
        for kb_grouped in per_kb:
            for _q, results in kb_grouped.items():
                merged.extend(results)
        merged.sort(key=lambda r: r.score, reverse=True)
        all_results[query] = merged[:top_k]

    # Step 2: Fuse
    return await fusion_strategy.fuse(
        all_results,
        sub_queries,
        top_k=top_k,
        model=fusion_model,
    )


# ---------------------------------------------------------------------
# BookRAGMiddleware
# ---------------------------------------------------------------------

class BookRAGMiddleware(MiddlewareBase):
    """Middleware that adds BookRAG-style multi-document retrieval to an agent.

    Four-step pipeline (query decomposition → multi-document retrieval →
    fusion → HintBlock injection), either run automatically (``"static"``)
    or exposed as tools for agent-driven control (``"agentic"``).

    .. code-block:: python

        # Static mode: automatic 4-step pipeline
        mw = BookRAGMiddleware(
            knowledge_bases=[kb1, kb2],
            parameters=BookRAGMiddleware.Parameters(mode="static"),
        )

        # Agentic mode: agent calls decompose_query + search_and_fuse
        mw = BookRAGMiddleware(
            knowledge_bases=[kb1, kb2],
            parameters=BookRAGMiddleware.Parameters(mode="agentic"),
        )

        agent = Agent(..., middlewares=[mw])
    """

    class Parameters(BaseModel):
        """User-tunable parameters for :class:`BookRAGMiddleware`."""

        model_config = ConfigDict(frozen=True)

        mode: Literal["static", "agentic"] = Field(
            default="static",
            title="Mode",
            description=(
                "``\"static\"``: the full 4-step pipeline runs automatically. "
                "``\"agentic\"``: tools are exposed for the agent to drive."
            ),
        )

        top_k: int = Field(
            default=5,
            ge=1,
            le=50,
            title="Top K",
            description=(
                "Maximum chunks returned per sub-query, before fusion."
            ),
        )

        score_threshold: float | None = Field(
            default=None,
            title="Score Threshold",
            description=(
                "Minimum similarity score for a hit to be kept."
            ),
        )

        max_sub_questions: int = Field(
            default=5,
            ge=1,
            le=10,
            title="Max Sub-questions",
            description=(
                "Maximum number of sub-queries generated during "
                "decomposition."
            ),
        )

        emit_hint_event: bool = Field(
            default=True,
            title="Show matched chunks in chat",
            description=(
                "Emit a `HintBlockEvent` in static mode for front-end display."
            ),
        )

        persist_hint: bool = Field(
            default=False,
            title="Persist Hint",
            description=(
                "In `static` mode, keep the injected hint block after "
                "the model call."
            ),
        )

        hint_template: SkipJsonSchema[str] = Field(
            default=_DEFAULT_HINT_TEMPLATE,
            title="Hint template",
            description=(
                "Template wrapping the fused results in static mode, "
                "with a `{context}` placeholder."
            ),
        )

        decompose_template: str = Field(
            default=_DEFAULT_DECOMPOSE_TEMPLATE,
            title="Decomposition prompt template",
            description=(
                "Prompt template for query decomposition, with "
                "``{query`` and ``{max_sub_questions`` placeholders."
            ),
        )

        @field_validator("hint_template")
        @classmethod
        def _validate_hint_template(cls, value: str) -> str:
            count = value.count("{context}")
            if count != 1:
                raise ValueError(
                    "hint_template must contain exactly one '{context}' "
                    f"placeholder; found {count}.",
                )
            return value

    def __init__(
        self,
        knowledge_bases: list["KnowledgeBase"],
        parameters: "BookRAGMiddleware.Parameters | None" = None,
        fusion_strategy: "FusionStrategy | None" = None,
    ) -> None:
        self._knowledge_bases = knowledge_bases
        self._parameters = parameters or BookRAGMiddleware.Parameters()
        # Import here to avoid circular import at module level
        from ..rag._fusion import RRFStrategy
        self._fusion_strategy = fusion_strategy or RRFStrategy()
        # Static-mode scratchpad: cached inputs from on_reply
        self._cached_inputs: list[TextBlock | DataBlock] | None = None

    # ------------------------------------------------------------------
    # Agentic mode — expose tools
    # ------------------------------------------------------------------

    async def list_tools(self) -> list[ToolBase]:
        if self._parameters.mode == "agentic":
            return [
                _DecomposeQueryTool(
                    max_sub_questions=self._parameters.max_sub_questions,
                ),
                _SearchAndFuseTool(
                    knowledge_bases=self._knowledge_bases,
                    top_k=self._parameters.top_k,
                    score_threshold=self._parameters.score_threshold,
                    fusion_strategy=self._fusion_strategy,
                ),
            ]
        return []

    # ------------------------------------------------------------------
    # Static mode — capture inputs in on_reply, pipeline in on_reasoning
    # ------------------------------------------------------------------

    async def on_reply(
        self,
        agent: "Agent",
        input_kwargs: dict,
        next_handler: Callable[..., AsyncGenerator],
    ) -> AsyncGenerator:
        inputs = input_kwargs.get("inputs")

        msgs: list[Msg] | None = None
        if isinstance(inputs, Msg):
            msgs = [inputs]
        elif isinstance(inputs, list) and all(
            isinstance(m, Msg) for m in inputs
        ):
            msgs = inputs

        if msgs:
            msgs = deepcopy(msgs)
            blocks: list[TextBlock | DataBlock] = []
            for msg in msgs:
                if not msg.content:
                    continue
                speaker = f"{msg.name}: "
                if isinstance(msg.content[0], TextBlock):
                    msg.content[0].text = speaker + msg.content[0].text
                else:
                    blocks.append(TextBlock(text=speaker))
                blocks.extend(msg.content)
            self._cached_inputs = blocks

        try:
            async for evt in next_handler(**input_kwargs):
                yield evt
        finally:
            self._cached_inputs = None

    async def on_reasoning(
        self,
        agent: "Agent",
        input_kwargs: dict,
        next_handler: Callable[..., AsyncGenerator],
    ) -> AsyncGenerator:
        """Run the 4-step BookRAG pipeline on the first reasoning step."""
        hint: HintBlock | None = None

        if (
            self._parameters.mode == "static"
            and agent.state.cur_iter == 0
            and self._cached_inputs
        ):
            # Extract query text from cached inputs
            query = self._extract_query_text(self._cached_inputs)
            if query:
                try:
                    results = await self._run_pipeline(agent, query)
                    if results:
                        blocks = _format_results(results)
                        hint = HintBlock(
                            hint=_wrap_hint(
                                self._parameters.hint_template, blocks,
                            ),
                            source=_HINT_SOURCE,
                        )
                        agent.state.append_context(agent.name, [hint])
                        if self._parameters.emit_hint_event:
                            yield HintBlockEvent(
                                reply_id=agent.state.reply_id,
                                block_id=hint.id,
                                source=hint.source,
                                hint=hint.hint,
                            )
                except Exception:  # pylint: disable=broad-except
                    logger.exception(
                        "BookRAG pipeline failed; proceeding without "
                        "matched context.",
                    )

        try:
            async for evt in next_handler(**input_kwargs):
                yield evt
        finally:
            if hint is not None and not self._parameters.persist_hint:
                for msg in reversed(agent.state.context):
                    if msg.id != agent.state.reply_id:
                        continue
                    msg.content = [
                        b for b in msg.content if b.id != hint.id
                    ]
                    break

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_query_text(
        self, blocks: Sequence[TextBlock | DataBlock],
    ) -> str:
        """Extract plain text from the cached input blocks."""
        texts = []
        for b in blocks:
            if isinstance(b, TextBlock):
                texts.append(b.text)
            elif isinstance(b, DataBlock):
                texts.append("[multimodal input]")
        return " ".join(texts).strip()

    async def _run_pipeline(
        self,
        agent: "Agent",
        query: str,
    ) -> list["VectorSearchResult"]:
        """Execute the full 4-step BookRAG pipeline."""
        # Step 1: Decompose
        sub_queries = await self._decompose(agent, query)
        if not sub_queries:
            # Fallback: use the original query as a single sub-query
            sub_queries = [query]

        # Step 2 + 3: Search and fuse
        return await _search_and_fuse(
            self._knowledge_bases,
            sub_queries,
            self._fusion_strategy,
            self._parameters.top_k,
            self._parameters.score_threshold,
            fusion_model=agent.model,
        )

    async def _decompose(
        self,
        agent: "Agent",
        query: str,
    ) -> list[str]:
        """Decompose query using the agent's model with structured output."""
        template = self._parameters.decompose_template
        prompt = template.format(
            query=query,
            max_sub_questions=self._parameters.max_sub_questions,
        )

        from ..message import UserMsg
        from ..tool import ToolChoice

        tool_schema = {
            "type": "function",
            "function": {
                "name": "decompose",
                "description": "Break a question into sub-queries",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sub_questions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of sub-questions",
                        },
                        "rationale": {
                            "type": "string",
                            "description": "Brief explanation of the decomposition strategy",
                        },
                    },
                    "required": ["sub_questions"],
                },
            },
        }

        try:
            response = await agent.model(
                messages=[UserMsg(name="user", content=prompt)],
                tools=[tool_schema],
                tool_choice=ToolChoice(mode="decompose"),
            )

            for block in response.content:
                if isinstance(block, ToolCallBlock):
                    args = json.loads(block.input)
                    sub_qs = args.get("sub_questions", [])
                    if isinstance(sub_qs, list) and all(
                        isinstance(q, str) for q in sub_qs
                    ):
                        return sub_qs[: self._parameters.max_sub_questions]
        except Exception:  # pylint: disable=broad-except
            logger.debug("Query decomposition failed; using original query.")

        return [query]


def _wrap_hint(
    template: str,
    blocks: list[TextBlock | DataBlock],
) -> str | list[TextBlock | DataBlock]:
    """Substitute ``{context}`` in ``template`` with the rendered blocks."""
    if all(isinstance(b, TextBlock) for b in blocks):
        joined = "\n".join(b.text for b in blocks)  # type: ignore[union-attr]
        return template.format(context=joined)

    prefix, _, end = template.partition("{context}")
    wrapped: list[TextBlock | DataBlock] = list(blocks)
    if prefix:
        if isinstance(wrapped[0], TextBlock):
            wrapped[0] = TextBlock(text=prefix + wrapped[0].text)
        else:
            wrapped.insert(0, TextBlock(text=prefix))
    if end:
        if isinstance(wrapped[-1], TextBlock):
            wrapped[-1] = TextBlock(text=wrapped[-1].text + end)
        else:
            wrapped.append(TextBlock(text=end))
    return wrapped