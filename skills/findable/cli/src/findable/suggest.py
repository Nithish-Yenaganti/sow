"""Missing setup → steps only the user can do. Each suggestion says what it unlocks."""

from __future__ import annotations

from findable.rules import Finding


def suggestions(code_site: dict, live: dict | None, url: str | None, gsc: dict | None, app_dev_command: str | None) -> list[Finding]:
    S: list[Finding] = []
    lsite = (live or {}).get("site", {})
    if url is None:
        S.append(Finding(
            "setup.live_url", "site", "Give findable a URL to scan live",
            "code scan only", "a reachable production URL or a running dev server",
            "medium", "SEO", who="user",
            evidence="unlocks: AI-bot access test, status codes, sitemap check, empty-without-JS check",
            fix="suggestions.md#live-url"
                + ("" if not app_dev_command else f" (or run `{app_dev_command}` and re-scan with the localhost URL)")))
    elif live is not None and not lsite.get("reachable", True):
        S.append(Finding(
            "setup.live_unreachable", "site", f"{url} could not be reached", lsite.get("error", "connection failed"),
            "a reachable URL", "high", "SEO", who="user", source="live",
            evidence="live checks were skipped", fix="suggestions.md#live-url"))
    if gsc is None:
        S.append(Finding(
            "setup.gsc_csv", "site", "Add Search Console exports to see what Google indexes and ranks",
            "no export in .findable/inputs/", "Page indexing and Performance exports in .findable/inputs/",
            "low", "SEO", who="user",
            evidence="unlocks: which pages Google isn't indexing and why, plus pages and searches ranking 8–20",
            fix="suggestions.md#gsc-index-export"))
        if not code_site.get("has_gsc_verification"):
            S.append(Finding(
                "setup.gsc_verify", "site", "Check the site is verified in Google Search Console",
                "no google-site-verification tag found in the code (DNS verification can't be seen from here)",
                "site verified in Search Console", "low", "SEO", who="user",
                evidence="without it you can't see indexing, queries or crawl problems",
                fix="suggestions.md#gsc-verify"))
    elif not ((gsc.get("index") or {}).get("urls") or (gsc.get("index") or {}).get("reasons")):
        S.append(Finding(
            "setup.gsc_index", "site", "Add the Search Console Page indexing export",
            "only the Performance export is in .findable/inputs/", "Page indexing export in .findable/inputs/",
            "low", "SEO", who="user", evidence="unlocks: which pages Google isn't indexing, and why",
            fix="suggestions.md#gsc-index-export"))
    has_sitemap = bool(code_site.get("sitemap")) or any(s.get("status") == 200 for s in lsite.get("sitemaps", []))
    if has_sitemap:
        S.append(Finding(
            "setup.submit_sitemap", "site", "Submit your sitemap to Google and Bing",
            "unknown (can't be checked without your dashboards)", "sitemap submitted in Search Console and Bing Webmaster Tools",
            "low", "SEO", who="user",
            evidence="Bing's index also feeds ChatGPT search and Copilot. Dismiss this once done",
            fix="suggestions.md#submit-sitemap"))
    return S
