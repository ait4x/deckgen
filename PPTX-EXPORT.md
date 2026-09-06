# ait4x deck → PowerPoint: the recipe

Everything learned building `export/week1-classpoint.pptx`. Follow this and the fonts land right first time.

## 1. Why font names matter

PowerPoint has no weight axis. A run stores only `typeface="…"` plus `b="1"` / `i="1"`. So **the family name carries the weight.** Windows (and Office on Mac) registers each *named instance* of a variable font as its own legacy family, following the RIBBI rule: Regular + Bold share the base name; every other instance becomes `"<Family> <Instance>"`.

Verified by reading the `name` + `fvar` tables of the fonts in `uploads/` (`fonts/Inter-Variable.ttf`, `fonts/JetBrainsMono-Variable.ttf`):

| CSS weight | Inter variable → name PowerPoint sees | `b` flag |
|---|---|---|
| 100 | `Inter Thin` | 0 |
| 200 | `Inter ExtraLight` | 0 |
| 300 | `Inter Light` | 0 |
| 400 | `Inter` | 0 |
| 500 | `Inter Medium` | 0 |
| 600 | `Inter SemiBold` | 0 |
| 700 | `Inter` | 1 |
| 800 | `Inter ExtraBold` | 0 (1 harmless) |
| 900 | `Inter Black` | 0 (1 harmless) |

Italic: same names, `i="1"`. JetBrains Mono variable has instances Thin/ExtraLight/Light/Regular/Medium/Bold/ExtraBold → `JetBrains Mono`, `JetBrains Mono Medium`, `JetBrains Mono ExtraBold`, etc. (no SemiBold).

**Trap — Google Fonts static ZIP.** The files in `uploads/Inter/static/` are named `Inter 18pt`, `Inter 24pt Black`, `Inter 28pt ExtraBold`… (optical-size families). Installing those does **not** create `Inter Black`. Use either:
- the variable file `Inter-VariableFont_opsz,wght.ttf` (one install, all names above appear), or
- rsms.me static cuts (`Inter Black.otf`, `Inter ExtraBold.otf` — family names match the table).

Never target `Inter 18pt …` names in a deck.

## 2. Author the deck so the export needs no font fixing

In the DC, put the **weight-specific family first**, then the generic stack, and keep `font-weight` for the browser:

```
font-family:'Inter Black',var(--font-d);font-weight:900      → display titles (≥ 88px)
font-family:'Inter ExtraBold',var(--font-d);font-weight:800  → slide titles / subheads (44–72px)
font-family:var(--font-d);font-weight:400 or 700             → body ("Inter", bold flag)
font-family:var(--font-m);font-weight:500                    → eyebrows/code ("JetBrains Mono" — 500 exports as plain; acceptable)
```

`--font-d:"Inter","Helvetica Now","Helvetica Neue",Helvetica,Arial,sans-serif`, `--font-m:"JetBrains Mono",Menlo,Consolas,monospace`. Load Inter + JetBrains Mono from Google Fonts in `<helmet>`; the browser falls through `'Inter Black'` (not a web family) to `Inter` at weight 900, while the PPTX export picks up `Inter Black` as the typeface name. Both sides render correctly.

Type scale (1920×1080): title 72 / sub 44 / body 36 / small 28 / mono 24; padding 96 / 120. Colours: ink `#000B1C`, text `#2A323D`, muted `#5C6470`, line `#E1E1DE`, teal `#64C2C3`, orange X `#ED6D24`, section bands from the secondary matrix (e.g. `#943890`).

## 3. Export (editable) from the deck-stage DC

`gen_pptx` with: `width 1920, height 1080, mode editable, resetTransformSelector "deck-stage"`, one entry per slide (`showJs: document.querySelector('deck-stage').goTo(n)`), `hideSelectors: ["[data-classpoint]"]` so the HTML ClassPoint placeholders don't ship (build.py adds the real buttons). Speaker notes come from `data-speaker-notes`. Save to `export/<name>.pptx`.

## 4. Post-process with `classpoint/build.py`

    python classpoint/build.py export/week1.pptx   → export/week1-classpoint.pptx

Standard library only. It:
1. Replaces the theme (ait4x colours; major font `Inter Black`, minor `Inter`) and adds a master + 6 layouts (Title, Section band, Content white, Content ink, Two column, Question). Save as `.potx` for a reusable template.
2. **Font safety net** (`fix_fonts`): any run still named plain `Inter` with `b="1"` is renamed by size — ≥ 88px → `Inter Black`, ≥ 44px → `Inter ExtraBold`. Only fires when step 2 was skipped; harmless otherwise.
3. Entrance animations: shapes grouped into rows (300 000 EMU bands), fade + float-up 500 ms, 150 ms between rows, auto-start on slide enter. Full-slide backgrounds and ClassPoint buttons excluded.
4. ClassPoint activities from `classpoint/activities.json` (`{"slideNo": {"type": "word_cloud|short_answer|multiple_choice", …}}`, format of github.com/venetanji/classpoint.py). Button art `classpoint/btn-*.png`; Word Cloud reuses Short Answer art until `btn-word-cloud.png` exists.

## 5. Classroom PC checklist

- Install `Inter-VariableFont_opsz,wght.ttf` and `JetBrainsMono-VariableFont_wght.ttf` (right-click → Install for all users). Restart PowerPoint.
- Open the `-classpoint.pptx`; confirm the title slide shows `Inter Black` in the font box, not "Inter Black" with a substitution warning.
- Fallback if fonts can't be installed: Arial (PowerPoint substitutes automatically; weights collapse to Bold).
- Fire one ClassPoint activity before class — a malformed tag fails silently.

## 6. Verify a PPTX's font names quickly

Unzip, then `grep -oh 'typeface="[^"]*"' ppt/slides/*.xml | sort | uniq -c`. Expected set: `Inter`, `Inter Black`, `Inter ExtraBold`, `JetBrains Mono`. Anything with `18pt/24pt/28pt` or `Inter Bold` is wrong.

## 7. The template (.potx)

`ait4x-template.potx` = theme + master + 8 layouts, one empty sample slide each. Regenerate any time with
`python classpoint/build.py --template ait4x-template.potx` (needs `polyu-design-logo.png` next to build.py).

Master: white, title 72 Inter ExtraBold, body 36 Inter (level 1 no bullet; levels 2–3 use the orange dot `·`), footer `SD5913 · PFAD.AIT4X.ORG` + slide number in JetBrains Mono 22 caps at y=1000. Chrome (eyebrow / footer / number, PolyU Design mark top-right on white layouts) is on the layouts so ink and violet ones invert it.

Layouts: Title (ink, a·t4x wordmark) · Section band (violet #943890) · Content — white · Content — ink · Two column (body + picture) · Question · Quote (paper #F4F4F2, 88 ExtraBold) · Statement (ink, 150 Black, centred).

Build.py applies this same master to every exported deck, so `week1-classpoint.pptx` and the .potx share layouts.
