# compliance

**Find what your web app is missing for privacy, payments, licensing and AI, and build what you agree to.** It isn't a lawyer, and it flags what needs one.

It asks about your business first (what you build, where your users are, whether you charge, whether kids may use it), then scans your code:

- **Privacy:** what personal data your forms and database collect, which services receive it, whether you have a privacy policy and whether it names them
- **Cookies & tracking:** analytics, session recording and ad pixels that load before consent, Google Fonts, Global Privacy Control
- **User rights:** delete account, download data, edit details
- **Terms & payments:** terms of service and sign-up agreement, refund policy, auto-renewal disclosure, online cancel, card fields
- **AI:** AI labels, training on user inputs, AI provider terms, who owns AI output
- **Licenses & assets:** GPL/AGPL/unknown dependency licenses, third-party notices, font files, stock images, paid UI kits
- **Claims:** "GDPR compliant", "#1", "100% secure", user counts
- **Content:** high-risk advice disclaimers, age checks, DMCA and report buttons for user uploads
- **Basics:** leaked secrets, `.env` in git, weak password hashing, security.txt, alt text, contact details, Impressum

Then it asks what you want done, shows **one** list of changes to approve, builds them (policies start as drafts for a lawyer), and re-checks. It never commits or deploys.

## Results

Saved in `.compliance/` in your project:
- `profile.json`: your answers about the business
- `data-map.json`: what you collect, why, how long, who gets it
- `report.md`: the full report with the source behind each check
- `drafts/`: generated policy drafts and third-party notices

## Develop

```bash
cd skills/compliance/cli   # from the repo root
uv run pytest
uv run compliance plan --path ../../../tests/compliance/fixtures/saas-nextjs
```

## Evals

[evals/compliance](../../evals/compliance) scans 8 open-source projects at pinned commits and checks hand-verified expectations (`must`, `must_not`, and `known_gaps` still to fix). It runs weekly in CI (`.github/workflows/evals.yml`) and on demand:

```bash
uv run --project skills/compliance/cli python evals/compliance/run.py          # from the repo root
uv run --project skills/compliance/cli python evals/compliance/run.py --show   # print every finding
```

When the eval finds a false alarm or a miss, fix the scanner and add a test to `tests/compliance/test_regressions.py`.

To release, bump the version in `cli/pyproject.toml`, `cli/src/compliance/__init__.py` and the root `.claude-plugin/marketplace.json`. Re-check `references/sources.md` before each release.
