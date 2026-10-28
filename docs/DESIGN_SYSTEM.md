# ToDo POS design system

This document records the shared visual contract for the existing Tkinter application. The implementation lives in [`todo/design_system.py`](../todo/design_system.py); `ToDoApp` applies it once when it starts. Screen layouts can adopt these tokens in stages without changing sales, inventory or payment logic.

## Visual direction

A calm work surface, high contrast text, and one clear primary action per task. State is carried by text and icons alongside color. The cashier must be able to find the total, current ticket, search field and payment action immediately.

| Role | Token | Value | Usage |
| --- | --- | --- | --- |
| Canvas | `canvas` | `#F6F7FB` | Screen background |
| Surface | `white` | `#FFFFFF` | Cards, forms and table rows |
| Primary | `primary` | `#2563EB` | Main in-page action |
| Navigation | `nav` | `#1E293B` | Navigation and strong body text |
| Ink | `ink` | `#0F172A` | Main text and figures |
| Muted | `muted` | `#475569` | Secondary descriptions |
| Success | `success` | `#15803D` | Completed actions |
| Warning | existing `#D97706` | `#D97706` | Low stock and attention; migration to a token pending |
| Danger | `danger` | `#DC2626` | Destructive actions |
| Border | `border` | `#E2E8F0` | Separators and table headers |
| Selection | `selection` | `#DBEAFE` | Selected rows and active controls |

Hover, pressed, disabled and field colors are also defined centrally. This first extraction preserves the appearance of existing ttk controls; it is a foundation for consistent screen changes.

## Type and spacing

- Segoe UI is the current Windows font family. Body text uses 10 pt; titles, search, quantity and totals use larger existing styles. Arabic glyphs and numerals must be inspected in the running application before changing the font.
- Spacing steps are 4, 8, 12, 16 and 24 pixels. New controls should use these steps and align labels and fields on a shared grid.
- The target minimum touch height is 44 logical pixels where space allows. Dense tables may need a separate keyboard-first treatment.

## Components and behavior

- `Primary.TButton` marks the main next action; `Success.TButton` confirms a completed transaction; `Danger.TButton` marks cancellation or deletion. Labels remain visible alongside color.
- `Search.TEntry`, `Quantity.TEntry`, `Treeview` and `TNotebook` provide shared type and padding. Screen-specific content stays in its screen module.
- Dialogs with long forms need a visible action footer and a scrollable body. The product editor and first-run wizard now follow this pattern.
- Input focus, scanner shortcuts and keyboard navigation take priority over decorative effects. New images and icons must be bundled locally.

## Validation gates

Every substantial layout change needs a Windows screenshot, geometry checks for essential controls, and the existing functional test suite. The screenshot harness currently captures six main routes plus the product editor in French, Arabic and English. Its manifest records actual display bounds and whether a window extends off screen. These captures are evidence, not a claim that every screen and DPI setting has been accepted.

Open work: review screenshots visually, expand capture to the remaining routes and dialogs, test full data and long labels, measure real Windows scaling at 100%, 125% and 150%, and compare against real LOGICA screens when available.
