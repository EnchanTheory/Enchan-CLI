import time
import re
import io
import contextlib
from typing import Optional
from enchan_cosmic import COSMIC_AVAILABLE, select_text_indices


TOKEN_CHUNK_SIZE = 360
TOKEN_CHUNK_STRIDE = 180
DEFAULT_CONTEXT_BUDGET = 5
SUMMARY_CONTEXT_BUDGET = 8
CHAT_HISTORY_CONTEXT_BUDGET = 12
HIERARCHICAL_STORY_CHUNK_THRESHOLD = 180
STORY_SECTION_TARGET_CHUNKS = 28
STORY_SECTION_MAX_COUNT = 48
STORY_SECTION_ANCHORS = 3
CHAT_HISTORY_COMPRESSION_QUERY = (
    "会話履歴 継続 目的 決定事項 実装 ファイル パス コマンド エラー 原因 対策 "
    "未解決 次アクション ユーザー要件 制約 仕様 重要な固有名詞 正確な表記 "
    "長文 文書 小説 全体 概要 構造 時系列 主要人物 重要事件 伏線 結論 "
    "conversation continuity decisions requirements files commands errors fixes "
    "open issues next steps exact names exact terms document overview structure timeline "
    "main characters key events conclusions"
)


def format_count(value: int) -> str:
    return f"{int(value):,}"


def count_text_tokens(tokenizer, text: str) -> int:
    if tokenizer is None or not text:
        return 0
    return len(tokenizer.encode(text, add_special_tokens=False))


def print_source_metrics(label: str, text: str, tokenizer) -> int:
    source_tokens = count_text_tokens(tokenizer, text)
    print(f"[System] {label}")
    print(f"[System] Source chars: {format_count(len(text))}")
    print(f"[System] Source tokens: {format_count(source_tokens)}")
    print("[System] Tokenizer: Gemma tokenizer")
    return source_tokens


def chunk_text(
    text: str,
    chunk_size: int = TOKEN_CHUNK_SIZE,
    chunk_stride: int = TOKEN_CHUNK_STRIDE,
    tokenizer=None,
) -> list[str]:
    # If using local in-process tokenizers (like HuggingFace), use precise token-slice chunking.
    # If using our RunningModelTokenizer, bypass the sequential HTTP detokenize requests in a loop
    # to avoid freezing/hanging on large files, and instead use highly efficient character-based chunking.
    if tokenizer is not None and type(tokenizer).__name__ != "RunningModelTokenizer":
        token_ids = tokenizer.encode(text, add_special_tokens=False)
        if token_ids:
            chunks = []
            step = max(1, min(chunk_size, chunk_stride))
            for i in range(0, len(token_ids), step):
                chunk_ids = token_ids[i:i + chunk_size]
                chunk = tokenizer.decode(chunk_ids, skip_special_tokens=True).strip()
                if chunk:
                    chunks.append(chunk)
                if i + chunk_size >= len(token_ids):
                    break
            if chunks:
                return chunks

    # Instant character-based chunking optimized for CJK/Japanese text (1 token ≈ 1.3 characters)
    char_chunk_size = int(chunk_size * 1.3)
    char_stride = int(chunk_stride * 1.3)
    
    chunks = []
    step = max(1, min(char_chunk_size, char_stride))
    for i in range(0, len(text), step):
        chunk = text[i:i + char_chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        if i + char_chunk_size >= len(text):
            break
    return chunks


def is_summary_query(query: str) -> bool:
    lowered = query.lower()
    markers = (
        "内容", "あらすじ", "物語", "全体", "概要", "要約", "流れ",
        "summary", "summarize", "overview", "plot", "story",
    )
    return any(marker in lowered for marker in markers)


def looks_like_story(text: str) -> bool:
    markers = ("章", "序章", "第一章", "第二章", "第三章", "登場人物", "あらすじ")
    return any(marker in text[:20000] for marker in markers)


def print_compression_metrics(
    total_chunks: int,
    core_chunks: int,
    compressed_text: str,
    tokenizer,
    source_tokens: Optional[int],
    elapsed: Optional[float] = None,
) -> None:
    compressed_tokens = count_text_tokens(tokenizer, compressed_text)
    print(f"[External Field] Chunks: {total_chunks} -> {core_chunks} core chunks")
    if elapsed is not None:
        print(f"[External Field] Compression time: {elapsed:.3f}s")
    print(f"[External Field] Compressed tokens: {format_count(compressed_tokens)}")
    if source_tokens:
        ratio = (1.0 - (compressed_tokens / source_tokens)) * 100.0
        print(f"[External Field] Compression ratio: {ratio:.2f}%")


def select_with_enchan_engine(
    query: str,
    chunks: list[str],
    effective_budget: int,
    story_summary_mode: bool,
) -> list[int]:
    return select_text_indices(
        query,
        chunks,
        effective_budget,
        preserve_order=story_summary_mode,
    )


def build_chat_history_compression_query(recent_history: list[dict]) -> str:
    recent_user_terms: list[str] = []
    for msg in reversed(recent_history):
        if msg.get("role") != "user":
            continue
        content = str(msg.get("content", "")).strip()
        if content:
            recent_user_terms.append(content[:300])
        if len(recent_user_terms) >= 2:
            break

    if not recent_user_terms:
        return CHAT_HISTORY_COMPRESSION_QUERY

    recent_user_terms.reverse()
    return (
        CHAT_HISTORY_COMPRESSION_QUERY
        + "\nRecent user focus and exact terms to preserve:\n"
        + "\n".join(recent_user_terms)
    )


def _has_cjk(text: str) -> bool:
    return any(
        "\u3040" <= ch <= "\u30ff"
        or "\u3400" <= ch <= "\u4dbf"
        or "\u4e00" <= ch <= "\u9fff"
        or "\uf900" <= ch <= "\ufaff"
        for ch in text
    )


def _add_index(indices: list[int], seen: set[int], idx: int, total: int) -> None:
    if 0 <= idx < total and idx not in seen:
        indices.append(idx)
        seen.add(idx)


def _story_query_lenses(query: str, chunks: list[str]) -> list[str]:
    joined_sample = "\n".join(chunks[: min(4, len(chunks))])
    if _has_cjk(joined_sample):
        lenses = [
            query,
            "物語 展開 事件 転換点 結末",
            "人物 関係 対立 感情 変化",
            "世界観 設定 謎 真理 目的",
            "伏線 予兆 秘密 発覚 解決",
        ]
    else:
        lenses = [
            query,
            "plot events turning points ending",
            "characters relationships conflicts emotions change",
            "setting world mystery truth purpose",
            "foreshadowing clues secrets reveal resolution",
        ]
    deduped = []
    seen = set()
    for lens in lenses:
        lens = lens.strip()
        if lens and lens not in seen:
            deduped.append(lens)
            seen.add(lens)
    return deduped


def select_story_timeline_indices(
    query: str,
    chunks: list[str],
    effective_budget: int,
) -> list[int]:
    if effective_budget <= 0 or not chunks:
        return []
    if len(chunks) <= effective_budget:
        return list(range(len(chunks)))

    target_count = min(len(chunks), max(effective_budget, 32))
    selected: list[int] = []
    seen: set[int] = set()
    total = len(chunks)
    lenses = _story_query_lenses(query, chunks)

    _add_index(selected, seen, 0, total)
    _add_index(selected, seen, total - 1, total)
    for idx, chunk in enumerate(chunks):
        if _chunk_heading(chunk):
            _add_index(selected, seen, idx, total)

    global_budget = max(1, min(target_count // max(1, len(lenses)), effective_budget))
    for lens in lenses:
        try:
            for idx in select_with_enchan_engine(lens, chunks, global_budget, True):
                _add_index(selected, seen, idx, total)
        except RuntimeError:
            pass

    segment_count = min(total, max(effective_budget, len(lenses) * 4))
    for segment in range(segment_count):
        start = int(segment * total / segment_count)
        end = int((segment + 1) * total / segment_count)
        end = max(start + 1, min(total, end))
        segment_chunks = chunks[start:end]
        lens = lenses[segment % len(lenses)]
        try:
            local_indices = select_with_enchan_engine(lens, segment_chunks, 1, False)
            if local_indices:
                _add_index(selected, seen, start + local_indices[0], total)
                continue
        except RuntimeError:
            pass
        _add_index(selected, seen, start + ((end - start) // 2), total)

    window_count = min(total, max(4, effective_budget // 2))
    for window in range(window_count):
        start = int(window * total / window_count)
        end = int((window + 1) * total / window_count)
        end = max(start + 1, min(total, end))
        window_chunks = chunks[start:end]
        for lens in lenses[:3]:
            try:
                local_indices = select_with_enchan_engine(lens, window_chunks, 2, False)
                for idx in local_indices:
                    _add_index(selected, seen, start + idx, total)
            except RuntimeError:
                pass
            if len(selected) >= target_count:
                break
        if len(selected) >= target_count:
            break

    cursor = 0
    while len(selected) < target_count and cursor < target_count:
        idx = int((cursor + 0.5) * total / target_count)
        _add_index(selected, seen, min(total - 1, idx), total)
        cursor += 1

    return sorted(selected[:target_count])

def _compact_line(text: str, limit: int) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: max(0, limit - 1)].rstrip() + "..."


def _chunk_heading(chunk: str) -> str:
    for line in chunk.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if "章" in stripped[:24] or stripped.startswith(("#", "第")):
            return _compact_line(stripped, 36)
        break
    return ""


def build_story_structure_digest(
    chunks: list[str],
    selected_indices: list[int],
    max_lines: int = 140,
    snippet_chars: int = 46,
) -> str:
    if not chunks:
        return ""

    selected = set(selected_indices)
    total = len(chunks)
    if total <= max_lines:
        digest_indices = list(range(total))
    else:
        digest_indices = []
        seen = set()
        for i in range(max_lines):
            idx = int(i * (total - 1) / max(1, max_lines - 1))
            if idx not in seen:
                digest_indices.append(idx)
                seen.add(idx)
        for idx in selected_indices:
            if idx not in seen:
                digest_indices.append(idx)
                seen.add(idx)
        digest_indices.sort()

    lines = [
        "[Full-Coverage Structural Digest]",
        "Every source chunk is represented; '*' marks MaxCut/timeline anchors.",
    ]
    for idx in digest_indices:
        marker = "*" if idx in selected else " "
        heading = _chunk_heading(chunks[idx])
        snippet = _compact_line(chunks[idx], snippet_chars)
        if heading and not snippet.startswith(heading):
            snippet = f"{heading} | {snippet}"
        lines.append(f"[{idx:03d}{marker}] {snippet}")

    if total > max_lines:
        lines.append(f"[Digest sampled {len(digest_indices)} of {total} chunks; selected excerpts are always included.]")
    return "\n".join(lines)


def build_story_structured_context(
    chunks: list[str],
    selected_indices: list[int],
) -> str:
    digest = build_story_structure_digest(chunks, selected_indices)
    anchors = ",".join(str(i) for i in selected_indices)
    return f"{digest}\n\n[MaxCut/Timeline Anchors]\n{anchors}"


def _partition_ranges(total: int, target_size: int = STORY_SECTION_TARGET_CHUNKS) -> list[tuple[int, int]]:
    if total <= 0:
        return []
    section_count = max(1, min(STORY_SECTION_MAX_COUNT, (total + max(1, target_size) - 1) // max(1, target_size)))
    ranges: list[tuple[int, int]] = []
    for section in range(section_count):
        start = int(section * total / section_count)
        end = int((section + 1) * total / section_count)
        end = max(start + 1, min(total, end))
        ranges.append((start, end))
    return ranges


def _select_section_anchor_indices(
    query: str,
    chunks: list[str],
    start: int,
    end: int,
    lenses: list[str],
    anchor_count: int = STORY_SECTION_ANCHORS,
) -> list[int]:
    section_chunks = chunks[start:end]
    if not section_chunks:
        return []
    anchors: list[int] = []
    seen: set[int] = set()
    total = len(chunks)

    for local_idx, chunk in enumerate(section_chunks):
        if _chunk_heading(chunk):
            _add_index(anchors, seen, start + local_idx, total)
            break

    for lens in lenses:
        try:
            local_indices = select_with_enchan_engine(lens, section_chunks, 1, False)
            for idx in local_indices:
                _add_index(anchors, seen, start + idx, total)
        except RuntimeError:
            pass
        if len(anchors) >= anchor_count:
            break

    fallback_points = [start, start + ((end - start) // 2), end - 1]
    for idx in fallback_points:
        _add_index(anchors, seen, idx, total)
        if len(anchors) >= anchor_count:
            break

    return sorted(anchors[:anchor_count])


def _section_title(chunks: list[str], start: int, end: int) -> str:
    for idx in range(start, end):
        heading = _chunk_heading(chunks[idx])
        if heading:
            return heading
    return _compact_line(chunks[start], 52)


def _format_section_line(
    section_no: int,
    start: int,
    end: int,
    chunks: list[str],
    section_anchor: bool,
    chunk_anchors: list[int],
) -> str:
    section_mark = "*" if section_anchor else " "
    title = _section_title(chunks, start, end)
    parts = []
    anchor_set = set(chunk_anchors)
    for idx in chunk_anchors:
        marker = "*" if idx in anchor_set else " "
        parts.append(f"[{idx:03d}{marker}] {_compact_line(chunks[idx], 58)}")
    joined = " / ".join(parts)
    return f"[S{section_no:02d}{section_mark} chunks {start:03d}-{end - 1:03d}] {title} :: {joined}"


def _select_global_sections(query: str, section_summaries: list[str], target_count: int) -> list[int]:
    if not section_summaries:
        return []
    if len(section_summaries) <= target_count:
        return list(range(len(section_summaries)))

    selected: list[int] = []
    seen: set[int] = set()
    lenses = _story_query_lenses(query, section_summaries)
    _add_index(selected, seen, 0, len(section_summaries))
    _add_index(selected, seen, len(section_summaries) - 1, len(section_summaries))
    for lens in lenses:
        try:
            for idx in select_with_enchan_engine(lens, section_summaries, max(1, target_count // 2), True):
                _add_index(selected, seen, idx, len(section_summaries))
        except RuntimeError:
            pass
        if len(selected) >= target_count:
            break

    cursor = 0
    while len(selected) < target_count and cursor < target_count:
        idx = int((cursor + 0.5) * len(section_summaries) / target_count)
        _add_index(selected, seen, min(len(section_summaries) - 1, idx), len(section_summaries))
        cursor += 1
    return sorted(selected[:target_count])


def build_hierarchical_story_context(
    query: str,
    chunks: list[str],
    effective_budget: int,
) -> tuple[str, list[int], int]:
    ranges = _partition_ranges(len(chunks))
    lenses = _story_query_lenses(query, chunks)

    per_section_anchors: list[list[int]] = []
    section_summaries: list[str] = []
    for section_no, (start, end) in enumerate(ranges):
        anchors = _select_section_anchor_indices(query, chunks, start, end, lenses)
        per_section_anchors.append(anchors)
        title = _section_title(chunks, start, end)
        snippets = " / ".join(_compact_line(chunks[idx], 56) for idx in anchors)
        section_summaries.append(f"S{section_no:02d} chunks {start}-{end - 1}: {title} :: {snippets}")

    global_section_count = min(len(section_summaries), max(effective_budget, min(16, len(section_summaries))))
    global_sections = _select_global_sections(query, section_summaries, global_section_count)
    global_section_set = set(global_sections)

    selected_indices: list[int] = []
    seen_indices: set[int] = set()
    for section_no in global_sections:
        for idx in per_section_anchors[section_no]:
            _add_index(selected_indices, seen_indices, idx, len(chunks))
    _add_index(selected_indices, seen_indices, 0, len(chunks))
    _add_index(selected_indices, seen_indices, len(chunks) - 1, len(chunks))
    selected_indices.sort()

    lines = [
        "[Hierarchical Multi-Pass Structural Digest]",
        f"Every source chunk is represented by one of {len(ranges)} section lines; '*' marks global MaxCut section/chunk anchors.",
        "Pass 1: partition full document into ordered sections.",
        "Pass 2: run MaxCut inside every section to keep local events and character changes.",
        "Pass 3: run MaxCut over section summaries to identify global timeline anchors.",
    ]
    for section_no, (start, end) in enumerate(ranges):
        lines.append(_format_section_line(section_no, start, end, chunks, section_no in global_section_set, per_section_anchors[section_no]))

    lines.append("")
    lines.append("[Global Section Anchors]")
    lines.append(",".join(f"S{idx:02d}" for idx in global_sections))
    lines.append("")
    lines.append("[MaxCut/Timeline Chunk Anchors]")
    lines.append(",".join(str(i) for i in selected_indices))
    return "\n".join(lines), selected_indices, len(ranges)

def compress_context(
    query: str,
    large_text: str,
    budget: int = DEFAULT_CONTEXT_BUDGET,
    tokenizer=None,
    source_tokens: Optional[int] = None,
    force_story_mode: Optional[bool] = None,
) -> str:
    chunks = chunk_text(large_text, tokenizer=tokenizer)
    
    # Diagnostic Print
    print(f"[Debug] force_story_mode={force_story_mode}")
    
    if force_story_mode is not None:
        story_summary_mode = force_story_mode
    else:
        story_summary_mode = is_summary_query(query) and looks_like_story(large_text)
        
    # Define baseline limit below which we don't need to compress at all
    baseline_limit = SUMMARY_CONTEXT_BUDGET if story_summary_mode else budget
    
    if len(chunks) <= baseline_limit:
        print_compression_metrics(len(chunks), len(chunks), large_text, tokenizer, source_tokens)
        return large_text
        
    # Hybrid Dynamic Scaling Formula:
    # Target 30% retention of original chunks (70% compression rate) to scale naturally,
    # but enforce a safe ceiling of 15 chunks to prevent VRAM crashes on 10K limit models.
    retention_ratio = 0.30
    dynamic_budget = int(len(chunks) * retention_ratio)
    effective_budget = max(baseline_limit, min(15, dynamic_budget))

    t0 = time.perf_counter()
    section_count = 0
    if story_summary_mode and len(chunks) >= HIERARCHICAL_STORY_CHUNK_THRESHOLD:
        compressed, selected_by_engine, section_count = build_hierarchical_story_context(query, chunks, effective_budget)
    elif story_summary_mode:
        selected_by_engine = select_story_timeline_indices(query, chunks, effective_budget)
        compressed = build_story_structured_context(chunks, selected_by_engine)
    else:
        selected_by_engine = select_with_enchan_engine(query, chunks, effective_budget, story_summary_mode)
        compressed = "\n... ".join(chunks[i] for i in selected_by_engine)

    if story_summary_mode:
        last_chunk = max(0, len(chunks) - 1)
        coverage = ",".join(str(i) for i in selected_by_engine)
        if section_count:
            print("[External Field] Mode: story-summary hierarchical multi-pass MaxCut")
            print(f"[External Field] Sections: {section_count}; every chunk represented by a section line")
        else:
            print("[External Field] Mode: story-summary multi-pass MaxCut coverage")
        print(f"[External Field] Coverage chunks: {coverage} / 0-{last_chunk}")
    print(f"\n[External Field] Compressing {len(chunks)} chunks using Enchan Engine DLL...")
    print_compression_metrics(
        len(chunks),
        len(selected_by_engine),
        compressed,
        tokenizer,
        source_tokens,
        time.perf_counter() - t0,
    )
    return compressed


def compress_chat_history(
    chat_history: list[dict],
    tokenizer=None,
    keep_turns: int = 4,
    budget: int = CHAT_HISTORY_CONTEXT_BUDGET,
) -> list[dict]:
    """
    Compresses older chat history using the Max-Cut semantic bridge.
    Keeps the most recent `keep_turns` messages intact.
    The older messages are concatenated, compressed using a stable conversation-continuity query,
    and placed as a single system message at the beginning of the returned history.
    """
    if len(chat_history) <= keep_turns:
        return list(chat_history)

    # Separate recent messages (to keep verbatim) and older messages (to compress)
    recent_history = chat_history[-keep_turns:]
    older_history = chat_history[:-keep_turns]

    compression_query = build_chat_history_compression_query(recent_history)

    # Format the older history into a single string
    formatted_older_lines = []
    for msg in older_history:
        role = msg.get("role", "unknown").capitalize()
        content = msg.get("content", "")
        formatted_older_lines.append(f"[{role}]: {content}")
    large_older_text = "\n\n".join(formatted_older_lines)

    # If the older text is empty, just return the recent history
    if not large_older_text.strip():
        return list(recent_history)

    # Keep chat compression invisible: the compressed frame is internal context, not user/log output.
    with contextlib.redirect_stdout(io.StringIO()):
        compressed_older_text = compress_context(
            query=compression_query,
            large_text=large_older_text,
            budget=budget,
            tokenizer=tokenizer,
            force_story_mode=True
        )

    # Build the new compressed history
    compressed_history = [
        {
            "role": "system",
            "content": (
                "The following is a compressed summary of previous conversation turns, "
                "retained for context. It is strictly informational.\n\n"
                f"{compressed_older_text}"
            )
        }
    ]
    compressed_history.extend(recent_history)
    
    return compressed_history

