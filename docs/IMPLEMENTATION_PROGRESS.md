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

## W02 — enforce checkout permissions

Checkout rechecks PRICE_EDIT and DISCOUNT for the submitting user, including held tickets. Caller flags do not authorize manual prices. Active price grids, quantity offers, pack prices and persisted open quote/order prices remain valid; document quantity allowances cannot be reused by split lines. Manual overrides are audited. Miscellaneous free-price lines retain their original behavior.

Validation: 16 additional permission regression cases; full suite includes stock-edit and returns permission tests. Catalog price restoration remains an allowed existing workflow.

## W05 / W06 — shared barcode and photos

The shared-barcode picker provides an editable × quantity and numeric keypad. Clicking a product adds it directly; the picker displays image, name and unit/pack price without stock/reference columns. Invalid, zero and nonfinite quantities leave the picker open. Cancel preserves the original sale quantity. Product identities and stocks remain separate.

Photo search checks that the file can actually be decoded before applying pagination. Missing/corrupt files and directories never create placeholder cards. File metadata invalidates the decode/thumbnail cache when an image is replaced at the same path. Explicit photo visibility remains required, regardless of barcode presence. List Article remains the default tab.

Validation: five photo service cases, existing visibility test uses a real image fixture; Windows Tk integration covers quantity3, fractional1.5, zero, cancel, repeat scan and image-only cards. Windows evidence is attached by Actions.

## W08 / W09 — ownership and duplicate payment

Held-ticket lists follow cashier ownership, matching existing resume/checkout rules. Checkout accepts an optional idempotency key tied to cashier, session and exact request fingerprint. A committed retry returns the original result without sale/payment/stock/sequence writes; reusing a key for a changed ticket is rejected. The Tk checkout retains the key across retries and resets after successful cart clearing. Existing transactional held-ticket consumption and post-commit print-error handling remain active.

Schema128 adds the request journal, preserving prior records. Backup validation supports128. Seven new cases cover sequential/concurrent retry, mismatch, rollback/retry, held retry, concurrent held consumption and ownership. Windows installer/upgrade and full backup tests are required on the delivery SHA.

## Remaining diagnostic work

W03/W07/W10/W12–W19 already have substantial regression coverage in the repository (rounding, packs, tax snapshots, cash, debts, supplier orders/returns, inventory, documents, reports, full media backups and import). Existing implementation is not a claim of complete LOGICA parity. Remaining gaps and requirements must stay open until independently demonstrated. Physical peripherals and comparative measurements on the same shop PC cannot be certified by hosted CI. Lot/expiry strategy and multi-workstation topology require explicit business scope before implementation.
