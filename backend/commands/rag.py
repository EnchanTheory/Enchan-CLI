"""CUI commands for the local RAG foundation."""

from __future__ import annotations

import shlex

from backend.core import registry
from backend.rag.service import get_default_service
from backend.rag.structure import LocalStructureAnalyzer
from backend.ui.theme import get_enchan_progress


def _parts(user_input: str) -> list[str]:
    return [part.strip("\"'") for part in shlex.split(user_input, posix=False)]


def _rebuild_with_progress(service, reference: str, generation_config: dict) -> dict:
    analyzer = LocalStructureAnalyzer(generation_config)
    with get_enchan_progress("RAG indexing") as progress:
        task = progress.add_task("Indexing", total=100)
        previous_stage = {"value": None}

        def on_progress(event: dict) -> None:
            stage = event.get("stage")
            if stage != previous_stage["value"]:
                previous_stage["value"] = stage
                progress.console.print(f"  {event.get('message', stage)}")
            progress.update(task, completed=float(event.get("percent", 0.0)))

        return service.rebuild(reference, force=True, progress=on_progress, analyzer=analyzer)


def _print_search_result(result: dict) -> None:
    collection = result["collection"]
    print(f"\n[RAG Search] {collection['name']} ({collection['id']})")
    print(f"  Candidates: {result['candidate_count']}")
    print(f"  Selected: {result['selected_count']}")
    print(f"  Selection: {result['selection_method']}")
    print(f"  Elapsed: {result['elapsed_seconds']:.3f}s")

    if result.get("update_available"):
        print(f"  Update available: source files changed; run /rag rebuild {collection['id']} to refresh.")
    elif result.get("source_missing"):
        print("  Warning: source directory is missing; results come from the last saved index.")
    for index, item in enumerate(result["results"], 1):
        metadata = item.get("metadata", {})
        source = metadata.get("source_path", "unknown")
        collection_name = metadata.get("collection_name")
        if collection_name:
            source = f"{collection_name}/{source}"
        line = metadata.get("line_start")
        timestamp = metadata.get("timestamp")
        line_end = metadata.get("line_end")
        location = f"lines {line}-{line_end}" if line else (timestamp or "")
        preview = " ".join(item.get("text", "").split())
        if len(preview) > 320:
            preview = preview[:317] + "..."
        print(f"\n  {index}. {source}{f' ({location})' if location else ''} score={item.get('score', 0):.4f}")
        print(f"     {preview}")


@registry.command("/rag", desc="Manage and search local RAG collections.")
def handle_rag(user_input: str, file_context: str, **kwargs) -> tuple[bool, str, bool]:
    service = get_default_service()
    generation_config = kwargs.get("generation_config") or {}
    parts = _parts(user_input)
    action = parts[1].lower() if len(parts) > 1 else "status"
    try:
        if action == "status":
            collections = service.list_collection_statuses()
            ready = sum(item.get("status") == "ready" for item in collections)
            stale = sum(item.get("status") == "stale" for item in collections)
            registered = sum(item.get("status") == "registered" for item in collections)
            missing = sum(item.get("status") == "source_missing" for item in collections)
            print("\n[RAG Status]")
            print(f"  Store: {service.store.root}")
            print(
                f"  Collections: {len(collections)} "
                f"({ready} ready, {stale} update available, {registered} not indexed, {missing} source missing)"
            )
        elif action == "sources":
            print("\n[RAG Sources]")
            for item in service.list_collection_statuses():
                print(f"  {item['id']}  {item['name']}  [{item.get('status', 'registered')}]  {item['source_path']}")
        elif action == "add":
            if len(parts) < 3:
                raise ValueError("Usage: /rag add <directory>")
            collection = service.register_directory(" ".join(parts[2:]))
            print(f"[RAG] Registered {collection['name']} ({collection['id']}).")
            print(f"[RAG] Indexing is manual and may take a long time. Run /rag rebuild {collection['id']} when ready.")
        elif action == "rebuild":
            reference = parts[2] if len(parts) > 2 else "sessions"
            if reference.lower() in {"all", "*"}:
                targets = [
                    item
                    for item in service.list_collection_statuses()
                    if item.get("status") in {"registered", "stale"}
                ]
                if not targets:
                    print("[RAG] All indexes are up to date.")
                for item in targets:
                    print(f"[RAG] Updating {item['name']} ({item['id']}).")
                    stats = _rebuild_with_progress(service, item["id"], generation_config)
                    print(
                        f"[RAG] Rebuilt {item['name']}: {stats['file_count']} files, "
                        f"{stats['chunk_count']} chunks; {stats.get('analyzed_count', 0)} analyzed, "
                        f"{stats.get('reused_count', 0)} reused."
                    )
                    for diagnostic in stats.get("diagnostics", [])[:10]:
                        print(f"  - {diagnostic}")
            else:
                stats = _rebuild_with_progress(service, reference, generation_config)
                print(f"[RAG] Rebuilt {reference}: {stats['file_count']} files, {stats['chunk_count']} chunks; {stats.get('analyzed_count', 0)} analyzed, {stats.get('reused_count', 0)} reused.")
                for diagnostic in stats.get("diagnostics", [])[:10]:
                    print(f"  - {diagnostic}")
        elif action == "search":
            if len(parts) < 4:
                raise ValueError("Usage: /rag search <collection> <query>")
            result = service.search(parts[2], " ".join(parts[3:]))
            _print_search_result(result)
        else:
            raise ValueError("Usage: /rag <status|sources|add|rebuild|search>")
    except (OSError, KeyError, RuntimeError, ValueError) as exc:
        print(f"[RAG Error] {exc}")
    return True, file_context, False
