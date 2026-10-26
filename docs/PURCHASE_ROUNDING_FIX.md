# Purchase and supplier return rounding

Receipts previously multiplied binary floats and used Python's ties-to-even `round`, while POS monetary calculations use decimal half-up rounding. This could understate a receipt and its supplier debt: quantity `0.29` at 50 cents produced 14 cents instead of 15; quantity `0.5` at 1 cent produced zero instead of 1.

The original `todo/services/purchases.py` now calculates both header and item totals with `Decimal(str(qty))` and the shared `services.money.rounded` helper. Supplier partial returns use the same helper for the cumulative refunded amount. The last return still receives the original stored residual, and the cumulative cap still prevents returning more than the stored purchase total.

Two regression tests in `tests/test_purchase_money_rounding.py` reproduced both failures before the fix. They cover the receipt header, item totals, supplier balance, partial refund allocation, final residual, stock, database integrity and foreign keys. The three receipt lines previously totalled 16 cents; they now total 19 cents (15 + 1 + 3).

This applies to new receipts and future partial returns. Existing purchases and posted returns are not rewritten. No UI change or database migration is included. Legacy documents with inconsistent stored totals still need separate reconciliation; this fix does not claim to repair historical accounts.
