"""Translation primitives for the global ToDo POS UI."""

from .service import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    Translator,
    language_direction,
    load_catalog,
    normalize_language,
)

__all__ = [
    "DEFAULT_LANGUAGE",
    "SUPPORTED_LANGUAGES",
    "Translator",
    "language_direction",
    "load_catalog",
    "normalize_language",
]
