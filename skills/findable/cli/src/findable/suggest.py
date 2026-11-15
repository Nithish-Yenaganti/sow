"""Missing setup → steps only the user can do. Each says what it unlocks."""

from __future__ import annotations

from findable.rules import Finding


def suggestions(code_site: dict, live: dict | None, url: str | None, gsc: dict | None, app_dev_command: str | None) -> list[Finding]:
    S: list[Finding] = []
    lsite = (live or {}).get("site", {})
    if url is None:
        S.append(Finding("setup.live_url", "site", "Give findable a URL to scan live", "code scan only",
                         evidence="unlocks: AI-bot access test, status codes, sitemap check, empty-without-JS check"
                                  + (f"; or run `{app_dev_command}` and re-scan with the localhost URL" if app_dev_command else "")))
    elif live is not None and not lsite.get("reachable", True):
        S.append(Finding("setup.live_unreachable", "site", f"{url} could not be reached", lsite.get("error", "connection failed"),
                         source="live", evidence="live checks were skipped"))
    index = (gsc or {}).get("index") or {}
    if gsc is None:
        S.append(Finding("setup.gsc_csv", "site", "Add Search Console exports to see what Google indexes and ranks",
                         "no export in .findable/inputs/",
                         evidence="unlocks: which pages Google isn't indexing and why, plus pages and searches ranking 8–20"))
        if not code_site.get("has_gsc_verification"):
            S.append(Finding("setup.gsc_verify", "site", "Check the site is verified in Google Search Console",
                             "no google-site-verification tag found in the code (DNS verification can't be seen from here)",
                             evidence="without it you can't see indexing, queries or crawl problems"))
    elif not (index.get("urls") or index.get("reasons")):
        S.append(Finding("setup.gsc_index", "site", "Add the Search Console Page indexing export",
                         "only the Performance export is in .findable/inputs/",
                         evidence="unlocks: which pages Google isn't indexing, and why"))
    if code_site.get("sitemap") or any(s.get("status") == 200 for s in lsite.get("sitemaps", [])):
        S.append(Finding("setup.submit_sitemap", "site", "Submit your sitemap to Google and Bing",
                         "unknown (can't be checked without your dashboards)",
                         evidence="Bing's index also feeds ChatGPT search and Copilot. Dismiss this once done"))
    return S
