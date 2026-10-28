"""
ElevenLabs TTS voice synthesis for Spectre-CLI.
Targeting prize: 'Best Use of ElevenLabs'.
Narrates resurrected memories and séance revelations in eerie, atmospheric spoken audio.
Provides zero-friction offline fallback when unauthenticated.
"""

import os
import logging
from pathlib import Path
from typing import Optional
import requests

from spectre.models.sentry_tracing import SentryAgentTracer

logger = logging.getLogger("spectre.speech")


class GhostNarrator:
    """
    Synthesizes eerie spoken-word outputs using ElevenLabs Text-to-Speech.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        voice_id: str = "pFZP5JQG7iQjIQuC4Bku",  # Default: Lily / Whisper
        model_id: str = "eleven_turbo_v2_5",
        tracer: Optional[SentryAgentTracer] = None,
    ):
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY", "")
        self.voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID", "pFZP5JQG7iQjIQuC4Bku")
        self.model_id = model_id or os.getenv("ELEVENLABS_MODEL_ID", "eleven_turbo_v2_5")
        self.tracer = tracer or SentryAgentTracer()
        self.output_dir = Path(".spectre_cache/audio")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 10)

    def speak(self, text: str, output_filename: str = "seance_whisper.mp3") -> Optional[Path]:
        """
        Converts text into eerie spoken word audio via ElevenLabs, traced in Sentry.
        """
        if not self.is_configured:
            logger.info("ElevenLabs API key not provided; skipping spoken audio generation.")
            return None

        # Clean markdown characters for smoother voice synthesis
        clean_text = text.replace("**", "").replace("#", "").replace("`", "").strip()
        if not clean_text:
            return None

        # Truncate to first 500 chars for snappy narration
        speech_text = clean_text[:500]

        span_data = {
            "ai.voice_id": self.voice_id,
            "ai.model_id": self.model_id,
            "ai.characters": len(speech_text),
        }

        with self.tracer.span(op="ai.tts.generate", description="ElevenLabs TTS synthesis", data=span_data):
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key,
            }
            payload = {
                "text": speech_text,
                "model_id": self.model_id,
                "voice_settings": {
                    "stability": 0.35,  # Slightly lower stability for a breathy, ghostly cadence
                    "similarity_boost": 0.85,
                    "style": 0.45,
                    "use_speaker_boost": True,
                },
            }

            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=20.0)
                resp.raise_for_status()

                out_path = self.output_dir / output_filename
                with open(out_path, "wb") as f:
                    f.write(resp.content)

                logger.info(f"Ghostly whisper saved to: {out_path}")
                return out_path
            except Exception as e:
                logger.warning(f"ElevenLabs TTS failed: {e}. Continuing with terminal-only séance.")
                return None
