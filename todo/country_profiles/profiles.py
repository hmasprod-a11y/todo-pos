"""Explicit country presentation profiles; these are not fiscal compliance claims."""

from __future__ import annotations

from dataclasses import dataclass


DEFAULT_COUNTRY_CODE = "MA"


@dataclass(frozen=True)
class CountryProfile:
    code: str
    currency: str
    currency_position: str
    decimal_separator: str
    date_format: str
    tax_label: str
    default_tax_rate_basis_points: int
    default_language: str

    def __post_init__(self):
        if self.currency_position not in ("prefix", "suffix"):
            raise ValueError("currency_position must be prefix or suffix")
        if not 0 <= self.default_tax_rate_basis_points <= 10000:
            raise ValueError("tax rate must be expressed in basis points")


PROFILES = {
    "MA": CountryProfile("MA", "DH", "suffix", ",", "DD/MM/YYYY", "TVA", 2000, "fr"),
    "FR": CountryProfile("FR", "€", "suffix", ",", "DD/MM/YYYY", "TVA", 2000, "fr"),
    "GB": CountryProfile("GB", "£", "prefix", ".", "DD/MM/YYYY", "VAT", 2000, "en"),
    "AE": CountryProfile("AE", "AED", "suffix", ".", "DD/MM/YYYY", "VAT", 500, "ar"),
    "SA": CountryProfile("SA", "SAR", "suffix", ".", "DD/MM/YYYY", "VAT", 1500, "ar"),
    "US": CountryProfile("US", "$", "prefix", ".", "MM/DD/YYYY", "Sales tax", 0, "en"),
}


def normalize_country_code(country_code: str | None) -> str:
    candidate = str(country_code or "").strip().upper()
    return candidate if candidate in PROFILES else DEFAULT_COUNTRY_CODE


def get_country_profile(country_code: str | None = None) -> CountryProfile:
    return PROFILES[normalize_country_code(country_code)]


def format_money(amount_cents: int, profile: CountryProfile | None = None) -> str:
    """Format integer minor units without leaking a country assumption into sales."""
    profile = profile or get_country_profile()
    amount = int(amount_cents)
    sign = "-" if amount < 0 else ""
    absolute = abs(amount)
    whole, fraction = divmod(absolute, 100)
    grouping = "," if profile.decimal_separator == "." else " "
    whole_text = f"{whole:,}".replace(",", grouping)
    number = f"{sign}{whole_text}{profile.decimal_separator}{fraction:02d}"
    return f"{profile.currency}{number}" if profile.currency_position == "prefix" else f"{number} {profile.currency}"
