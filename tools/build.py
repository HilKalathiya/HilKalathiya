#!/usr/bin/env python3
"""Rebuilds the profile from showcase.yml and the live state of each project repo.

For every project listed in showcase.yml it makes a light treeless clone of the
repository, reads the values the config points at (README numbers, commit
count, last-update date, test counts...), draws the figures as self-contained
SVGs (light + dark, fonts embedded) and writes README.md.

Run:  python3 tools/build.py              (clones into .cache/)
      python3 tools/build.py --offline    (reuse .cache/ without fetching)
"""
import argparse, base64, datetime as dt, fnmatch, glob, io, math, os, re, subprocess, sys, textwrap
from xml.sax.saxutils import escape as esc

import yaml
from fontTools import ttLib
from PIL import ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "assets")
CACHE = os.path.join(ROOT, ".cache")
FONTS = os.path.join(ROOT, "tools", "fonts")
WARNINGS = []


def warn(msg):
    WARNINGS.append(msg)
    print("WARNING:", msg, file=sys.stderr)


# ================================================================ live repo data
class Repo:
    def __init__(self, owner, name, offline=False):
        self.name = name
        self.dir = os.path.join(CACHE, name + ".git")
        url = f"https://github.com/{owner}/{name}.git"
        if not offline:
            if os.path.isdir(self.dir):
                self._git("fetch", "-q", "--filter=blob:none", "origin", "+HEAD:HEAD", check=False)
            else:
                os.makedirs(CACHE, exist_ok=True)
                subprocess.run(["git", "clone", "-q", "--bare", "--filter=blob:none", url, self.dir], check=True)
        self.ok = os.path.isdir(self.dir)
        self._files = {}

    def _git(self, *args, check=True):
        r = subprocess.run(["git", "-C", self.dir, *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if check and r.returncode:
            raise RuntimeError(r.stderr.strip())
        return r.stdout

    def file(self, path):
        if path not in self._files:
            try:
                self._files[path] = self._git("show", f"HEAD:{path}").lstrip("﻿")
            except RuntimeError:
                self._files[path] = None
        return self._files[path]

    def paths(self):
        return self._git("ls-tree", "-r", "--name-only", "HEAD").splitlines()

    def commits(self):
        return int(self._git("rev-list", "--count", "HEAD").strip())

    def updated(self):
        iso = self._git("log", "-1", "--format=%cI").strip()
        d = dt.datetime.fromisoformat(iso).astimezone(dt.timezone(dt.timedelta(hours=5, minutes=30)))
        return f"{d.day} {d.strftime('%b %Y')}"


def resolve(v, repo, where):
    """Replace every {$...} binding in v with the value read from the repo."""
    if isinstance(v, list):
        if all(isinstance(x, (str, dict)) for x in v) and any(isinstance(x, dict) and _is_binding(x) for x in v) \
                and any(isinstance(x, str) for x in v):
            return "".join(str(resolve(x, repo, where)) for x in v)  # text with live parts
        return [resolve(x, repo, where) for x in v]
    if isinstance(v, dict):
        if _is_binding(v):
            return _bind(v, repo, where)
        return {k: resolve(x, repo, f"{where}.{k}") for k, x in v.items()}
    return v


def _is_binding(d):
    return isinstance(d, dict) and any(k.startswith("$") for k in d)


def _fmt(val, b):
    f = b.get("format")
    if f:
        try:
            return f.format(int(val))
        except (ValueError, TypeError):
            pass
    return str(val)


def _bind(b, repo, where):
    fb = b.get("fallback")
    try:
        if "$git" in b:
            val = {"commits": repo.commits, "updated": repo.updated}[b["$git"]]()
        elif "$match" in b:
            text = repo.file(b.get("file", "README.md")) or ""
            m = re.search(b["$match"], text, re.M)
            if not m:
                raise LookupError(f"no match for {b['$match']!r} in {b.get('file', 'README.md')}")
            val = m.group(b.get("group", 1)).strip()
        elif "$count" in b:
            files = [b["file"]] if "file" in b else [p for p in repo.paths() if fnmatch.fnmatch(p, b["glob"])]
            rx = re.compile(b["$count"], re.M)
            val = sum(len(rx.findall(repo.file(p) or "")) for p in files)
            if val == 0:
                raise LookupError(f"count of {b['$count']!r} is 0")
        elif "$cell" in b:
            text = repo.file(b.get("file", "README.md")) or ""
            rx = re.compile(b["$cell"])
            val = None
            for line in text.splitlines():
                if not line.startswith("|"):
                    continue
                cells = [c.strip().replace("*", "") for c in line.strip().strip("|").split("|")]
                if cells and rx.search(cells[0]):
                    nums = re.findall(r"-?\d+(?:\.\d+)?", cells[b["col"]])
                    val = nums[b.get("pick", 0)]
                    break
            if val is None:
                raise LookupError(f"no table row for {b['$cell']!r}")
        else:
            raise LookupError(f"unknown binding {b}")
        return _fmt(val, b)
    except Exception as e:  # never break the profile: fall back and report
        warn(f"{repo.name} {where}: {e}; using fallback {fb!r}")
        if fb is None:
            return ""
        return str(fb)


def load_project(entry, owner, offline):
    repo = Repo(owner, entry["repo"], offline)
    own = repo.file(".github/showcase.yml")
    if own:  # the project repo can own its panel
        try:
            entry = {**entry, **(yaml.safe_load(own) or {})}
            print(f"{repo.name}: using its own .github/showcase.yml")
        except yaml.YAMLError as e:
            warn(f"{repo.name}: .github/showcase.yml is not valid YAML ({e}); ignored")
    p = resolve(entry, repo, entry["repo"])
    p["updated"] = repo.updated()
    p["commits"] = repo.commits()
    p["url"] = f"https://github.com/{owner}/{entry['repo']}"
    return p


# ================================================================ fonts + type
def _woff(path):
    f = ttLib.TTFont(path, recalcTimestamp=False)
    f.flavor = "woff"
    buf = io.BytesIO()
    f.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


FONT_FILES = {"lora600": ("PLora", 600, "Lora-600.ttf"), "lora400": ("PLora", 400, "Lora-400.ttf"),
              "inter400": ("PInter", 400, "Inter-400.otf"), "inter600": ("PInter", 600, "Inter-600.otf")}
_B64 = {}


def font_face(used):
    out = ""
    for k in used:
        fam, w, fn = FONT_FILES[k]
        if k not in _B64:
            _B64[k] = _woff(os.path.join(FONTS, fn))
        out += f"@font-face{{font-family:'{fam}';font-weight:{w};src:url(data:font/woff;base64,{_B64[k]}) format('woff')}}\n"
    return out


_F = {}


def tw(t, size, bold=False):
    k = bold
    if k not in _F:
        _F[k] = ImageFont.truetype(os.path.join(FONTS, "Inter-600.otf" if bold else "Inter-400.otf"), 100)
    return _F[k].getlength(t) * size / 100


def wrap_px(s, px, size, bold=False):
    """Wrap text to a pixel width (Inter metrics)."""
    words, lines, cur = s.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if tw(t, size, bold) > px and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


# ================================================================ themes
THEMES = {
    "light": dict(ink="#1f2328", body="#454d57", mute="#656d76", rule="#d0d7de",
                  faint="#eaeef2", accent="#0b7285", bg="#ffffff"),
    "dark": dict(ink="#e6edf3", body="#b6bec7", mute="#8b949e", rule="#30363d",
                 faint="#21262d", accent="#3bc9db", bg="#0d1117"),
}
PALS = {
 "rose":   {"light": dict(bg="#fbeff1", accent="#b8234f", faint="#f2d9de", rule="#e3bcc5"), "dark": dict(bg="#271a1f", accent="#ff8fa8", faint="#3a2830", rule="#55383f")},
 "teal":   {"light": dict(bg="#e6f3f5", accent="#0b7285", faint="#cbe4e8", rule="#a9cfd6"), "dark": dict(bg="#11252a", accent="#3bc9db", faint="#1d3a41", rule="#2c5560")},
 "indigo": {"light": dict(bg="#ecedfc", accent="#4547c9", faint="#d5d7f6", rule="#b7baee"), "dark": dict(bg="#1a1b36", accent="#a5a9ff", faint="#2a2c52", rule="#40437a")},
 "amber":  {"light": dict(bg="#fdf1dc", accent="#a65a00", faint="#f3dfb9", rule="#e3c88f"), "dark": dict(bg="#2a2112", accent="#ffc266", faint="#3d3119", rule="#5a4824")},
 "green":  {"light": dict(bg="#e7f5ea", accent="#247a37", faint="#cde8d3", rule="#a8d3b1"), "dark": dict(bg="#14261a", accent="#6fd58a", faint="#1f3b27", rule="#2e5a3b")},
 "slate":  {"light": dict(bg="#eceff3", accent="#3d4b5c", faint="#d9dfe6", rule="#bcc5cf"), "dark": dict(bg="#1c2128", accent="#a9b7c8", faint="#2b323b", rule="#404a56")},
}
STRAND = {"rose": "#ff8fa8", "teal": "#3bc9db", "indigo": "#a5a9ff", "amber": "#ffc266", "green": "#6fd58a", "slate": "#a9b7c8"}
# the lead panel is dark in both themes, like the header
LEAD = dict(bg="#0e1726", ink="#ffffff", body="#c6d0db", mute="#8d9bab", rule="#26354a", faint="#17233a",
            accent="#7cc4ff", model="#ffc266", code="#3bc9db", person="#ff8fa8")
PAD = 28
W_IN = 880

SERIF = "'PLora',Lora,Georgia,'Times New Roman',serif"
SANS = "'PInter',Inter,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"


def PAL(theme, key):
    c = dict(THEMES[theme])
    c.update(PALS[key][theme])
    return c


def svg(name, theme, w, h, body, used, title, c, pad=0, rx=20):
    if pad:
        body = (f'<rect width="{w+2*pad}" height="{h+2*pad}" rx="{rx}" fill="{c["bg"]}"/>'
                f'<g transform="translate({pad},{pad})">{body}</g>')
        w, h = w + 2 * pad, h + 2 * pad
    doc = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" viewBox="0 0 {w:.0f} {h:.0f}" role="img" aria-label="{esc(title)}">
<style>
{font_face(used)}
text{{font-family:{SANS};fill:{c["ink"]}}}
.serif{{font-family:{SERIF}}}
.b{{font-weight:600}}
.body{{fill:{c["body"]}}}
.mute{{fill:{c["mute"]}}}
.acc{{fill:{c["accent"]}}}
</style>
{body}
</svg>'''
    with open(os.path.join(OUT, f"{name}-{theme}.svg"), "w", encoding="utf-8") as f:
        f.write(doc)
    return f"{name}-{theme}.svg"


def T(x, y, s, size=15, cls="", anchor="start", extra=""):
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" class="{cls}"{a} {extra}>{esc(str(s))}</text>'


def para_px(x, y, s, px, size=15, lh=23, cls="body"):
    lines = wrap_px(s, px, size)
    return "".join(T(x, y + i * lh, ln, size, cls) for i, ln in enumerate(lines)), len(lines)


def num(s, default=0.0):
    try:
        return float(str(s).replace(",", "").rstrip("%"))
    except ValueError:
        return default


# ================================================================ header
def header(theme, cfg, strands):
    W, H = W_IN + 2 * PAD, 396
    bg = "#14202b" if theme == "light" else "#161b22"
    X = 48
    b = f'<rect width="{W}" height="{H}" rx="22" fill="{bg}"/>'
    n = len(strands)
    for k, col in enumerate(strands):
        pts = []
        for i in range(61):
            t = i / 60
            x = 540 + t * 360
            y = 150 + 46 * math.sin(t * 5.2 + k * 1.15) * (0.55 + 0.45 * t) + (k - (n - 1) / 2) * 30 - t * 18
            pts.append((x, y))
        b += (f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="none" stroke="{col}" '
              f'stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" opacity="0.95"/>')
        b += f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="6" fill="{col}"/>'
    b += T(X, 130, cfg["name"], 76, "serif b", extra='letter-spacing="-2" style="fill:#ffffff"')
    for i, ln in enumerate(cfg["tagline"]):
        b += T(X, 188 + i * 36, ln, 29, "serif", extra='style="font-weight:400;fill:#d6dde5"')
    p, _ = para_px(X, 276, cfg["intro"], 520, 15, 23, "mute")
    b += p
    pill = cfg["pill"]
    pw = tw(pill, 14.5, True) + 40
    b += f'<rect x="{X}" y="{H-62}" width="{pw:.0f}" height="34" rx="17" fill="#3bc9db"/>'
    b += T(X + 20, H - 40, pill, 14.5, "b", extra='style="fill:#0b1b22"')
    alt = f"{cfg['name']}. {' '.join(cfg['tagline'])} {cfg['pill']}."
    svg("header", theme, W, H, b, ["lora600", "lora400", "inter400", "inter600"], alt,
        {**THEMES[theme], "mute": "#9aa7b4", "body": "#9aa7b4"})
    return alt


def heading(name, theme, title, note):
    c = THEMES[theme]
    W, H = W_IN + 2 * PAD, 76
    b = f'<rect x="0" y="12" width="40" height="5" rx="2.5" fill="{c["ink"]}"/>'
    b += T(0, 58, title, 34, "serif b", extra='letter-spacing="-0.8"')
    b += T(W, 58, note, 14, "mute", "end")
    svg(name, theme, W, H, b, ["lora600", "inter400"], title, c)


# ================================================================ lead panel (eCTD)
def lead(theme, p, name):
    c = LEAD
    W = W_IN
    b = ""
    b += T(0, 18, p.get("kicker", "").upper(), 12.5, "b", extra=f'letter-spacing="1.4" style="fill:{c["accent"]}"')
    title_lines = wrap_px(p["title"], W, 40, True)
    y = 70
    for ln in title_lines:
        b += T(0, y, ln, 42, "serif b", extra='letter-spacing="-1"')
        y += 48
    y -= 30
    # status pill + live meta
    pw = tw(p["status"], 13.5, True) + 26
    b += f'<rect x="0" y="{y}" width="{pw:.0f}" height="26" rx="13" fill="{c["accent"]}"/>'
    b += T(13, y + 18, p["status"], 13.5, "b", extra=f'style="fill:{c["bg"]}"')
    b += T(pw + 14, y + 18, f"Updated {p['updated']}  ·  {p['commits']:,} commits", 13, "mute")
    y += 62
    t, n = para_px(0, y, p["desc"], 800, 16.5, 26, "body")
    b += t
    y += n * 26 + 18
    # pipeline
    steps = p["pipeline"]
    k = len(steps)
    gap = 14
    bw = (W - (k - 1) * gap) / k
    bh = 150
    roles = {"model": ("Model", c["model"]), "code": ("Code", c["code"]), "person": ("Person", c["person"])}
    for i, (nm, sub, role) in enumerate(steps):
        x = i * (bw + gap)
        lab, col = roles[role]
        b += f'<rect x="{x:.1f}" y="{y}" width="{bw:.1f}" height="{bh}" rx="12" fill="{c["faint"]}" stroke="{col if role != "code" else c["rule"]}" stroke-width="{1.6 if role != "code" else 1}"/>'
        b += f'<circle cx="{x+16:.1f}" cy="{y+22}" r="4" fill="{col}"/>'
        b += T(x + 26, y + 26, f"{i+1:02d}", 11.5, "b", extra=f'style="fill:{c["mute"]}" letter-spacing="0.6"')
        b += T(x + 12, y + 50, nm, 17, "serif b")
        for j, ln in enumerate(wrap_px(sub, bw - 22, 11.5)[:4]):
            b += T(x + 12, y + 72 + j * 15, ln, 11.5, "body")
        cw = tw(lab, 11, True) + 16
        b += f'<rect x="{x+12:.1f}" y="{y+bh-28}" width="{cw:.0f}" height="18" rx="9" fill="{col}" fill-opacity="0.18"/>'
        b += T(x + 20, y + bh - 15, lab, 11, "b", extra=f'style="fill:{col}"')
        if i < k - 1:
            ax = x + bw + 2
            b += f'<path d="M{ax:.1f} {y+bh/2:.1f} l{gap-4:.1f} 0 m-4 -4 l4 4 l-4 4" fill="none" stroke="{c["mute"]}" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>'
    y += bh + 30
    t, n = para_px(0, y, p["pipeline_note"], W, 13.5, 20, "mute")
    b += t
    y += (n - 1) * 20 + 30
    b += f'<line x1="0" y1="{y}" x2="{W}" y2="{y}" stroke="{c["rule"]}" stroke-width="1"/>'
    y += 22
    # stats
    st = p["stats"]
    cw = W / len(st)
    hmax = 0
    for i, s in enumerate(st):
        x = i * cw
        b += T(x, y + 40, s["value"], 44, "serif b", extra=f'letter-spacing="-1" style="fill:{c["accent"]}"')
        lines = wrap_px(s["label"], cw - 26, 13)
        for j, ln in enumerate(lines):
            b += T(x, y + 66 + j * 18, ln, 13, "body")
        hmax = max(hmax, 66 + (len(lines) - 1) * 18)
    y += hmax + 34
    for j, ln in enumerate(wrap_px(p["built"], W, 13)):
        b += T(0, y + j * 19, ln, 13, "mute")
    y += (len(wrap_px(p["built"], W, 13)) - 1) * 19 + 6
    alt = (f"{p['title']}: {p['desc']} " + " ".join(f"{s['value']} {s['label']}." for s in p["stats"]))
    svg(name, theme, W, y, b, ["lora600", "inter400", "inter600"], alt, c, PAD, 22)
    return alt


# ================================================================ feature panels
L, R = 410, W_IN


def blk_dots(c, d, y):
    b = T(L, y + 14, d["title"], 14, "b")
    if d.get("note"):
        b += T(R, y + 14, d["note"], 12.5, "mute", "end")
    rows = d["rows"]
    PX0, PX1 = 646, 826
    gy0, gy1 = y + 30, y + 44 + len(rows) * 32
    dec = d.get("decimals")

    def pxv(v):
        return PX0 + (max(0.5, min(1.0, v)) - 0.5) / 0.5 * (PX1 - PX0)

    for v, lab in ((0.5, "0.5"), (0.75, "0.75"), (1.0, "1.0")):
        b += f'<line x1="{pxv(v):.1f}" y1="{gy0}" x2="{pxv(v):.1f}" y2="{gy1}" stroke="{c["faint"] if v != 0.5 else c["rule"]}" stroke-width="1"/>'
        b += T(pxv(v), gy1 + 20, lab, 11.5, "mute", "middle")
    b += T(L, gy1 + 20, d.get("axis", ""), 12, "mute")
    for i, r in enumerate(rows):
        yy = gy0 + 26 + i * 32
        v = num(r["value"])
        ours = r.get("ours")
        b += T(L, yy + 4.5, r["label"], 13.5, "b" if ours else "body")
        col = c["accent"] if ours else c["ink"]
        lo = hi = None
        if r.get("ci"):
            lo, hi = num(r["ci"][0]), num(r["ci"][1])
        elif r.get("sd") and num(r["sd"]) > 0:
            lo, hi = v - num(r["sd"]), v + num(r["sd"])
        if lo is not None:
            b += f'<line x1="{pxv(lo):.1f}" y1="{yy}" x2="{pxv(hi):.1f}" y2="{yy}" stroke="{col}" stroke-width="2"/>'
            if r.get("ci"):
                for xx in (pxv(lo), pxv(hi)):
                    b += f'<line x1="{xx:.1f}" y1="{yy-4}" x2="{xx:.1f}" y2="{yy+4}" stroke="{col}" stroke-width="2"/>'
        if ours:
            b += f'<circle cx="{pxv(v):.1f}" cy="{yy}" r="5.5" fill="{col}"/>'
        else:
            b += f'<circle cx="{pxv(v):.1f}" cy="{yy}" r="5" fill="{c["bg"]}" stroke="{col}" stroke-width="2"/>'
        shown = f"{v:.{dec}f}" if dec else str(r["value"])
        b += T(R, yy + 4.5, shown, 14, "b", "end")
    return b, gy1 + 34 - y


def blk_rule(c, y):
    return f'<line x1="{L}" y1="{y}" x2="{R}" y2="{y}" stroke="{c["rule"]}" stroke-width="1"/>', 1


def blk_stats(c, d, y):
    b, hmax = "", 0
    items = d["items"]
    cw = (R - L) / len(items)
    for i, s in enumerate(items):
        x = L + i * cw
        b += T(x, y + 30, s["value"], 34, "serif b acc", extra='letter-spacing="-0.8"')
        lines = wrap_px(s["label"], cw - 14, 12.5)
        for j, ln in enumerate(lines):
            b += T(x, y + 54 + j * 17, ln, 12.5, "body")
        hmax = max(hmax, 54 + (len(lines) - 1) * 17)
    return b, hmax + 8


def blk_note(c, d, y):
    b, h = "", 0
    if d.get("title"):
        b += T(L, y + 13, d["title"], 13, "b")
        h = 20
    t, n = para_px(L, y + h + 13, d["text"], R - L, 13, 19, "body")
    return b + t, h + 13 + (n - 1) * 19 + 6


def blk_progress(c, d, y):
    done, total = int(num(d["done"])), int(num(d["total"]))
    b = T(L, y + 14, d.get("title", "Progress"), 14, "b")
    b += T(R, y + 14, f"{done} of {total} steps shipped", 12.5, "mute", "end")
    ty = y + 26
    gap = 4.4
    sw = (R - L - (total - 1) * gap) / max(total, 1)
    for i in range(total):
        x = L + i * (sw + gap)
        if i < done:
            b += f'<rect x="{x:.1f}" y="{ty}" width="{sw:.1f}" height="10" rx="2" fill="{c["accent"]}"/>'
        else:
            b += f'<rect x="{x+0.75:.1f}" y="{ty+0.75}" width="{sw-1.5:.1f}" height="8.5" rx="2" fill="none" stroke="{c["rule"]}" stroke-width="1.5"/>'
    t, n1 = para_px(L, ty + 36, d["text"], R - L, 13, 19, "body")
    b += t
    h = ty + 36 + n1 * 19 - y
    if d.get("next"):
        t, n2 = para_px(L, ty + 42 + n1 * 19, d["next"], R - L, 13, 19, "mute")
        b += t
        h += 6 + n2 * 19
    return b, h - 10


def blk_forecast(c, d, y):
    """Illustrative ICU forecast (shape only, labelled as not real data)."""
    X0, X1 = 446, R
    Y0, Y1 = y + 32, y + 172
    b = T(L, y + 14, "ICU beds in use", 14, "b")
    b += T(X1, y + 14, "Illustrative data, not real patients", 12.5, "mute", "end")
    vmin, vmax = 44, 86

    def px(i, n):
        return X0 + (X1 - X0) * i / (n - 1)

    def py(v):
        return Y1 - (v - vmin) / (vmax - vmin) * (Y1 - Y0)

    for v in (50, 65, 80):
        b += f'<line x1="{X0}" y1="{py(v):.1f}" x2="{X1}" y2="{py(v):.1f}" stroke="{c["faint"]}" stroke-width="1"/>'
        b += T(X0 - 8, py(v) + 4, str(v), 11.5, "mute", "end")
    n_past, n_fut = 31, 11
    n = n_past + n_fut - 1

    def f(i):
        return 63 + 9 * math.sin(i * 0.5) + 3.2 * math.sin(i * 1.7 + 1) + i * 0.12

    past = [(px(i, n), py(f(i))) for i in range(n_past)]
    today_x = past[-1][0]
    fut = [(px(n_past - 1 + j, n), py(63 + 9 * math.sin((n_past - 1 + j) * 0.5) + (n_past - 1 + j) * 0.12)) for j in range(n_fut)]
    up = [(x, yy - (2 + j * 1.15) * (Y1 - Y0) / (vmax - vmin)) for j, (x, yy) in enumerate(fut)]
    dn = [(x, yy + (2 + j * 1.15) * (Y1 - Y0) / (vmax - vmin)) for j, (x, yy) in enumerate(fut)]
    poly = up + dn[::-1]
    b += f'<polygon points="{" ".join(f"{x:.1f},{yy:.1f}" for x, yy in poly)}" fill="{c["accent"]}" fill-opacity="0.16"/>'
    b += f'<line x1="{today_x:.1f}" y1="{Y0-8}" x2="{today_x:.1f}" y2="{Y1+6}" stroke="{c["rule"]}" stroke-width="1" stroke-dasharray="3 3"/>'
    b += f'<polyline points="{" ".join(f"{x:.1f},{yy:.1f}" for x, yy in past)}" fill="none" stroke="{c["ink"]}" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/>'
    fl = [past[-1]] + fut[1:]
    b += f'<polyline points="{" ".join(f"{x:.1f},{yy:.1f}" for x, yy in fl)}" fill="none" stroke="{c["accent"]}" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>'
    b += f'<circle cx="{today_x:.1f}" cy="{past[-1][1]:.1f}" r="3.6" fill="{c["ink"]}"/>'
    b += T(X0 + 14, Y1 - 10, "Actual", 12.5, "b")
    b += T(X1, Y1 - 10, "Forecast with 80% interval", 12.5, "b acc", "end")
    b += T(X0, Y1 + 24, "30 days ago", 12, "mute")
    b += T(today_x, Y1 + 24, "Today", 12, "mute", "middle")
    b += T(X1, Y1 + 24, "10 days ahead", 12, "mute", "end")
    return b, Y1 + 30 - y


BLOCKS = {"dots": blk_dots, "stats": blk_stats, "note": blk_note, "progress": blk_progress, "forecast": blk_forecast}


def feature(theme, p, name):
    c = PAL(theme, p["colour"])
    # right column
    b_right, y = "", 20
    for i, d in enumerate(p["blocks"]):
        if i:
            if d["kind"] in ("stats", "note") and p["blocks"][i - 1]["kind"] in ("dots",):
                r, _ = blk_rule(c, y + 4)
                b_right += r
                y += 26
            else:
                y += 24
        part, h = BLOCKS[d["kind"]](c, d, y)
        b_right += part
        y += h
    right_h = y
    # left column
    b = T(0, 50, p["title"], 34, "serif b", extra='letter-spacing="-0.6"')
    pw = tw(p["status"], 13.5, True) + 26
    b += f'<rect x="0" y="66" width="{pw:.0f}" height="26" rx="13" fill="{c["accent"]}"/>'
    b += T(13, 84, p["status"], 13.5, "b", extra=f'style="fill:{c["bg"]}"')
    b += T(0, 116, f"Updated {p['updated']}", 12.5, "mute")
    t, n = para_px(0, 152, p["desc"], 350, 15, 23, "body")
    b += t
    built = wrap_px(p["built"], 350, 13)
    left_h = 152 + n * 23 + 20 + len(built) * 19
    H = max(right_h, left_h) + 4
    y0 = H - 24 - (len(built) - 1) * 19
    b += "".join(T(0, y0 + i * 19, ln, 13, "mute") for i, ln in enumerate(built))
    alt = f"{p['title']} ({p['status']}): {p['desc']}"
    svg(name, theme, W_IN, H, b + b_right, ["lora600", "inter400", "inter600"], alt, c, PAD)
    return alt


# ================================================================ cards, skills, recognition
def card(theme, p, name):
    c = PAL(theme, p["colour"])
    W, H = 272, 270
    b = f'<rect x="0" y="0" width="44" height="6" rx="3" fill="{c["accent"]}"/>'
    b += T(W, 7, f"Updated {p['updated']}", 11.5, "mute", "end")
    b += T(0, 56, p["title"], 25, "serif b", extra='letter-spacing="-0.4"')
    t, _ = para_px(0, 92, p["desc"], W, 15.5, 23, "body")
    b += t
    chips = [(s.strip(), tw(s.strip(), 12.5) + 22) for s in p["stack"].split(",")]
    rows, cur, cw = [], [], 0
    for t_, w in chips:
        if cw + w > W and cur:
            rows.append(cur)
            cur, cw = [], 0
        cur.append((t_, w))
        cw += w + 6
    rows.append(cur)
    y0 = H - 4 - len(rows) * 31
    for r, row in enumerate(rows):
        x = 0
        for t_, w in row:
            yy = y0 + r * 31
            b += f'<rect x="{x:.0f}" y="{yy}" width="{w:.0f}" height="25" rx="12.5" fill="{c["faint"]}"/>'
            b += T(x + 11, yy + 17, t_, 12.5, "")
            x += w + 6
    alt = f"{p['title']}. {p['desc']} Built with {p['stack']}."
    svg(name, theme, W, H, b, ["lora600", "inter400"], alt, c, 22, 18)
    return alt


def skills(theme, items):
    c = PAL(theme, "slate")
    W, y, b = W_IN, 6, ""
    for gi, (label, its) in enumerate(items):
        if gi:
            b += f'<rect x="0" y="{y-14}" width="{W}" height="1" fill="{c["rule"]}"/>'
        b += T(0, y + 22, label, 20, "serif b", extra='letter-spacing="-0.2"')
        x, row = 220, 0
        for t in its:
            w = tw(t, 13.5) + 26
            if x + w > W:
                x, row = 220, row + 1
            yy = y + row * 38
            b += f'<rect x="{x:.0f}" y="{yy}" width="{w:.0f}" height="30" rx="15" fill="{c["faint"]}"/>'
            b += T(x + 12, yy + 20, t, 13.5, "")
            x += w + 8
        y += (row + 1) * 38 + 22
    alt = "Skills. " + " ".join(f"{a}: {', '.join(i)}." for a, i in items)
    svg("skills", theme, W, y - 10, b, ["lora600", "inter400"], alt, c, PAD)
    return alt


def recognition(theme, items):
    W, H, g = W_IN + 2 * PAD, 190, 18
    cw = (W - 2 * g) / 3
    b = ""
    for i, (key, big, org, sub) in enumerate(items):
        c = PAL(theme, key)
        x = i * (cw + g)
        b += f'<rect x="{x:.1f}" y="0" width="{cw:.1f}" height="{H}" rx="20" fill="{c["bg"]}"/>'
        b += f'<rect x="{x+28:.1f}" y="28" width="44" height="6" rx="3" fill="{c["accent"]}"/>'
        b += T(x + 28, 98, big, 46, "serif b", extra=f'letter-spacing="-1" style="fill:{c["accent"]}"')
        b += T(x + 28, 138, org, 16, "b", extra=f'style="fill:{c["ink"]}"')
        b += T(x + 28, 160, sub, 13.5, "", extra=f'style="fill:{c["body"]}"')
    alt = "Recognition. " + " ".join(f"{o}: {bg}, {s}." for _, bg, o, s in items)
    svg("recognition", theme, W, H, b, ["lora600", "inter400", "inter600"], alt, THEMES[theme])
    return alt


# ================================================================ README
def pic(name, alt, width="100%", href=None):
    a = esc(alt, {'"': "&quot;"})
    tag = (f'<picture><source media="(prefers-color-scheme: dark)" srcset="assets/{name}-dark.svg">'
           f'<img src="assets/{name}-light.svg" alt="{a}" width="{width}"></picture>')
    return f'<a href="{href}">{tag}</a>' if href else tag


def links_line(links):
    return " &nbsp;·&nbsp; ".join(f"[{t}]({u})" for t, u in links)


WORDS = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="use .cache/ without fetching")
    args = ap.parse_args()
    cfg = yaml.safe_load(open(os.path.join(ROOT, "showcase.yml"), encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)
    for f in glob.glob(os.path.join(OUT, "*.svg")):
        os.remove(f)

    projects = [load_project(e, cfg["owner"], args.offline) for e in cfg["projects"]]
    leads = [p for p in projects if p["layout"] == "lead"]
    feats = [p for p in projects if p["layout"] == "feature"]
    cards = [p for p in projects if p["layout"] == "card"]
    strands = [LEAD["accent"]] * len(leads) + [STRAND[p["colour"]] for p in feats]

    alts = {}
    sec = cfg["sections"]
    n_sel = len(leads) + len(feats)
    for th in THEMES:
        alts["header"] = header(th, cfg, strands)
        heading("h-selected", th, sec["selected"][0], f"{WORDS[n_sel]} {sec['selected'][1][0].lower()}{sec['selected'][1][1:]}" if n_sel in WORDS else sec["selected"][1])
        heading("h-also", th, *sec["also"])
        heading("h-skills", th, *sec["skills"])
        heading("h-recog", th, *sec["recognition"])
        for p in leads:
            alts[p["repo"]] = lead(th, p, "p-" + p["repo"].lower())
        for p in feats:
            alts[p["repo"]] = feature(th, p, "p-" + p["repo"].lower())
        for p in cards:
            alts[p["repo"]] = card(th, p, "c-" + p["repo"].lower())
        alts["skills"] = skills(th, cfg["skills"])
        alts["recognition"] = recognition(th, cfg["recognition"])

    md = ["<!-- Generated by tools/build.py from showcase.yml. Edit showcase.yml, not this file. -->", "",
          pic("header", alts["header"]), "", links_line(cfg["links"]), "",
          pic("h-selected", sec["selected"][0]), ""]
    for p in leads + feats:
        md += [pic("p-" + p["repo"].lower(), alts[p["repo"]], href=p["url"]), ""]
        if p.get("links"):
            md += [links_line(p["links"]), ""]
    md += [pic("h-also", sec["also"][0]), ""]
    md += ["\n".join(pic("c-" + p["repo"].lower(), alts[p["repo"]], "32%", p["url"]) for p in cards), ""]
    md += [pic("h-skills", sec["skills"][0]), "", pic("skills", alts["skills"]), "",
           pic("h-recog", sec["recognition"][0]), "", pic("recognition", alts["recognition"]), ""]
    with open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(f"built {len(os.listdir(OUT))} assets for {len(projects)} projects; {len(WARNINGS)} warning(s)")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("### Profile build\n\n")
            f.write("\n".join(f"- ⚠️ {w}" for w in WARNINGS) or "All live values found.")
            f.write("\n")


if __name__ == "__main__":
    main()
