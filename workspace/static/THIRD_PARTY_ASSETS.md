# Workmoire visual resources

Interface resources are served locally. Package versions are pinned in
`package-lock.json`; there are no runtime font or icon CDN requests.

| Resource | Upstream | Pinned source | License and local use |
| --- | --- | --- | --- |
| Interface icons | https://github.com/lucide-icons/lucide | `lucide` 1.62.0 | ISC, with MIT notices for Feather-derived icons. Named imports in `web/interface-assets.js` bundle only the icons in use. The favicon adapts `BookOpen`. |
| Latin UI type | https://github.com/rsms/inter | `@fontsource-variable/inter` 5.3.0 | SIL Open Font License 1.1. Normal variable WOFF2 files from Fontsource. |
| Chinese fallback type | https://github.com/notofonts/noto-cjk | `@fontsource-variable/noto-sans-sc` 5.3.1 | SIL Open Font License 1.1. Used when native Chinese fonts are unavailable; Unicode subsets load on demand. |

`vendor/THIRD_PARTY_LICENSES.txt` contains the dependency license notices,
including Lucide and both bundled fonts. Keep the notices and lockfile with
redistributions. Rebuild with `npm ci` and `npm run build`.

The interface uses neutral white and gray surfaces, dark text, and one blue
interaction accent. Chinese text prefers native platform fonts, followed by the
bundled Noto fallback. There are no decorative hero illustrations. User-uploaded
images retain their intrinsic aspect ratio and remain authenticated.
