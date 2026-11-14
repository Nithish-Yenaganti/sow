# findable accuracy eval

findable 0.3.0 · run 2026-11-13 · 12 real sites · 31 hand-verified checks · **12/12 sites pass**

Each site is scanned live (12 pages). A site passes when findable reports every real problem we verified by hand (`must`) and none of the false alarms it used to raise (`must_not`).

| Site | Stack | Pages | Findings | Result |
|---|---|---|---|---|
| https://example.com | plain HTML | 1 | 6 | ✅ pass |
| https://excalidraw.com | client-rendered app | 1 | 2 | ✅ pass |
| https://svelte.dev | SvelteKit | 13 | 24 | ✅ pass |
| https://www.cloudflare.com | Cloudflare (CDN) | 12 | 10 | ✅ pass |
| https://wordpress.org/news | WordPress under a sub-path | 12 | 13 | ✅ pass |
| https://astro.build | Astro | 12 | 12 | ✅ pass |
| https://python.org | Django, apex -> www redirect | 13 | 35 | ✅ pass |
| https://docs.astral.sh/uv | MkDocs under a sub-path | 12 | 14 | ✅ pass |
| https://jekyllrb.com | Jekyll | 12 | 14 | ✅ pass |
| https://gohugo.io | Hugo | 12 | 29 | ✅ pass |
| https://nextjs.org | Next.js | 12 | 0 | ✅ pass |
| https://nuxt.com | Nuxt | 12 | 0 | ✅ pass |

Expectations and why: [sites.json](sites.json). Re-run: `uv run --project skills/findable/cli python evals/findable/run.py`
