"""Deterministic tax calculations using integer minor units only."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaxBreakdown:
    net_cents: int
    tax_cents: int
    gross_cents: int
    rate_basis_points: int
    tax_included: bool


def _round_div(numerator: int, denominator: int) -> int:
    """Round positive ratios half up, deterministically across Python versions."""
    return (numerator * 2 + denominator) // (denominator * 2)


def calculate_tax(
    amount_cents: int, rate_basis_points: int, *, tax_included: bool
) -> TaxBreakdown:
    """Calculate a receipt-safe tax snapshot from a net or gross line amount.

    amount_cents is gross when tax_included is true; otherwise it is net.
    The result always satisfies gross = net + tax exactly.
    """
    amount = int(amount_cents)
    rate = int(rate_basis_points)
    if amount < 0:
        raise ValueError("amount_cents must be non-negative")
    if not 0 <= rate <= 100000:
        raise ValueError("rate_basis_points must be between 0 and 100000")

    if tax_included:
        gross = amount
        net = _round_div(gross * 10000, 10000 + rate)
        tax = gross - net
    else:
        net = amount
        tax = _round_div(net * rate, 10000)
        gross = net + tax
    return TaxBreakdown(net, tax, gross, rate, bool(tax_included))
