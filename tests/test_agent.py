"""
Unit tests for Spectre-CLI.
Verifies file ingestion, chunking, offline vector store, Sentry tracing, and agent communion.
"""

import unittest
from pathlib import Path
import tempfile
import shutil

from spectre.config import SpectreConfig
from spectre.agent import SpectreAgent
from spectre.ingest import FileIngestor
from spectre.memory.local_store import LocalVectorStore
from spectre.models.ollama_client import GemmaClient
from spectre.models.sentry_tracing import SentryAgentTracer


class TestSpectreAgent(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="spectre_test_")
        self.cache_dir = Path(self.test_dir) / ".cache"
        self.config = SpectreConfig(
            cache_dir=self.cache_dir,
            offline_mode=True,
            sentry_dsn="",
            mongodb_uri="",
            elevenlabs_api_key="",
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_file_ingestion_and_chunking(self):
        # Create a sample legacy file with ghost signals
        sample_file = Path(self.test_dir) / "legacy_auth.py"
        sample_file.write_text(
            "# Legacy Authentication Module\n"
            "# TODO: Fix insecure MD5 hashing from 2021\n"
            "def login(user, pw):\n"
            "    # DEPRECATED: Do not use in production!\n"
            "    return hashlib.md5(pw.encode()).hexdigest()\n",
            encoding="utf-8",
        )

        ingestor = FileIngestor(chunk_size=200, chunk_overlap=50)
        files = ingestor.scan_directory(Path(self.test_dir))
        self.assertEqual(len(files), 1)

        chunks = ingestor.chunk_file(sample_file)
        self.assertGreaterEqual(len(chunks), 1)
        self.assertIn("TODO", str(chunks[0]["metadata"]["ghost_signals"]))

    def test_local_vector_store(self):
        store_path = self.cache_dir / "test_mem.json"
        store = LocalVectorStore(storage_path=store_path)

        docs = [
            {"text": "Python machine learning pipeline", "source_file": "ml.py", "chunk_index": 0},
            {"text": "Deprecated CSS stylesheet for landing page", "source_file": "style.css", "chunk_index": 0},
        ]
        # Two dummy 4-dimensional normalized vectors
        embs = [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
        ]

        inserted = store.store_documents(docs, embs)
        self.assertEqual(inserted, 2)
        self.assertEqual(store.count(), 2)

        # Query closer to doc 0
        results = store.search([0.9, 0.1, 0.0, 0.0], top_k=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].source_file, "ml.py")

    def test_sentry_tracing_and_cost_audit(self):
        tracer = SentryAgentTracer(dsn=None)
        with tracer.span(op="test.op", description="Unit test span"):
            tracer.record_inference("gemma2:9b", prompt_tokens=100, completion_tokens=50, latency_ms=120.0, is_local=True)
            tracer.record_tool_call("search_graveyard", latency_ms=15.0, success=True)

        summary = tracer.get_audit_summary()
        self.assertEqual(summary["total_prompt_tokens"], 100)
        self.assertEqual(summary["total_completion_tokens"], 50)
        self.assertEqual(summary["total_tokens"], 150)
        self.assertEqual(summary["total_tool_calls"], 1)
        self.assertEqual(summary["local_inference_cost_usd"], 0.0)
        self.assertGreater(summary["cloud_cost_saved_usd"], 0.0)

    def test_agent_full_resurrect_and_commune_offline(self):
        agent = SpectreAgent(self.config)

        # Create dummy deprecated script
        file_path = Path(self.test_dir) / "abandoned_script.py"
        file_path.write_text("print('Ghost in the Machine test')", encoding="utf-8")

        res_result = agent.resurrect(Path(self.test_dir))
        self.assertGreaterEqual(res_result["chunks_indexed"], 1)

        commune_result = agent.commune("Why was this script abandoned?", speak=False)
        self.assertIn("response", commune_result)
        self.assertGreater(len(commune_result["memories"]), 0)


if __name__ == "__main__":
    unittest.main()
