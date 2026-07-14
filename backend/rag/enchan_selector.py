"""Thin ctypes adapter for the sparse Enchan Cosmic v2 RAG capability."""

from __future__ import annotations

import ctypes

from backend.enchan_cosmic import get_engine_dll


def select_rag_candidate_indices(
    edges: list[tuple[int, int]],
    relevance: list[float],
    budget: int,
    *,
    seed: int = 42,
) -> list[int]:
    if budget <= 0 or not relevance:
        return []
    dll = get_engine_dll()
    if not dll.enchan_engine_has_capability(b"rag.enchan"):
        raise RuntimeError("Enchan Engine RAG capability is unavailable")
    function = getattr(dll, "enchan_rag_select_candidates", None)
    if function is None:
        raise RuntimeError("Enchan Engine RAG ABI is unavailable")
    function.argtypes = [
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_int),
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_float),
        ctypes.c_int,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_int),
        ctypes.c_int,
    ]
    function.restype = ctypes.c_int

    flat_edges = [value for edge in edges for value in edge]
    edge_values = flat_edges or [0, 0]
    edge_array = (ctypes.c_int * len(edge_values))(*edge_values)
    relevance_array = (ctypes.c_float * len(relevance))(*relevance)
    out_capacity = min(len(relevance), budget)
    out_indices = (ctypes.c_int * out_capacity)()
    count = function(
        len(relevance),
        edge_array,
        len(edges),
        relevance_array,
        budget,
        seed,
        out_indices,
        out_capacity,
    )
    if count <= 0:
        raise RuntimeError(f"Enchan Engine RAG selection failed: {count}")
    selected = []
    seen = set()
    for offset in range(min(count, out_capacity)):
        index = int(out_indices[offset])
        if 0 <= index < len(relevance) and index not in seen:
            selected.append(index)
            seen.add(index)
    if not selected:
        raise RuntimeError("Enchan Engine RAG selection returned no valid indices")
    return selected
