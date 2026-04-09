"""KidOS TTS Engine — Local Text-to-Speech Tool"""

import asyncio
import re
from concurrent.futures import ThreadPoolExecutor

import pyttsx3

from kidos.core.logger import get_logger

logger = get_logger("kidos.tools.tts")


class TTSTool:
    """Wrapper around pyttsx3 for server-side audio playback.

    pyttsx3 uses Windows SAPI5 COM objects which must be initialized
    on the same thread that calls runAndWait(). We use a dedicated
    single-thread executor so the COM apartment stays consistent
    and does NOT block the FastAPI event loop.
    """

    def __init__(self, rate: int = 170, volume: float = 1.0, voice_index: int = 1):
        self.rate = rate
        self.volume = volume
        self.voice_index = voice_index
        self._executor = ThreadPoolExecutor(max_workers=1)
        logger.info("TTSTool initialized (rate=%d, vol=%.1f)", rate, volume)

    # ── Internal sync worker ─────────────────────────────────────────────

    def _speak_sync(self, text: str) -> None:
        """Run on the dedicated worker thread — never call from async."""
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", self.rate)
            engine.setProperty("volume", self.volume)

            voices = engine.getProperty("voices")
            if voices and len(voices) > self.voice_index:
                engine.setProperty("voice", voices[self.voice_index].id)

            logger.info('Speaking (%d chars): "%s …"', len(text), text[:80])
            engine.say(text)
            engine.runAndWait()
            engine.stop()
            logger.info("Speech finished successfully.")
        except Exception as e:
            logger.error("TTS worker error: %s", e, exc_info=True)

    # ── Public async API ─────────────────────────────────────────────────

    @staticmethod
    def _clean(text: str) -> str:
        """Strip markdown / emoji so the voice reads clean prose."""
        text = re.sub(r"[*_`~#>]", "", text)           # markdown chars
        text = re.sub(r"\[.*?\]\(.*?\)", "", text)      # [link](url)
        text = re.sub(r"!\[.*?\]\(.*?\)", "", text)     # ![img](url)
        text = re.sub(
            r"[\U0001F600-\U0001FAFF\u2600-\u27BF]", "", text  # emoji
        )
        return text.strip()

    async def speak(self, text: str) -> None:
        """Queue text for speech — returns immediately, audio plays in background."""
        if not text:
            return
        clean = self._clean(text)
        if not clean:
            return
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._executor, self._speak_sync, clean)
