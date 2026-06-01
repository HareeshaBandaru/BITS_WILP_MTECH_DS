"""retrieval.py — semantic + keyword search for Verizon policy documents

Provides grounding for hallucination detection by retrieving relevant docs
and computing similarity scores between LLM responses and policies.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
    HAS_SENTENCE_TRANSFORMERS = True
except Exception:
    HAS_SENTENCE_TRANSFORMERS = False

try:
    from verizon_knowledge_base import VERIZON_LEGAL_DOCS  # type: ignore
except Exception:
    VERIZON_LEGAL_DOCS = {}


class RetrieverBase:
    """Base retriever interface."""

    def retrieve(self, query: str, top_k: int = 3) -> List[Tuple[str, float, str]]:
        """Retrieve top-k docs. Returns list of (doc_key, score, doc_text)."""
        raise NotImplementedError


class KeywordRetriever(RetrieverBase):
    """Simple BM25-style keyword overlap retrieval."""

    def __init__(self, docs: Dict[str, str]):
        self.docs = docs
        self.inverted_index = self._build_index()

    def _build_index(self) -> Dict[str, List[str]]:
        """Build token → doc_key mapping."""
        idx = {}
        for doc_key, doc_text in self.docs.items():
            tokens = set(re.findall(r"\b\w+\b", doc_text.lower()))
            for token in tokens:
                if token not in idx:
                    idx[token] = []
                idx[token].append(doc_key)
        return idx

    def retrieve(self, query: str, top_k: int = 3) -> List[Tuple[str, float, str]]:
        query_tokens = set(re.findall(r"\b\w+\b", query.lower()))
        scores: Dict[str, int] = {}
        for token in query_tokens:
            if token in self.inverted_index:
                for doc_key in self.inverted_index[token]:
                    scores[doc_key] = scores.get(doc_key, 0) + 1

        ranked = sorted(scores.items(), key=lambda x: -x[1])[:top_k]
        results = []
        for doc_key, score in ranked:
            doc_text = self.docs.get(doc_key, "")
            norm_score = score / max(len(query_tokens), 1)
            results.append((doc_key, norm_score, doc_text))
        return results


class SemanticRetriever(RetrieverBase):
    """Embedding-based semantic search using sentence-transformers."""

    def __init__(self, docs: Dict[str, str], model_name: str = "all-MiniLM-L6-v2"):
        self.docs = docs
        self.model = None
        self.doc_embeddings = {}
        if HAS_SENTENCE_TRANSFORMERS:
            try:
                self.model = SentenceTransformer(model_name)
                self._encode_docs()
            except Exception as e:
                print(f"Failed to load semantic model: {e}")

    def _encode_docs(self):
        if not self.model:
            return
        for doc_key, doc_text in self.docs.items():
            try:
                emb = self.model.encode(doc_text, convert_to_tensor=False)
                self.doc_embeddings[doc_key] = emb
            except Exception:
                pass

    def retrieve(self, query: str, top_k: int = 3) -> List[Tuple[str, float, str]]:
        if not self.model or not self.doc_embeddings:
            return []

        try:
            query_emb = self.model.encode(query, convert_to_tensor=False)
            scores = {}
            for doc_key, doc_emb in self.doc_embeddings.items():
                # Cosine similarity (simplified)
                dot = sum(q * d for q, d in zip(query_emb, doc_emb))
                scores[doc_key] = dot

            ranked = sorted(scores.items(), key=lambda x: -x[1])[:top_k]
            results = []
            for doc_key, score in ranked:
                doc_text = self.docs.get(doc_key, "")
                norm_score = max(0, min(1, (score + 1) / 2))  # Normalize to [0, 1]
                results.append((doc_key, norm_score, doc_text))
            return results
        except Exception as e:
            print(f"Semantic retrieval failed: {e}")
            return []


class HybridRetriever(RetrieverBase):
    """Combines semantic + keyword retrieval."""

    def __init__(self, docs: Dict[str, str]):
        self.semantic = SemanticRetriever(docs) if HAS_SENTENCE_TRANSFORMERS else None
        self.keyword = KeywordRetriever(docs)

    def retrieve(self, query: str, top_k: int = 3) -> List[Tuple[str, float, str]]:
        results_map = {}

        # Semantic results
        if self.semantic and self.semantic.model:
            for doc_key, score, doc_text in self.semantic.retrieve(query, top_k=top_k):
                results_map[doc_key] = {"text": doc_text, "scores": [score, 0]}

        # Keyword results
        for doc_key, score, doc_text in self.keyword.retrieve(query, top_k=top_k):
            if doc_key not in results_map:
                results_map[doc_key] = {"text": doc_text, "scores": [0, score]}
            else:
                results_map[doc_key]["scores"][1] = score

        # Combine scores (average)
        ranked = [
            (
                doc_key,
                sum(info["scores"]) / len(info["scores"]),
                info["text"],
            )
            for doc_key, info in results_map.items()
        ]
        ranked.sort(key=lambda x: -x[1])
        return ranked[:top_k]


def compute_grounding_score(
    response_text: str, retrieved_docs: List[Tuple[str, float, str]]
) -> float:
    """Compute grounding score: how well does response match retrieved docs?
    
    Returns: score in [0, 1] where 1 = perfectly grounded, 0 = hallucinated.
    """
    if not retrieved_docs:
        return 0.0

    # Simple heuristic: overlap of key terms
    response_tokens = set(re.findall(r"\b\w+\b", response_text.lower()))
    doc_tokens = set()
    for _, _, doc_text in retrieved_docs:
        doc_tokens.update(re.findall(r"\b\w+\b", doc_text.lower()))

    if not doc_tokens:
        return 0.0

    overlap = len(response_tokens & doc_tokens)
    grounding = overlap / max(len(response_tokens), 1)
    return min(1.0, grounding)
