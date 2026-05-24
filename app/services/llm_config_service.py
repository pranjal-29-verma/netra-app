"""
In-memory cache for the active LLM config.
Loaded once on startup and refreshed whenever admin changes the config.
Chat endpoint reads from here — zero DB hits per message.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class _CachedConfig:
    model: str
    api_key: str  # already decrypted


_cache: Optional[_CachedConfig] = None
_use_custom: bool = False


def get_active_llm() -> tuple[str, str | None]:
    """
    Returns (model_name, api_key).
    api_key is None when falling back to .env so llm_service uses its own resolver.
    """
    if _use_custom and _cache is not None:
        return _cache.model, _cache.api_key
    return None, None  # signal: use .env defaults


def reload(db) -> None:
    """Called on startup and after any admin change. Reads DB once."""
    global _cache, _use_custom
    from app.models.llm_config import LLMConfig, SystemConfig
    from app.core.encryption import decrypt

    sys_cfg = db.query(SystemConfig).filter(SystemConfig.id == 1).first()
    _use_custom = sys_cfg.use_custom_llm if sys_cfg else False

    active = db.query(LLMConfig).filter(LLMConfig.is_active == True).first()
    if active:
        _cache = _CachedConfig(
            model=active.model_name,
            api_key=decrypt(active.api_key_encrypted),
        )
    else:
        _cache = None


def set_use_custom(value: bool) -> None:
    global _use_custom
    _use_custom = value


def set_active_cache(model: str, api_key_plain: str) -> None:
    global _cache
    _cache = _CachedConfig(model=model, api_key=api_key_plain)


def clear_active_cache() -> None:
    global _cache
    _cache = None
