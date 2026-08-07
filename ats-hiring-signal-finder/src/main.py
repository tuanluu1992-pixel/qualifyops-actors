"""ATS Hiring Signal Finder — Greenhouse, Lever & Ashby.

Turns official public ATS job boards into one scored hiring-signal record per company:
open roles, a deterministic hiring signal, locations, and evidence job URLs. No LinkedIn,
no browser, no paid upstream — just the companies' own public ATS APIs.
"""
from __future__ import annotations

import asyncio
import json
import re
import urllib.parse
import urllib.request

from apify import Actor

GREENHOUSE = "https://boards-api.greenhouse.io/v1/boards/{}/jobs?content=false"
LEVER = "https://api.lever.co/v0/postings/{}?mode=json"
ASHBY = "https://api.ashbyhq.com/posting-api/job-board/{}"

SALES = re.compile(r"\b(sales|account executive|business development|revenue|sdr|bdr|partnerships)\b", re.I)
MKT = re.compile(r"\b(marketing|growth|demand gen|content|brand|seo|lifecycle)\b", re.I)
ENG = re.compile(r"\b(engineer|developer|software|data|devops|platform|machine learning|ml|ai)\b", re.I)
OPS = re.compile(r"\b(operations|success|support|implementation|onboarding|logistics)\b", re.I)
SENIOR = re.compile(r"\b(head|director|vp|vice president|chief|principal|lead)\b", re.I)


def _fetch(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "QualifyOps-ATS/1.0 (+https://apify.com/qualifyops)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def classify(titles: list[str]) -> tuple[str, list[str]]:
    joined = " | ".join(titles).lower()
    reasons = []
    counts = {
        "sales_expansion": len(SALES.findall(joined)),
        "marketing_expansion": len(MKT.findall(joined)),
        "technical_product_investment": len(ENG.findall(joined)),
        "operations_expansion": len(OPS.findall(joined)),
    }
    dominant = max(counts, key=counts.get) if any(counts.values()) else "general_hiring"
    for k, v in counts.items():
        if v:
            reasons.append(f"{v}x {k}")
    return dominant, reasons


def score(open_roles: int, titles: list[str], signal: str) -> tuple[int, list[str]]:
    s, reasons = 0, []
    if open_roles >= 2:
        s += 15; reasons.append("+15 multiple open roles")
    if open_roles >= 5:
        s += 10; reasons.append("+10 high vacancy volume")
    if any(SENIOR.search(t) for t in titles):
        s += 15; reasons.append("+15 senior/leadership role present")
    if signal != "general_hiring":
        s += 15; reasons.append("+15 clear hiring signal")
    return min(s, 100), reasons


def parse_source(item) -> tuple[str, str] | None:
    """Accept {'platform','slug'} or a board URL string."""
    if isinstance(item, dict) and item.get("platform") and item.get("slug"):
        return item["platform"].lower(), item["slug"].strip()
    url = item.get("url") if isinstance(item, dict) else item
    if not isinstance(url, str):
        return None
    host = urllib.parse.urlparse(url if "//" in url else "https://" + url)
    path = [p for p in host.path.split("/") if p]
    h = host.hostname or ""
    if "greenhouse" in h and path:
        return "greenhouse", path[-1]
    if "lever.co" in h and path:
        return "lever", path[0]
    if "ashbyhq" in h and path:
        return "ashby", path[-1]
    return None


def fetch_company(platform: str, slug: str) -> dict:
    if platform == "greenhouse":
        data = _fetch(GREENHOUSE.format(slug))
        jobs = data.get("jobs", [])
        rows = [{"title": j.get("title"), "location": (j.get("location") or {}).get("name"),
                 "url": j.get("absolute_url"), "updated": j.get("updated_at")} for j in jobs]
        board = f"https://boards.greenhouse.io/{slug}"
    elif platform == "lever":
        data = _fetch(LEVER.format(slug))
        rows = [{"title": j.get("text"), "location": (j.get("categories") or {}).get("location"),
                 "url": j.get("hostedUrl"), "updated": j.get("createdAt")} for j in data]
        board = f"https://jobs.lever.co/{slug}"
    elif platform == "ashby":
        data = _fetch(ASHBY.format(slug))
        jobs = data.get("jobs", [])
        rows = [{"title": j.get("title"), "location": j.get("location"),
                 "url": j.get("jobUrl") or j.get("applyUrl"), "updated": None} for j in jobs]
        board = f"https://jobs.ashbyhq.com/{slug}"
    else:
        raise ValueError(f"Unknown platform: {platform}")
    titles = [r["title"] for r in rows if r.get("title")]
    signal, sig_reasons = classify(titles)
    sc, sc_reasons = score(len(rows), titles, signal)
    return {
        "company": slug,
        "platform": platform,
        "open_roles": len(rows),
        "roles": titles[:60],
        "locations": sorted({r["location"] for r in rows if r.get("location")})[:20],
        "hiring_signal": signal,
        "signal_reasons": sig_reasons,
        "signal_score": sc,
        "score_reasons": sc_reasons,
        "board_url": board,
        "evidence_job_urls": [r["url"] for r in rows[:5] if r.get("url")],
        "status": "ok",
        "error": None,
    }


async def main() -> None:
    async with Actor:
        inp = await Actor.get_input() or {}
        sources = list(inp.get("companies") or []) + list(inp.get("boardUrls") or [])
        max_companies = int(inp.get("maxCompanies", 100))
        parsed = [p for p in (parse_source(s) for s in sources) if p][:max_companies]
        if not parsed:
            Actor.log.warning("No valid ATS sources provided.")
            return
        for platform, slug in parsed:
            try:
                rec = fetch_company(platform, slug)
            except Exception as exc:  # noqa: BLE001
                rec = {"company": slug, "platform": platform, "open_roles": 0, "status": "error",
                       "error": f"{type(exc).__name__}: {exc}"}
            await Actor.push_data(rec)
            Actor.log.info(f"{platform}/{slug}: {rec.get('open_roles')} roles, signal={rec.get('hiring_signal')}")


if __name__ == "__main__":
    asyncio.run(main())
