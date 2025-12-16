from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_env: str
    db_path: str
    llm_provider: str
    require_confirm_for_costly_runs: bool
    max_llm_calls_per_day: int
    max_embed_calls_per_day: int

    @staticmethod
    def from_env() -> "Settings":
        def _b(name: str, default: str) -> bool:
            return os.getenv(name, default).strip() in ("1", "true", "True", "yes", "YES")

        def _i(name: str, default: str) -> int:
            return int(os.getenv(name, default).strip())

        return Settings(
            app_env=os.getenv("APP_ENV", "dev").strip(),
            db_path=os.getenv("DB_PATH", "/app/_local/data/app.db").strip(),
            llm_provider=os.getenv("LLM_PROVIDER", "openai").strip(),
            require_confirm_for_costly_runs=_b("DEFAULT_REQUIRE_CONFIRM_FOR_COSTLY_RUNS", "1"),
            max_llm_calls_per_day=_i("MAX_LLM_CALLS_PER_DAY", "50"),
            max_embed_calls_per_day=_i("MAX_EMBED_CALLS_PER_DAY", "200"),
        )
