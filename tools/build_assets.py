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
PALS = {
 "rose":   {"light": dict(bg="#fbeff1", accent="#b8234f", faint="#f2d9de", rule="#e3bcc5"), "dark": dict(bg="#271a1f", accent="#ff8fa8", faint="#3a2830", rule="#55383f")},
 "teal":   {"light": dict(bg="#e6f3f5", accent="#0b7285", faint="#cbe4e8", rule="#a9cfd6"), "dark": dict(bg="#11252a", accent="#3bc9db", faint="#1d3a41", rule="#2c5560")},
 "indigo": {"light": dict(bg="#ecedfc", accent="#4547c9", faint="#d5d7f6", rule="#b7baee"), "dark": dict(bg="#1a1b36", accent="#a5a9ff", faint="#2a2c52", rule="#40437a")},
 "amber":  {"light": dict(bg="#fdf1dc", accent="#a65a00", faint="#f3dfb9", rule="#e3c88f"), "dark": dict(bg="#2a2112", accent="#ffc266", faint="#3d3119", rule="#5a4824")},
 "green":  {"light": dict(bg="#e7f5ea", accent="#247a37", faint="#cde8d3", rule="#a8d3b1"), "dark": dict(bg="#14261a", accent="#6fd58a", faint="#1f3b27", rule="#2e5a3b")},
 "slate":  {"light": dict(bg="#eceff3", accent="#3d4b5c", faint="#d9dfe6", rule="#bcc5cf"), "dark": dict(bg="#1c2128", accent="#a9b7c8", faint="#2b323b", rule="#404a56")},
}
PAD = 28
from PIL import ImageFont
_F = {}


def tw(t, size, bold=False):
    k = (size, bold)
    if k not in _F:
        _F[k] = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-%s.otf" % ("SemiBold" if bold else "Regular"), 100)
    return _F[k].getlength(t) * size / 100


def PAL(theme, key):
    c = dict(THEMES[theme]); c.update(PALS[key][theme]); c["band"] = c["accent"]
    return c


SERIF = "'PLora',Lora,Georgia,'Times New Roman',serif"
SANS = "'PInter',Inter,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "'PMono','Latin Modern Mono',ui-monospace,Menlo,Consolas,monospace"


def svg(name, theme, w, h, body, used, title, pal=None, pad=0, rx=20):
    c = pal or THEMES[theme]
    if pad:
        body = (f'<rect width="{w+2*pad}" height="{h+2*pad}" rx="{rx}" fill="{c["bg"]}"/>'
                f'<g transform="translate({pad},{pad})">{body}</g>')
        w, h = w + 2 * pad, h + 2 * pad
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
    b = T(0, 50, title, tsize, "serif b", extra='letter-spacing="-0.6"')
    pw = tw(status, 13.5, True) + 26
    b += f'<rect x="0" y="66" width="{pw:.0f}" height="26" rx="13" fill="{c["accent"]}"/>'
    b += T(13, 84, status, 13.5, "b", extra=f'style="fill:{c["bg"]}"')
    b += para(0, 128, desc, wrap, 15, 23, "body")
    lines = textwrap.wrap(built, 46)
    y0 = h - 24 - (len(lines) - 1) * 19
    b += "".join(T(0, y0 + i * 19, ln, 13, "mute") for i, ln in enumerate(lines))
    return b


# ---------------------------------------------------------------- header
def header(theme):
    W, H = 880 + 2 * PAD, 396
    bg = "#14202b" if theme == "light" else "#161b22"
    cols = ["#ff8fa8", "#3bc9db", "#a5a9ff"]
    X = 48
    b = f'<rect width="{W}" height="{H}" rx="22" fill="{bg}"/>'
    # three strands in the project colours
    for k, col in enumerate(cols):
        pts = []
        for i in range(0, 61):
            t = i / 60
            x = 540 + t * 360
            y = 150 + 46 * math.sin(t * 5.2 + k * 1.15) * (0.55 + 0.45 * t) + (k - 1) * 34 - t * 18
            pts.append((x, y))
        b += f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="none" stroke="{col}" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" opacity="0.95"/>'
        b += f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="6" fill="{col}"/>'
    b += T(X, 130, "Hil Kalathiya", 76, "serif b", extra=f'letter-spacing="-2" style="fill:#ffffff"')
    for i, ln in enumerate(["Machine learning for healthcare", "and data systems."]):
        b += T(X, 188 + i * 36, ln, 29, "serif", extra='style="font-weight:400;fill:#d6dde5"')
    b += para(X, 276, "B.Tech in ICT at PDEU, graduating in 2027. I work on forecasting, "
              "reinforcement learning and agentic systems.", 56, 15, 23, "mute")
    b = b.replace('class="body mute"', 'class="mute"')
    pill = "Looking for machine learning internships, 2026–27"
    pw = tw(pill, 14.5, True) + 40
    b += f'<rect x="{X}" y="{H-62}" width="{pw:.0f}" height="34" rx="17" fill="#3bc9db"/>'
    b += T(X + 20, H - 40, pill, 14.5, "b", extra='style="fill:#0b1b22"')
    svg("header", theme, W, H, b, ["lora600", "lora400", "inter400", "inter600"],
        "Hil Kalathiya. Machine learning for healthcare and data systems. Looking for machine learning internships, 2026 to 2027.",
        {**THEMES[theme], "mute": "#9aa7b4", "body": "#9aa7b4"})


# ---------------------------------------------------------------- HospitalOps
# build steps from the HospitalOps-AI README status table
STEPS, DONE = 19, 17


def hospital(theme):
    c = PAL(theme, "teal")
    W, H = 880, 372
    b = plate_frame(c, W, "HospitalOps AI", "In progress",
                    "Decision support for hospital operations: live bed and ward capacity, admission and ICU "
                    "demand forecasts, what-if simulation, and a MILP optimizer that plans surge beds and "
                    "equipment. It advises operations staff and makes no clinical decisions.",
                    "Built with FastAPI, React, TypeScript, MongoDB, Redis, MLflow and Docker.", H, 40)
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
    b += T(X1, ty - 8, f"{DONE} of {STEPS} steps shipped", 12.5, "mute", "end")
    gap = 4.4
    sw = (X1 - 410 - (STEPS - 1) * gap) / STEPS
    for i in range(STEPS):
        x = 410 + i * (sw + gap)
        if i < DONE:
            b += f'<rect x="{x:.1f}" y="{ty}" width="{sw:.1f}" height="10" rx="2" fill="{c["accent"]}"/>'
        else:
            b += f'<rect x="{x+0.75:.1f}" y="{ty+0.75}" width="{sw-1.5:.1f}" height="8.5" rx="2" fill="none" stroke="{c["rule"]}" stroke-width="1.5"/>'
    shipped = ("Shipped: access control, beds and admissions, data ingestion, ARIMA, Prophet and LSTM "
               "forecasts, MLflow tracking, what-if simulation and the MILP optimizer.")
    b += para(410, ty + 36, shipped, 70, 13, 19, "body")
    b += para(410, ty + 42 + 19 * len(textwrap.wrap(shipped, 70)), "Next: a review screen for optimizer plans, then agent orchestration with RAG.", 70, 13, 19, "mute")
    svg("hospitalops", theme, W, H, b, ["lora600", "inter400", "inter600"], f"HospitalOps AI: illustrative ICU bed forecast and build progress, {DONE} of {STEPS} steps shipped", c, PAD)


# ---------------------------------------------------------------- OpenEnv
def openenv(theme):
    c = PAL(theme, "indigo")
    W, H = 880, 340
    b = plate_frame(c, W, "OpenEnv", "Live demo on Hugging Face",
                    "An environment where an agent cleans a dirty table one action at a time and is graded "
                    "against a hidden clean copy. A PPO agent trained in it matches a hand-written expert, "
                    "and a zero-shot LLM trails on the hardest task.",
                    "Built with OpenEnv, FastAPI, pandas, Stable-Baselines3 and Hugging Face Spaces, together with Chetan Gadhiya and Sahaj Saliya.", H, 40)
    L, R = 410, 880
    b += T(L, 34, "Final grader score, hardest task", 14, "b")
    b += T(R, 34, "Mean ± std over held-out seeds", 12.5, "mute", "end")
    PX0, PX1 = 640, 826
    gy0, gy1 = 56, 222

    def pxv(v):
        return PX0 + (v - 0.5) / 0.5 * (PX1 - PX0)

    for v, lab in ((0.5, "0.5"), (0.75, "0.75"), (1.0, "1.0")):
        b += f'<line x1="{pxv(v):.1f}" y1="{gy0}" x2="{pxv(v):.1f}" y2="{gy1}" stroke="{c["faint"] if v != 0.5 else c["rule"]}" stroke-width="1"/>'
        b += T(pxv(v), gy1 + 20, lab, 11.5, "mute", "middle")
    b += T(L, gy1 + 20, "1.0 is a perfect restore", 12, "mute")
    # hard-clean column of the README benchmark table (LLM: 5 seeds, others: 10)
    rows = [("PPO agent, trained", 0.967, 0.004, True),
            ("Rule-based expert", 0.968, 0.003, False),
            ("Llama 3.1 8B, zero-shot", 0.838, 0.037, False),
            ("Do nothing", 0.608, 0.0, False),
            ("Random actions", 0.534, 0.058, False)]
    for i, (lab, v, sd, ours) in enumerate(rows):
        y = 80 + i * 32
        b += T(L, y + 4.5, lab, 13.5, "b" if ours else "body")
        col = c["accent"] if ours else c["ink"]
        if sd:
            x0, x1 = pxv(v - sd), pxv(v + sd)
            b += f'<line x1="{x0:.1f}" y1="{y}" x2="{x1:.1f}" y2="{y}" stroke="{col}" stroke-width="2"/>'
        if ours:
            b += f'<circle cx="{pxv(v):.1f}" cy="{y}" r="5.5" fill="{col}"/>'
        else:
            b += f'<circle cx="{pxv(v):.1f}" cy="{y}" r="5" fill="{c["bg"]}" stroke="{col}" stroke-width="2"/>'
        b += T(R, y + 4.5, f"{v:.3f}", 14, "b", "end")
    b += f'<line x1="{L}" y1="266" x2="{R}" y2="266" stroke="{c["rule"]}" stroke-width="1"/>'
    b += para(L, 292, "The trained policy never issues an invalid action. Reward and final score are kept separate, "
              "so going in circles earns nothing.", 70, 13, 19, "body")
    svg("openenv", theme, W, H, b, ["lora600", "inter400", "inter600"],
        "OpenEnv: on the hardest data-cleaning task a trained PPO agent scores 0.967, level with a rule-based expert at 0.968, "
        "ahead of a zero-shot Llama 3.1 8B at 0.838", c, PAD)


# ---------------------------------------------------------------- CrohnSight
def crohnsight(theme):
    c = PAL(theme, "rose")
    W, H = 880, 452
    b = plate_frame(c, W, "CrohnSight", "Complete",
                    "Reads small-bowel capsule-endoscopy frames and videos. It finds Crohn's lesions, grades their "
                    "severity and shows where on the frame the model is looking. It runs as an offline web app on a "
                    "CPU. A research prototype, not a medical device.",
                    "Built with PyTorch, ONNX, FastAPI and Next.js, together with Sahaj Saliya. Guided by Prof. Dr. Babalu Kumar Singh at PDEU.",
                    H, 40)
    L, R = 410, 880
    b += T(L, 34, "Lesion detection, AUROC", 14, "b")
    b += T(R, 34, "Interval shown where reported", 12.5, "mute", "end")
    PX0, PX1 = 646, 826
    gy0, gy1 = 62, 226

    def pxv(v):
        return PX0 + (v - 0.5) / 0.5 * (PX1 - PX0)

    for v, lab in ((0.5, "0.5"), (0.75, "0.75"), (1.0, "1.0")):
        b += f'<line x1="{pxv(v):.1f}" y1="{gy0}" x2="{pxv(v):.1f}" y2="{gy1}" stroke="{c["faint"] if v != 0.5 else c["rule"]}" stroke-width="1"/>'
        b += T(pxv(v), gy1 + 20, lab, 11.5, "mute", "middle")
    b += T(L, gy1 + 20, "Chance is 0.5, perfect is 1.0", 12, "mute")
    rows = [("CrohnIPI, cross-validated", 0.992, (0.989, 0.995), True),
            ("Kvasir-Capsule, external", 0.944, (0.86, 0.98), False),
            ("SEE-AI erosion, external", 0.897, None, False),
            ("SEE-AI stenosis, external", 0.916, None, False),
            ("SEE-AI erythema, external", 0.897, None, False)]
    for i, (lab, v, ci, internal) in enumerate(rows):
        y = 88 + i * 32
        b += T(L, y + 4.5, lab, 13.5, "b" if internal else "body")
        col = c["accent"] if internal else c["ink"]
        if ci:
            x0, x1 = pxv(ci[0]), pxv(ci[1])
            b += f'<line x1="{x0:.1f}" y1="{y}" x2="{x1:.1f}" y2="{y}" stroke="{col}" stroke-width="2"/>'
            b += f'<line x1="{x0:.1f}" y1="{y-4}" x2="{x0:.1f}" y2="{y+4}" stroke="{col}" stroke-width="2"/><line x1="{x1:.1f}" y1="{y-4}" x2="{x1:.1f}" y2="{y+4}" stroke="{col}" stroke-width="2"/>'
        if internal:
            b += f'<circle cx="{pxv(v):.1f}" cy="{y}" r="5.5" fill="{col}"/>'
        else:
            b += f'<circle cx="{pxv(v):.1f}" cy="{y}" r="5" fill="none" stroke="{col}" stroke-width="2"/>'
        b += T(R, y + 4.5, f"{v:.3f}", 14, "b", "end")
    b += f'<line x1="{L}" y1="272" x2="{R}" y2="272" stroke="{c["rule"]}" stroke-width="1"/>'
    stats = [("96.7%", "Lesion versus normal accuracy. Best published: 94.6%."),
             ("0.94", "Severity grading across four tiers, quadratic weighted kappa."),
             ("10", "EfficientNet-B2 models in the ensemble, running on a CPU.")]
    for i, (big, lab) in enumerate(stats):
        x = L + i * 152
        b += T(x, 318, big, 34, "serif b acc", extra='letter-spacing="-0.8"')
        b += para(x, 342, lab, 22, 12.5, 17, "body")
    b += T(L, 408, "Known limits", 13, "b")
    b += para(L, 428, "Whole-video lesion detection is near chance (AUROC 0.57), and the flare-risk model only matches its baseline.", 66, 13, 19, "body")
    svg("crohnsight", theme, W, H, b, ["lora600", "inter400", "inter600"],
        "CrohnSight: Crohn's lesion detection from capsule endoscopy, AUROC 0.992 internal and 0.944 on an external dataset", c, PAD)


# ---------------------------------------------------------------- section heading
def heading(name, theme, title, note):
    c = THEMES[theme]
    W, H = 880 + 2 * PAD, 76
    b = f'<rect x="0" y="12" width="40" height="5" rx="2.5" fill="{c["ink"]}"/>'
    b += T(0, 58, title, 34, "serif b", extra='letter-spacing="-0.8"')
    b += T(W, 58, note, 14, "mute", "end")
    svg(name, theme, W, H, b, ["lora600", "inter400"], title)


# ---------------------------------------------------------------- compact project card
def card(name, theme, key, title, desc, stack):
    c = PAL(theme, key)
    W, H = 272, 262
    b = f'<rect x="0" y="0" width="44" height="6" rx="3" fill="{c["accent"]}"/>'
    b += T(0, 56, title, 25, "serif b", extra='letter-spacing="-0.4"')
    b += para(0, 92, desc, 29, 15.5, 23, "body")
    x, y = 0, H - 40
    chips = []
    for t in [t.strip() for t in stack.split(",")]:
        chips.append((t, tw(t, 12.5) + 22))
    rows, cur, cw = [], [], 0
    for t, w in chips:
        if cw + w > W and cur:
            rows.append(cur); cur, cw = [], 0
        cur.append((t, w)); cw += w + 6
    rows.append(cur)
    y0 = H - 4 - len(rows) * 31
    for r, row in enumerate(rows):
        x = 0
        for t, w in row:
            yy = y0 + r * 31
            b += f'<rect x="{x:.0f}" y="{yy}" width="{w:.0f}" height="25" rx="12.5" fill="{c["faint"]}"/>'
            b += T(x + 11, yy + 17, t, 12.5, "", extra=f'style="fill:{c["ink"]}"')
            x += w + 6
    svg(name, theme, W, H, b, ["lora600", "inter400"], f"{title}. {desc} Built with {stack}.", c, 22, 18)


# ---------------------------------------------------------------- skills as chips
def skills(theme):
    c = PAL(theme, "slate")
    W = 880
    y = 6
    b = ""
    for gi, (label, items) in enumerate(SKILLS):
        if gi:
            b += f'<rect x="0" y="{y-14}" width="{W}" height="1" fill="{c["rule"]}"/>'
        b += T(0, y + 22, label, 20, "serif b", extra='letter-spacing="-0.2"')
        x, row = 220, 0
        for t in items:
            w = tw(t, 13.5) + 26
            if x + w > W:
                x, row = 220, row + 1
            yy = y + row * 38
            b += f'<rect x="{x:.0f}" y="{yy}" width="{w:.0f}" height="30" rx="15" fill="{c["faint"]}"/>'
            b += T(x + 12, yy + 20, t, 13.5, "", extra=f'style="fill:{c["ink"]}"')
            x += w + 8
        y += (row + 1) * 38 + 22
    H = y - 10
    svg("skills", theme, W, H, b, ["lora600", "inter400"],
        "Skills. " + " ".join(f"{a}: {', '.join(i)}." for a, i in SKILLS), c, PAD)


# ---------------------------------------------------------------- recognition tiles
def recognition(theme):
    W, H = 880 + 2 * PAD, 190
    g = 18
    tw = (880 + 2 * PAD - 2 * g) / 3
    b = ""
    for i, (key, big, org, sub) in enumerate(RECOG):
        c = PAL(theme, key)
        x = i * (tw + g)
        b += f'<rect x="{x:.1f}" y="0" width="{tw:.1f}" height="{H}" rx="20" fill="{c["bg"]}"/>'
        b += f'<rect x="{x+28:.1f}" y="28" width="44" height="6" rx="3" fill="{c["accent"]}"/>'
        b += T(x + 28, 98, big, 46, "serif b acc", extra=f'letter-spacing="-1" style="fill:{c["accent"]}"')
        b += T(x + 28, 138, org, 16, "b", extra=f'style="fill:{c["ink"]}"')
        b += T(x + 28, 160, sub, 13.5, "", extra=f'style="fill:{c["body"]}"')
    svg("recognition", theme, int(W), H, b, ["lora600", "inter400", "inter600"],
        "Recognition. " + " ".join(f"{o}: {bg}, {s}" for _, bg, o, s in RECOG))


SKILLS = [("Machine learning", ["scikit-learn", "pandas", "NumPy", "PyTorch", "ARIMA", "Prophet", "Reinforcement learning"]),
          ("LLM systems", ["LangGraph", "LangChain", "RAG", "Chroma", "Cohere", "OpenRouter", "Llama 3"]),
          ("Backend", ["Python", "FastAPI", "Node.js", "MongoDB", "MySQL", "SQLite", "Redis", "Docker"]),
          ("Frontend", ["React", "Next.js", "TypeScript", "Tailwind CSS", "Vite"]),
          ("Fundamentals", ["Data structures and algorithms", "Object-oriented design", "C++", "SQL", "Git"])]
RECOG = [("amber", "Top 25", "Smart India Hackathon", "2024, and again in 2025"),
         ("indigo", "Elite", "NPTEL", "Deep Learning certification"),
         ("green", "Certified", "ISRO-IIRS", "Artificial intelligence and ML")]

for th in THEMES:
    header(th); crohnsight(th); hospital(th); openenv(th)
    heading("h-selected", th, "Selected work", "Three projects I'm proudest of")
    heading("h-also", th, "Also built", "Smaller and earlier work")
    heading("h-skills", th, "Skills", "What I build with")
    heading("h-recog", th, "Recognition", "Competitions and certifications")
    card("card-mdt", th, "amber", "MDT AI Copilot", "Anomaly detection, forecasting and a natural-language assistant over 5G measurement data.", "Python, LangGraph, scikit-learn, Chroma, FastAPI")
    card("card-misinfo", th, "green", "Misinformation AI", "A tool for combating misinformation, built with team AI Gyani.", "TypeScript, Python")
    card("card-senso", th, "slate", "Senso Gown", "A patient vitals monitor with a live dashboard and SMS alerts.", "ESP8266, MySQL, Twilio")
    skills(th); recognition(th)
print(len(os.listdir(OUT)))
