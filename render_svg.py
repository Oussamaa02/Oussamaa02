#!/usr/bin/env python3
"""Animated dithered-pixel SVGs for the GitHub profile README.

Pure stdlib. Reads public-stats.json (verified snapshot) and writes:
  assets/heatmap.svg   - LED dot-matrix contribution heatmap
  assets/analytics.svg - pixel-font stats + dithered monthly bars

Animation (CSS inside SVG, works in <img> on GitHub):
  * intro: stepped pixel "pop" in Bayer-dissolve order, plays on every load
  * loop : scanline sweep + LED twinkle, runs forever
  * prefers-reduced-motion disables motion
"""
import json, datetime as dt, random
from pathlib import Path

ROOT = Path(__file__).parent
S = json.loads((ROOT / "public-stats.json").read_text())

BG = "#07090a"
PANEL = "#0b0e0d"
LINE = "#1b2420"
DIM = "#16201b"
OFF = "#0f1512"
MUTED = "#5f6f66"
TEXT = "#c9d6cf"
G = ["#123a22", "#1f6b39", "#2ea84f", "#39d353", "#7dffa0"]  # dither inks
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"

BAYER4 = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]

# ---------------------------------------------------------------- pixel font
F = {
 "0": ["01110","10001","10011","10101","11001","10001","01110"],
 "1": ["00100","01100","00100","00100","00100","00100","01110"],
 "2": ["01110","10001","00001","00010","00100","01000","11111"],
 "3": ["11110","00001","00001","01110","00001","00001","11110"],
 "4": ["00010","00110","01010","10010","11111","00010","00010"],
 "5": ["11111","10000","11110","00001","00001","10001","01110"],
 "6": ["00110","01000","10000","11110","10001","10001","01110"],
 "7": ["11111","00001","00010","00100","01000","01000","01000"],
 "8": ["01110","10001","10001","01110","10001","10001","01110"],
 "9": ["01110","10001","10001","01111","00001","00010","01100"],
 ",": ["00000","00000","00000","00000","00000","01100","00100"],
 ".": ["00000","00000","00000","00000","00000","01100","01100"],
}

def pixel_text(s, x, y, px, gap, fill, cls="", delay0=0.0, step=0.012):
    out, cx, n = [], x, 0
    for ch in s:
        g = F[ch]
        for r, row in enumerate(g):
            for c, bit in enumerate(row):
                if bit == "1":
                    d = delay0 + (BAYER4[r % 4][c % 4] + n * 3) * step
                    out.append(f'<rect class="px {cls}" x="{cx + c*(px+gap)}" y="{y + r*(px+gap)}" '
                               f'width="{px}" height="{px}" fill="{fill}" style="animation-delay:{d:.3f}s"/>')
        cx += (4 if ch in ',.' else 6) * (px + gap)
        n += 1
    return "".join(out), cx - x

def css(extra=""):
    return f"""<style>
.px{{transform-box:fill-box;transform-origin:center;animation:pop .42s steps(4,end) both}}
@keyframes pop{{0%{{transform:scale(0);opacity:0}}60%{{transform:scale(1.35);opacity:1}}100%{{transform:scale(1);opacity:1}}}}
.tw{{animation:pop .42s steps(4,end) both,tw 3.2s steps(3,end) infinite}}
@keyframes tw{{0%,100%{{opacity:1}}50%{{opacity:.45}}}}
.scan{{animation:scan 6s steps(60,end) infinite;animation-delay:1.6s;opacity:0}}
@keyframes scan{{0%{{transform:translateX(0);opacity:.9}}100%{{transform:translateX(var(--w));opacity:.9}}}}
.cur{{animation:blink 1s steps(1,end) infinite}}
@keyframes blink{{50%{{opacity:0}}}}
.fade{{animation:fade .6s steps(5,end) both}}
@keyframes fade{{from{{opacity:0}}to{{opacity:1}}}}
{extra}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important;opacity:1!important;transform:none!important}}.scan{{display:none}}}}
</style>"""

def dither_defs(px=2, pitch=3):
    """LED-dot Bayer patterns for 5 levels. Tile = 4x4 dots."""
    t = 4 * pitch
    defs = []
    thresholds = [0, 4, 8, 12, 16]  # dots lit out of 16
    for lvl in range(5):
        dots = []
        for r in range(4):
            for c in range(4):
                lit = BAYER4[r][c] < thresholds[lvl] if lvl else False
                col = G[min(lvl, 4)] if lit else (DIM if lvl == 0 else OFF)
                if lvl == 4 and lit:
                    col = G[4] if BAYER4[r][c] < 6 else G[3]
                dots.append(f'<rect x="{c*pitch}" y="{r*pitch}" width="{px}" height="{px}" fill="{col}"/>')
        defs.append(f'<pattern id="d{lvl}" width="{t}" height="{t}" patternUnits="userSpaceOnUse">{"".join(dots)}</pattern>')
    return "".join(defs)

def frame(w, h, title):
    return (f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="10" fill="{BG}" stroke="{LINE}"/>'
            f'<text x="28" y="36" font-family="{FONT}" font-size="13" fill="{MUTED}" letter-spacing="1.5">'
            f'<tspan fill="{G[3]}">●</tspan>&#160;&#160;{title}</text>'
            f'<rect class="cur" x="{28 + 9*len(title) + 34}" y="25" width="8" height="14" fill="{G[3]}"/>')

# ---------------------------------------------------------------- heatmap
def heatmap():
    daily = S["daily_contributions"]
    start = dt.date.fromisoformat(S["period_start"])
    end = dt.date.fromisoformat(S["period_end"])
    nz = sorted(v for v in daily.values() if v > 0) or [1]
    q = [nz[min(len(nz) - 1, int(len(nz) * f))] for f in (0.25, 0.5, 0.75)]
    def lvl(v):
        if v == 0: return 0
        if v <= q[0]: return 1
        if v <= q[1]: return 2
        if v <= q[2]: return 3
        return 4

    cell, gapc = 12, 3
    pitch = cell + gapc
    ox, oy = 64, 78
    first_sun = start - dt.timedelta(days=(start.weekday() + 1) % 7)
    weeks = ((end - first_sun).days // 7) + 1
    W = ox + weeks * pitch + 40
    H = oy + 7 * pitch + 76

    rects, months, seen = [], [], set()
    d = start
    random.seed(7)
    while d <= end:
        wk = (d - first_sun).days // 7
        dow = (d.weekday() + 1) % 7
        v = daily.get(d.isoformat(), 0)
        L = lvl(v)
        x, y = ox + wk * pitch, oy + dow * pitch
        # dissolve order: diagonal sweep + Bayer jitter -> pixel pop-in
        delay = 0.15 + (wk + dow) * 0.018 + BAYER4[dow % 4][wk % 4] * 0.012
        cls = "px tw" if L >= 3 and random.random() < 0.35 else "px"
        tw = f";animation-delay:{delay:.3f}s,{delay + random.uniform(0, 3):.2f}s" if "tw" in cls else f";animation-delay:{delay:.3f}s"
        rects.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{cell}" height="{cell}" fill="url(#d{L})" style="{tw[1:]}"><title>{d.isoformat()}: {v}</title></rect>')
        if d.day <= 7 and dow == 0 and (d.year, d.month) not in seen:
            seen.add((d.year, d.month))
            months.append(f'<text class="fade" x="{x}" y="{oy - 10}" font-family="{FONT}" font-size="10" fill="{MUTED}" '
                          f'letter-spacing="1" style="animation-delay:{0.1 + wk*0.012:.2f}s">{d.strftime("%b").upper()}</text>')
        d += dt.timedelta(days=1)

    days = "".join(
        f'<text class="fade" x="{ox - 12}" y="{oy + i*pitch + 10}" text-anchor="end" font-family="{FONT}" font-size="10" fill="{MUTED}">{t}</text>'
        for i, t in ((1, "MON"), (3, "WED"), (5, "FRI")))

    span = weeks * pitch
    scan = (f'<g style="--w:{span - 6}px"><rect class="scan" x="{ox - 3}" y="{oy - 4}" width="6" height="{7*pitch + 5}" '
            f'fill="url(#sg)"/></g>')

    total = f'{S["total_contributions"]:,}'
    num, nw = pixel_text(total, ox, H - 52, 3, 1, G[3], delay0=1.1, step=0.01)
    legend_x = W - 40 - 5 * 18 - 70
    legend = (f'<text class="fade" x="{legend_x}" y="{H - 30}" font-family="{FONT}" font-size="10" fill="{MUTED}" style="animation-delay:1.3s">LESS</text>'
              + "".join(f'<rect class="px" x="{legend_x + 38 + i*18}" y="{H - 40}" width="12" height="12" fill="url(#d{i})" style="animation-delay:{1.3 + i*.06:.2f}s"/>' for i in range(5))
              + f'<text class="fade" x="{legend_x + 38 + 5*18 + 4}" y="{H - 30}" font-family="{FONT}" font-size="10" fill="{MUTED}" style="animation-delay:1.6s">MORE</text>')
    caption = (f'<text class="fade" x="{ox + nw + 14}" y="{H - 36}" font-family="{FONT}" font-size="12" fill="{TEXT}" letter-spacing="1" style="animation-delay:1.4s">CONTRIBUTIONS</text>'
               f'<text class="fade" x="{ox + nw + 14}" y="{H - 22}" font-family="{FONT}" font-size="10" fill="{MUTED}" letter-spacing="1" style="animation-delay:1.5s">{S["period_start"]} → {S["period_end"]} · SNAPSHOT</text>')

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
           f'aria-label="Contribution heatmap: {total} contributions, {S["period_start"]} to {S["period_end"]}">'
           f'<defs>{dither_defs()}<linearGradient id="sg" x1="0" x2="1"><stop offset="0" stop-color="{G[4]}" stop-opacity="0"/>'
           f'<stop offset=".5" stop-color="{G[4]}" stop-opacity=".55"/><stop offset="1" stop-color="{G[4]}" stop-opacity="0"/></linearGradient></defs>'
           + css() + frame(W, H, "~/oussamaa02 — contributions") + days + "".join(months) + "".join(rects) + scan + num + caption + legend + "</svg>")
    return svg, W

def date_span(a, b, empty):
    return f"{a[5:]} → {b[5:]}" if a and b else empty

# ---------------------------------------------------------------- analytics
def analytics(W):
    H = 470
    out = []
    cards = [
        ("CURRENT STREAK", str(S["current_streak"]), "DAYS", date_span(S["current_streak_start"], S["current_streak_end"], "NO ACTIVE STREAK"), True),
        ("LONGEST STREAK", str(S["longest_streak"]), "DAYS", date_span(S["longest_streak_start"], S["longest_streak_end"], "—"), True),
        ("ACTIVE DAYS", str(S["active_days"]), f'/ {S["calendar_days"]}', f'{S["active_day_percent"]}% OF THE YEAR', False),
        ("BEST DAY", str(S["best_day_count"]), "COMMITS", (S["best_day_dates"][0] if S["best_day_count"] else "—"), False),
        ("AVG / ACTIVE DAY", f'{S["avg_per_active_day"]}', "", "CONTRIBUTIONS", False),
    ]
    pad, top = 28, 62
    cw = (W - pad * 2 - 12 * 4) / 5
    ch = 118
    for i, (lab, val, unit, sub, hot) in enumerate(cards):
        x = pad + i * (cw + 12)
        d0 = 0.15 + i * 0.12
        out.append(f'<rect class="fade" x="{x:.1f}" y="{top}" width="{cw:.1f}" height="{ch}" rx="6" fill="{PANEL}" stroke="{LINE}" style="animation-delay:{d0:.2f}s"/>')
        out.append(f'<text class="fade" x="{x+14:.1f}" y="{top+24}" font-family="{FONT}" font-size="10" fill="{MUTED}" letter-spacing="1.4" style="animation-delay:{d0+.1:.2f}s">{lab}</text>')
        num, nw = pixel_text(val, x + 14, top + 40, 5, 1, G[4] if hot else TEXT, delay0=d0 + 0.2, step=0.011)
        out.append(num)
        if unit:
            out.append(f'<text class="fade" x="{x+14+nw+6:.1f}" y="{top+80}" font-family="{FONT}" font-size="10" fill="{MUTED}" letter-spacing="1" style="animation-delay:{d0+.5:.2f}s">{unit}</text>')
        out.append(f'<text class="fade" x="{x+14:.1f}" y="{top+104}" font-family="{FONT}" font-size="10" fill="{MUTED}" letter-spacing="1" style="animation-delay:{d0+.55:.2f}s">{sub}</text>')

    # monthly dithered pixel bars
    mo = S["monthly_contributions"]
    keys = list(mo.keys())
    mx = max(mo.values()) or 1
    by = H - 50
    bh = 190
    btop = by - bh
    out.append(f'<text class="fade" x="{pad}" y="{btop - 16}" font-family="{FONT}" font-size="10" fill="{MUTED}" letter-spacing="1.4" style="animation-delay:.9s">CONTRIBUTIONS / MONTH</text>')
    n = len(keys)
    slot = (W - pad * 2) / n
    blk, bg_ = 6, 2
    bp = blk + bg_
    cols = 5
    bw = cols * bp - bg_
    for i, k in enumerate(keys):
        v = mo[k]
        rows = max(1, round(v / mx * (bh // bp)))
        bx = pad + i * slot + (slot - bw) / 2
        hot = v == mx
        for r in range(rows):
            frac = r / max(1, (bh // bp))
            for c in range(cols):
                # dither: density increases toward the top of each bar
                lvl = 1 + int(frac * 3.99)
                if r == rows - 1:
                    lvl = 4
                lit = BAYER4[r % 4][c % 4] < [0, 6, 10, 14, 16][lvl]
                col = (G[4] if hot else G[3]) if (lit and lvl >= 3) else (G[lvl] if lit else DIM)
                d = 1.0 + i * 0.05 + r * 0.022 + BAYER4[r % 4][c % 4] * 0.004
                out.append(f'<rect class="px" x="{bx + c*bp:.1f}" y="{by - (r+1)*bp + bg_}" width="{blk}" height="{blk}" fill="{col}" style="animation-delay:{d:.3f}s"/>')
        lab = dt.date.fromisoformat(k + "-01").strftime("%b").upper()
        out.append(f'<text class="fade" x="{bx + bw/2:.1f}" y="{by + 18}" text-anchor="middle" font-family="{FONT}" font-size="10" fill="{MUTED}" style="animation-delay:{1.0 + i*.05:.2f}s">{lab}</text>')
        out.append(f'<text class="fade" x="{bx + bw/2:.1f}" y="{by - rows*bp - 6}" text-anchor="middle" font-family="{FONT}" font-size="10" '
                   f'fill="{G[4] if hot else TEXT}" style="animation-delay:{1.3 + i*.05 + rows*.02:.2f}s">{v}</text>')

    span = W - pad * 2
    scan = (f'<g style="--w:{span - 8}px"><rect class="scan" x="{pad}" y="{btop}" width="8" height="{bh + 2}" fill="url(#sg)"/></g>')
    foot = (f'<text class="fade" x="{pad}" y="{H - 14}" font-family="{FONT}" font-size="9.5" fill="{MUTED}" letter-spacing="1" style="animation-delay:1.8s">'
            f'{S["period_start"]} → {S["period_end"]} · EDGE MONTHS PARTIAL · VERIFIED PUBLIC SNAPSHOT</text>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
           f'aria-label="GitHub analytics: current streak {S["current_streak"]} days, longest {S["longest_streak"]} days, '
           f'{S["active_days"]} active days, best day {S["best_day_count"]}, average {S["avg_per_active_day"]} per active day, monthly bars">'
           f'<defs><linearGradient id="sg" x1="0" x2="1"><stop offset="0" stop-color="{G[4]}" stop-opacity="0"/>'
           f'<stop offset=".5" stop-color="{G[4]}" stop-opacity=".4"/><stop offset="1" stop-color="{G[4]}" stop-opacity="0"/></linearGradient></defs>'
           + css() + frame(W, H, "~/oussamaa02 — analytics") + "".join(out) + scan + foot + "</svg>")
    return svg

if __name__ == "__main__":
    hm, W = heatmap()
    (ROOT / "assets" / "heatmap.svg").write_text(hm)
    (ROOT / "assets" / "analytics.svg").write_text(analytics(W))
    print("width", W, "heatmap", len(hm), "analytics", (ROOT / "assets" / "analytics.svg").stat().st_size)
