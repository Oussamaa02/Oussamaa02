#!/usr/bin/env python3
"""Refresh public-stats.json from the public GitHub contribution calendar.

Stdlib only. Reads the same calendar GitHub shows on the profile (the default
"last year" view: from the Sunday before one year ago through today, 365-371
days), so the total matches GitHub's own "N contributions in the last year".

Refuses to overwrite the snapshot if the page shape changes, the cell sum
disagrees with GitHub's headline, or the data looks wrong, so a GitHub markup
change fails the workflow instead of publishing bad numbers.
"""
import html, json, os, re, time, urllib.request
from datetime import date, timedelta
from pathlib import Path

USER = "Oussamaa02"
ROOT = Path(__file__).parent
OUT = ROOT / "public-stats.json"
URL = f"https://github.com/users/{USER}/contributions"
API = "https://api.github.com"


def get(url: str, accept: str, token: str | None = None) -> str:
    headers = {"User-Agent": f"{USER}-profile-stats", "Accept": accept}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
                return r.read().decode("utf-8")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(5 * (attempt + 1))
    raise SystemExit(f"fetch failed for {url}: {last}")


def parse(page: str) -> tuple[dict[str, int], int]:
    tips = {
        m[0]: html.unescape(re.sub(r"<[^>]+>", "", m[1])).strip()
        for m in re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>(.*?)</tool-tip>', page, re.S)
    }
    if not tips:
        raise SystemExit("no tooltips found: GitHub calendar markup changed")
    daily: dict[str, int] = {}
    for attrs in re.findall(r"<td\b([^>]+)>", page):
        d = re.search(r'data-date="(\d{4}-\d{2}-\d{2})"', attrs)
        ident = re.search(r'\bid="([^"]+)"', attrs)
        if not (d and ident):
            continue
        tip = tips.get(ident[1])
        if tip is None:
            raise SystemExit(f"missing tooltip for {d[1]}")
        n = re.match(r"([\d,]+) contribution", tip)
        if not n and not tip.startswith("No contributions"):
            raise SystemExit(f"unrecognised tooltip for {d[1]}: {tip!r}")
        daily[d[1]] = int(n[1].replace(",", "")) if n else 0
    head = re.search(r"([\d,]+)\s+contributions?\s+in the last year", re.sub(r"\s+", " ", page))
    if not head:
        raise SystemExit("headline total not found: GitHub calendar markup changed")
    return dict(sorted(daily.items())), int(head[1].replace(",", ""))


def languages(token: str | None) -> list[list] | None:
    """Share of code (bytes) across the user's own public, non-fork repos."""
    try:
        repos = json.loads(get(f"{API}/users/{USER}/repos?per_page=100", "application/vnd.github+json", token))
        total: dict[str, int] = {}
        for r in repos:
            if r.get("fork"):
                continue
            for lang, n in json.loads(get(f"{API}/repos/{USER}/{r['name']}/languages",
                                          "application/vnd.github+json", token)).items():
                total[lang] = total.get(lang, 0) + n
    except SystemExit as e:
        print(f"languages skipped: {e}")
        return None
    s = sum(total.values())
    if not s:
        return None
    ranked = sorted(total.items(), key=lambda kv: -kv[1])
    top, rest = ranked[:6], sum(n for _, n in ranked[6:])
    out = [[k, round(n / s * 100, 1)] for k, n in top]
    if rest:
        out.append(["Other", round(rest / s * 100, 1)])
    return out


def main() -> None:
    daily, headline = parse(get(URL, "text/html"))
    days = [date.fromisoformat(k) for k in daily]
    start, end = days[0], days[-1]
    if len(days) < 365 or (end - start).days + 1 != len(days):
        raise SystemExit(f"unexpected calendar window: {start}..{end}, {len(days)} cells")

    total = sum(daily.values())
    if total != headline:
        raise SystemExit(f"cell sum {total} != GitHub headline {headline}; refusing")
    active = sum(v > 0 for v in daily.values())

    prev = json.loads(OUT.read_text()) if OUT.exists() else {}
    if total == 0 and prev.get("total_contributions", 0) > 0:
        raise SystemExit("fetched 0 contributions but previous snapshot was non-zero; refusing")

    best = max(daily.values())
    best_dates = [d for d, n in daily.items() if n == best]

    longest = streak = 0
    long_start = long_end = None
    for d in days:
        if daily[str(d)]:
            streak += 1
            if streak > longest:
                longest, long_end = streak, d
                long_start = d - timedelta(days=streak - 1)
        else:
            streak = 0

    # Current streak ends today when today has contributions, otherwise yesterday.
    anchor = end if daily[str(end)] else end - timedelta(days=1)
    current, cursor = 0, anchor
    while cursor >= start and daily[str(cursor)] > 0:
        current += 1
        cursor -= timedelta(days=1)

    months: dict[str, int] = {}
    for d in days:
        months[str(d)[:7]] = months.get(str(d)[:7], 0) + daily[str(d)]

    langs = languages(os.environ.get("GH_TOKEN")) or prev.get("languages")

    stats = {
        "as_of": str(end),
        "period_start": str(start),
        "period_end": str(end),
        "calendar_days": len(days),
        "total_contributions": total,
        "contributed_today": daily[str(end)] > 0,
        "active_days": active,
        "active_day_percent": round(active / len(days) * 100, 1),
        "best_day_count": best,
        "best_day_dates": best_dates,
        "avg_per_active_day": round(total / active, 1) if active else 0,
        "current_streak": current,
        "current_streak_end": str(anchor) if current else None,
        "current_streak_start": str(anchor - timedelta(days=current - 1)) if current else None,
        "longest_streak": longest,
        "longest_streak_start": str(long_start) if long_start else None,
        "longest_streak_end": str(long_end) if long_end else None,
        "streak_rule": "Current streak ends today when today has contributions, otherwise yesterday "
        "(today may be incomplete). Both streaks are clipped to the displayed calendar window.",
        "window_rule": "Same window as GitHub's profile calendar: the Sunday before one year ago through today (UTC).",
        "monthly_contributions": months,
        "daily_contributions": daily,
        "languages": langs,
        "sources": [URL, f"{API}/users/{USER}/repos"],
    }
    OUT.write_text(json.dumps(stats, indent=2) + "\n")
    print(f"{start}..{end}: {total} contributions (GitHub says {headline}), {active} active days, "
          f"streak {current}/{longest}")


if __name__ == "__main__":
    main()
