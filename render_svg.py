#!/usr/bin/env python3
"""Minimal animated contribution card for the GitHub profile README.

Pure stdlib. Reads public-stats.json and writes two themes of one card:
  assets/profile-dark.svg
  assets/profile-light.svg
The README picks one with <picture> + prefers-color-scheme, which follows
the visitor's GitHub theme.

Contents: header (live dot, handle, total, 30-day trend), dot heatmap with a
weekday-rhythm column, monthly bars aligned under their weeks, a stats row and
a language strip.

Animation is CSS inside the SVG (works in <img> on GitHub): dots pop in once
along a diagonal, then a soft sweep, glowing top-level days, a blinking cursor
and a pulsing dot when you've contributed today. prefers-reduced-motion
turns all of it off.
"""
import json, random
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
S = json.loads((ROOT / "public-stats.json").read_text())
USER = "oussamaa02"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"

THEMES = {
    "dark": dict(bg="#0a0d0c", line="#1a211e", off="#141a17", muted="#5d6b64", text="#c9d6cf", hi="#eef7f1",
                 l1="#0e4429", l2="#006d32", l3="#26a641", l4="#39d353", acc="#39d353"),
    "light": dict(bg="#fbfcfb", line="#e3e8e5", off="#ebedf0", muted="#7d8a83", text="#2a3530", hi="#0f1a14",
                  l1="#9be9a8", l2="#40c463", l3="#30a14e", l4="#216e39", acc="#1f883d"),
}
# GitHub linguist colours for the languages likely to show up.
LANG_COLORS = {
    "Jupyter Notebook": "#DA5B0B", "Java": "#b07219", "Python": "#3572A5", "TypeScript": "#3178c6",
    "JavaScript": "#f1e05a", "TeX": "#3D6117", "CSS": "#663399", "HTML": "#e34c26", "Shell": "#89e051",
    "Dockerfile": "#384d54", "Kotlin": "#A97BFF", "C": "#555555", "C++": "#f34b7d", "Go": "#00ADD8",
    "Rust": "#dea584", "Dart": "#00B4AB", "Swift": "#F05138", "Cuda": "#3A4E3A", "Makefile": "#427819",
}
LANG_SHORT = {"Jupyter Notebook": "Jupyter"}

W, PX = 880, 32
CHAR13, CHAR12, CHAR11, CHAR10 = 7.8, 7.2, 6.6, 6.0  # monospace advance per font size


def esc(s) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, fs=11, fill="var(--muted)", anchor=None, weight=None, delay=0.0):
    a = f' text-anchor="{anchor}"' if anchor else ""
    w = f' font-weight="{weight}"' if weight else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{fs}" fill="{fill}"{a}{w} class="f" '
            f'style="animation-delay:{delay:.2f}s">{esc(s)}</text>')


def css() -> str:
    return f"""<style>
text{{font-family:{MONO}}}
.d{{transform-box:fill-box;transform-origin:center;animation:pop .5s steps(5,end) both}}
@keyframes pop{{0%{{transform:scale(0)}}70%{{transform:scale(1.3)}}100%{{transform:scale(1)}}}}
.g{{animation:pop .5s steps(5,end) both,glow 5s ease-in-out infinite}}
@keyframes glow{{0%,100%{{opacity:1}}50%{{opacity:.55}}}}
.f{{animation:fade .7s ease both}}@keyframes fade{{from{{opacity:0}}to{{opacity:1}}}}
.b{{transform-box:fill-box;transform-origin:bottom;animation:grow .6s steps(6,end) both}}
@keyframes grow{{from{{transform:scaleY(0)}}to{{transform:scaleY(1)}}}}
.bx{{transform-box:fill-box;transform-origin:left;animation:growx .6s steps(6,end) both}}
@keyframes growx{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
.c{{animation:blink 1.1s steps(1,end) infinite}}@keyframes blink{{50%{{opacity:0}}}}
.ring{{transform-box:fill-box;transform-origin:center;animation:ring 2s ease-out infinite}}
@keyframes ring{{0%{{transform:scale(1);opacity:.7}}100%{{transform:scale(3);opacity:0}}}}
.sw{{animation:sw 7s linear 2s infinite;opacity:0}}
@keyframes sw{{0%{{transform:translateX(0);opacity:0}}5%,55%{{opacity:1}}60%,100%{{transform:translateX(var(--w));opacity:0}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}.sw,.ring{{display:none}}}}
</style>"""


def card(theme: str) -> str:
    daily = S["daily_contributions"]
    keys = list(daily)
    start = date.fromisoformat(keys[0])
    off = (start.weekday() + 1) % 7  # row 0 = Sunday, like GitHub
    weeks = -(-(len(keys) + off) // 7)

    sub_y, oy = 60, 96
    rw = 96  # weekday-rhythm column
    p = (W - 2 * PX - rw) / weeks
    r = p * 0.34
    by = oy + 7 * p + 46
    sy = by + 34
    stats_end = sy + 66
    lang_info = S.get("languages") or {}
    if isinstance(lang_info, list):  # older snapshot format
        lang_info = {"shares": lang_info, "scope": "public"}
    langs = lang_info.get("shares") or []
    H = round(stats_end + (66 if langs else 0))

    nz = sorted(v for v in daily.values() if v) or [1]
    q = [nz[int(len(nz) * f)] for f in (0.25, 0.5, 0.75)]
    def lvl(v):
        return 0 if not v else 1 if v <= q[0] else 2 if v <= q[1] else 3 if v <= q[2] else 4

    o = [f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="12" fill="var(--bg)" stroke="var(--line)"/>']

    # header: live dot + handle + cursor, total + 30-day trend
    if S.get("contributed_today"):
        o.append(f'<circle class="ring" cx="{PX+4}" cy="36" r="4" fill="var(--acc)"/>')
        o.append(f'<circle cx="{PX+4}" cy="36" r="4" fill="var(--acc)"/>')
    else:
        o.append(f'<circle cx="{PX+4}" cy="36" r="4" fill="var(--muted)"/>')
    o.append(text(PX + 16, 40, USER, fs=13, fill="var(--hi)", weight=600))
    o.append(f'<rect class="c" x="{PX + 16 + len(USER) * CHAR13 + 5:.1f}" y="29" width="7" height="14" fill="var(--acc)"/>')
    o.append(f'<text x="{W-PX}" y="40" text-anchor="end" font-size="12" fill="var(--muted)" class="f" style="animation-delay:.9s">'
             f'<tspan fill="var(--hi)" font-weight="600">{S["total_contributions"]:,}</tspan> contributions in the last year</text>')
    vals = list(daily.values())
    last30, prev30 = sum(vals[-30:]), sum(vals[-60:-30])
    if prev30 and last30 >= prev30:
        trend = f'<tspan fill="var(--acc)">▲ {last30:,}</tspan> in the last 30 days · {last30 / prev30:.1f}× the 30 before'
    elif prev30:
        trend = f'<tspan fill="var(--text)">▼ {last30:,}</tspan> in the last 30 days · {prev30:,} the 30 before'
    else:
        trend = f'<tspan fill="var(--acc)">{last30:,}</tspan> in the last 30 days'
    o.append(f'<text x="{W-PX}" y="{sub_y}" text-anchor="end" font-size="11" fill="var(--muted)" class="f" '
             f'style="animation-delay:1.1s">{trend}</text>')

    # heatmap
    random.seed(7)
    col = ["var(--off)", "var(--l1)", "var(--l2)", "var(--l3)", "var(--l4)"]
    for i, k in enumerate(keys):
        n = i + off
        wk, dw = divmod(n, 7)
        L = lvl(daily[k])
        cx, cy = PX + wk * p + p / 2, oy + dw * p + p / 2
        d = 0.1 + (wk + dw) * 0.014
        if L == 4 and random.random() < 0.5:
            o.append(f'<circle class="d g" cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{col[L]}" '
                     f'style="animation-delay:{d:.3f}s,{random.uniform(0, 5):.2f}s"/>')
        else:
            o.append(f'<circle class="d" cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{col[L]}" style="animation-delay:{d:.3f}s"/>')
    hw = weeks * p
    o.append('<defs><linearGradient id="sg" x1="0" x2="1"><stop offset="0" stop-color="var(--acc)" stop-opacity="0"/>'
             '<stop offset=".5" stop-color="var(--acc)" stop-opacity=".18"/><stop offset="1" stop-color="var(--acc)" stop-opacity="0"/>'
             '</linearGradient></defs>')
    o.append(f'<g style="--w:{hw - 40:.0f}px"><rect class="sw" x="{PX}" y="{oy - 4}" width="40" height="{7 * p + 8:.1f}" fill="url(#sg)"/></g>')

    # weekday rhythm, one bar per heatmap row
    wd = [0] * 7
    for k, v in daily.items():
        wd[(date.fromisoformat(k).weekday() + 1) % 7] += v
    mx = max(wd) or 1
    x0, bw = PX + hw + 18, rw - 44
    for i, name in enumerate(["sun", "mon", "tue", "wed", "thu", "fri", "sat"]):
        cy, top = oy + i * p + p / 2, wd[i] == mx
        o.append(text(x0, cy + 3.5, name, fs=9.5, fill="var(--hi)" if top else "var(--muted)", delay=1.2))
        o.append(f'<rect class="bx" x="{x0 + 26:.1f}" y="{cy - 3:.1f}" width="{max(1, wd[i] / mx * bw):.1f}" height="6" rx="3" '
                 f'fill="{"var(--l4)" if top else "var(--l2)"}" opacity="{1 if top else .7}" style="animation-delay:{1.2 + i * .05:.2f}s"/>')

    # monthly bars under the weeks they cover (a shared week goes to the later month)
    mo = S["monthly_contributions"]
    mmax = max(mo.values()) or 1
    span = {}
    for j, k in enumerate(keys):
        wk = (j + off) // 7
        a, b = span.get(k[:7], (wk, wk))
        span[k[:7]] = (min(a, wk), max(b, wk))
    for i, m in enumerate(mo):
        a, b = span[m]
        if i:
            a += 1
        x, w = PX + a * p + 2, max(p - 4, (b - a + 1) * p - 4)
        v = mo[m]
        h, top = max(2, v / mmax * 30), v == mmax
        o.append(f'<rect class="b" x="{x:.1f}" y="{by - h:.1f}" width="{w:.1f}" height="{h:.1f}" rx="2" '
                 f'fill="{"var(--l4)" if top else "var(--l2)"}" opacity="{1 if top else .75}" style="animation-delay:{1 + i * .05:.2f}s"/>')
        o.append(text(x + w / 2, by + 16, date.fromisoformat(m + "-01").strftime("%b").lower(), fs=10, anchor="middle", delay=1 + i * .05))
        if top:
            o.append(text(x + w / 2, by - h - 6, v, fs=10, anchor="middle", fill="var(--hi)", delay=1.6))

    # stats row
    o.append(f'<line x1="{PX}" x2="{W-PX}" y1="{sy:.1f}" y2="{sy:.1f}" stroke="var(--line)"/>')
    stats = [
        (S["current_streak"], "days", "current streak"),
        (S["longest_streak"], "days", "longest streak"),
        (S["active_days"], f'/ {S["calendar_days"]}', "active days"),
        (S["best_day_count"], "", "best day"),
        (S["avg_per_active_day"], "", "avg / active day"),
    ]
    cw = (W - 2 * PX) / len(stats)
    for i, (v, unit, label) in enumerate(stats):
        x = PX + i * cw
        if i:
            o.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{sy + 14:.1f}" y2="{stats_end - 16:.1f}" stroke="var(--line)"/>')
        tx = x + 18 if i else x
        u = f'<tspan font-size="11" fill="var(--muted)" dx="5">{esc(unit)}</tspan>' if unit else ""
        o.append(f'<text x="{tx:.1f}" y="{sy + 34:.1f}" class="f" style="animation-delay:{1.3 + i * .08:.2f}s">'
                 f'<tspan font-size="18" font-weight="600" fill="{"var(--acc)" if i < 2 else "var(--hi)"}">{v}</tspan>{u}</text>')
        o.append(text(tx, sy + 51, label, fs=10, delay=1.35 + i * .08))

    # language strip
    if langs:
        o.append(f'<line x1="{PX}" x2="{W-PX}" y1="{stats_end:.1f}" y2="{stats_end:.1f}" stroke="var(--line)"/>')
        scope = "incl. private repos" if lang_info.get("scope") == "all" else "public repos"
        o.append(text(PX, stats_end + 22, "languages", fs=10, delay=1.5))
        o.append(text(W - PX, stats_end + 22, f"weighted by my commits · last year · {scope}", fs=10, anchor="end", delay=1.5))
        ly = stats_end + 16
        x, lx, tw = PX, PX, W - 2 * PX
        for i, (name, pct) in enumerate(langs):
            c = LANG_COLORS.get(name, "#8b949e")
            w = pct / 100 * tw
            o.append(f'<rect class="bx" x="{x:.1f}" y="{ly + 14:.1f}" width="{max(1, w - 2):.1f}" height="6" rx="3" fill="{c}" '
                     f'style="animation-delay:{1.5 + i * .06:.2f}s"/>')
            x += w
            label = f"{LANG_SHORT.get(name, name)} {pct:g}%"
            o.append(f'<circle cx="{lx + 3:.1f}" cy="{ly + 36:.1f}" r="3" fill="{c}" class="f" style="animation-delay:1.8s"/>')
            o.append(text(lx + 11, ly + 39.5, label, fs=10, delay=1.8))
            lx += len(label) * CHAR10 + 28

    label = (f'{S["total_contributions"]:,} contributions from {S["period_start"]} to {S["period_end"]}; '
             f'current streak {S["current_streak"]} days, longest {S["longest_streak"]} days, '
             f'{S["active_days"]} active days, best day {S["best_day_count"]}')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="{esc(label)}"><title>{esc(label)}</title>{css()}' + "".join(o) + "</svg>")
    # Bake theme colours in (no CSS variables in presentation attributes, for any renderer).
    for k, v in sorted(THEMES[theme].items(), key=lambda kv: -len(kv[0])):
        svg = svg.replace(f"var(--{k})", v)
    return svg


if __name__ == "__main__":
    for theme in THEMES:
        svg = card(theme)
        (ROOT / "assets" / f"profile-{theme}.svg").write_text(svg)
        print(theme, len(svg))
