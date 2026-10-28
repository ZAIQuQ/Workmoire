# Code-block design research

Audited on 2026-10-28 in Chromium using a light browser preference. These are
observed styles from actual article code blocks, not claims about every page or
breakpoint on a site. Font sizes below are CSS pixels.

| Primary reference | Observed code typography and surface | Useful pattern |
| --- | --- | --- |
| [Josh Comeau: custom CSS reset](https://www.joshwcomeau.com/css/custom-css-reset/) | Cartograph CF, 16 / 25.6; no common ligatures; custom Shiki light/dark themes; pale blue surface; 6px corners | Comfortable type, clear syntax hierarchy and deliberate spacing |
| [Anthony Fu: Why Not Prettier](https://antfu.me/posts/why-not-prettier) | DM Mono, 14.4 / 20.16; Shiki Vitesse; `#fafafa` light surface; 6px corners | Restrained syntax colors and low visual weight in a white article |
| [Ahmad Shadeed: CSS nesting](https://ishadeed.com/article/css-nesting/) | System monospace stack, 16 / 24; `#282a36` dark surface; 8px corners | Comfortable dark code areas and local scrolling |
| [Dan Abramov: a complete guide to useEffect](https://overreacted.io/a-complete-guide-to-useeffect/) | System monospace stack, 14 / 20; `#232936` dark surface; 12px corners | Strong readability of long examples with a compact text size |

Source references also included [Vitesse](https://github.com/antfu/vscode-theme-vitesse)
(MIT) and [Maple Mono](https://github.com/subframe7536/maple-font) (SIL OFL 1.1).
We compared Maple Mono NL, JetBrains Mono, DM Mono and the existing system
fallback with the same Python sample, Chinese comments and ambiguous glyphs.
Maple's rounded forms fit the requested appearance. The NL variant retains
literal operator shapes; contextual/common ligatures are also disabled in CSS.
The commercial Cartograph font was only observed on its author's website.

## Applied choices

- Locally served Maple Mono NL v7.9, regular and medium: about 135 KB combined.
  Chinese uses the existing platform/Noto fallback. No runtime third-party requests.
- Desktop code uses 14px / 25.2px, 22px horizontal padding and 12px corners,
  aligned with the shared product-style tokens.
  Phones use 13px / 23.4px and 16px padding. No decorative window controls.
- Default light surface `#f7f8fa`, optional charcoal `#22262e`. Keywords use
  muted violet, callable names blue, strings green and numbers ochre. Comments
  remain upright and legible. Both palettes' text and comments meet 4.5:1
  contrast against their code background, verified in the browser.
- The code theme is a browser preference shared by native blocks and AI preview
  code. It does not change the document's saved state or the surrounding UI.
- Language, line count, fold, theme and copy controls share a compact header.
  Long scripts scroll locally, bounded to 620px or 65% of the viewport height.
  Horizontal scrolling preserves source indentation without widening the page.

## Folding behavior

Folding is a document node attribute when deliberately changed in editing mode.
It survives save/reload, revision restore, and native JSON/ZIP exports. Older
documents without this attribute open expanded. Markdown remains full fenced
code; it has no portable folding attribute.

Reading-mode toggles and search expansion are temporary view changes. Search
reveals a hidden match before scrolling to it. A collapsed block shows its
language, line count and first nonempty line, with a click target to expand it.
The source DOM stays mounted while hidden; copying always takes the full source.
When a writer folds the block containing the caret, the caret moves to a visible
text position. Folding is a separate undo step. User selection across a whole
document does not automatically expand every block.

## Verification

Browser coverage exercises saved folding, caret/undo safety, complete copy and
export, read-only toggles, theme persistence, search reveal, local font loading,
contrast, scrolling and 320px/390px layouts. Backend coverage verifies strict
boolean attributes, history restoration, and JSON/ZIP round trips. Synthetic
visual reviews cover the whole editing page, both palettes and phone layouts.
Font provenance, checksums and redistribution notices are recorded in
[the asset inventory](../workspace/static/THIRD_PARTY_ASSETS.md).
