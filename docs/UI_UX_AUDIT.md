# ToDo POS UI/UX audit — working inventory

This is a source and CI evidence inventory, not final visual acceptance. The starting comparison is [commit `9ca0da1`](https://github.com/hmasprod-a11y/todo-pos/commit/9ca0da1b2c9dae6cf66489593143d6d620e82398). The Windows screenshot harness was added in [`ba077e3`](https://github.com/hmasprod-a11y/todo-pos/commit/ba077e37328c05c2ffe197ea2dcfcc7a51ac1983). Its [baseline evidence artifact](https://github.com/hmasprod-a11y/todo-pos/actions/runs/40590215106/artifacts/12773697378) contains 21 real Tk captures for six routes and the product editor across French, Arabic and English. The product editor change is in [`4c7da19`](https://github.com/hmasprod-a11y/todo-pos/commit/4c7da194ce30a4e30fdcfb7f39ee6a8c11d2ab9c); the [later evidence artifact](https://github.com/hmasprod-a11y/todo-pos/actions/runs/40617161111/artifacts/12786270943) includes top and bottom views of that editor.

| Area | Source inventory | Current evidence | Remaining review |
| --- | --- | --- | --- |
| Sale and barcode search | `sale.py`, `payment.py`, `virtual_keyboard.py` | Cashier geometry test and Windows capture in three languages | Full cart, long names, touch, payment and popup screenshots |
| Products and pricing | `products.py`, `promotions.py` | Main screen and product editor captures; fixed footer/scroll test | Barcode/offer rows, photo and category overflow |
| Stock and inventory | `stock.py`, `inventory.py`, `inventory_sessions.py` | Stock main screen capture | Filled tables and all stock dialogs |
| Cash and journal | `cashdesk.py`, `journal.py`, `cashier_tools.py` | Cash main screen capture and cashier geometry test | Close/count dialogs, full ledger, keyboard focus |
| Purchases and suppliers | `purchases.py`, `suppliers.py`, `supplier_payments.py`, `supplier_returns.py` | Functional tests only | Windows screenshots and clipping checks |
| Customers and documents | `clients.py`, `customer_orders.py`, `quotations.py`, `returns.py`, `loyalty.py` | Functional tests only | Windows screenshots and long content |
| Reports and settings | `statistics.py`, `settings.py` | Main screen captures and layout tests in three languages | Dialogs, filled reports and scaling |
| Entry and setup | `login.py`, `onboarding.py` | Windows onboarding capture and action visibility gate in three languages | Screen scaling and long translated copy |

## Findings and status

| ID | Source or observed risk | Action | Evidence |
| --- | --- | --- | --- |
| UI-01 | Product editor requested 1100×900, taller than a 768 pixel display; Save/Cancel were at the bottom of the form. | Fit the window to the display, scroll its body and keep actions in a footer. | Windows geometry and capture gate on the delivery commit |
| UI-02 | `ToDoApp` held many shared ttk colors, fonts and paddings inline. | Extracted the same settings into `todo/design_system.py`; later screens should consume the semantic tokens. | Existing screenshot and functional gates must remain green |
| UI-03 | First-run setup requested a fixed 560×760 window with its start action at the bottom. | Fit height to the display, scroll its body and keep Start in a footer. | Windows capture and geometry gate on the delivery commit |\n| UI-07 | Many other secondary windows use fixed geometry without a screen-height clamp. | Audit each dialog and apply the visible-footer pattern where needed. | Open |
| UI-04 | Screens contain many independent literal color values and glyph-based icons. | Consolidate per semantic role; replace unclear final glyphs with a licensed offline icon set. | Open |
| UI-05 | The capture runner requests 1366×768 but can only photograph the visible area of its actual virtual display. | Manifest records actual bounds and off-screen clipping. | OS-level 100/125/150% scaling remains open |
| UI-06 | LOGICA executable/screens were not available in this repository review. | Compare only after actual screens can be inspected. | Open |

No LOGICA visual comparison or full-page acceptance is claimed from source review or a successful build. A successful Windows build proves packaging and automated gates only.
