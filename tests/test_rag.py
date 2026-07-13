import json
import tempfile
import unittest
from pathlib import Path

from backend.rag.service import RAGService


class RAGFoundationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = self.root / "store"

    def tearDown(self):
        self.temp.cleanup()

    def test_directory_index_persists_and_reloads(self):
        source = self.root / "documents"
        source.mkdir()
        (source / "design.md").write_text("# RAG design\n\nEnchan keeps retrieval local and private.", encoding="utf-8")
        (source / "notes.txt").write_text("CPUで動く小型モデルのためのメモ。", encoding="utf-8")

        service = RAGService(self.store, selector=lambda query, texts, limit, **kwargs: [0])
        collection = service.register_directory(source)
        built = service.rebuild(collection["id"])
        self.assertTrue(built["changed"])
        self.assertEqual(built["file_count"], 2)
        self.assertGreaterEqual(built["chunk_count"], 2)

        unchanged = service.rebuild(collection["id"])
        self.assertFalse(unchanged["changed"])
        reloaded = RAGService(self.store, selector=lambda query, texts, limit, **kwargs: [0])
        result = reloaded.search(collection["id"], "retrieval local private")
        self.assertEqual(result["selection_method"], "enchan_cosmic_v2")
        self.assertEqual(result["results"][0]["metadata"]["source_path"], "design.md")

    def test_changed_file_refreshes_index(self):
        source = self.root / "changing"
        source.mkdir()
        document = source / "notes.txt"
        document.write_text("alpha baseline", encoding="utf-8")
        service = RAGService(self.store, selector=lambda *args, **kwargs: [0])
        collection = service.register_directory(source)
        service.rebuild(collection["id"])

        document.write_text("beta changed content with a different size", encoding="utf-8")
        changed = service.rebuild(collection["id"])
        self.assertTrue(changed["changed"])
        result = service.search(collection["id"], "beta changed")
        self.assertIn("beta changed", result["results"][0]["text"])

    def test_search_reports_changes_without_automatic_rebuild(self):
        source = self.root / "manual-update"
        source.mkdir()
        document = source / "notes.txt"
        document.write_text("alpha baseline", encoding="utf-8")
        service = RAGService(self.store, selector=lambda *args, **kwargs: [0])
        collection = service.register_directory(source)
        service.rebuild(collection["id"])

        document.write_text("beta changed content with a different size", encoding="utf-8")
        stale = service.search(collection["id"], "alpha baseline")
        self.assertTrue(stale["update_available"])
        self.assertEqual(stale["index_status"], "stale")
        self.assertIn("alpha baseline", stale["results"][0]["text"])

        service.rebuild(collection["id"])
        refreshed = service.search(collection["id"], "beta changed")
        self.assertFalse(refreshed["update_available"])
        self.assertIn("beta changed", refreshed["results"][0]["text"])

    def test_registered_collection_requires_manual_rebuild(self):
        source = self.root / "registered-only"
        source.mkdir()
        (source / "notes.txt").write_text("not indexed yet", encoding="utf-8")
        service = RAGService(self.store)
        collection = service.register_directory(source)
        with self.assertRaisesRegex(RuntimeError, "not indexed"):
            service.search(collection["id"], "indexed")
    def test_session_source_indexes_only_conversation_messages(self):
        sessions = self.root / "sessions"
        sessions.mkdir()
        events = [
            {"type": "system", "content": "secret system prompt"},
            {"type": "message", "role": "user", "content": "RAGについて決めたことは？", "ts": "2026-07-13T00:00:00+00:00"},
            {"type": "tool", "content": "very large command output"},
            {"type": "message", "role": "model", "content": "検索はローカルにします。"},
        ]
        log = sessions / "sample.jsonl"
        log.write_text("not-json\n" + "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events), encoding="utf-8")

        service = RAGService(self.store, selector=lambda *args, **kwargs: [0])
        collection = service.ensure_session_collection(sessions)
        service.rebuild(collection["id"])
        chunks = service.store.load_chunks(collection["id"])
        self.assertEqual(len(chunks), 1)
        self.assertIn("RAGについて", chunks[0]["text"])
        self.assertIn("検索はローカル", chunks[0]["text"])
        self.assertNotIn("system prompt", chunks[0]["text"])
        self.assertNotIn("command output", chunks[0]["text"])

    def test_engine_failure_uses_deterministic_relevance_fallback(self):
        source = self.root / "fallback"
        source.mkdir()
        (source / "a.txt").write_text("privacy local local local", encoding="utf-8")
        (source / "b.txt").write_text("unrelated material", encoding="utf-8")

        def unavailable(*args, **kwargs):
            raise RuntimeError("engine unavailable")

        service = RAGService(self.store, selector=unavailable)
        collection = service.register_directory(source)
        service.rebuild(collection["id"])
        first = service.search(collection["id"], "privacy local", selection_count=1)
        second = service.search(collection["id"], "privacy local", selection_count=1)
        self.assertEqual(first["selection_method"], "relevance_fallback")
        self.assertEqual(first["results"][0]["id"], second["results"][0]["id"])
        self.assertEqual(first["results"][0]["metadata"]["source_path"], "a.txt")

    def test_long_lines_are_bounded_into_multiple_chunks(self):
        source = self.root / "long-lines"
        source.mkdir()
        (source / "long.txt").write_text("prefix " + ("x" * 1000) + " retrieval-needle", encoding="utf-8")
        service = RAGService(self.store, selector=lambda *args, **kwargs: [0])
        collection = service.register_directory(source)
        collection["chunk_chars"] = 300
        collection["chunk_overlap"] = 40
        service.store.save_collection(collection)
        built = service.rebuild(collection["id"])
        self.assertGreater(built["chunk_count"], 1)
        self.assertTrue(all(len(chunk["text"]) <= 300 for chunk in service.store.load_chunks(collection["id"])))

    def test_generated_rag_data_is_not_indexed_recursively(self):
        source = self.root / "parent"
        source.mkdir()
        (source / "source.txt").write_text("real source document", encoding="utf-8")
        nested_store = source / ".enchan" / "rag"
        generated = nested_store / "collections" / "fake"
        generated.mkdir(parents=True)
        (generated / "derived.txt").write_text("derived private chunk", encoding="utf-8")
        service = RAGService(nested_store)
        collection = service.register_directory(source)
        built = service.rebuild(collection["id"])
        self.assertEqual(built["file_count"], 1)
        chunks = service.store.load_chunks(collection["id"])
        self.assertEqual({chunk["metadata"]["source_path"] for chunk in chunks}, {"source.txt"})
    def test_collections_are_path_isolated(self):
        first = self.root / "first"
        second = self.root / "second"
        first.mkdir()
        second.mkdir()
        service = RAGService(self.store)
        first_collection = service.register_directory(first)
        same_collection = service.register_directory(first / ".")
        second_collection = service.register_directory(second)
        self.assertEqual(first_collection["id"], same_collection["id"])
        self.assertNotEqual(first_collection["id"], second_collection["id"])


if __name__ == "__main__":
    unittest.main()

