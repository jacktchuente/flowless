from __future__ import annotations

from dataclasses import dataclass
import os
import time

from django.conf import settings
from openai import OpenAI
from redis import Redis

LLM_LAST_CALL_AT_REDIS_KEY = "llm:last_call_at"
LLM_DELAY_LOCK_REDIS_KEY = "llm:delay_lock"


@dataclass
class LLMResponse:
    content: str
    raw_response: object


class LLMService:
    def __init__(
            self,
            *,
            api_key: str | None = None,
            base_url: str | None = None,
            model: str | None = None,
    ):
        self.api_key = api_key or settings.LLM_API_KEY
        self.base_url = base_url or settings.LLM_URL
        self.model = model or settings.LLM_MODEL

        if not self.api_key:
            raise ValueError("LLM_API_KEY is not configured.")
        if not self.base_url:
            raise ValueError("LLM_URL is not configured.")
        if not self.model:
            raise ValueError("LLM_MODEL is not configured.")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
        self.redis_client = self._build_redis_client()

    def complete(
            self,
            *,
            prompt: str,
            system_prompt: str | None = None,
            temperature: float = 0,
    ) -> LLMResponse:
        self._wait_for_llm_slot()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        content = response.choices[0].message.content or ""
        return LLMResponse(content=content, raw_response=response)

    @staticmethod
    def _build_redis_client() -> Redis | None:
        redis_host = getattr(settings, "REDIS_HOST", None) or os.getenv("REDIS_HOST")
        redis_port = getattr(settings, "REDIS_PORT", None) or os.getenv("REDIS_PORT")
        if not redis_host or not redis_port:
            return None
        return Redis(host=redis_host, port=int(redis_port), decode_responses=True)

    def _wait_for_llm_slot(self) -> None:
        delay_seconds = int(getattr(settings, "LLM_DELAY", 0) or 0)
        if delay_seconds <= 0 or self.redis_client is None:
            return

        lock_timeout = max(delay_seconds + 30, 60)
        with self.redis_client.lock(LLM_DELAY_LOCK_REDIS_KEY, timeout=lock_timeout, blocking_timeout=lock_timeout):
            while True:
                last_call_at = self.redis_client.get(LLM_LAST_CALL_AT_REDIS_KEY)
                if not last_call_at:
                    break

                elapsed = time.time() - float(last_call_at)
                remaining = delay_seconds - elapsed
                if remaining <= 0:
                    break

                time.sleep(min(remaining, 0.5))

            self.redis_client.set(LLM_LAST_CALL_AT_REDIS_KEY, str(time.time()))
