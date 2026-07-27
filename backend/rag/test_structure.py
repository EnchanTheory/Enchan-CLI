import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.rag.indexer import RAGIndexer
from backend.rag.structure import (
    STRUCTURE_SCHEMA,
    LocalStructureAnalyzer,
    StructureOutputError,
    is_structure_failure,
)


VALID_STRUCTURE = {
    "language": "en",
    "summary": "A summary.",
    "entities": [],
    "concepts": [],
    "claims": [],
    "events": [],
    "texture": [],
    "relations": [],
}


class _Response:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return json.dumps(self.body).encode("utf-8")


class LocalStructureAnalyzerTests(unittest.TestCase):
    def test_enchan_request_uses_json_schema_and_disables_thinking(self):
        requests = []

        def urlopen(request, timeout):
            requests.append((request, timeout))
            return _Response({
                "choices": [{"message": {"content": json.dumps(VALID_STRUCTURE)}}],
            })

        analyzer = LocalStructureAnalyzer({"backend": "enchan"})
        with patch("backend.rag.structure.urllib.request.urlopen", side_effect=urlopen):
            result = analyzer({"text": "Example", "metadata": {}})

        payload = json.loads(requests[0][0].data.decode("utf-8"))
        self.assertEqual(payload["json_schema"], STRUCTURE_SCHEMA)
        self.assertEqual(
            payload["chat_template_kwargs"],
            {"enable_thinking": False},
        )
        self.assertEqual(result["summary"], "A summary.")

    def test_malformed_large_output_stops_after_two_requests(self):
        calls = 0

        def urlopen(_request, timeout):
            nonlocal calls
            calls += 1
            return _Response({
                "choices": [{"message": {"content": '{"language":"en"'}}],
            })

        analyzer = LocalStructureAnalyzer({"backend": "enchan"})
        with patch("backend.rag.structure.urllib.request.urlopen", side_effect=urlopen):
            with self.assertRaises(StructureOutputError):
                analyzer({"text": "x" * 12_000, "metadata": {}})

        self.assertEqual(calls, 2)


class _Source:
    def snapshot(self):
        return {"files": {"doc.txt": {"mtime_ns": 1}}}

    def load_documents(self, progress=None):
        if progress is not None:
            progress(1, 1, "doc.txt")
        return ([{
            "source_path": "doc.txt",
            "title": "Doc",
            "text": "content",
            "pre_chunked": True,
        }], [])


class _Store:
    def __init__(self, root):
        self.root = root
        self.json = {}
        self.chunks = {}
        self.collection = None

    def collection_dir(self, collection_id):
        path = self.root / collection_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def load_json(self, collection_id, name, default):
        return self.json.get((collection_id, name), default)

    def save_json(self, collection_id, name, value):
        self.json[(collection_id, name)] = value

    def save_chunks(self, collection_id, chunks):
        self.chunks[collection_id] = chunks

    def save_collection(self, collection):
        self.collection = collection


class RAGIndexerFailureCacheTests(unittest.TestCase):
    def test_permanent_output_failure_is_not_retried_on_next_rebuild(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _Store(Path(tmp))
            indexer = RAGIndexer(store)
            collection = {"id": "test", "index_version": 0}
            calls = 0

            def analyzer(_unit):
                nonlocal calls
                calls += 1
                raise StructureOutputError("malformed")

            first = indexer.rebuild(
                collection,
                _Source(),
                force=True,
                analyzer=analyzer,
            )
            second = indexer.rebuild(
                collection,
                _Source(),
                force=True,
                analyzer=analyzer,
            )

            cache = store.json[("test", "structure_cache.json")]["chunks"]
            self.assertEqual(calls, 1)
            self.assertEqual(first["analysis_failed_count"], 1)
            self.assertEqual(second["analysis_attempted_count"], 0)
            self.assertEqual(second["reused_count"], 1)
            self.assertTrue(is_structure_failure(next(iter(cache.values()))))
            self.assertEqual(
                next(iter(store.chunks["test"]))["structure"],
                {},
            )

    def test_transient_failure_is_retried_on_next_rebuild(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _Store(Path(tmp))
            indexer = RAGIndexer(store)
            collection = {"id": "test", "index_version": 0}
            calls = 0

            def analyzer(_unit):
                nonlocal calls
                calls += 1
                if calls == 1:
                    raise RuntimeError("server unavailable")
                return dict(VALID_STRUCTURE)

            first = indexer.rebuild(
                collection,
                _Source(),
                force=True,
                analyzer=analyzer,
            )
            second = indexer.rebuild(
                collection,
                _Source(),
                force=True,
                analyzer=analyzer,
            )

            self.assertEqual(calls, 2)
            self.assertEqual(first["analysis_failed_count"], 1)
            self.assertEqual(second["analyzed_count"], 1)


if __name__ == "__main__":
    unittest.main()
