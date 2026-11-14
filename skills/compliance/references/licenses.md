# Licenses: code, fonts and images

## Open-source code
- **Permissive** (MIT, ISC, BSD, Apache-2.0): free to use commercially. Keep the copyright notice: list them in a third-party notices file (`compliance notices`). Apache-2.0 also asks you to keep its NOTICE file.
- **Weak copyleft** (LGPL, MPL, EPL): fine to use unmodified. If you change their own files, share those changes.

### Strong copyleft {#strong-copyleft}
GPL code shipped inside your app (browser bundle, desktop or mobile app) can require releasing your app's code under the GPL. Options: replace it with a permissive package (recommended), keep it and comply, or ask a lawyer. Dev-only tools (not shipped) are usually fine.

### Network copyleft {#network-copyleft}
AGPL (and SSPL) also apply when users only use your app over the network. Running modified AGPL code on your server can mean publishing your source. Replace it, or get a lawyer's view before launch.

### Source-available {#restricted}
BUSL, Elastic, PolyForm and "non-commercial" licenses aren't open source. Read the exact limits (often no competing service, no commercial use) before shipping.

### No clear license {#unknown}
No license means no permission. Check the package's repository for a LICENSE file; if there isn't one, replace it or ask the author.

### Couldn't check {#unchecked}
Install dependencies (`npm install`) so the lockfile or `node_modules` has license data, then scan again. Python: run `uvx pip-licenses` inside the project's environment.

## Fonts {#fonts}
- Google Fonts and Fontsource fonts use the SIL Open Font License: free, including commercially. Host them yourself in the EU (see playbooks).
- Fonts bought for desktop use often need a separate **web** or **app** license. Check the receipt or the foundry's license page; keep the license file next to the font.
- If unsure, swap to an OFL font of similar style.

## Images, icons and UI kits {#assets}
- Use only images you made, bought, or that have a license allowing this use (Unsplash, Pexels and similar each have their own license: read it).
- Stock-site preview files (with "shutterstock", "istock" etc. in the name) are watermarked comps and aren't licensed.
- Icon sets: Lucide (ISC), Heroicons (MIT) and Material Symbols (Apache-2.0) are free. Font Awesome Free icons are CC BY 4.0; Pro icons need an active license.
- Paid templates and UI kits (Tailwind Plus, ThemeForest) usually cover one project or "end product". Check the license tier.
- Add a credits page when a license asks for attribution (CC BY images, some icon sets).
