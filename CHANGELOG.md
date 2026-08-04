# Changelog

All notable changes to `alpha` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions are shared by the backend and frontend and track the phase in
[`ARCHITECTURE.md`](./ARCHITECTURE.md): `0.4.x` is the Phase 4 API & export
layer.

This file starts at 0.4.0. Earlier phases predate it and are described in
`ARCHITECTURE.md` rather than reconstructed here.

## [Unreleased]

## [0.4.0]

### Added

- **Locale-correct number formatting across the UI.** Every figure now runs
  through a shared formatter (`frontend/src/data/formatNumber.js`, bound to the
  active locale by `useFormat.js`). Large amounts abbreviate above 1,000,000 and
  carry an exact-value tooltip and `aria-label`.
- **Locale-aware PDF export.** `POST /api/v1/valuation/export` takes
  `?locale=en|de|es`, which sets the brief's separators and currency-symbol
  placement (`1.234.567 €` vs `$1,234,567`). The PDF uses full digits — no
  abbreviations in a disclosure document. The CSV is unaffected and stays raw.
- **Frontend test suite.** `vitest`, plus `npm test`. The suite pins the
  scale-word and separator conventions per locale.
- Phase-4 export & embed: CSV/PDF investor reports and the embeddable
  single-region widget (`frontend/embed.html`).

### Changed

- **Per-hectare display.** The UI and the PDF report per-service yields per
  hectare rather than per m², since per-m² figures are sub-cent. The API
  contract and the CSV keep the raw per-sqm values.
- **The side panel leads with totals, not per-unit rates.** The standing-asset
  value moved above the yield breakdown, and the Total Ecosystem Value block's
  headline is the whole-area annual total; the per-hectare rate is still shown,
  demoted beneath it.
- The TEV headline carries its period on its own baseline (`212,5 Mrd. € / Jahr`)
  rather than in a caption underneath. The figures either side of it are stocks,
  so an unlabelled flow was a plausible misreading.

### Fixed

- **Scale words are no longer hand-rolled.** English *billion* is 10⁹ but German
  *Billion* is 10¹² (10⁹ is a *Milliarde*), and Spanish has no short form for
  10⁹ at all. All scale words now come from CLDR via `Intl`'s compact notation,
  so a €1.5 Mrd. figure can never render as "1,5 Bio." — a factor-of-1000 error
  on a financial disclosure.
- A compact scale word could fuse with the currency symbol on some ICU builds:
  Chromium 141 renders 1.2e12 in es/BRL as `1,2 BR$`, which reads as 1.2 reais
  rather than 1.2 trillion. The separator is now guaranteed regardless of the
  runtime's ICU version.
- The systemic-premium multiplier was interpolated into its sentence unformatted,
  so a German reader saw `×1.595 systemisch` — one thousand five hundred
  ninety-five, rather than 1.6.
- The PDF's discount rate used Python's `{:.1%}`, printing `@ 3.0%` beside
  comma-decimal money in an otherwise localised German report.
- Currency amounts no longer emit a stray `,0` from clamped fraction digits, and
  keep their thousands separators just below the abbreviation threshold.

[Unreleased]: https://github.com/richardkfm/alpha/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/richardkfm/alpha/releases/tag/v0.4.0
