---
name: findable
description: Check and fix whether Google and AI engines (ChatGPT, Perplexity, Claude, Gemini, Bing/Copilot) can find, read and cite this website — SEO, AEO and GEO. Use when the user asks to audit or improve SEO, search visibility, indexing, sitemap/robots, structured data, AI crawler access, LLM/AI citations, "why don't I show up in ChatGPT", or says "run findable" / "/findable". Runs the `findable` CLI in the project, asks the user only when there are real choices, applies fixes as a reviewable diff, and verifies them.
---

# findable

One job: **can Google and AI engines find, read and cite this site, and what blocks it?**

The `findable` CLI does the scanning. You do three things: ask the user when there's a real choice, apply the fixes they pick, and explain the results plainly. Follow `references/safety.md` at all times.

## Running the CLI

The CLI ships inside this skill, in `cli/`. Run it from the user's project root as:

```
uv run --quiet --project "${CLAUDE_SKILL_DIR}/cli" findable <command> --json
```

Outside Claude Code, replace `${CLAUDE_SKILL_DIR}` with this skill's folder path. Below, `findable …` means this command. The first run takes a few seconds to set up.

If `uv` is missing, tell the user to install it (see `suggestions.md#install-uv`) and stop.

Always pass `--json` and read the output. Exit codes: `0` ok · `1` error · `2` verify found failures · `3` needs input.

## Flow

### 1. Scan
Run `findable scan --json`.

**If exit code is 3 (`needs_input`):** show each item in `questions` to the user.
- Claude Code: use the multiple-choice question tool. The option with `recommended: true` goes first, labelled "(Recommended)".
- Codex and others: a numbered list. The user replies with a number.
- Re-run with the answer, e.g. `findable scan --json --app apps/web` or `--url https://example.com` or `--url none`.

Two special answers:
- **"Start the dev server":** start the given command in the background, wait until the localhost URL responds, then re-run with `--url http://localhost:PORT`.
- **"I'll give you the URL":** ask for it, then re-run with `--url <it>`.

Never pick an option yourself when the CLI asked.

### 2. Report
Summarise in at most 6 lines:
- the site and which sources were scanned
- open counts by severity
- fixed / regressed / new since the last run
- the top 3 `do_first` items, each tagged **you** (`who: user`) or **auto-fix**
- the path to `.findable/report.html`

Use the finding's own `title`, `current`, `target` and `evidence`. Don't add vague advice. For any finding the user asks about, explain *why it matters* in one or two sentences from `references/checks.md`.

Then list the **user steps** (`who: user`): each one with its exact steps from the file named in `fix` (`suggestions.md#…` or `playbooks/cdn.md`). You can't do these for the user.

### 3. Choose fixes
Ask which findings to fix, as a multi-select. Offer only `auto_fixable` ones, with critical/high pre-recommended. At most 10 options, plus "All recommended".

For each chosen finding with `fix_options`, ask which variant (recommended first), unless there is only one.

Also ask when a fix conflicts with something already in the repo, e.g. an existing sitemap generator or an SEO plugin: patch the existing one (recommended) or replace it.

### 4. Fix
For each chosen finding:
1. Open the file in `file`. Read the playbook section in `fix` (`playbooks/nextjs.md` for Next.js, otherwise `playbooks/generic.md`, adapted to the framework).
2. Make the smallest change that reaches `target`, in the project's existing style.
3. **Content changes** (titles, descriptions, answer-first paragraphs, FAQ text): write them from the page's real content. Show them to the user before applying, because they change the user's voice. Never invent facts, prices or claims.
4. Never commit, push or deploy. Leave the changes in the working tree and show the diff summary.

### 5. Verify
Run `findable verify --json --ids <fingerprints of what you fixed>`, adding `--url http://localhost:PORT` if a dev server is running.
- `fixed` ✓ · `still failing` → fix again, at most 2 more tries, then report what's left and why
- `not re-checked` → tell the user it gets confirmed after deploy, on the next `findable scan`

Finish with: what changed (files), what's verified, what the user must do (deploy, user steps), and "Run `/findable` after deploying to confirm on production."

## Other commands
- `findable report --json`: latest results without re-scanning
- `findable dismiss "<fingerprint>" --reason "<why>"`: when the user says a finding is intentional. Always ask for the reason.
- Search Console data: if the user wants striking-distance pages, explain `suggestions.md#gsc-export` (they drop the export into `.findable/inputs/`), then re-scan.

## Files
- `references/checks.md`: what every rule means and why it matters
- `references/ai-bots.md`: AI crawler user agents, search vs. training
- `references/schema.md`: JSON-LD templates
- `references/aeo-content.md`: answer-first writing
- `references/safety.md`: hard rules
- `playbooks/nextjs.md`, `playbooks/generic.md`: fix recipes
- `playbooks/cdn.md`: user steps for CDN/WAF bot blocking
- `suggestions.md`: every user-only step
