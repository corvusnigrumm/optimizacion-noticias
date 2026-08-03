---
name: Corvus Obsidian
colors:
  surface: '#f7f9fb'
  surface-dim: '#d8dadc'
  surface-bright: '#f7f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f6'
  surface-container: '#eceef0'
  surface-container-high: '#e6e8ea'
  surface-container-highest: '#e0e3e5'
  on-surface: '#191c1e'
  on-surface-variant: '#45464d'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f3'
  outline: '#76777d'
  outline-variant: '#c6c6cd'
  surface-tint: '#565e74'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#131b2e'
  on-primary-container: '#7c839b'
  inverse-primary: '#bec6e0'
  secondary: '#515f74'
  on-secondary: '#ffffff'
  secondary-container: '#d5e3fd'
  on-secondary-container: '#57657b'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#07006c'
  on-tertiary-container: '#7073ff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae2fd'
  primary-fixed-dim: '#bec6e0'
  on-primary-fixed: '#131b2e'
  on-primary-fixed-variant: '#3f465c'
  secondary-fixed: '#d5e3fd'
  secondary-fixed-dim: '#b9c7e0'
  on-secondary-fixed: '#0d1c2f'
  on-secondary-fixed-variant: '#3a485c'
  tertiary-fixed: '#e1e0ff'
  tertiary-fixed-dim: '#c0c1ff'
  on-tertiary-fixed: '#07006c'
  on-tertiary-fixed-variant: '#2f2ebe'
  background: '#f7f9fb'
  on-background: '#191c1e'
  surface-variant: '#e0e3e5'
typography:
  headline-display:
    fontFamily: Geist
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.04em
  headline-lg:
    fontFamily: Geist
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Geist
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
  headline-md:
    fontFamily: Geist
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Geist
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Geist
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Geist
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  mono-label:
    fontFamily: Geist
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  xs: 8px
  sm: 12px
  md: 16px
  lg: 24px
  xl: 32px
  container-margin: 40px
  gutter: 20px
---

## Brand & Style
The design system embodies "Corvus Obsidian"—a high-performance, analytical aesthetic for **Corvus Nigrum Optimization**. The brand personality is intelligent, sharp, and commanding, drawing inspiration from the raven's predatory precision and dark plumage.

The visual style is a blend of **Minimalism** and **Modern Corporate**. It prioritizes extreme clarity, utilizing heavy whitespace to frame dense data and complex optimization workflows. The mood is professional and authoritative, utilizing high-contrast typography and subtle tonal layering to create a premium, developer-centric experience that feels both technical and refined.

## Colors
The palette is rooted in a monochromatic foundation with a singular, high-precision accent.

- **Primary (Obsidian):** A deep, near-black slate used for primary headings, sidebars, and key interactive states. This represents the "Corvus Nigrum" (Black Raven) identity.
- **Secondary (Steel):** A range of cool greys used for secondary information and borders to maintain a technical feel.
- **Tertiary (Indigo Pulse):** A sophisticated deep indigo used sparingly for call-to-actions, focus states, and success indicators, providing a "digital" spark to the interface.
- **Neutral:** A stark white background (#FFFFFF) paired with extremely light grey surfaces (#F8FAFC) to define container boundaries without introducing visual clutter.

## Typography
This design system utilizes **Geist** exclusively. Its systematic, technical nature perfectly suits an optimization platform.

- **Headlines:** Use tight letter-spacing and bold weights to create a "locked-in" professional look.
- **Body Text:** Standard weight for maximum readability on white backgrounds.
- **Labels:** Use uppercase for metadata and categorization to differentiate from functional body text.
- **Numeric Data:** Since Geist features excellent mono-spacing for numbers, use it for all optimization metrics and data tables to ensure columns align perfectly.

## Layout & Spacing
The layout follows a **Fluid Grid** model built on a 4px baseline shift. 

- **Desktop:** 12-column grid with 24px margins and 20px gutters. 
- **Tablet:** 8-column grid with 20px margins.
- **Mobile:** 4-column grid with 16px margins.

The spacing rhythm is intentional: use larger gaps (`xl`) between distinct functional modules (e.g., Sidebar vs. Main Content) and tighter gaps (`xs` or `sm`) within components to create a sense of mechanical density and efficiency.

## Elevation & Depth
Depth is conveyed through **Low-Contrast Outlines** and **Tonal Layering** rather than traditional shadows, maintaining a sharp, modern silhouette.

- **Level 0 (Base):** White (#FFFFFF) - The canvas.
- **Level 1 (Surfaces):** Light Grey (#F8FAFC) with a 1px border (#E2E8F0) - Used for cards and sidebars.
- **Level 2 (Interaction):** When hovered, cards should not lift via shadow, but rather transition their border color to the Secondary Steel (#94A3B8).
- **Overlays:** Modals and dropdowns use a very thin, sharp 1px border in Obsidian (#0F172A) with a minimal, neutral-tinted ambient shadow (4px blur, 10% opacity) to provide just enough separation from the background.

## Shapes
Following the 'ROUND_FOUR' requirement, the shape language is intentionally balanced.

- **Standard Elements:** 0.5rem (8px) for buttons, input fields, and small UI elements.
- **Large Elements:** 1rem (16px) for cards and main dashboard containers.
- **Special Elements:** 1.5rem (24px) for prominent "Optimization Start" buttons or floating action banners.

This roundedness softens the high-contrast "Obsidian" palette, preventing the UI from feeling overly aggressive while maintaining its professional edge.

## Components

### Buttons
- **Primary:** Solid Obsidian (#0F172A) background with White text. Bold weight.
- **Secondary:** White background with 1px Steel border. Obsidian text.
- **Accent:** Solid Indigo Pulse (#6366F1) for high-priority actions like "Run Optimization."

### Input Fields
- **Default State:** White background, 1px Light Grey border, Body-sm typography.
- **Focus State:** 1px Indigo Pulse border with a subtle 2px Indigo glow (low opacity).

### Cards
- White background, 1px border (#E2E8F0), and 1rem rounded corners. 
- Header areas within cards should have a subtle bottom border to separate titles from data content.

### Chips & Badges
- Use for status (e.g., "Optimizing," "Complete"). 
- Small caps typography, 0.5rem roundedness, and a light-tinted version of the status color (e.g., Light Indigo background with Deep Indigo text).

### Sidebar
- Full-height, slight grey tint (#F8FAFC), with a sharp vertical border on the right. 
- Navigation items use Obsidian for active states and Steel for inactive states.