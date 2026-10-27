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

## W11 — duplicate barcode stock entry

New-product conflicts now offer three explicit actions: top up one selected existing product; create a linked variant with independent stock/prices; create an independent product. Top-up changes only the selected stock through the ledger and enforces manual-stock settings/permissions. Variant links are flattened to their root and cycles are rejected. Existing product edits retain their confirmation. No historical product IDs are merged.

Five service cases and Windows ProductEditor controls cover these actions. New schema128 tables are optional when validating older backups, required for schema128 backups.

## W14 — supplier integrity

Supplier returns now aggregate repeated purchase-item rows and the total stock consumed across separate purchase lines for the same product. Partial refunds use cumulative rounding against the original purchase-line total. Regression cases reproduce over-return/over-stock requests and check final cents.

Receiving a loaded supplier order now changes stock, writes the purchase/payment and closes/links the order in one transaction. A repeated receipt is rejected even without a supplier invoice reference; failure rolls everything back. This path supports complete receipts only: a partial quantity is rejected with an explicit message instead of silently closing the whole order. A full partial-receipt/remainder workflow remains an open business requirement.

## W03 / W13 / W19 — shared shop-day reconciliation

A single isolated fixture opens with100DH, receives10units at5DH with10DH supplier payment, sells cash/mixed/credit, collects a client debt, refunds half the mixed sale, returns one unit to the supplier, makes another supplier payment, records an expense and cash in/out, then closes. Expected outcomes: stock3; client debt15DH; supplier debt30DH; net revenue59DH; gross margin29DH; counted/expected cash122DH and difference0. The fixture asserts the services, report totals and movement ledger together.

## Release limitations that remain open

- Physical printer/drawer/scanner/scale/RFID/display models and real drivers are unavailable to hosted CI. Simulated tests do not certify hardware.
- Comparative LOGICA/ToDo timings on the same shop computer, touch/DPI/RTL visual acceptance and a real second-device backup transfer remain unverified. Synthetic Windows measurements are published separately.
- Full LOGICA transaction-history migration needs a source database/schema sample and an agreed mapping; the existing ToDo catalogue exchange does not prove that migration.
- Partial supplier receipts, BL/invoice lifecycle beyond the current quote/order/receipt flow, lot/expiry FEFO/FIFO policy, specialized sector modules and the multi-cashier network topology need a product scope decision. None are silently presented as implemented.

## W07 — pack quantity regression after the handoff

The subsequent pack guard correctly rejects partial carton quantities even when there is no special carton price. Its first version also rejected fractional quantities scanned through an ordinary unit barcode, breaking both the stock-boundary regression and the required fractional shared-barcode workflow. Unit barcodes without a price override now retain fractional-product behavior; carton multipliers and explicit pack-price barcodes still enforce whole packs. Both cases are covered by service tests; delivery requires the full Windows GUI gate.

Price precedence is unchanged: explicit pack price, otherwise applicable quantity offer, otherwise active grid price, otherwise catalog price. Authorized manual prices are checked at checkout; explicit catalog-price restoration remains available. Existing stored sale prices/costs/taxes are snapshots used by returns and reports rather than recalculated from later catalog edits.

## Post-handoff validation on main

### W10 and W12 safeguards

- [W12 inventory validation](https://github.com/hmasprod-a11y/todo-pos/commit/4377c0377d8cf25e2ea8e4359babb2ab87876b95) rejects fractional counted quantities for products that disallow fractions and rejects inactive counted products before any stock movement. Rejected inventory sessions remain open for correction.
- [W10 pack returns](https://github.com/hmasprod-a11y/todo-pos/commit/6d8de69cb46b68d2cd4ff36dad6cf704a6c88f9d) preserve carton quantities on returns even when the carton barcode has no explicit price override. Fractional unit-barcode products remain supported.
- The full Windows build at 6d8de69 ran 313 unit tests, Tk smoke and integrated purchase/report tests, installed runtime and upgrade checks, and produced a verified complete Windows ZIP and installer. The [Windows run](https://github.com/hmasprod-a11y/todo-pos/actions/runs/40424887105), [tests run](https://github.com/hmasprod-a11y/todo-pos/actions/runs/40424887134) and [Quick build](https://github.com/hmasprod-a11y/todo-pos/actions/runs/40424886968) all succeeded.

### W21 automated layout and language subset

- [Statistics layout](https://github.com/hmasprod-a11y/todo-pos/commit/6098251d960bb372c616ac806f2ca8eaf527692d) arranges nine KPI cards in three columns and makes the report vertically scrollable. A Windows Tk test verifies the KPI grid and access to the lower financial summary in French, Arabic and English at a requested 1366×768 window size.
- [Settings administration layout](https://github.com/hmasprod-a11y/todo-pos/commit/4d39bba746cad592426bd4ebb28a95f210253889) separates backup and user controls into rows so their actions fit compact widths in all three languages. The Windows Tk test checks the actual control widths and labels.
- [Data recovery and database dialogs](https://github.com/hmasprod-a11y/todo-pos/commit/40dc6ed66e00fbc3388d3061894b01345bb4a4dd) now display English labels, warnings and restore confirmations. The database actions use two rows. The UI test opens the database dialog and checks the English prompts without restoring data.
- [License and administration labels](https://github.com/hmasprod-a11y/todo-pos/commit/275c2c6dfbe4e5b9b73f0697b96023feb9026052) complete the remaining explicit English text in Settings, including permissions, PIN and audit labels. The UI test opens the license dialog and checks its English sections.
- On 275c2c6 the [full Windows build](https://github.com/hmasprod-a11y/todo-pos/actions/runs/40533796776), [tests](https://github.com/hmasprod-a11y/todo-pos/actions/runs/40533796137) and [Quick build](https://github.com/hmasprod-a11y/todo-pos/actions/runs/40533796579) succeeded. The [Windows package artifact](https://github.com/hmasprod-a11y/todo-pos/actions/runs/40533796776/artifacts/12748135927) includes the installer and portable application with its runtime files. The package artifact digest is `sha256:5ef3494dffbf98f9d7e4c9e3f1b80da3f3af4fa0dbd2bdcedf4ca259233ff620`.

The automated W21 checks demonstrate reachability and selected English strings on the hosted Windows runner. They do not certify every visual state, physical touch interaction, right-to-left reading order or high-DPI rendering on the shop display.

### Requirements still needing external evidence or scope

- W04/W20: measure LOGICA and ToDo on the same shop PC with the same representative data before claiming a comparative speed or memory advantage.
- W16/W17: verify transfer on a second computer; full LOGICA history and client balances require the source schema/sample and a signed-off mapping with dry-run totals.
- W18: certify the exact printer, drawer, scanner, scale, RFID and display models physically.
- W14/W15: agree how partial supplier receipts carry remainders, and the required BL/invoice states and legal fields.
- W21: perform touch, RTL reading order, 1366×768 and DPI visual acceptance on the target hardware.
- W23/W24/W25: decide lot/expiry allocation policy, specialized sector modules and multi-cashier topology. Local SQLite is certified only for a local workstation.
