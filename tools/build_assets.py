#!/usr/bin/env python3
"""Builds the profile's figures as self-contained SVGs (light + dark).

Fonts are subset and embedded so the type renders the same everywhere:
  Lora (display), Inter (text), Latin Modern Mono (code only).
Run:  python3 tools/build_assets.py   (writes to ./assets)
"""
import base64, io, math, os, textwrap
from xml.sax.saxutils import escape as esc
from fontTools import subset, ttLib
from fontTools.varLib import instancer

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
os.makedirs(OUT, exist_ok=True)

GLYPHS = "".join(chr(c) for c in range(32, 127)) + "−–—’“”…×"


# ---------------------------------------------------------------- fonts
def _woff_b64(font: ttLib.TTFont) -> str:
    opts = subset.Options()
    opts.flavor = "woff"
    opts.layout_features = ["kern", "liga", "tnum"]
    opts.name_IDs = []
    opts.notdef_outline = True
    sub = subset.Subsetter(opts)
    sub.populate(text=GLYPHS)
    sub.subset(font)
    buf = io.BytesIO()
    font.flavor = "woff"
    font.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


def lora(weight):
    f = ttLib.TTFont("/usr/share/fonts/truetype/google-fonts/Lora-Variable.ttf")
    f = instancer.instantiateVariableFont(f, {"wght": weight})
    return _woff_b64(f)


def static(path):
    return _woff_b64(ttLib.TTFont(path))


LM = "/usr/share/texmf/fonts/opentype/public/lm/lmmono10-regular.otf"
INTER = "/usr/share/fonts/opentype/inter/"
FONT_CSS = {
    "lora600": lora(600),
    "lora400": lora(400),
    "inter400": static(INTER + "Inter-Regular.otf"),
    "inter600": static(INTER + "Inter-SemiBold.otf"),
    "lm": static(LM),
}


def font_face(used):
    spec = {
        "lora600": ("PLora", 600), "lora400": ("PLora", 400),
        "inter400": ("PInter", 400), "inter600": ("PInter", 600), "lm": ("PMono", 400),
    }
    out = ""
    for k in used:
        fam, w = spec[k]
        out += (f"@font-face{{font-family:'{fam}';font-weight:{w};"
                f"src:url(data:font/woff;base64,{FONT_CSS[k]}) format('woff')}}\n")
    return out


# ---------------------------------------------------------------- themes
THEMES = {
    "light": dict(ink="#1f2328", body="#454d57", mute="#656d76", rule="#d0d7de",
                  faint="#eaeef2", accent="#0b7285", warn="#b4281c", band="#0b7285"),
    "dark": dict(ink="#e6edf3", body="#b6bec7", mute="#8b949e", rule="#30363d",
                 faint="#21262d", accent="#3bc9db", warn="#ff8a80", band="#3bc9db"),
}
SERIF = "'PLora',Lora,Georgia,'Times New Roman',serif"
SANS = "'PInter',Inter,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "'PMono','Latin Modern Mono',ui-monospace,Menlo,Consolas,monospace"


def svg(name, theme, w, h, body, used, title):
    c = THEMES[theme]
    doc = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title)}">
<style>
{font_face(used)}
text{{font-family:{SANS};fill:{c["ink"]}}}
.serif{{font-family:{SERIF}}}
.mono{{font-family:{MONO}}}
.b{{font-weight:600}}
.body{{fill:{c["body"]}}}
.mute{{fill:{c["mute"]}}}
.acc{{fill:{c["accent"]}}}
</style>
{body}
</svg>'''
    with open(os.path.join(OUT, f"{name}-{theme}.svg"), "w", encoding="utf-8") as f:
        f.write(doc)


def T(x, y, s, size=15, cls="", anchor="start", extra=""):
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    return f'<text x="{x}" y="{y}" font-size="{size}" class="{cls}"{a} {extra}>{esc(s)}</text>'


def para(x, y, s, width, size=15, lh=23, cls="body"):
    return "".join(T(x, y + i * lh, ln, size, cls) for i, ln in enumerate(textwrap.wrap(s, width)))


def plate_frame(c, w, title, status, desc, built, h, wrap=40, tsize=34):
    b = f'<rect x="0" y="0" width="{w}" height="2" fill="{c["ink"]}"/>'
    b += T(0, 64, title, tsize, "serif b", extra='letter-spacing="-0.6"')
    b += T(0, 92, status, 14, "b acc")
    b += para(0, 128, desc, wrap, 15, 23, "body")
    lines = textwrap.wrap(built, 46)
    y0 = h - 24 - (len(lines) - 1) * 19
    b += "".join(T(0, y0 + i * 19, ln, 13, "mute") for i, ln in enumerate(lines))
    return b


# ---------------------------------------------------------------- header
def header(theme):
    c = THEMES[theme]
    W, H = 880, 188
    b = T(0, 66, "Hil Kalathiya", 62, "serif b", extra='letter-spacing="-1.6"')
    b += T(0, 112, "Machine learning for healthcare and data systems.", 26, "serif body", extra='style="font-weight:400"')
    b += para(0, 148, "B.Tech in Information and Communication Technology at PDEU, graduating in 2027. "
              "I work on forecasting, reinforcement learning and agentic systems.", 76, 15, 23, "mute")
    svg("header", theme, W, H, b, ["lora600", "lora400", "inter400"], "Hil Kalathiya. Machine learning for healthcare and data systems.")


# ---------------------------------------------------------------- HospitalOps
def hospital(theme):
    c = THEMES[theme]
    W, H = 880, 352
    b = plate_frame(c, W, "HospitalOps AI", "In progress",
                    "Decision support for hospital operations. Live bed and ward capacity, admission and ICU "
                    "demand forecasts and, next, what-if simulation and resource optimization. It supports "
                    "operations staff and makes no clinical decisions.",
                    "Built with FastAPI, React, TypeScript, MongoDB, Redis and Docker.", H, 40)
    X0, X1 = 446, 880
    Y0, Y1 = 66, 206
    b += T(410, 34, "ICU beds in use", 14, "b")
    b += T(X1, 34, "Illustrative data, not real patients", 12.5, "mute", "end")
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
    # interval band
    up = [(x, y - (2 + j * 1.15) * (Y1 - Y0) / (vmax - vmin)) for j, (x, y) in enumerate(fut)]
    dn = [(x, y + (2 + j * 1.15) * (Y1 - Y0) / (vmax - vmin)) for j, (x, y) in enumerate(fut)]
    poly = up + dn[::-1]
    b += f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in poly)}" fill="{c["band"]}" fill-opacity="0.16"/>'
    b += f'<line x1="{today_x:.1f}" y1="{Y0-8}" x2="{today_x:.1f}" y2="{Y1+6}" stroke="{c["rule"]}" stroke-width="1" stroke-dasharray="3 3"/>'
    b += f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in past)}" fill="none" stroke="{c["ink"]}" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/>'
    fl = [past[-1]] + fut[1:]
    b += f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in fl)}" fill="none" stroke="{c["accent"]}" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>'
    b += f'<circle cx="{today_x:.1f}" cy="{past[-1][1]:.1f}" r="3.6" fill="{c["ink"]}"/>'
    b += T(X0 + 14, Y1 - 10, "Actual", 12.5, "b")
    b += T(X1, Y1 - 10, "Forecast with 80% interval", 12.5, "b acc", "end")
    b += T(X0, Y1 + 24, "30 days ago", 12, "mute")
    b += T(today_x, Y1 + 24, "Today", 12, "mute", "middle")
    b += T(X1, Y1 + 24, "10 days ahead", 12, "mute", "end")
    # build progress
    ty = 262
    b += T(410, ty - 8, "Build progress", 14, "b")
    b += T(X1, ty - 8, "9 of 13 steps shipped", 12.5, "mute", "end")
    sw, gap = 28, 5.4
    for i in range(13):
        x = 410 + i * (sw + gap)
        if i < 9:
            b += f'<rect x="{x:.1f}" y="{ty}" width="{sw}" height="10" rx="2" fill="{c["accent"]}"/>'
        else:
            b += f'<rect x="{x+0.75:.1f}" y="{ty+0.75}" width="{sw-1.5}" height="8.5" rx="2" fill="none" stroke="{c["rule"]}" stroke-width="1.5"/>'
    b += para(410, ty + 36, "Shipped: access control, patients and beds, data ingestion, dashboard, "
              "baseline forecasts, ARIMA and Prophet.", 70, 13, 19, "body")
    b += para(410, ty + 36 + 40, "Next: LSTM forecasting, simulation, optimization, agent orchestration.", 70, 13, 19, "mute")
    svg("hospitalops", theme, W, H, b, ["lora600", "inter400", "inter600"], "HospitalOps AI: illustrative ICU bed forecast and build progress, 9 of 13 steps shipped")


# ---------------------------------------------------------------- OpenEnv
def openenv(theme):
    c = THEMES[theme]
    W, H = 880, 322
    b = plate_frame(c, W, "OpenEnv", "Live demo on Hugging Face",
                    "A reinforcement-learning environment where an LLM agent learns to clean tabular data "
                    "from reward instead of fixed rules. A penalty on repeated actions stops it from looping.",
                    "Built with Llama 3, FastAPI, Docker and Hugging Face Spaces, together with Chetan Gadhiya and Sahaj Saliya.", H, 40)
    L, R = 410, 880
    b += T(L, 34, "One episode", 14, "b")
    b += T(R, 34, "Example run from the project README", 12.5, "mute", "end")
    cols = [(L, "Step", "start"), (456, "What the agent sees", "start"), (656, "Action", "start"), (R, "Reward", "end")]
    for x, lab, an in cols:
        b += T(x, 70, lab, 12.5, "mute", an)
    rows = [("1", "12 missing, 3 duplicates", "fill_missing", "+1.0"),
            ("2", "0 missing, 3 duplicates", "remove_duplicates", "+0.8"),
            ("3", "0 missing, 0 duplicates", "terminate", "0.0")]
    y = 78
    b += f'<line x1="{L}" y1="{y}" x2="{R}" y2="{y}" stroke="{c["ink"]}" stroke-width="1"/>'
    for i, (s, o, a, r) in enumerate(rows):
        base = y + 30 + i * 38
        b += T(L, base, s, 14, "b")
        b += T(456, base, o, 14, "body")
        b += T(656, base, a, 13.5, "mono")
        b += T(R, base, r, 15, "b acc" if r != "0.0" else "b mute", "end")
        b += f'<line x1="{L}" y1="{base+13}" x2="{R}" y2="{base+13}" stroke="{c["rule"]}" stroke-width="1"/>'
    b += T(L, 218, "Total reward 1.8 in three steps, with no rows lost.", 15, "b")
    b += para(L, 252, "The environment also penalises an unnecessary operation (−0.3) and a repeated action (−1.0), "
              "which is what stops reward-neutral loops.", 70, 13, 19, "body")
    svg("openenv", theme, W, H, b, ["lora600", "inter400", "inter600", "lm"], "OpenEnv: one example episode, reward 1.8 in three steps")


# ---------------------------------------------------------------- Crohn's
def crohns(theme):
    c = THEMES[theme]
    W, H = 880, 292
    b = plate_frame(c, W, "Crohn's severity prediction", "Research, early stage",
                    "Machine learning to predict early how severe a patient's Crohn's disease will be. "
                    "The work starts with the data: finding a dataset that suits severity prediction "
                    "before choosing models.",
                    "Academic project at PDEU.", H, 40, 30)
    L, R = 410, 880
    b += T(L, 34, "Where the project stands", 14, "b")
    steps = [("Dataset", True), ("Preparation", False), ("Modelling", False), ("Evaluation", False)]
    xs = [L + 8, L + 8 + 152, L + 8 + 304, R - 8]
    y = 92
    b += f'<line x1="{xs[0]}" y1="{y}" x2="{xs[1]}" y2="{y}" stroke="{c["accent"]}" stroke-width="2"/>'
    b += f'<line x1="{xs[1]}" y1="{y}" x2="{xs[-1]}" y2="{y}" stroke="{c["rule"]}" stroke-width="2" stroke-dasharray="4 4"/>'
    for i, ((lab, now), x) in enumerate(zip(steps, xs)):
        if now:
            b += f'<circle cx="{x}" cy="{y}" r="9" fill="{c["accent"]}" fill-opacity="0.18"/><circle cx="{x}" cy="{y}" r="5.5" fill="{c["accent"]}"/>'
        else:
            b += f'<circle cx="{x}" cy="{y}" r="5.5" fill="none" stroke="{c["rule"]}" stroke-width="2"/>'
        an = "start" if i == 0 else ("end" if i == 3 else "middle")
        lx = L if i == 0 else (R if i == 3 else x)
        b += T(lx, y + 34, lab, 14, "b" if now else "mute", an)
    b += T(L, y + 56, "Current step", 12.5, "b acc")
    b += para(L, 188, "The aim is early prediction, so the first job is a dataset with outcomes to learn from. "
              "Model choices come after that.", 70, 13.5, 20, "body")
    svg("crohns", theme, W, H, b, ["lora600", "inter400", "inter600"], "Crohn's severity prediction: project is at the dataset stage")


for th in THEMES:
    header(th); hospital(th); openenv(th); crohns(th)
print(sorted(os.listdir(OUT)), [round(os.path.getsize(os.path.join(OUT, f)) / 1024) for f in sorted(os.listdir(OUT))])
