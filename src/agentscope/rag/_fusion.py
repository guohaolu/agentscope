# -*- coding: utf-8 -*-
"""Fusion strategies for combining retrieval results across multiple queries.

BookRAG-style retrieval returns results from several sub-queries. These
strategies merge the per-query hits into a single ranked list.
"""
import json
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from ..message import TextBlock

if TYPE_CHECKING:
    from ..model import ChatModelBase
    from ._vdb import VectorSearchResult


class FusionStrategy(ABC):
    """Abstract base class for fusion strategies.

    A fusion strategy takes the results of multiple parallel retrievals
    (one per sub-query) and produces a single ranked list of chunks.
    """

    @abstractmethod
    async def fuse(
        self,
        all_results: dict[str, list["VectorSearchResult"]],
        queries: list[str],
        top_k: int,
        *,
        model: "ChatModelBase | None" = None,
    ) -> list["VectorSearchResult"]:
        """Fuse multiple retrieval results into a single ranked list.

        Args:
            all_results: Mapping from sub-query text to its retrieved
                chunks. Empty dict produces empty list.
            queries: The original sub-queries (ordered).
            top_k: Maximum number of results to return.
            model: Optional LLM model for LLM-based fusion strategies.

        Returns:
            At most ``top_k`` results ranked by relevance to the overall
            user request.
        """


# -------------------------------------------------------------------
# RRF — Reciprocal Rank Fusion (no API calls, purely mathematical)
# -------------------------------------------------------------------

class RRFStrategy(FusionStrategy):
    """Reciprocal Rank Fusion for merging multi-query retrieval results.

    For each sub-query, each chunk at rank ``r`` (1-based) gets score
    ``1 / (k + r)`` where ``k=60``. Scores from all queries are summed
    for each chunk, and the top-k chunks by total score are returned.
    Identical chunks (same ``document_id`` + ``chunk_index``) are
    deduplicated.
    """

    def __init__(self, k: int = 60) -> None:
        """Initialize with the RRF constant ``k``.

        Args:
            k: The RRF constant. Default 60 (Kitsure et al., 2010).
        """
        self.k = k

    async def fuse(
        self,
        all_results: dict[str, list["VectorSearchResult"]],
        queries: list[str],
        top_k: int,
        *,
        model: "ChatModelBase | None" = None,
    ) -> list["VectorSearchResult"]:
        if not all_results:
            return []

        scores: dict[tuple[str, int], float] = {}
        chunk_map: dict[tuple[str, int], "VectorSearchResult"] = {}

        for query_results in all_results.values():
            for rank_1based, result in enumerate(query_results, start=1):
                key = (result.document_id, result.chunk.chunk_index)
                score = 1.0 / (self.k + rank_1based)
                scores[key] = scores.get(key, 0.0) + score
                # Keep the result with the highest original similarity score
                if key not in chunk_map or result.score > chunk_map[key].score:
                    chunk_map[key] = result

        ranked = sorted(
            chunk_map.items(),
            key=lambda item: scores[item[0]],
            reverse=True,
        )
        return [r for _, r in ranked[:top_k]]


# -------------------------------------------------------------------
# LLM Fusion — let the model rank across all retrieved chunks
# -------------------------------------------------------------------

class LLMFusionStrategy(FusionStrategy):
    """LLM-based fusion: the model re-ranks all retrieved chunks by
    relevance to the original query.

    Prompts the model with a structured tool call request: given the
    grouped retrieval results, output the top-k chunks in order.
    Falls back to :class:`RRFStrategy` when the model call fails.
    """

    PROMPT_TEMPLATE = (
        "You are an evidence fusion assistant. Below are retrieval results "
        "from {n_queries} sub-queries:\n\n"
        "## Retrieval Results\n\n"
        "{grouped_results}\n\n"
        "Rank ALL chunks by overall relevance to the user's original question. "
        "Use the `rank_chunks` tool to return the top {top_k} most relevant "
        "chunks in order."
    )

    async def fuse(
        self,
        all_results: dict[str, list["VectorSearchResult"]],
        queries: list[str],
        top_k: int,
        *,
        model: "ChatModelBase | None" = None,
    ) -> list["VectorSearchResult"]:
        if not all_results or model is None:
            return await RRFStrategy().fuse(all_results, queries, top_k)

        # Build a flat numbered list of all chunks
        chunk_entries: list[dict] = []
        chunk_by_label: dict[int, "VectorSearchResult"] = {}
        label = 1
        for query, results in all_results.items():
            for result in results:
                text = result.chunk.content.text if isinstance(
                    result.chunk.content, TextBlock
                ) else "[multimodal]"
                chunk_entries.append({
                    "label": label,
                    "query": query,
                    "source": result.chunk.source,
                    "score": result.score,
                    "content": text,
                })
                chunk_by_label[label] = result
                label += 1

        grouped_text = "\n\n".join(
            f"### Sub-query: {e['query']}\n"
            f"- **Chunk [{e['label']}]** (source: {e['source']}, score: {e['score']:.3f})\n"
            f"  {e['content']}"
            for e in chunk_entries
        )

        prompt = self.PROMPT_TEMPLATE.format(
            n_queries=len(all_results),
            grouped_results=grouped_text,
            top_k=top_k,
        )

        from ..message import UserMsg
        from ..tool import ToolChoice

        tool_schema = {
            "type": "function",
            "function": {
                "name": "rank_chunks",
                "description": "Rank the retrieved chunks by relevance",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "top_chunks": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "rank": {"type": "integer", "description": "Rank position (1=most relevant)"},
                                    "chunk_id": {"type": "integer", "description": "The chunk label in brackets"},
                                    "reason": {"type": "string", "description": "Brief relevance explanation"},
                                },
                                "required": ["rank", "chunk_id", "reason"],
                            },
                        },
                    },
                    "required": ["top_chunks"],
                },
            },
        }

        try:
            response = await model(
                messages=[UserMsg(name="user", content=prompt)],
                tools=[tool_schema],
                tool_choice=ToolChoice(mode="rank_chunks"),
            )

            # Extract tool call from response content
            from ..message import ToolCallBlock
            tool_call = None
            for block in response.content:
                if isinstance(block, ToolCallBlock):
                    tool_call = block
                    break

            if tool_call is None:
                return await RRFStrategy().fuse(all_results, queries, top_k)

            args = json.loads(tool_call.input)
        except Exception:
            return await RRFStrategy().fuse(all_results, queries, top_k)

        ranked_ids = [
            c["chunk_id"] for c in args.get("top_chunks", [])
            if isinstance(c.get("chunk_id"), int) and c["chunk_id"] in chunk_by_label
        ]

        if not ranked_ids:
            return await RRFStrategy().fuse(all_results, queries, top_k)

        return [chunk_by_label[i] for i in ranked_ids[:top_k]]