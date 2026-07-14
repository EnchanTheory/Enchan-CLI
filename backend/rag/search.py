"""Language-neutral hybrid retrieval and Enchan candidate selection."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter, defaultdict
from typing import Any, Callable

from backend.rag.structure import structure_text


INDEX_VERSION = 4


def normalize_text(text: str) -> str:
    """Normalize mixed-script text without assuming a language or tokenizer."""
    normalized = unicodedata.normalize("NFKC", str(text)).casefold()
    normalized = "".join(
        " " if unicodedata.category(char)[0] in {"P", "S", "Z", "C"} else char
        for char in normalized
    )
    return re.sub(r"\s+", " ", normalized).strip()


def lexical_features(text: str) -> list[str]:
    """Return word and within-word character features for every Unicode script."""
    normalized = normalize_text(text)
    if not normalized:
        return []
    terms = normalized.split()
    features: list[str] = []
    for term in terms:
        features.append(f"w:{term}")
        for size in (2, 3):
            features.extend(
                f"c{size}:{term[index:index + size]}"
                for index in range(max(0, len(term) - size + 1))
            )
    features.extend(f"b:{left}\u241f{right}" for left, right in zip(terms, terms[1:]))
    return features



def _metadata_text(chunk: dict[str, Any]) -> str:
    metadata = chunk.get("metadata", {})
    values: list[str] = []
    for key in ("source_path", "title", "heading"):
        value = metadata.get(key)
        if value:
            values.append(str(value))

    structured = structure_text(chunk.get("structure", {}))
    if structured:
        values.append(structured)
    return "\n".join(values)


def _chunk_counter(chunk: dict[str, Any]) -> Counter[str]:
    counter: Counter[str] = Counter(lexical_features(chunk.get("text", "")))
    metadata_counter = Counter(lexical_features(_metadata_text(chunk)))
    for feature, frequency in metadata_counter.items():
        counter[feature] += frequency * 2
    return counter


def build_lexical_index(
    chunks: list[dict[str, Any]],
    progress: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    counters: list[Counter[str]] = []
    total = len(chunks)
    for position, chunk in enumerate(chunks, 1):
        counters.append(_chunk_counter(chunk))
        if progress is not None and (position == total or position == 1 or position % 25 == 0):
            progress(position, total)
    document_frequency: Counter[str] = Counter()
    for counter in counters:
        document_frequency.update(counter.keys())

    document_count = len(chunks)
    idf = {
        gram: math.log((document_count + 1) / (frequency + 1)) + 1.0
        for gram, frequency in document_frequency.items()
    }
    postings: dict[str, list[list[float | int]]] = defaultdict(list)
    norms: list[float] = []
    for index, counter in enumerate(counters):
        squared = 0.0
        for gram, frequency in counter.items():
            weight = float(frequency) * idf[gram]
            postings[gram].append([index, weight])
            squared += weight * weight
        norms.append(math.sqrt(squared))
    return {
        "version": INDEX_VERSION,
        "document_count": document_count,
        "idf": idf,
        "norms": norms,
        "postings": dict(postings),
    }


def retrieve_candidates(
    query: str,
    chunks: list[dict[str, Any]],
    index: dict[str, Any],
    limit: int,
) -> list[dict[str, Any]]:
    query_counter = Counter(lexical_features(query))
    idf = index.get("idf", {})
    query_weights = {
        gram: float(frequency) * float(idf[gram])
        for gram, frequency in query_counter.items()
        if gram in idf
    }
    query_norm = math.sqrt(sum(weight * weight for weight in query_weights.values()))
    if query_norm == 0:
        return []

    scores: dict[int, float] = defaultdict(float)
    for gram, query_weight in query_weights.items():
        for document_index, document_weight in index.get("postings", {}).get(gram, []):
            scores[int(document_index)] += query_weight * float(document_weight)

    norms = index.get("norms", [])
    normalized_query = normalize_text(query)
    query_terms = set(normalized_query.split())
    ranked = []
    for document_index, dot_product in scores.items():
        if document_index >= len(chunks) or document_index >= len(norms) or not norms[document_index]:
            continue
        cosine_score = dot_product / (query_norm * float(norms[document_index]))
        searchable = normalize_text(
            f"{chunks[document_index].get('text', '')}\n{_metadata_text(chunks[document_index])}"
        )
        searchable_terms = set(searchable.split())
        term_coverage = (
            len(query_terms & searchable_terms) / len(query_terms)
            if query_terms
            else 0.0
        )
        phrase_match = 1.0 if normalized_query and normalized_query in searchable else 0.0
        score = cosine_score * 0.60 + term_coverage * 0.35 + phrase_match * 0.05
        if score > 0:
            ranked.append((score, str(chunks[document_index].get("id", "")), document_index))
    ranked.sort(key=lambda item: (-item[0], item[1]))

    candidates = []
    for score, _, document_index in ranked[:max(1, limit)]:
        candidate = dict(chunks[document_index])
        candidate["score"] = score
        candidates.append(candidate)
    return candidates


def _tfidf_vector(text: str, idf: dict[str, float]) -> tuple[dict[str, float], float]:
    counter = Counter(lexical_features(text))
    vector = {
        gram: float(frequency) * float(idf[gram])
        for gram, frequency in counter.items()
        if gram in idf
    }
    norm = math.sqrt(sum(weight * weight for weight in vector.values()))
    return vector, norm


def _semantic_keys(candidate: dict[str, Any]) -> set[str]:
    structure = candidate.get("structure", {})
    keys: set[str] = set()
    for kind in ("entities", "concepts", "claims", "events"):
        keys.update(f"{kind}:{str(value).casefold()}" for value in structure.get(kind, []))
    for relation in structure.get("relations", []):
        keys.add(f"entity:{str(relation.get('source', '')).casefold()}")
        keys.add(f"entity:{str(relation.get('target', '')).casefold()}")
    return keys


def build_candidate_similarity_edges(
    candidates: list[dict[str, Any]],
    index: dict[str, Any],
    threshold: float = 0.4,
) -> list[tuple[int, int]]:
    idf = index.get("idf", {})
    vectors = [_tfidf_vector(f"{item['text']}\n{structure_text(item.get('structure', {}))}", idf) for item in candidates]
    semantic_keys = [_semantic_keys(item) for item in candidates]
    edges: list[tuple[int, int]] = []
    for left in range(len(vectors)):
        left_vector, left_norm = vectors[left]
        if left_norm == 0:
            continue
        for right in range(left + 1, len(vectors)):
            right_vector, right_norm = vectors[right]
            if right_norm == 0:
                continue
            small, large = (left_vector, right_vector) if len(left_vector) <= len(right_vector) else (right_vector, left_vector)
            dot = sum(weight * large.get(gram, 0.0) for gram, weight in small.items())
            similarity = dot / (left_norm * right_norm)
            if similarity > threshold or bool(semantic_keys[left] & semantic_keys[right]):
                edges.append((left, right))
    return edges


def select_candidates(
    query: str,
    candidates: list[dict[str, Any]],
    limit: int,
    index: dict[str, Any] | None = None,
    selector: Callable[..., list[int]] | None = None,
) -> tuple[list[dict[str, Any]], str]:
    if not candidates or limit <= 0:
        return [], "relevance_fallback"
    try:
        if selector is not None:
            indices = selector(query, [item["text"] for item in candidates], limit, preserve_order=False)
        else:
            from backend.rag.enchan_selector import select_rag_candidate_indices
            edges = build_candidate_similarity_edges(candidates, index or {})
            indices = select_rag_candidate_indices(
                edges,
                [float(item.get("score", 0.0)) for item in candidates],
                limit,
                seed=42,
            )
        valid: list[int] = []
        seen = set()
        for value in indices:
            candidate_index = int(value)
            if 0 <= candidate_index < len(candidates) and candidate_index not in seen:
                valid.append(candidate_index)
                seen.add(candidate_index)
        if not valid:
            raise RuntimeError("Enchan selection returned no candidates")
        return [candidates[candidate_index] for candidate_index in valid[:limit]], "enchan_cosmic_v2"
    except Exception:
        return candidates[:limit], "relevance_fallback"
