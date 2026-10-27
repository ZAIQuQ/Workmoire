# Workmoire visual resources

All interface resources are served locally. The build uses the exact package
versions in `package-lock.json`; there are no runtime font, icon or illustration
CDN requests.

| Resource | Upstream | Pinned source | License and local use |
| --- | --- | --- | --- |
| Interface icons | https://github.com/lucide-icons/lucide | `lucide` 1.62.0 | ISC, with MIT notices for Feather-derived icons. Named imports in `web/interface-assets.js` bundle only the icons in use. The favicon adapts `BookOpen`. |
| Latin UI type | https://github.com/vercel/geist-font | `@fontsource-variable/geist` 5.3.0 | SIL Open Font License 1.1. Normal variable WOFF2 files from Fontsource. |
| Chinese UI type | https://github.com/notofonts/noto-cjk | `@fontsource-variable/noto-sans-sc` 5.3.1 | SIL Open Font License 1.1. Fontsource Unicode subsets load on demand. |
| Reading illustrations | https://github.com/lunahq/react-open-doodles | commit `5f36351f860e4ed0543c5247c845f4546443fc6f` | MIT-licensed SVG components, artwork credited to Pablo Stanley's Open Doodles. See `illustrations/SOURCES.md` and `illustrations/LICENSE.txt`. |

`vendor/THIRD_PARTY_LICENSES.txt` contains the dependency license notices,
including Lucide and the fonts. Keep this file, the illustration notices and the
lockfile with redistributions. Rebuild with `npm ci` and `npm run build`.

The two illustrations keep their original geometry and viewBox. Changes are
limited to removing the React component wrapper, converting JSX attributes to
SVG attributes, setting the two palette colors, and declaring intrinsic image
dimensions. CSS uses automatic height and contain sizing, never stretching or
cropping. Uploaded document images retain their own intrinsic aspect ratio.
