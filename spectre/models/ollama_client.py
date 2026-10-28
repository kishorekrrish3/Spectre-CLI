"""
Local Gemma-2 LLM and embedding client via Ollama.
Targeting prize: 'Best Use of Gemma'.
Provides zero-cloud data privacy and graceful offline simulation fallback.
"""

import time
import hashlib
import logging
from typing import List, Dict, Any, Optional
import requests

from spectre.models.sentry_tracing import SentryAgentTracer

logger = logging.getLogger("spectre.gemma")


class GemmaClient:
    """
    Interface for local Gemma-2 model inference and embedding generation via Ollama.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "gemma2:9b",
        embed_model: str = "nomic-embed-text",
        tracer: Optional[SentryAgentTracer] = None,
        force_offline: bool = False,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.embed_model = embed_model
        self.tracer = tracer or SentryAgentTracer()
        self.force_offline = force_offline
        self._is_alive = False
        self._check_connection()

    def _check_connection(self) -> bool:
        if self.force_offline:
            self._is_alive = False
            return False
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=1.5)
            self._is_alive = resp.status_code == 200
        except Exception:
            self._is_alive = False
        return self._is_alive

    @property
    def is_available(self) -> bool:
        return self._is_alive

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> Dict[str, Any]:
        """
        Generates text using local Gemma-2 via Ollama, traced via Sentry.
        """
        start_time = time.perf_counter()
        span_data = {
            "ai.model_id": self.model,
            "ai.temperature": temperature,
            "ai.system_prompt": system_prompt[:120] if system_prompt else None,
        }

        with self.tracer.span(op="ai.inference", description=f"Gemma-2 generate ({self.model})", data=span_data):
            if not self._is_alive:
                return self._offline_fallback_generate(prompt, system_prompt, start_time)

            payload = {
                "model": self.model,
                "prompt": prompt,
                "system": system_prompt or "",
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            }

            try:
                resp = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=60.0)
                resp.raise_for_status()
                data = resp.json()

                response_text = data.get("response", "")
                prompt_tokens = data.get("prompt_eval_count", len(prompt.split()))
                completion_tokens = data.get("eval_count", len(response_text.split()))
                duration_ms = (time.perf_counter() - start_time) * 1000

                self.tracer.record_inference(
                    model_name=self.model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    latency_ms=duration_ms,
                    is_local=True,
                )

                return {
                    "text": response_text,
                    "model": self.model,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "duration_ms": duration_ms,
                    "source": "ollama_gemma2",
                }
            except Exception as e:
                logger.warning(f"Ollama inference error: {e}. Falling back to spectral echo.")
                return self._offline_fallback_generate(prompt, system_prompt, start_time)

    def get_embedding(self, text: str) -> List[float]:
        """
        Generates vector embeddings for a text snippet.
        """
        with self.tracer.span(op="ai.embedding", description=f"Embedding ({self.embed_model})"):
            if not self._is_alive:
                return self._offline_fallback_embedding(text)

            payload = {
                "model": self.embed_model,
                "prompt": text,
            }

            try:
                resp = requests.post(f"{self.base_url}/api/embeddings", json=payload, timeout=15.0)
                resp.raise_for_status()
                data = resp.json()
                return data.get("embedding", [])
            except Exception as e:
                logger.warning(f"Ollama embedding error: {e}. Falling back to synthetic vector.")
                return self._offline_fallback_embedding(text)

    def _offline_fallback_generate(
        self, prompt: str, system_prompt: Optional[str], start_time: float
    ) -> Dict[str, Any]:
        """
        Graceful offline fallback when Ollama daemon is unreachable.
        """
        duration_ms = (time.perf_counter() - start_time) * 1000
        tokens_in = len(prompt.split())

        spectral_response = (
            "*[The séance bell tolls in offline stillness]*\n\n"
            "A faint spectral resonance echoes through the machine. The physical spirit "
            f"of Gemma-2 is resting (Ollama server not detected at {self.base_url}).\n\n"
            "Yet the historical ether remembers: the graveyard whispers of deprecated functions, "
            "abandoned configurations, and orphaned TODO comments waiting for renewal.\n\n"
            f"> Re-summon local Gemma-2 anytime with: `ollama run {self.model}`"
        )
        tokens_out = len(spectral_response.split())

        self.tracer.record_inference(
            model_name=f"{self.model}-offline-echo",
            prompt_tokens=tokens_in,
            completion_tokens=tokens_out,
            latency_ms=duration_ms,
            is_local=True,
        )

        return {
            "text": spectral_response,
            "model": f"{self.model} (offline-simulation)",
            "prompt_tokens": tokens_in,
            "completion_tokens": tokens_out,
            "duration_ms": duration_ms,
            "source": "offline_echo",
        }

    def _offline_fallback_embedding(self, text: str, dimension: int = 768) -> List[float]:
        """
        Generates a deterministic 768-dim pseudo-vector using MD5/SHA256 seeds for offline operation.
        """
        import numpy as np

        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16) % (2**32)
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(dimension)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()
