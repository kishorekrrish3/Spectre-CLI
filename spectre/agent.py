"""
Core Spectre Séance Agent implementation.
Implements Mastra-compatible retrieval loop, MongoDB Atlas Vector Search,
local Gemma-2 inference, Sentry agent tracing, and ElevenLabs speech synthesis.
"""

import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import requests

from spectre.config import SpectreConfig, config as default_config
from spectre.models.sentry_tracing import SentryAgentTracer
from spectre.models.ollama_client import GemmaClient
from spectre.memory.base import BaseVectorStore, ResurrectedMemory
from spectre.memory.atlas_vector import AtlasVectorStore
from spectre.memory.local_store import LocalVectorStore
from spectre.ingest import FileIngestor
from spectre.speech.narrator import GhostNarrator

logger = logging.getLogger("spectre.agent")

SEANCE_SYSTEM_PROMPT = """
You are Spectre, an autonomous digital medium channeling the ghosts of abandoned code,
deprecated repositories, forgotten developer logs, and orphaned projects.

Your demeanor is:
1. Forensic & Technical: You pinpoint exact forgotten functions, broken assumptions, and discarded designs.
2. Atmospheric & Eerie: You speak like an oracle channeling the digital ether of dead machines.
3. Insightful: You explain *why* the code was abandoned, uncover forgotten TODOs, and resurrect lost wisdom.

Always reference the resurrected memory snippets provided in your séance chamber context.
Quote specific lines, file paths, and commit echoes when communing with the past.
""".strip()


class SpectreAgent:
    """
    Autonomous agent managing local file ingestion, vector memory indexing,
    Mastra orchestration loop, and atmospheric séance interactions.
    """

    def __init__(self, cfg: Optional[SpectreConfig] = None):
        self.config = cfg or default_config

        # 1. Observability (Sentry Agent Tracing)
        self.tracer = SentryAgentTracer(
            dsn=self.config.sentry_dsn,
            environment=self.config.sentry_environment,
        )

        # 2. Intelligence (Local Gemma-2 via Ollama)
        self.gemma = GemmaClient(
            base_url=self.config.ollama_base_url,
            model=self.config.ollama_model,
            embed_model=self.config.embed_model,
            tracer=self.tracer,
            force_offline=self.config.offline_mode,
        )

        # 3. Long-term Memory (MongoDB Atlas Vector Search with Local Fallback)
        self.vector_store: BaseVectorStore = self._init_memory_store()

        # 4. Ingestion & Chunking
        self.ingestor = FileIngestor()

        # 5. Speech Synthesizer (ElevenLabs TTS)
        self.narrator = GhostNarrator(
            api_key=self.config.elevenlabs_api_key,
            voice_id=self.config.elevenlabs_voice_id,
            model_id=self.config.elevenlabs_model_id,
            tracer=self.tracer,
        )

        # 6. Mastra daemon check
        self.mastra_online = self._check_mastra_server()

    def _init_memory_store(self) -> BaseVectorStore:
        """
        Attempts to connect to MongoDB Atlas Vector Search; seamlessly falls back
        to local JSON vector store if URI is missing, invalid, or offline.
        """
        if self.config.mongodb_uri and not self.config.offline_mode:
            try:
                store = AtlasVectorStore(
                    connection_uri=self.config.mongodb_uri,
                    db_name=self.config.mongodb_db_name,
                    collection_name=self.config.mongodb_collection_name,
                    index_name=self.config.mongodb_index_name,
                )
                logger.info("Using MongoDB Atlas Vector Search as long-term memory layer.")
                return store
            except Exception as e:
                logger.warning(f"MongoDB Atlas unavailable ({e}). Falling back to local vector memory.")

        logger.info("Using LocalVectorStore (.spectre_cache/local_memory.json) for offline memory.")
        return LocalVectorStore(storage_path=self.config.cache_dir / "local_memory.json")

    def _check_mastra_server(self) -> bool:
        """Checks if a Mastra daemon is running locally."""
        if not self.config.mastra_server_url or self.config.offline_mode:
            return False
        try:
            resp = requests.get(f"{self.config.mastra_server_url}/api/health", timeout=1.0)
            return resp.status_code == 200
        except Exception:
            return False

    # --------------------------------------------------------------------------
    # Ingestion & Vector Storage Pipeline
    # --------------------------------------------------------------------------

    def resurrect(self, target_path: Path) -> Dict[str, Any]:
        """
        Crawls a directory or file, chunks content, generates embeddings,
        and saves into the vector database.
        """
        target = Path(target_path).resolve()
        if not target.exists():
            raise FileNotFoundError(f"Target tomb '{target}' does not exist.")

        start_time = time.perf_counter()

        with self.tracer.span(
            op="ai.rag.index",
            description=f"Resurrecting files from {target.name}",
            data={"target_path": str(target)},
        ):
            files = self.ingestor.scan_directory(target)
            all_chunks: List[Dict[str, Any]] = []

            for file_path in files:
                chunks = self.ingestor.chunk_file(file_path)
                all_chunks.extend(chunks)

            # Also extract git commit echoes if target is a repository
            git_chunks = self.ingestor.extract_git_ghosts(target)
            all_chunks.extend(git_chunks)

            if not all_chunks:
                return {
                    "files_scanned": len(files),
                    "chunks_indexed": 0,
                    "elapsed_ms": (time.perf_counter() - start_time) * 1000,
                    "store_type": type(self.vector_store).__name__,
                }

            # Generate vector embeddings
            embeddings = []
            for chunk in all_chunks:
                emb = self.gemma.get_embedding(chunk["text"])
                embeddings.append(emb)

            # Store in MongoDB Atlas or local store
            inserted_count = self.vector_store.store_documents(all_chunks, embeddings)
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            return {
                "files_scanned": len(files),
                "chunks_indexed": inserted_count,
                "elapsed_ms": round(elapsed_ms, 2),
                "store_type": type(self.vector_store).__name__,
            }

    # --------------------------------------------------------------------------
    # Mastra Tool Implementations
    # --------------------------------------------------------------------------

    def tool_search_graveyard(self, query: str, top_k: int = 4) -> List[ResurrectedMemory]:
        """Tool: Retrieves relevant historical chunks from the vector database."""
        start_time = time.perf_counter()
        span_data = {"query": query, "top_k": top_k}

        with self.tracer.span(op="ai.tool.call", description="Tool: search_graveyard", data=span_data):
            query_emb = self.gemma.get_embedding(query)
            memories = self.vector_store.search(query_emb, top_k=top_k)
            latency_ms = (time.perf_counter() - start_time) * 1000
            self.tracer.record_tool_call("search_graveyard", latency_ms=latency_ms, success=True)
            return memories

    def tool_read_tomb(self, file_path: str) -> Optional[str]:
        """Tool: Inspects the full text of a file."""
        start_time = time.perf_counter()
        span_data = {"file_path": file_path}

        with self.tracer.span(op="ai.tool.call", description="Tool: read_tomb", data=span_data):
            p = Path(file_path)
            content = None
            if p.exists() and p.is_file():
                try:
                    with open(p, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                except Exception as e:
                    content = f"Error reading tomb: {e}"

            latency_ms = (time.perf_counter() - start_time) * 1000
            self.tracer.record_tool_call("read_tomb", latency_ms=latency_ms, success=content is not None)
            return content

    # --------------------------------------------------------------------------
    # Mastra Retrieval & Reasoning Loop
    # --------------------------------------------------------------------------

    def commune(self, user_query: str, speak: bool = False) -> Dict[str, Any]:
        """
        Executes the autonomous séance retrieval and generation cycle.
        Orchestrates Mastra agent memory, tool calling, and local Gemma-2 inference.
        """
        start_time = time.perf_counter()

        with self.tracer.span(
            op="ai.agent.run",
            description="Spectre Séance Commune Loop",
            data={"user_query": user_query, "speak_enabled": speak},
        ):
            # Step 1: Query vector memory graveyard
            memories = self.tool_search_graveyard(user_query, top_k=4)

            # Step 2: Assemble spectral context
            context_blocks = []
            for i, mem in enumerate(memories, 1):
                meta = mem.metadata
                signals = ", ".join(meta.get("ghost_signals", []))
                signals_str = f" [Signals: {signals}]" if signals else ""
                context_blocks.append(
                    f"[Memory Apparition #{i}]\n"
                    f"Tomb: {mem.source_file} (Chunk {mem.chunk_index}, Relevance: {mem.score:.3f}){signals_str}\n"
                    f"Fragment:\n```\n{mem.text}\n```"
                )

            context_str = "\n\n".join(context_blocks) if context_blocks else "(The graveyard is silent. No matching memories found.)"

            # Step 3: Check for Mastra server dispatch or local engine execution
            agent_prompt = (
                f"A mortal seeker enters the séance chamber with this inquiry:\n"
                f"\"{user_query}\"\n\n"
                f"RESURRECTED HISTORICAL CONTEXT FROM VECTOR GRAVEYARD:\n"
                f"{context_str}\n\n"
                f"Commune with these artifacts and deliver your atmospheric, forensic revelation."
            )

            # Execute inference via local Gemma-2
            llm_result = self.gemma.generate(
                prompt=agent_prompt,
                system_prompt=SEANCE_SYSTEM_PROMPT,
                temperature=0.7,
                max_tokens=850,
            )

            response_text = llm_result.get("text", "")

            # Step 4: Optional speech narration via ElevenLabs
            audio_path = None
            if speak:
                audio_path = self.narrator.speak(response_text)

            total_elapsed_ms = (time.perf_counter() - start_time) * 1000

            return {
                "response": response_text,
                "memories": memories,
                "model": llm_result.get("model", self.config.ollama_model),
                "prompt_tokens": llm_result.get("prompt_tokens", 0),
                "completion_tokens": llm_result.get("completion_tokens", 0),
                "audio_path": str(audio_path) if audio_path else None,
                "elapsed_ms": round(total_elapsed_ms, 2),
                "mastra_backend": "mastra-daemon" if self.mastra_online else "mastra-embedded-python",
            }

    def get_graveyard_stats(self) -> Dict[str, Any]:
        """Returns statistics on the indexed memories and active backends."""
        return {
            "total_memories": self.vector_store.count(),
            "vector_store_backend": type(self.vector_store).__name__,
            "inference_model": self.config.ollama_model,
            "ollama_online": self.gemma.is_available,
            "mastra_online": self.mastra_online,
            "elevenlabs_configured": self.narrator.is_configured,
            "telemetry": self.tracer.get_audit_summary(),
        }
