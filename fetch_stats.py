#!/usr/bin/env python3
"""Refresh public-stats.json from the public GitHub contribution calendar.

Stdlib only. Covers the trailing 365 days ending today (UTC).
GitHub's calendar endpoint ignores cross-year ranges, so each calendar year
in the window is fetched separately and the window is sliced locally.

Refuses to overwrite the snapshot if the page shape changes or data looks
wrong, so a GitHub markup change fails the workflow instead of publishing zeros.
"""
import html, json, re, sys, time, urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

USER = "Oussamaa02"
ROOT = Path(__file__).parent
OUT = ROOT / "public-stats.json"
URL = "https://github.com/users/{u}/contributions?from={y}-01-01&to={y}-12-31"


def fetch(year: int) -> str:
    req = urllib.request.Request(
        URL.format(u=USER, y=year),
        headers={"User-Agent": f"{USER}-profile-stats", "Accept": "text/html"},
    )
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(5 * (attempt + 1))
    raise SystemExit(f"fetch failed for {year}: {last}")


def parse(page: str, start: date, end: date, into: dict) -> None:
    tips = {
        m[0]: html.unescape(re.sub(r"<[^>]+>", "", m[1])).strip()
        for m in re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>(.*?)</tool-tip>', page, re.S)
    }
    if not tips:
        raise SystemExit("no tooltips found: GitHub calendar markup changed")
    for attrs in re.findall(r"<td\b([^>]+)>", page):
        d = re.search(r'data-date="(\d{4}-\d{2}-\d{2})"', attrs)
        ident = re.search(r'\bid="([^"]+)"', attrs)
        if not (d and ident) or not (str(start) <= d[1] <= str(end)):
            continue
        tip = tips.get(ident[1])
        if tip is None:
            raise SystemExit(f"missing tooltip for {d[1]}")
        n = re.match(r"([\d,]+) contribution", tip)
        if not n and not tip.startswith("No contributions"):
            raise SystemExit(f"unrecognised tooltip for {d[1]}: {tip!r}")
        into[d[1]] = int(n[1].replace(",", "")) if n else 0


def main() -> None:
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=364)
    daily: dict[str, int] = {}
    for year in sorted({start.year, end.year}):
        parse(fetch(year), start, end, daily)

    days = [start + timedelta(days=i) for i in range(365)]
    # GitHub may not have rendered "today" yet in some timezones: treat as 0.
    for d in days:
        daily.setdefault(str(d), 0)
    missing = [str(d) for d in days[:-1] if str(d) not in daily]
    if missing or len(daily) != 365:
        raise SystemExit(f"incomplete window: {len(daily)} days, missing {missing[:5]}")

    total = sum(daily.values())
    active = sum(v > 0 for v in daily.values())

    # Sanity guard: never replace a real snapshot with an all-zero fetch.
    if OUT.exists():
        prev = json.loads(OUT.read_text())
        if total == 0 and prev.get("total_contributions", 0) > 0:
            raise SystemExit("fetched 0 contributions but previous snapshot was non-zero; refusing")

    best = max(daily.values())
    best_dates = [d for d, n in sorted(daily.items()) if n == best]

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

    anchor = end if daily[str(end)] else end - timedelta(days=1)
    current, cursor = 0, anchor
    while cursor >= start and daily[str(cursor)] > 0:
        current += 1
        cursor -= timedelta(days=1)

    months: dict[str, int] = {}
    for d in days:
        months[str(d)[:7]] = months.get(str(d)[:7], 0) + daily[str(d)]

    stats = {
        "as_of": str(end),
        "period_start": str(start),
        "period_end": str(end),
        "calendar_days": 365,
        "total_contributions": total,
        "active_days": active,
        "active_day_percent": round(active / 365 * 100, 1),
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
        "(today may be incomplete). Both streaks are clipped to the displayed 365-day window.",
        "monthly_contributions": months,
        "daily_contributions": dict(sorted(daily.items())),
        "sources": [URL.format(u=USER, y=y) for y in sorted({start.year, end.year})],
    }
    OUT.write_text(json.dumps(stats, indent=2) + "\n")
    print(f"{start}..{end}: {total} contributions, {active} active days, streak {current}/{longest}")


if __name__ == "__main__":
    main()
