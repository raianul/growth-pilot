# Design System Specification: The Precision Architect

## 1. Overview & Creative North Star
The Creative North Star for this design system is **"The Precision Architect."** 

This system moves beyond the generic "SaaS Blue" aesthetic to create a digital environment that feels curated, authoritative, and intentionally airy. We are building an editorial experience where the "white space" isn't just empty—it is a functional element that guides the eye. By utilizing high-contrast typography scales and deep, professional blues, we signal a level of sophistication found in architectural journals and high-end financial reports. 

To break the "template" look, we prioritize **intentional asymmetry** and **tonal layering**. Elements should not always sit in a rigid grid; instead, use overlapping surfaces and varied padding to create a sense of bespoke craftsmanship.

---

## 2. Colors & Surface Logic

This system relies on a sophisticated hierarchy of blues and neutrals. The goal is to create depth through color shifts rather than structural lines.

### The "No-Line" Rule
**Explicit Instruction:** Designers are prohibited from using 1px solid borders for sectioning or layout containment. Boundaries must be defined solely through background color shifts. For example, a `surface_container_low` (#f2f4f6) section sitting on a `surface` (#f7f9fb) background provides all the separation necessary.

### Surface Hierarchy & Nesting
Treat the UI as a series of physical layers. Use the `surface_container` tiers to create "nested" importance:
*   **Background Canvas:** `surface` (#f7f9fb).
*   **Secondary Content Areas:** `surface_container_low` (#f2f4f6).
*   **Interactive Cards/Modules:** `surface_container_lowest` (#ffffff).
*   **Active/Elevated Overlays:** `surface_container_high` (#e6e8ea).

### The "Glass & Gradient" Rule
While we avoid dark glassmorphism, we use "Frosted Glass" for floating elements (like navigation bars or hovering menus). Use semi-transparent surface colors with a `backdrop-blur` of 12px–20px. 
*   **Signature Textures:** For primary CTAs and Hero sections, use a subtle linear gradient (135°) transitioning from `primary` (#0037b0) to `primary_container` (#1d4ed8). This adds a "lithographic" soul to the interface that flat colors lack.

---

## 3. Typography: The Editorial Voice

We utilize a dual-font strategy to balance character with readability.

*   **Display & Headlines (Manrope):** This is our "voice." Manrope’s geometric yet warm proportions provide a modern, architectural feel. Use `display-lg` (3.5rem) with tight letter-spacing (-0.02em) for high-impact editorial moments.
*   **Body & Utility (Inter):** Inter is the "workhorse." Use it for all functional data, labels, and long-form text. It is designed for maximum legibility on digital screens.

**Hierarchy Strategy:** 
Maintain a significant "Size Jump" between headlines and body text. If a headline is `headline-lg`, the sub-text should skip `title-lg` and go straight to `body-lg` to create high-contrast, professional tension.

---

## 4. Elevation & Depth

We convey hierarchy through **Tonal Layering** and **Ambient Light** rather than traditional drop shadows.

*   **The Layering Principle:** Depth is achieved by "stacking." Place a `surface_container_lowest` card on a `surface_container_low` section. The subtle shift from #f2f4f6 to #ffffff creates a "soft lift" that feels more premium than a heavy shadow.
*   **Ambient Shadows:** When an element must "float" (e.g., a Modal or Popover), use an extra-diffused shadow. 
    *   *Blur:* 40px–60px.
    *   *Opacity:* 4%–6%.
    *   *Color:* Use a tinted version of `on_surface` (#191c1e) to mimic natural light.
*   **The "Ghost Border" Fallback:** If a border is required for accessibility (e.g., in a high-data table), it must be a "Ghost Border": use `outline_variant` at 15% opacity. **Never use 100% opaque borders.**

---

## 5. Components

### Buttons
*   **Primary:** Uses the "Signature Gradient" (`primary` to `primary_container`). Roundedness set to `md` (0.75rem). Text is `label-md` in `on_primary`.
*   **Secondary:** `surface_container_highest` background with `primary` text. No border.
*   **Tertiary:** Purely typographic using `primary` color, with a subtle `surface_container_low` background shift on hover.

### Input Fields
*   **Styling:** Forgo the traditional "bottom line" or "box border." Use `surface_container_lowest` with a "Ghost Border" and a 4px inner padding shift on focus.
*   **Labels:** Always use `label-md` in `on_surface_variant` for a muted, professional look.

### Cards & Lists
*   **Rule:** Absolutely no divider lines. 
*   **Separation:** Use vertical white space (Scale `8` or `12`) to separate items. In lists, use a subtle `surface_container_low` background on hover to define the row.
*   **Nesting:** A card (`surface_container_lowest`) should have a `lg` (1rem) corner radius to feel soft yet structural.

### Floating Action Navigation
A bespoke component for this system. A bottom-centered or side-docked navigation bar using the **Glassmorphism Rule** (surface-lowest at 80% opacity + blur). This keeps the focus on the content while providing a high-end, modern utility.

---

## 6. Do’s and Don'ts

### Do:
*   **Use Asymmetric Padding:** Allow more room on the left/right of a container than the top/bottom to create an editorial flow.
*   **Trust the White Space:** If a section feels crowded, increase the spacing scale instead of adding a border.
*   **Apply Tonal Depth:** Always check if a background color shift can replace a shadow.

### Don’t:
*   **Don't use #000000 for text:** Always use `on_surface` (#191c1e) to maintain a professional, slightly softer contrast.
*   **Don't use standard "Grey" shadows:** Shadows should always be low-opacity and slightly tinted by the background.
*   **Don't use Divider Lines:** If you feel the need to "draw a line," use a 24px–32px gap instead.
*   **Don't use Sharp Corners:** Stick strictly to the `md` (12px) and `lg` (16px) tokens to maintain the "Modern Architect" feel.