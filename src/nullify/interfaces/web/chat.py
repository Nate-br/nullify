from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

MODELS_DIR = Path(__file__).resolve().parents[3] / "models" / "llm"
last_report: dict[str, Any] | None = None

class ChatEngine:
    _instance: ChatEngine | None = None
    _init_lock = threading.Lock()

    def __new__(cls):
        with cls._init_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._llm = None
                cls._instance._lock = threading.Lock()
        return cls._instance

    def available(self) -> bool:
        return (MODELS_DIR / "qwen2.5-3b-instruct-q4_k_m.gguf").exists()

    def generate(self, messages: list[dict]) -> str:
        with self._lock:
            if self._llm is None:
                from llama_cpp import Llama
                self._llm = Llama(
                    model_path=str(MODELS_DIR / "qwen2.5-3b-instruct-q4_k_m.gguf"),
                    n_ctx=2048,
                    n_threads=4,
                    verbose=False,
                )
            res = self._llm.create_chat_completion(
                messages=messages,
                max_tokens=256,
                temperature=0.4,
            )
            return res["choices"][0]["message"]["content"]
