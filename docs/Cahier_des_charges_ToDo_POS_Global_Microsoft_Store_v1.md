# Cahier des charges — ToDo POS Global / Microsoft Store

**Version:** v1  
**Target:** ToDo POS 2.x  
**Primary platform:** Windows / Microsoft Store  
**Business model:** Freemium global  
**Principle:** Offline-first; internet only for services that require it.

## 1. Product vision
Build one global ToDo POS core, then add:
- Languages
- Country Profiles
- Tax/Fiscal Modules
- Commercial Plans

The same core must serve Morocco, UK, UAE, France and other markets without forks.

## 2. Commercial editions
### ToDo Free
- Free forever
- Ads allowed only outside critical cashier flows
- Sale / barcode / basic stock
- Product limit configurable (initial hypothesis: 1000)
- One user
- Basic reports
- Local backup

### ToDo Pro
- One-time purchase / durable entitlement
- No ads
- Unlimited products
- Full suppliers/purchases
- Promotions
- Loyalty
- Advanced statistics
- Customer display
- Scale / RFID / serial devices
- Advanced import/export
- Permissions / multi-user

Future optional add-ons:
- Cloud backup
- Multi-store
- Advanced analytics

## 3. Ads policy
Ads must never appear in:
- Sale screen
- Payment
- Change
- Cash closure
- Receipt

Allowed:
- Dashboard
- Settings
- Reports
- About

Offline loss of ads must never affect POS operation.

## 4. Localization
P0 languages:
- English
- French
- Arabic

Move away from hardcoded two-language `self.tr(fr, ar)`.
Target architecture:
- `translations/en.json`
- `translations/fr.json`
- `translations/ar.json`

Arabic requires real RTL behavior.

## 5. Country Profiles
First-run country selection.
Country profile controls:
- Currency
- Currency placement
- Decimal separator
- Date format
- Tax terminology
- Default tax behavior
- Receipt fields
- Fiscal connector availability
- Default languages

Never claim a country compliance level before it is actually implemented and tested.

## 6. Global Tax Engine
Each product must support:
- Tax class / rate
- Tax included in price: yes/no

Each sale must snapshot:
- unit price
- net amount
- tax rate
- tax amount
- gross amount

Receipt/report must support tax breakdown.

## 7. Microsoft Store packaging
Target:
- PyInstaller runtime
- MSIX package
- Microsoft Store identity
- Store-managed updates
- x64 first, ARM64 later if justified

Legacy ZIP / Setup.exe may remain for direct/reseller distribution, but Store distribution should be MSIX.

## 8. Updates
Store version:
- update same product/package
- database backup before migration
- versioned migrations
- integrity check after migration
- safe recovery/rollback path on failure

## 9. Licensing / entitlements
Introduce `LicenseProvider` abstraction.

Providers:
- `MicrosoftStoreLicenseProvider`
- `LocalLicenseProvider`

Store entitlements first, local signed license fallback for direct/reseller installs.

POS must not require internet on every launch.

## 10. Offline-first guarantee
These must work without internet:
- Sale
- Barcode
- Stock
- Payment
- Returns
- Cash closure
- Reports
- Printing
- Scale
- RFID
- Customer display

Internet may be used for:
- Store purchase
- Periodic entitlement revalidation
- Updates
- Ads
- Cloud services
- Remote support

## 11. Hardware abstraction
Target service layer:
- PrinterService
- ScannerService
- ScaleService
- RFIDService
- CashDrawerService
- CustomerDisplayService

UI screens must not directly own device-specific logic.

## 12. Reliability release gate
Before commercial release:
- 1000 consecutive scans
- 100 consecutive sales
- 50 cash closures
- FR → AR → EN repeated switching
- printer disconnected
- scale disconnected
- serial disconnected
- internet disconnected
- crash recovery
- power-loss transaction integrity
- upgrade old DB
- restore backup
- Windows 10/11 clean install

Critical rule: no frozen cashier UI, no unhandled popup exceptions.

## 13. Performance targets
Target hardware:
- 4 GB RAM
- SSD
- low-end Windows POS/tablet
- 1366x768
- touch support

Targets:
- Barcode scan < 200 ms
- Search < 300 ms
- Checkout < 1 s without printer
- App launch < 5 s
- 20k products smooth
- 100k products usable

## 14. Sales UI
Maintain the cashier-first design:
- clear barcode/search field
- central cart
- large total
- visible last-sale reminder
- fast payment
- no unnecessary popups
- touch + keyboard support

## 15. First-run wizard
Steps:
1. Language
2. Country
3. Shop name
4. Currency / tax
5. Receipt printer
6. Barcode scanner test
7. Optional import
8. Admin PIN
9. Ready

## 16. Demo mode
Separate isolated demo database with sample data.
Must never merge with live shop data.

## 17. Privacy
Minimize data collection.
Do not transmit customer/sales/stock/price data without explicit feature and consent.

Required before Store release:
- Privacy Policy
- Terms of Use
- Support page
- Contact
- Data export/deletion policy

## 18. Telemetry
Optional technical telemetry only:
- version
- Windows version
- crash type
- feature usage count
- performance timing

No customer names, product names, turnover or barcodes.

## 19. Backup / restore
Free:
- local backup

Pro:
- scheduled backup
- external drive backup
- encrypted backup option

Future:
- optional cloud backup

Restore flow:
validate → preview → safety backup → restore → integrity check → restart.

## 20. Security
Keep and strengthen:
- hashed PINs
- encrypted SMTP secret
- signed license
- permissions
- audit trail
- no default admin PIN after setup
- no hardcoded secrets
- dependency/security scanning

## 21. Store listing
Name: **ToDo POS**
Subtitle: **Offline Point of Sale for Retail & Grocery**

Store listing languages:
- English
- French
- Arabic

Short demo video:
Scan → Cart → Pay → Change → Receipt → Stock.

## 22. Free → Pro conversion
Use a central feature entitlement service:
- `FeatureService.can("PROMOTIONS")`
- `FeatureService.can("MULTI_USER")`
- `FeatureService.can("CUSTOMER_DISPLAY")`

Do not scatter `if pro` across screens.

## 23. Target architecture
```
todo/
  core/
  services/
  screens/
  hardware/
  commerce/
  licensing/
  localization/
  country_profiles/
  fiscal/
  ads/
  cloud/
  storage/
```

## 24. Database evolution
Add/version:
- country_code
- tax_profiles
- product_tax_class
- sale tax snapshots
- entitlements
- app_installation
- commerce_state
- feature_flags

Money remains integer minor units.

## 25. Global formatting
Never hardcode:
- DH
- TVA
- DD/MM/YYYY

Locale/country profile supplies them.

## 26. Store certification gate
A release may ship only if:
- Unit tests green
- UI tests green
- Windows build green
- MSIX build green
- clean install pass
- upgrade pass
- backup/restore pass
- offline pass
- cash closure stress pass
- EN/FR/AR pass
- disconnected peripherals pass
- Defender/SmartScreen test pass

## 27. Roadmap
### P0 — Stabilisation
Freeze new features. Fix crashes/freezes. Add endurance/stress coverage.

#### P0.1 — Reliability gates — complete (2026-09-29)
Regression coverage now exercises the critical cashier paths without changing shop
data compatibility: 1000 barcode scans, 100 completed sales, 50 cash closures,
interrupted-sale rollback, repeated FR/AR shell rebuilds, Tk focus safety,
disconnected printer and serial peripherals, and the installed frozen
application's first launch. Evidence commits: `d4014ca`, `cad488a`,
`c2f3ecd`, `4448b38`, `41a56e7`, `cadd95f`, `d201ce2`, and
`9a2b442`. The three release workflows (Quick test build,
ToDo tests, and Windows build) are required green for each change.

### P1 — Global Core — in progress (2026-09-29)
English + localization engine + Tax Engine + Country Profiles.

Foundations delivered: JSON translation catalogues and English shell navigation;
country profiles with persisted defaults; integer-safe tax calculation; immutable
sale tax snapshots; country-aware product tax defaults; visible country/tax
settings; and receipt tax breakdowns. Evidence commits: `de215b6`, `9e0ae8e`,
`f353a0e`, `bfdcb3a`, `3847307`, `223aad8`, `39b8313`, `7434866`,
`f4ddc6b`, `dde3b6c`, and `0a64280`.

### P2 — Commercial Engine — foundations delivered (2026-09-30)
A central offline-safe `FeatureService`, Local and Microsoft Store cached
entitlement providers, and durable entitlement/commerce/feature-flag tables are
in place. Core cashier features stay available offline. Store SDK activation and any user-facing purchase flow remain deliberately
deferred until Store packaging and publisher identity are ready. An offline-safe
ads policy boundary now forbids ads on sale, payment, change, cash closure and
receipt surfaces. Evidence commits: `e623887`, `80d2fde`, `63214f9`,
`71872cb`, `3d88d15`, and `a059cba`.

### P3 — Store Packaging — scaffold delivered (2026-09-30)
MSIX manifest template, packaging script, validation tests and Store release checklist are in place. Actual Store publication still requires the final Partner Center publisher/package identity and official visual assets; no identity or assets are invented. The tested portable Windows build and Setup installer remain available for direct distribution until those external inputs are supplied.

### P4 — Productisation — in progress (2026-09-30)
The offline first-run wizard now configures language, country defaults, shop
name, currency/tax defaults, receipt printer, barcode test and a mandatory
replacement admin PIN. The optional demo remains isolated in its own database.
Privacy Policy, Terms of Use, and Support/data guidance are included in the
packaged documentation and available from in-app Help. The catalogue page size
is configurable from Settings (20–1000) instead of a hard-coded query limit.
Optional import is intentionally not reworked without a reproduced Import/Export
defect. Evidence commits: `4ce88b`, `a79734e`, `8dc1e11`, `54e3118`, `a66aa5c`,
`e878246`, `3ddbde4`, `b0c94fe`, `2d12e35`, `37b77b0`, `66c6b45`, `a15c519`,
and `649fd0c`.

### P5 — Store Launch
EN/FR/AR listing + Free release.

### P6 — Monetisation
ToDo Pro durable add-on.

### P7 — Country fiscal connectors
Implement only per-country, after requirements are verified.

### P8 — Services
Cloud backup + multi-store + subscriptions.

---

# Current execution rule

The current priority is **finish the remaining P1 localization work and P4
first-run usability**, while preserving the completed P0.1 reliability gate.
P2 foundations and the implemented P4 items must not be repeated. Do not start
Store commerce, ads, licensing gates, or MSIX packaging until their respective
roadmap phases and publisher inputs are ready.

Workflow:
1. Read exact `main` HEAD.
2. Verify the three current CI workflows.
3. Work in small, reviewable commits.
4. After each commit, verify Quick test build + ToDo tests + Windows build.
5. If CI is red, stop feature work and fix the confirmed failure.
6. Do not redo already-completed modules without a reproduced bug.
7. Preserve existing offline POS behavior and shop data compatibility.

