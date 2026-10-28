# Product style: type, corners and surfaces

Reviewed primary product references in Chromium on 2026-10-28. The references
are public documentation, a public Yuque document, and the editor images shown
on Feishu's official product page. Measurements from a marketing/help page are
not presented as measurements of its authenticated editor.

| Reference | Observed evidence | Applied decision |
| --- | --- | --- |
| [Notion page styling](https://www.notion.com/help/customize-and-style-your-content) | Help UI uses NotionInter/Inter with sans-serif fallbacks; its guide distinguishes default, serif and mono page styles. Controls use restrained rounding; page typography supplies the hierarchy. | Consistent sans-serif defaults and clear weight/spacing hierarchy; preserve dedicated math/code typography. |
| [Feishu Docs](https://www.feishu.cn/product/docs) | Official editor images show a white document, compact action areas and light boundaries. The public page's font stack includes Helvetica Neue, PingFang SC and Microsoft YaHei. | Neutral white/gray surfaces, compact rounded controls and softened separators. Marketing gradients and illustrations are not used. |
| [Yuque help document](https://www.yuque.com/yuque/help/vbtstk) | The public document uses Chinese sans-serif fallbacks and 15px / 26.1px body text; inspected controls include 8px corners. Its knowledge-base home places a white rounded content surface on a light gray background. | A quiet desktop document surface, rounded selection areas and comfortable Chinese reading text. |

These products do not use the same radius everywhere. Workmoire applies a small
shared scale rather than treating every element as a pill: 4px for small inline
details, 6px for compact controls, 8px for standard buttons/inputs, 12px for menus
and content blocks, and 16px for dialogs and the desktop editor surface.

## Actual font audit

Before this change, Chromium's platform-font inspection showed local **Noto
Sans CJK SC Regular/Bold** for Chinese and bundled Inter for Latin. It did not
show Song/SimSun in the inspected UI or document text. However, the system font
did not provide intermediate weights consistently: a 600-weight heading used
the available bold face.

The UI and document now prefer the existing bundled **Noto Sans SC Variable**
after Inter. Body text uses 400, interface emphasis uses 500, and editor titles
and headings use 550. Chrome's actual glyph inspection confirms the bundled
Chinese face is used, instead of only checking the declared CSS stack. Its
internal PostScript name contains `Thin`, which is the variable font's default
name; the CSS weight range and rendered weights remain variable. Native
sans-serif fonts provide fallbacks while local subsets load.

Math retains KaTeX's mathematical glyphs, code retains Maple Mono NL, and PDF
page typography belongs to the uploaded source. PDF controls share the app's
font and visual tokens. The symbol picker also uses the UI sans-serif stack.

## Surfaces and controls

- A light neutral canvas frames the desktop's white document surface. Phones
  use the full width for editing.
- Document rows use spacing and a rounded selected surface instead of a full
  set of horizontal rules and a sharp vertical selection bar.
- Buttons, fields, menus, tags, template cards, search, editor controls and the
  PDF toolbar use shared radius/color values in `design-tokens.css`.
- Borders are lighter; popup shadows are subtle and dialogs have their own
  elevation. Text remains dark enough to read, and focus outlines remain visible.
- Navigation and document-list labels are slightly larger; the existing simple
  navigation, tag workflow and document controls stay in place.

## Verification and delivery

Visual review covers login, the editor, tag menus, tag management, templates,
PDF reading and phone layouts. The browser audit checks actual Chinese glyph
fonts, shared tokens, PDF toolbar fitting and no page overflow from 320px to
1440px. All font/icon requests remain local. The combined login/document sample
loaded roughly 0.95 MB of WOFF2 resources in a fresh browser; Unicode subsets
are cached and only requested for the characters used.

The existing browser suite exercises editing, Chinese composition, tables,
math, media, code folding, tags, drafts and responsive controls. No new runtime
dependency or generated artwork is introduced. Font and icon license notices
remain in the existing asset inventory and bundled license files.
