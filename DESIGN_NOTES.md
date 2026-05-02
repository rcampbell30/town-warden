# Town Warden — Design Notes

This document describes the design system used in the Town Warden public dashboard (`frontend/index.html`).
It is intended to help future contributors maintain visual consistency, and to guide town-cloners who adapt this project for other locations.

---

## Design Principles

1. **Trustworthy over dramatic** — civic data should calm, not alarm. No red-alert styling without good reason.
2. **Plain English first** — residents should understand everything without technical knowledge.
3. **Transparent about limitations** — every data source explains what it can and cannot tell you.
4. **Local without being tacky** — Blackpool identity is present but tasteful, not a seaside theme park.
5. **Not an official system** — design must never imply police, council, NHS, or emergency-service endorsement.

---

## Colour Palette (Blackpool)

| Name              | Hex       | Usage                                   |
|-------------------|-----------|-----------------------------------------|
| Seaside Amber     | `#F68712` | Primary brand, hero gradient, accents   |
| Tower Red         | `#B22222` | Secondary hero gradient, warnings       |
| Coastal Blue      | `#1E90FF` | Links, incident markers, interactive    |
| Promenade Navy    | `#102A43` / `#1C3152` | Text, headings, dark surfaces |
| Sand/Off-white    | `#FFF8ED` | Page background (light mode)            |
| Civic Green       | `#146C50` | Connected/healthy status                |
| Muted Ink         | `#4F6674` | Secondary text, captions                |

Dark mode counterparts are defined in `body.dark` within the `:root` overrides.

---

## CSS Variable System

The file uses two layered `:root` variable blocks (a result of incremental development):

- **First block** (`--bg`, `--surface`, `--text`, `--brand`, etc.) — used by base element resets and earlier component styles.
- **Second block** (`--page-bg`, `--ink`, `--panel`, `--line`, `--amber`, `--navy`, etc.) — the primary Blackpool-specific design layer, overrides layout and component colours.

Future maintainers: prefer the second set (`--ink`, `--panel`, `--amber`, etc.) for any new component styles.

---

## Visual Identity Elements

### Hero Banner
- Gradient: amber → red → purple (Blackpool Illuminations palette)
- Inline SVG watermark: simplified Blackpool skyline (buildings + Tower + arcade) at 16% opacity, bottom-right
- Wave/wave dots at bottom edge (::after pseudo-element)
- "Lights On/Off" button references Blackpool Illuminations

### Section Dividers
Sections use a decorative amber/white/red striped bar (repeating-linear-gradient) — a reference to Blackpool rock candy.

### Footer
- Blackpool rock motif (::before on `.footer-rock`)
- Tram SVG (::after on `.footer`) with amber stroke and red wheels
- Copy: "No compote here — only the finest seaside rock."

### Favicon
Simplified Blackpool Tower silhouette on Promenade Navy (#102A43) background.

---

## Data Source Visual Hierarchy

Each data source has a **data-currency badge** that communicates how fresh the data is:

| Source         | Badge label      | Badge style class  |
|----------------|------------------|--------------------|
| Police.uk      | Updated monthly  | `.source-currency.historical` (amber-tinted) |
| Open-Meteo     | Near real-time   | `.source-currency.live` (blue-tinted)         |
| Street Manager | Live notifications | `.source-currency.realtime` (green-tinted)  |

This is critical for resident trust: Police.uk is retrospective/historical, not a live feed.

---

## Incident / Police.uk Copy Guidelines

**Always use:**
- "published Police.uk data"
- "historical incident patterns"
- "recorded period" (not "date of incident")
- "approximately reported near" (not "at")
- "not a live emergency alert"

**Never use:**
- "live crime"
- "real-time incidents"
- "active threat"
- "danger now"

---

## Developer Dashboard (`dev.html`)

`dev.html` is intentionally **not linked** from the public dashboard. It is accessible only by direct URL and is intended for the project owner.

- Contains raw source health, analytics, agent logs, and admin controls
- Admin actions require the backend admin token on every request (token is never stored client-side)
- Do not add a public link to `dev.html` from `index.html`

---

## Adapting for Another Town (Cloneability)

Town Warden is designed to be town-agnostic. To adapt for another town:

1. Create a new JSON config in `config/towns/<yourtown>.json` following the Blackpool example
2. Set `TOWN_CONFIG=config/towns/<yourtown>.json` in your environment
3. The frontend reads from `/town-config` endpoint and renders dynamically
4. Blackpool-specific copy is in `DEFAULT_TOWN_CONFIG` and `SOURCE_PUBLIC_COPY` in `index.html`
5. Blackpool-specific quick-search landmarks are in `BLACKPOOL_LANDMARKS` — replace with your town's landmarks
6. Colour palette can be adjusted in the second `:root` block, replacing amber/red/navy with your town's palette

Assets to replace for a new town:
- Favicon (tower SVG in `<head>`)
- Hero SVG watermark (skyline in `.hero::before`)
- Footer tram SVG (`.footer::after`)
- `BLACKPOOL_LANDMARKS` array
- `DEFAULT_TOWN_CONFIG` fallback values

---

## Accessibility Notes

- All major sections have `aria-label` or `aria-labelledby`
- Status pill has `role="status"` and `aria-live="polite"`
- Search input has `aria-describedby`
- Focus-visible outlines are defined (`outline: 3px solid var(--focus)`)
- `.sr-only` class defined for screen-reader-only text
- Touch targets are minimum 44px height
