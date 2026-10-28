"""
Sentry Agent Tracing integration for Spectre-CLI.
Audits token usage, tool latency, span hierarchies, and local inference cost savings.
Targeting prize: 'Best Use of Sentry Agent Tracing'.
"""

import time
import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager

try:
    import sentry_sdk
    from sentry_sdk.tracing import Span
    HAS_SENTRY = True
except ImportError:
    HAS_SENTRY = False

logger = logging.getLogger("spectre.tracing")


class SentryAgentTracer:
    """
    Manages Sentry tracing for AI Agent lifecycle, LLM inference, RAG retrieval, and tools.
    """

    def __init__(self, dsn: Optional[str] = None, environment: str = "seance-production"):
        self.enabled = False
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tool_calls = 0
        self.total_inference_time_ms = 0.0

        if HAS_SENTRY and dsn:
            try:
                sentry_sdk.init(
                    dsn=dsn,
                    traces_sample_rate=1.0,
                    environment=environment,
                    send_default_pii=False,  # Privacy first: do not leak raw file contents
                    release="spectre-cli@1.0.0",
                )
                self.enabled = True
                logger.info("Sentry Agent Tracing initialized successfully.")
            except Exception as e:
                logger.warning(f"Failed to initialize Sentry SDK: {e}")
        else:
            logger.info("Sentry Agent Tracing running in offline/local telemetry mode.")

    @contextmanager
    def span(self, op: str, description: str, data: Optional[Dict[str, Any]] = None):
        """
        Hierarchical span context manager for AI agent actions.
        """
        start_time = time.perf_counter()
        span_obj = None

        if self.enabled and HAS_SENTRY:
            span_obj = sentry_sdk.start_span(op=op, description=description)
            span_obj.__enter__()
            if data:
                for k, v in data.items():
                    span_obj.set_data(k, v)

        try:
            yield span_obj
        except Exception as exc:
            if self.enabled and HAS_SENTRY:
                sentry_sdk.capture_exception(exc)
            raise
        finally:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            if span_obj:
                span_obj.set_data("duration_ms", elapsed_ms)
                span_obj.__exit__(None, None, None)

    def record_inference(
        self,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        is_local: bool = True,
    ):
        """
        Audits token usage and local inference savings.
        """
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_inference_time_ms += latency_ms

        # Typical cloud LLM costs: ~$3.00/1M input tokens, ~$15.00/1M output tokens
        cloud_equiv_cost = (prompt_tokens * 3.0 / 1_000_000) + (completion_tokens * 15.0 / 1_000_000)
        local_cost = 0.0 if is_local else cloud_equiv_cost

        if self.enabled and HAS_SENTRY:
            sentry_sdk.set_measurement("ai.tokens.prompt", prompt_tokens)
            sentry_sdk.set_measurement("ai.tokens.completion", completion_tokens)
            sentry_sdk.set_measurement("ai.tokens.total", prompt_tokens + completion_tokens)
            sentry_sdk.set_measurement("ai.inference.latency_ms", latency_ms)
            sentry_sdk.set_tag("ai.model", model_name)
            sentry_sdk.set_tag("ai.inference.type", "local_offline" if is_local else "cloud")
            sentry_sdk.set_extra("ai.cloud_savings_usd", cloud_equiv_cost - local_cost)

    def record_tool_call(self, tool_name: str, latency_ms: float, success: bool):
        """
        Audits tool invocation latency and reliability.
        """
        self.total_tool_calls += 1
        if self.enabled and HAS_SENTRY:
            sentry_sdk.set_measurement(f"ai.tool.{tool_name}.latency_ms", latency_ms)
            sentry_sdk.set_tag(f"ai.tool.{tool_name}.success", str(success))

    def get_audit_summary(self) -> Dict[str, Any]:
        """
        Returns full audit report of agent telemetry, token usage, and cost savings.
        """
        cloud_cost_saved = (
            (self.total_prompt_tokens * 3.0 / 1_000_000)
            + (self.total_completion_tokens * 15.0 / 1_000_000)
        )
        return {
            "sentry_enabled": self.enabled,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
            "total_tool_calls": self.total_tool_calls,
            "total_inference_time_ms": round(self.total_inference_time_ms, 2),
            "local_inference_cost_usd": 0.000,
            "cloud_cost_saved_usd": round(cloud_cost_saved, 5),
        }
