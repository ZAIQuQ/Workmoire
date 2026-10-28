# Workmoire visual resources

Interface resources are served locally. Package versions are pinned in
`package-lock.json`; there are no runtime font or icon CDN requests.

| Resource | Upstream | Pinned source | License and local use |
| --- | --- | --- | --- |
| Rich editor | https://github.com/ueberdosis/tiptap and https://github.com/ProseMirror | Tiptap 3.32.0; ProseMirror versions locked in `package-lock.json` | MIT. Native editing, block drag controls, tables, clipboard, history and Markdown compatibility. |
| PDF reading and text extraction | https://github.com/mozilla/pdf.js | `pdfjs-dist` 6.4.299 | Apache-2.0. Locally served PDF viewer and bounded text extraction from the selected authenticated attachment. |
| Formula rendering | https://github.com/KaTeX/KaTeX | `katex` 0.19.1 | MIT. Used by editable formula nodes; trusted commands are disabled. |
| Syntax highlighting | https://github.com/wooorm/lowlight and https://github.com/highlightjs/highlight.js | `lowlight` 3.3.0, `highlight.js` 11.12.0 | MIT / BSD-3-Clause. Incremental code-block highlighting. |
| Interface icons | https://github.com/lucide-icons/lucide | `lucide` 1.62.0 | ISC, with MIT notices for Feather-derived icons. Named imports in `web/interface-assets.js` bundle only the icons in use. The favicon adapts `BookOpen`. |
| Latin UI type | https://github.com/rsms/inter | `@fontsource-variable/inter` 5.3.0 | SIL Open Font License 1.1. Normal variable WOFF2 files from Fontsource. |
| Chinese UI and document type | https://github.com/notofonts/noto-cjk | `@fontsource-variable/noto-sans-sc` 5.3.1 | SIL Open Font License 1.1. Preferred variable type for consistent Chinese glyphs and weights; Unicode subsets load on demand, with platform fonts as fallbacks. |
| Code type | https://github.com/subframe7536/maple-font | Maple Mono NL v7.9, Regular and Medium WOFF2 | SIL Open Font License 1.1. Rounded monospaced code without operator ligatures. Files and original notice in `fonts/maple-mono/`. |

`vendor/THIRD_PARTY_LICENSES.txt` contains the dependency license notices,
including the editor runtime, its transitive packages, Lucide and both bundled fonts. Keep the notices and lockfile with
redistributions. Rebuild with `npm ci` and `npm run build`.

Maple Mono is vendored separately from npm. Its unmodified files come from the
[official v7.9 archive](https://github.com/subframe7536/maple-font/releases/download/v7.9/MapleMonoNL-Woff2.zip).
The archive SHA256 was checked against the release's `.sha256` file:
`ee68eea2553fb2b5fffba69b57ecb5e5ba5dd6132785485c900e3e680ed7d221`.
The installed files are `MapleMonoNL-Regular.woff2`
(`10c30e7541fcc653e58cc23b0df459848fedbc2419c1ccf41969e78908c90eed`)
and `MapleMonoNL-Medium.woff2`
(`3c96bf2eff8a311ff09f26db2cd88400716cf7efccaa003817093df82e7925ad`).
Retain `fonts/maple-mono/LICENSE.txt` when redistributing them. The code palettes
are project CSS; no commercial font files or personal-site artwork are bundled.

The interface uses neutral white and gray surfaces, dark text, and one blue
interaction accent. UI and document text prefer bundled Inter and variable Noto
Sans SC, with platform sans-serif fallbacks. There are no decorative hero illustrations. User-uploaded
images retain their intrinsic aspect ratio and remain authenticated.

## GitHub project icon

- Source: [Primer Octicons mark-github](https://github.com/primer/octicons/blob/9a274e212ee25c400ff666ce25a57866b7eacc25/icons/mark-github-16.svg).
- License: MIT; retained in `github-icon.LICENSE`. Used unchanged in the About dialog.
