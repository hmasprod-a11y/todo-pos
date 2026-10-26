# Implementation progress — LOGICA / ToDo comparison

## W00 — source baseline

- Canonical repository: `hmasprod-a11y/todo-pos` (transferred from `holemed02-sudo/todo-pos`).
- Starting main commit: `86430215472de313e39e863d17eaacd799cc26ac`.
- The uploaded Windows archive identified `d6bc5c74a2ad2546b285c8cf0850e49ca6a70170`; main is newer. The current `todo/services/sales.py` was compared with that archive and its text is identical before this change. Other main changes are preserved.
- Source of truth is `todo/`, with existing `tests/` and three workflows; `baseline/`, `overrides/` and packaged `_internal` are not edited.

## W01 — aggregate checkout stock guard

A product can appear in several cart lines through different barcodes or packs. Previously each line was checked against the same starting stock. With `block_insufficient_stock=1` and `allow_negative_stock=1`, two quantities of 6 could sell against stock 10 and leave -2. The settings UI tries to keep these flags mutually exclusive, but the business service must also handle inconsistent stored settings.

Checkout now adds the required base-unit quantities by `product_id`, then checks the combined demand inside the existing write transaction before sale, payment, stock movement or ticket sequence writes. An explicit block takes precedence over allowing negative stock. Distinct products sharing a barcode retain independent stock. Disabled stock tracking and miscellaneous items retain their existing behavior.

### Validation

- The new regression module fails in 5 cases on the original service.
- All 12 regression tests pass after the fix, including all policy combinations, exact/fractional boundaries, packs, shared barcode/different products, disabled tracking, miscellaneous items, invalid quantities and rollback invariants.
- Full local source suite: 264 tests passed.
- Windows workflows and packaged EXE validation must pass on the delivery commit; their status is recorded by GitHub Actions rather than assumed from local results.

## Next work

- W02: enforce sensitive price/discount permissions at business-service boundaries while preserving authorized price grids, promotions and stored quote/order prices.
- W03 and later: continue the shared financial reconciliation tests and the staged diagnostic backlog. W01 does not close those separate tasks.
