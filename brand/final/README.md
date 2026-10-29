# Motorpuls logo, provisional asset set

Direction **A: Heartline** (provisional pick; the owner may still choose another direction).

## Files (final/)

- `favicon/android-chrome-192.png`
- `favicon/android-chrome-512.png`
- `favicon/apple-touch-icon.png`
- `favicon/favicon-16.png`
- `favicon/favicon-32.png`
- `favicon/favicon.ico`
- `favicon/favicon.svg`
- `favicon/head-snippet.html`
- `favicon/site.webmanifest`
- `motorpuls-icon-1024-transparent.png`
- `motorpuls-icon-1024.png`
- `motorpuls-icon.svg`
- `motorpuls-symbol-on-light.svg`
- `motorpuls-symbol.svg`
- `motorpuls-wordmark-dark-on-light.svg`
- `motorpuls-wordmark-dark-on-light@2x.png`
- `motorpuls-wordmark-light-on-dark.svg`
- `motorpuls-wordmark-light-on-dark@2x.png`
- `preview-sheet.png`
- `README.md`

Wordmark and lockup SVGs are outlined paths with a tight viewBox and a transparent background.
`@2x.png` renders are 1280 px wide (1x = 640 px). The symbol SVG is square (viewBox 0 0 96 96),
transparent, coloured for dark backgrounds; `motorpuls-symbol-on-light.svg` is the light-background version.
`motorpuls-icon-1024.png` is opaque, full bleed graphite. The transparent 1024 uses the dark-background colours.
Favicons at 16, 32 and 48 px use a separately drawn small variant (heavier strokes, fewer details).

## Colours

| Token | Hex | Use |
|---|---|---|
| graphite | `#111214` | dark background, icon tile |
| paper | `#F5F6F6` | light background (site --paper) |
| ink | `#0C0E11` | logo ink on light (site --ink) |
| ink on dark | `#F5F6F6` | logo ink on dark |
| pulse | `#FF5B1F` | accent on dark |
| pulse on light | `#E84A12` | accent graphics (spike, needle) on light |
| pulse text on light | `#C2410C` | orange letterforms on light (direction C) |

Contrast (WCAG 2.x):

- ink `#F5F6F6` on `#111214`: 17.31:1 (needs 4.5:1) pass
- accent `#FF5B1F` on `#111214`: 6.04:1 (needs 3.0:1) pass
- accent_text `#FF5B1F` on `#111214`: 6.04:1 (needs 4.5:1) pass
- ink `#0C0E11` on `#F5F6F6`: 17.85:1 (needs 4.5:1) pass
- accent `#E84A12` on `#F5F6F6`: 3.58:1 (needs 3.0:1) pass
- accent_text `#C2410C` on `#F5F6F6`: 4.78:1 (needs 4.5:1) pass
- raw `#FF5B1F` on `#F5F6F6` would be 2.87:1, which is why the light versions use the darker values.

## Concept (direction A, Heartline)

The heartbeat is the word space: a single QRS spike sits between MOTOR and PULS, drawn as one mitred
stroke at the weight of the type, its flat line on the baseline and its R peak landing on the cap height.
The symbol is the same spike re-proportioned for a square, ending in the orange dot from the old
placeholder, now the live point of the trace (it can carry the slow pulse animation the site already uses).

References used for the finish benchmark: Polestar identity by Stockholm Design Lab
(https://www.stockholmdesignlab.se/work/polestar), Top Gear (https://www.topgear.com),
Road & Track identity by Godfrey Dadich Partners (https://www.godfreydadich.com/work/roadandtrack).

## Fonts

- Archivo variable (wght 100 to 900, wdth 62 to 125), Google Fonts, SIL OFL. Source: `fonts/Archivo[wdth,wght].ttf`.
- Wordmark: Archivo instantiated at wght 850, wdth 125 with fontTools, tracking -12/1000 em plus hand kerning
  (see `KERN` in `scripts/designs.py`). Labels on the sheets use other Archivo instances.

## Re-render

```
cd /workspace/motorpuls/brand
python3 scripts/build.py final --direction A   # or B or C: rebuilds final/ for that direction
python3 scripts/build.py directions            # contact sheet
python3 scripts/build.py qa A B C              # QA renders and contrast report
```

Requires python3 with fonttools, shapely, cairosvg and Pillow.
