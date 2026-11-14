# compliance

**Find what your website or app is missing for privacy, payments, licenses and AI, and fix it.**

compliance is a skill for your AI coding assistant (Claude Code, Codex). It asks a few questions about your business, checks your code, explains what's missing in plain words, and builds what you agree to.

> **It is not a lawyer.** It never says your site is "compliant". Every policy it writes starts as a draft for a lawyer to review, every check shows the law or official guidance it comes from, and it tells you clearly what needs legal advice.

## Why it exists

When you build an app quickly, the "boring" parts are easy to forget, and they're the ones that cause trouble later:

- You collect emails but have no privacy policy, or it doesn't mention the services that receive the data.
- Analytics or ad trackers load before visitors agree to cookies.
- Users can sign up but can't delete their account.
- You charge a subscription but don't explain renewals or how to cancel.
- A package, font or image in your project isn't licensed for how you use it.
- Your homepage says "100% secure" or "GDPR compliant".

compliance finds these early and helps you fix them, without pretending to replace a lawyer.

## What it covers

| Topic | What it checks |
|---|---|
| **Privacy** | What personal data you collect, who receives it, and whether your privacy policy says so |
| **Cookies** | Whether trackers and analytics wait for consent |
| **Rights** | Whether users can delete their account, download their data and edit their details |
| **Terms** | Whether you have terms of service and an agreement at sign-up |
| **Payments** | Refund policy, renewal notices, online cancelling, how card details are handled |
| **AI** | AI labels, training on user data, AI provider terms, who owns AI output |
| **Licenses** | Open-source licenses (like GPL), font files, stock images, paid templates |
| **Claims** | Marketing promises like "#1", "100% secure" or "GDPR compliant" |
| **Content** | Disclaimers for risky advice, age checks, copyright takedowns for uploads |
| **Basics** | Leaked secret keys, weak password storage, contact details, Impressum |

## How it works

1. **Ask:** "Do I need a privacy policy?" or "Check my app for GDPR gaps".
2. **About your business** (asked once): what you build (SaaS, store, AI, marketplace, content, health or finance, kids), where your users are, whether you charge, whether kids may use it, and the name and contact details your policies should show.
3. **Scan:** it reads your code. This never changes anything.
4. **Report:** what you collect, what's missing, and who should handle each item: the assistant, you, or a lawyer.
5. **Decide:** a few simple questions per area, like "How long should we keep data after an account is deleted?"
6. **One approval:** one list of every document, code change and removal. Nothing changes until you say yes.
7. **Build and check:** it writes the pages and code, then checks each fix worked.
8. **Hand-over:** what's done, what you need to do, and what to take to a lawyer.

## What it can build

- **Documents** (as drafts): privacy policy, cookie policy, terms of service, refund policy, acceptable use, copyright takedown (DMCA), accessibility statement, Impressum, AI disclosure.
- **Code:** cookie consent before trackers load, delete-account and download-data flows, renewal notices and cancel links, AI labels, footer links to every policy.
- **Notices:** a third-party license list for the packages you use.

## Tested on real projects

Tested on 8 open-source projects (SaaS starters, AI chat apps, a store, a blog) at fixed versions, with every expected result checked by reading the code: [see the results](../../evals/compliance/RESULTS.md).

## What it won't do

- Give legal advice, or call your site "compliant".
- Change anything without your approval, or commit and publish anything for you.
- Sign up for services or change settings in your dashboards. It tells you the steps.
- Check anything over the internet: it only reads your project.

## Install

Needs [uv](https://docs.astral.sh/uv/getting-started/installation/). Then in Claude Code:

```
/plugin marketplace add Nithish-Yenaganti/sow
/plugin install sow@sow
```

Or for any assistant: `npx skills add Nithish-Yenaganti/sow`

## Where results go

In your project, in `.compliance/`:

| File | What's in it |
|---|---|
| `report.md` | The full report, with the source behind each check |
| `profile.json` | Your answers about the business |
| `data-map.json` | What you collect, why, how long you keep it, and who gets it |
| `drafts/` | Policy drafts and the third-party license list |

<details>
<summary><b>Commands (for developers)</b></summary>

Your assistant runs these for you. To run them yourself, from your project folder: `uv run --project path/to/skills/compliance/cli compliance <command>`.

| Command | What it does |
|---|---|
| `compliance plan` | Asks about the business, says what a scan will check |
| `compliance scan` | Reads the project and writes the report |
| `compliance decide` | Asks the per-area questions |
| `compliance changes` | The one list of changes to approve |
| `compliance draft <doc>` | Writes a policy draft |
| `compliance notices` | Writes the third-party license list |
| `compliance verify --ids …` | Re-checks specific fixes |
| `compliance dismiss <id> --reason …` | Marks a finding as intentional |
| `compliance report` | Shows the latest results |

Add `--json` for machine-readable output.

**Develop:**

```bash
cd skills/compliance/cli
uv run pytest
uv run compliance plan --path ../../../tests/compliance/fixtures/saas-nextjs
```

**Evals:** [evals/compliance](../../evals/compliance) scans 8 open-source projects at pinned commits and checks hand-verified expectations (`must`, `must_not`, and `known_gaps` still to fix). It runs weekly in CI (`.github/workflows/evals.yml`) and on demand, from the repo root:

```bash
uv run --project skills/compliance/cli python evals/compliance/run.py          # summary
uv run --project skills/compliance/cli python evals/compliance/run.py --show   # every finding
```

When the eval finds a false alarm or a miss, fix the scanner and add a test to `tests/compliance/test_regressions.py`.

To release, bump the version in `cli/pyproject.toml`, `cli/src/compliance/__init__.py` and the root `.claude-plugin/marketplace.json`. Re-check `references/sources.md` before each release.

</details>
