"""JSON-backed translations with deterministic safe fallbacks."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Mapping

SUPPORTED_LANGUAGES = ("en", "fr", "ar")
DEFAULT_LANGUAGE = "fr"
_TRANSLATIONS_DIR = Path(__file__).with_name("translations")


def normalize_language(language: str | None) -> str:
    """Return a supported BCP-47 base language, or the product default."""
    candidate = str(language or "").strip().lower().replace("_", "-").split("-", 1)[0]
    return candidate if candidate in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def language_direction(language: str | None) -> str:
    return "rtl" if normalize_language(language) == "ar" else "ltr"


@lru_cache(maxsize=len(SUPPORTED_LANGUAGES))
def load_catalog(language: str | None) -> Mapping[str, str]:
    """Load one shipped catalog and reject malformed translation resources."""
    normalized = normalize_language(language)
    path = _TRANSLATIONS_DIR / f"{normalized}.json"
    with path.open(encoding="utf-8") as source:
        catalog = json.load(source)
    if not isinstance(catalog, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in catalog.items()
    ):
        raise ValueError(f"Invalid translation catalog: {path.name}")
    return catalog


class _SafeValues(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


class Translator:
    """Translate stable UI keys while keeping an incomplete catalog non-fatal."""

    def __init__(self, language: str | None = None):
        self.language = normalize_language(language)

    @property
    def direction(self) -> str:
        return language_direction(self.language)

    def text(self, key: str, **values: object) -> str:
        key = str(key)
        template = load_catalog(self.language).get(key)
        if template is None and self.language != DEFAULT_LANGUAGE:
            template = load_catalog(DEFAULT_LANGUAGE).get(key)
        if template is None:
            return key
        return template.format_map(_SafeValues(values))

    __call__ = text
