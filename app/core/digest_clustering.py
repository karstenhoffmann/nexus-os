"""Clustering strategies for Digest generation.

Provides two strategies for grouping chunks into topics:
1. Hybrid: Embedding-based k-means clustering + LLM for naming/summaries
2. Pure LLM: LLM does clustering + naming in one call

Hybrid is recommended for cost-efficiency; Pure LLM for quality.
"""

from __future__ import annotations

import json
import logging
import math
import random
from dataclasses import dataclass, field
from typing import Any

from app.core.llm_providers import LLMProvider, ChatResponse
from app.core.prompts import get_prompt
from app.core.storage import DB

logger = logging.getLogger(__name__)

# Default number of topic clusters
DEFAULT_NUM_CLUSTERS = 7
MIN_CLUSTER_SIZE = 3  # Minimum chunks per cluster


@dataclass
class TopicCluster:
    """A cluster of related chunks forming a topic."""

    topic_index: int
    topic_name: str  # LLM-generated topic name
    summary: str  # LLM-generated summary
    chunk_ids: list[int] = field(default_factory=list)
    key_points: list[str] = field(default_factory=list)

    @property
    def chunk_count(self) -> int:
        return len(self.chunk_ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic_index": self.topic_index,
            "topic_name": self.topic_name,
            "summary": self.summary,
            "chunk_ids": self.chunk_ids,
            "key_points": self.key_points,
            "chunk_count": self.chunk_count,
        }


@dataclass
class ClusteringResult:
    """Result of clustering operation."""

    strategy: str  # 'hybrid' or 'pure_llm'
    clusters: list[TopicCluster]
    tokens_input: int = 0
    tokens_output: int = 0
    cost_usd: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "num_clusters": len(self.clusters),
            "clusters": [c.to_dict() for c in self.clusters],
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "cost_usd": round(self.cost_usd, 6),
        }


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def _kmeans_cluster(
    embeddings: list[list[float]],
    k: int,
    max_iterations: int = 50,
) -> list[int]:
    """Simple k-means clustering for embeddings.

    Args:
        embeddings: List of embedding vectors
        k: Number of clusters
        max_iterations: Max iterations for convergence

    Returns:
        List of cluster assignments (0 to k-1) for each embedding
    """
    n = len(embeddings)
    if n == 0:
        return []
    if n <= k:
        return list(range(n))

    dim = len(embeddings[0])

    # Initialize centroids using k-means++ style
    centroid_indices = [random.randint(0, n - 1)]
    for _ in range(1, k):
        # Find point farthest from existing centroids
        max_dist = -1.0
        max_idx = 0
        for i, emb in enumerate(embeddings):
            if i in centroid_indices:
                continue
            min_dist = min(
                1 - _cosine_similarity(emb, embeddings[c])
                for c in centroid_indices
            )
            if min_dist > max_dist:
                max_dist = min_dist
                max_idx = i
        centroid_indices.append(max_idx)

    centroids = [embeddings[i][:] for i in centroid_indices]
    assignments = [0] * n

    for iteration in range(max_iterations):
        # Assign points to nearest centroid
        new_assignments = []
        for emb in embeddings:
            best_cluster = 0
            best_sim = -2.0
            for c_idx, centroid in enumerate(centroids):
                sim = _cosine_similarity(emb, centroid)
                if sim > best_sim:
                    best_sim = sim
                    best_cluster = c_idx
            new_assignments.append(best_cluster)

        # Check for convergence
        if new_assignments == assignments:
            break
        assignments = new_assignments

        # Update centroids
        for c_idx in range(k):
            cluster_points = [
                embeddings[i] for i, a in enumerate(assignments) if a == c_idx
            ]
            if cluster_points:
                new_centroid = [0.0] * dim
                for point in cluster_points:
                    for d in range(dim):
                        new_centroid[d] += point[d]
                for d in range(dim):
                    new_centroid[d] /= len(cluster_points)
                centroids[c_idx] = new_centroid

    return assignments


async def hybrid_cluster(
    chunks: list[dict[str, Any]],
    llm: LLMProvider,
    db: DB,
    num_clusters: int = DEFAULT_NUM_CLUSTERS,
) -> ClusteringResult:
    """Cluster chunks using embeddings + LLM for naming.

    Strategy:
    1. Use k-means on embeddings to group similar chunks
    2. For each cluster, use LLM to generate topic name and summary

    Args:
        chunks: List of chunk dicts with 'id', 'chunk_text', 'embedding', etc.
        llm: LLM provider for naming/summarizing
        db: Database instance for prompt registry
        num_clusters: Target number of clusters

    Returns:
        ClusteringResult with named topic clusters
    """
    if not chunks:
        return ClusteringResult(strategy="hybrid", clusters=[])

    # Get prompt from registry
    prompt_template = get_prompt("topic_naming_hybrid", db)
    if prompt_template is None:
        raise ValueError("Prompt 'topic_naming_hybrid' not found in registry")

    # Extract embeddings
    embeddings = [c["embedding"] for c in chunks]

    # Adjust k if we have fewer chunks
    k = min(num_clusters, len(chunks) // MIN_CLUSTER_SIZE)
    k = max(k, 1)

    logger.info(f"Clustering {len(chunks)} chunks into {k} clusters")

    # Run k-means
    assignments = _kmeans_cluster(embeddings, k)

    # Group chunks by cluster
    cluster_chunks_map: dict[int, list[dict[str, Any]]] = {}
    for chunk, cluster_id in zip(chunks, assignments):
        if cluster_id not in cluster_chunks_map:
            cluster_chunks_map[cluster_id] = []
        cluster_chunks_map[cluster_id].append(chunk)

    # Generate topic names and summaries for each cluster
    clusters: list[TopicCluster] = []
    total_input = 0
    total_output = 0
    total_cost = 0.0

    for cluster_id in sorted(cluster_chunks_map.keys()):
        chunk_list = cluster_chunks_map[cluster_id]

        # Skip very small clusters
        if len(chunk_list) < MIN_CLUSTER_SIZE // 2:
            continue

        # Prepare sample texts for LLM (limit to avoid token overflow)
        sample_texts = []
        for c in chunk_list[:10]:  # Max 10 samples per cluster
            text = c["chunk_text"][:500]  # Truncate long chunks
            title = c.get("title", "")
            sample_texts.append(f"[{title}] {text}")

        samples_joined = "\n---\n".join(sample_texts)

        # Format prompt with variables
        prompt = prompt_template.template.format(samples_joined=samples_joined)

        try:
            response = await llm.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=prompt_template.temperature,
                max_tokens=prompt_template.max_tokens,
            )

            total_input += response.tokens_input
            total_output += response.tokens_output
            total_cost += llm.estimate_cost(response.tokens_input, response.tokens_output)

            # Parse JSON response
            content = response.content.strip()
            # Handle markdown code blocks
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()

            try:
                data = json.loads(content)
                topic_name = data.get("topic_name", f"Thema {cluster_id + 1}")
                summary = data.get("summary", "")
                key_points = data.get("key_points", [])
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse LLM response for cluster {cluster_id}")
                topic_name = f"Thema {cluster_id + 1}"
                summary = ""
                key_points = []

            clusters.append(TopicCluster(
                topic_index=len(clusters),
                topic_name=topic_name,
                summary=summary,
                chunk_ids=[c["id"] for c in chunk_list],
                key_points=key_points,
            ))

        except Exception as e:
            logger.error(f"LLM error for cluster {cluster_id}: {e}")
            # Create cluster with default name on error
            clusters.append(TopicCluster(
                topic_index=len(clusters),
                topic_name=f"Thema {cluster_id + 1}",
                summary="",
                chunk_ids=[c["id"] for c in chunk_list],
            ))

    return ClusteringResult(
        strategy="hybrid",
        clusters=clusters,
        tokens_input=total_input,
        tokens_output=total_output,
        cost_usd=total_cost,
    )


async def pure_llm_cluster(
    chunks: list[dict[str, Any]],
    llm: LLMProvider,
    db: DB,
    num_clusters: int = DEFAULT_NUM_CLUSTERS,
) -> ClusteringResult:
    """Cluster chunks using pure LLM analysis.

    Strategy:
    1. Send chunk summaries to LLM
    2. LLM identifies themes and assigns chunks to clusters
    3. LLM provides names and summaries for each cluster

    Args:
        chunks: List of chunk dicts with 'id', 'chunk_text', etc.
        llm: LLM provider
        db: Database instance for prompt registry
        num_clusters: Target number of clusters

    Returns:
        ClusteringResult with named topic clusters
    """
    if not chunks:
        return ClusteringResult(strategy="pure_llm", clusters=[])

    # Get prompt from registry
    prompt_template = get_prompt("clustering_pure_llm", db)
    if prompt_template is None:
        raise ValueError("Prompt 'clustering_pure_llm' not found in registry")

    # Prepare chunk summaries for LLM
    chunk_summaries = []
    for i, c in enumerate(chunks[:100]):  # Limit to 100 chunks for context
        text = c["chunk_text"][:300]
        title = c.get("title", "Unbekannt")
        chunk_summaries.append(f"[{i}] ({title}) {text}")

    summaries_text = "\n".join(chunk_summaries)

    # Format prompt with variables
    prompt = prompt_template.template.format(
        chunk_count=len(chunk_summaries),
        num_clusters=num_clusters,
        summaries_text=summaries_text,
    )

    try:
        response = await llm.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=prompt_template.temperature,
            max_tokens=prompt_template.max_tokens,
        )

        # Parse response
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()

        data = json.loads(content)
        llm_clusters = data.get("clusters", [])

        clusters = []
        for i, lc in enumerate(llm_clusters):
            # Map chunk indices back to chunk IDs
            indices = lc.get("chunk_indices", [])
            chunk_ids = [
                chunks[idx]["id"]
                for idx in indices
                if idx < len(chunks)
            ]

            clusters.append(TopicCluster(
                topic_index=i,
                topic_name=lc.get("topic_name", f"Thema {i + 1}"),
                summary=lc.get("summary", ""),
                chunk_ids=chunk_ids,
                key_points=lc.get("key_points", []),
            ))

        return ClusteringResult(
            strategy="pure_llm",
            clusters=clusters,
            tokens_input=response.tokens_input,
            tokens_output=response.tokens_output,
            cost_usd=llm.estimate_cost(response.tokens_input, response.tokens_output),
        )

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM clustering response: {e}")
        # Fallback: single cluster with all chunks
        return ClusteringResult(
            strategy="pure_llm",
            clusters=[TopicCluster(
                topic_index=0,
                topic_name="Alle Inhalte",
                summary="Automatische Gruppierung fehlgeschlagen",
                chunk_ids=[c["id"] for c in chunks],
            )],
        )

    except Exception as e:
        logger.error(f"Pure LLM clustering failed: {e}")
        raise


async def cluster_chunks(
    chunks: list[dict[str, Any]],
    llm: LLMProvider,
    db: DB,
    strategy: str = "hybrid",
    num_clusters: int = DEFAULT_NUM_CLUSTERS,
) -> ClusteringResult:
    """Cluster chunks into topics using the specified strategy.

    Args:
        chunks: List of chunk dicts. For hybrid, must include 'embedding'.
        llm: LLM provider for naming/summarizing
        db: Database instance for prompt registry
        strategy: 'hybrid' or 'pure_llm'
        num_clusters: Target number of clusters

    Returns:
        ClusteringResult with topic clusters
    """
    if strategy == "hybrid":
        # Verify embeddings are present
        if chunks and "embedding" not in chunks[0]:
            raise ValueError("Hybrid strategy requires chunks with embeddings")
        return await hybrid_cluster(chunks, llm, db, num_clusters)
    elif strategy == "pure_llm":
        return await pure_llm_cluster(chunks, llm, db, num_clusters)
    else:
        raise ValueError(f"Unknown clustering strategy: {strategy}")
