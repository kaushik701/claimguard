# Design tokens (frontend)

Look: calm, credible compliance tool. Light by default, dark supported. No gradients, no emoji icons.

| Token | Light | Dark |
|---|---|---|
| `--bg` | #F5F6F8 | #0F1218 |
| `--surface` | #FFFFFF | #171B23 |
| `--border` | #DADDE3 | #2A303B |
| `--text` | #14171F | #E7EAF0 |
| `--muted` | #545B69 | #9AA3B2 |
| `--primary` | #1F3A93 | #7C9CFF |
| `--high-bg / --high-fg / --high-line` | #FDE8E5 / #9A1C10 / #D92D20 | #3A1814 / #FFB4A8 / #F0654F |
| `--med-bg / --med-fg / --med-line` | #FDF0D2 / #7A4100 / #B54708 | #3A2A10 / #FFD08A / #E0A040 |
| `--low-bg / --low-fg` | #EAF6EE / #0F5A2F | #12301F / #9BE3B6 |
| `--quote-bg` | #FAFAFB | #1C212B |

- Fonts: IBM Plex Sans (UI), IBM Plex Mono (IDs, numbers), Source Serif 4 (rule quotes).
- Radius 6/8 px; spacing scale 4/8/12/16/24/32.
- Risk always shown with text label + colour (never colour alone). Contrast ≥ 4.5:1.
- Touch targets ≥ 44 px; keyboard shortcuts on review screens; visible focus ring (2 px primary).
- Components: RiskPill, StatTile, ClaimHighlighter, FlagCard, CitationBlock (quote + doc/page + "Open page"),
  PageViewer (PDF page image with quote highlight), RewriteDiff (original struck / suggested), ConfidenceBar,
  ProgressSteps (SSE), Heatmap, MetricTile (value vs target), EmptyState, ErrorBanner.
- Reference mock-ups: the "ClaimGuard UI" design canvas (Flag review, Overview, Queue, New audit, Evaluation,
  Portfolio, Pre-flight). Match its layout; this token file wins on colours.
