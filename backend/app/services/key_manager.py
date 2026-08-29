import os
import sys
import time
import asyncio
import logging
from typing import List, Dict, Optional, Any, Callable, Awaitable
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

logger = logging.getLogger(__name__)


class KeyManager:
    """
    Automated Gemini API Key Pool Rotator.
    - Loads GEMINI_API_KEYS (comma-separated list) from .env.
    - Maintains an async-safe round-robin counter to rotate through the keys.
    - Maintains a blacklisted_keys dictionary with timestamps (60s cooldown on 429).
    - get_next_key() returns the next available non-blacklisted key or raises a clean error if all are exhausted.
    """

    def __init__(self, cooldown_seconds: float = 60.0):
        self.cooldown_seconds = cooldown_seconds
        self._keys: List[str] = []
        self._index: int = 0
        self._lock = asyncio.Lock()
        self.blacklisted_keys: Dict[str, float] = {}  # {key: timestamp_until_cooldown_expires}
        self.reload_keys()

    def reload_keys(self) -> List[str]:
        """Loads and parses all distinct API keys from GEMINI_API_KEYS, GEMINI_API_KEY, or GOOGLE_API_KEY."""
        raw_keys = (
            os.getenv("GEMINI_API_KEYS")
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or ""
        )

        extracted = []
        for part in raw_keys.replace("\n", ",").split(","):
            clean = part.strip()
            if clean and clean not in extracted:
                extracted.append(clean)

        self._keys = extracted
        if not self._keys:
            logger.warning("[KEY-MANAGER] No Gemini API keys found in environment variables.")
        else:
            masked = [f"{k[:6]}...{k[-4:]}" if len(k) > 10 else "***" for k in self._keys]
            print(f"[KEY-MANAGER] Initialized pool with {len(self._keys)} distinct Gemini API key(s): {', '.join(masked)}")

        return self._keys

    def get_keys_count(self) -> int:
        return len(self._keys)

    def blacklist_key(self, key: str, duration: Optional[float] = None) -> None:
        """Temporarily marks an API key as rate-limited (HTTP 429) for 60 seconds."""
        cooldown = duration if duration is not None else self.cooldown_seconds
        expiry = time.time() + cooldown
        self.blacklisted_keys[key] = expiry
        masked = f"{key[:6]}...{key[-4:]}" if len(key) > 10 else "***"
        print(f"⚠️ [KEY-ROTATOR] Blacklisted key {masked} for {cooldown:.0f}s due to 429 rate limit.")
        logger.warning("Gemini key %s blacklisted for %s seconds due to 429 quota limit.", masked, cooldown)

    def is_blacklisted(self, key: str) -> bool:
        """Checks if a key is currently under rate-limit cooldown."""
        if key not in self.blacklisted_keys:
            return False
        if time.time() >= self.blacklisted_keys[key]:
            del self.blacklisted_keys[key]
            return False
        return True

    def get_next_key(self) -> str:
        """
        Returns the next available, non-blacklisted key using round-robin rotation.
        Raises a clean error if all keys are currently rate-limited.
        """
        if not self._keys:
            self.reload_keys()
        if not self._keys:
            raise ValueError(
                "No Gemini API keys found. Please set GEMINI_API_KEYS, GEMINI_API_KEY, or GOOGLE_API_KEY in .env"
            )

        total = len(self._keys)
        # Search for next non-blacklisted key starting from current index
        for i in range(total):
            idx = (self._index + i) % total
            candidate = self._keys[idx]
            if not self.is_blacklisted(candidate):
                self._index = (idx + 1) % total
                return candidate

        # Clean expired keys and re-check
        now = time.time()
        for k in list(self.blacklisted_keys.keys()):
            if now >= self.blacklisted_keys[k]:
                del self.blacklisted_keys[k]

        for i in range(total):
            idx = (self._index + i) % total
            candidate = self._keys[idx]
            if not self.is_blacklisted(candidate):
                self._index = (idx + 1) % total
                return candidate

        # If all keys are strictly rate-limited, raise a clean fallback error
        raise RuntimeError(
            "All Gemini API keys in the pool are currently rate-limited (HTTP 429). Please wait 60 seconds before retrying."
        )

    # Aliases for backward compatibility
    def get_next_api_key(self) -> str:
        return self.get_next_key()

    def get_active_key(self) -> str:
        return self.get_next_key()

    def get_gemini_llm(
        self,
        model: str = "gemini-1.5-flash",
        temperature: float = 0.2,
        api_key: Optional[str] = None,
        max_retries: int = 1,
    ) -> ChatGoogleGenerativeAI:
        """
        Instantiates ChatGoogleGenerativeAI with the next key in rotation.
        """
        selected_key = api_key or self.get_next_key()
        masked = f"{selected_key[:6]}...{selected_key[-4:]}" if len(selected_key) > 10 else "***"
        logger.debug("Instantiating ChatGoogleGenerativeAI (model: %s) with key: %s", model, masked)

        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=selected_key,
            temperature=temperature,
            max_retries=max_retries,
        )

    def get_gemini_embeddings(
        self,
        model: str = "models/gemini-embedding-001",
        api_key: Optional[str] = None,
    ) -> GoogleGenerativeAIEmbeddings:
        """
        Instantiates GoogleGenerativeAIEmbeddings with the next key in rotation.
        """
        selected_key = api_key or self.get_next_key()
        return GoogleGenerativeAIEmbeddings(
            model=model,
            google_api_key=selected_key,
        )

    async def execute_with_failover(
        self,
        invoke_fn: Callable[[ChatGoogleGenerativeAI], Awaitable[Any]],
        model: str = "gemini-1.5-flash",
        temperature: float = 0.2,
        max_attempts: Optional[int] = None,
    ) -> Any:
        """
        Executes an async LLM invocation. If HTTP 429 (ResourceExhausted) occurs:
        1. Immediately blacklists the failing key for 60s.
        2. Acquires the next available key from the pool.
        3. Re-instantiates the model and retries the invocation immediately.
        """
        attempts = max_attempts or max(len(self._keys) * 2, 4)
        last_error = None
        fallback_models = [model, "gemini-2.5-flash", "gemini-2.0-flash"]

        for attempt in range(attempts):
            try:
                key = self.get_next_key()
            except RuntimeError as ex:
                # All keys blacklisted, wait momentarily for earliest
                if self.blacklisted_keys:
                    earliest_key = min(self.blacklisted_keys, key=lambda k: self.blacklisted_keys[k])
                    key = earliest_key
                else:
                    raise ex

            current_model_name = fallback_models[min(attempt // len(self._keys) if self._keys else 0, len(fallback_models) - 1)]

            try:
                llm = ChatGoogleGenerativeAI(
                    model=current_model_name,
                    google_api_key=key,
                    temperature=temperature,
                    max_retries=1,
                )
                return await invoke_fn(llm)

            except Exception as exc:
                last_error = exc
                err_str = str(exc).lower()
                is_429 = (
                    "429" in err_str
                    or "resource_exhausted" in err_str
                    or "quota" in err_str
                    or "rate limit" in err_str
                )

                if is_429:
                    masked = f"{key[:6]}...{key[-4:]}" if len(key) > 10 else "***"
                    print(f"⚠️ [KEY-FAILOVER] Key {masked} hit 429 on model '{current_model_name}'. Blacklisting and rotating immediately...")
                    self.blacklist_key(key, self.cooldown_seconds)
                    await asyncio.sleep(0.2)
                    continue
                else:
                    logger.error("[KEY-MANAGER] Non-429 error during LLM invocation: %s", exc)
                    raise exc

        raise last_error or RuntimeError("All Gemini API keys exhausted or rate limited.")


# Aliases & Singleton Instance
GeminiKeyManager = KeyManager
key_manager = KeyManager()
