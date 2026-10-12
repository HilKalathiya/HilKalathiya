#!/usr/bin/env python3
"""Generates the self-hosted SVG design system for the GitHub profile README.
Pure SVG + SMIL/CSS animation only (GitHub renders these inside <img>; no JS, no web fonts).
"""
import os, sys
from xml.sax.saxutils import escape as esc

OUT = sys.argv[1] if len(sys.argv) > 1 else "assets"
os.makedirs(OUT, exist_ok=True)

# ---------- design tokens ----------
BG, PANEL, PANEL2, LINE = "#0b0f1a", "#111827", "#0f1626", "#1e2a44"
TXT, MUTED, DIM = "#e5e7eb", "#94a3b8", "#64748b"
CY, VI, PK, GR, AM = "#22d3ee", "#a78bfa", "#f472b6", "#34d399", "#fbbf24"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Helvetica Neue',Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"


def write(name, w, h, body, defs="", style=""):
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">
<defs>
<linearGradient id="g1" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{CY}"/><stop offset="1" stop-color="{VI}"/></linearGradient>
<linearGradient id="g2" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{CY}"/><stop offset="0.55" stop-color="{VI}"/><stop offset="1" stop-color="{PK}"/></linearGradient>
<linearGradient id="gline" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{CY}" stop-opacity="0"/><stop offset="0.5" stop-color="{VI}"/><stop offset="1" stop-color="{PK}" stop-opacity="0"/></linearGradient>
<filter id="blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="55"/></filter>
<filter id="glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="#ffffff" stroke-opacity="0.035"/></pattern>
{defs}
</defs>
<style>
text{{font-family:{SANS}}}
.m{{font-family:{MONO}}}
{style}
</style>
{body}
</svg>'''
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(svg)


def t(x, y, s, size=14, fill=TXT, weight=400, mono=False, anchor="start", extra=""):
    cls = ' class="m"' if mono else ""
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}"{cls} {extra}>{esc(s)}</text>'


def pill(x, y, label, fg=CY, size=12, mono=True, pad=12, h=26, bg=None, stroke=None):
    w = int(len(label) * (size * 0.62 if mono else size * 0.58)) + pad * 2
    bg = bg or fg
    st = stroke or fg
    return (f'<g><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h/2}" fill="{bg}" fill-opacity="0.10" stroke="{st}" stroke-opacity="0.45"/>'
            + t(x + w / 2, y + h / 2 + size * 0.36, label, size, fg, 600, mono, "middle") + "</g>"), w


def panel(w, h, r=22, accent=True):
    s = f'<rect width="{w}" height="{h}" rx="{r}" fill="{PANEL}"/>'
    s += f'<rect width="{w}" height="{h}" rx="{r}" fill="url(#grid)"/>'
    s += f'<rect x="0.75" y="0.75" width="{w-1.5}" height="{h-1.5}" rx="{r}" fill="none" stroke="{LINE}" stroke-width="1.5"/>'
    if accent:
        s += f'<rect x="{r}" y="0" width="{w-2*r}" height="2" fill="url(#g2)" opacity="0.9"/>'
    return s


# =====================================================================
# 1. HERO
# =====================================================================
def hero():
    W, H = 1000, 420
    b = f'<rect width="{W}" height="{H}" rx="26" fill="{BG}"/>'
    b += f'<clipPath id="hc"><rect width="{W}" height="{H}" rx="26"/></clipPath><g clip-path="url(#hc)">'
    # aurora
    b += f'''<g filter="url(#blur)" opacity="0.55">
<circle cx="180" cy="90" r="150" fill="{CY}" opacity="0.55"><animateTransform attributeName="transform" type="translate" values="0 0;90 50;20 110;0 0" dur="16s" repeatCount="indefinite"/></circle>
<circle cx="560" cy="360" r="170" fill="{VI}" opacity="0.6"><animateTransform attributeName="transform" type="translate" values="0 0;-120 -40;60 -70;0 0" dur="19s" repeatCount="indefinite"/></circle>
<circle cx="880" cy="110" r="140" fill="{PK}" opacity="0.45"><animateTransform attributeName="transform" type="translate" values="0 0;-70 70;-20 -20;0 0" dur="22s" repeatCount="indefinite"/></circle>
</g>'''
    b += f'<rect width="{W}" height="{H}" fill="url(#grid)"/>'
    b += f'<rect width="{W}" height="{H}" fill="{BG}" opacity="0.35"/>'

    # neural network (right)
    layers = [(650, 4), (745, 6), (840, 6), (930, 3)]
    cy0, span = 215, 250
    pos = []
    for x, n in layers:
        step = span / (n - 1) if n > 1 else 0
        pos.append([(x, cy0 - span / 2 + i * step) for i in range(n)])
    # edges
    ei = 0
    for a, bb in zip(pos, pos[1:]):
        for i, p in enumerate(a):
            for j, q in enumerate(bb):
                active = (i * 3 + j * 5) % 7 == 0
                if active:
                    dur = 1.6 + (ei % 5) * 0.35
                    b += (f'<line x1="{p[0]}" y1="{p[1]:.1f}" x2="{q[0]}" y2="{q[1]:.1f}" stroke="{CY}" stroke-opacity="0.85" stroke-width="1.4" stroke-dasharray="3 9">'
                          f'<animate attributeName="stroke-dashoffset" from="24" to="0" dur="{dur}s" repeatCount="indefinite"/></line>')
                else:
                    b += f'<line x1="{p[0]}" y1="{p[1]:.1f}" x2="{q[0]}" y2="{q[1]:.1f}" stroke="#94a3b8" stroke-opacity="0.13"/>'
                ei += 1
    k = 0
    for li, layer in enumerate(pos):
        for (x, y) in layer:
            col = [CY, VI, PK, GR][li]
            b += (f'<circle cx="{x}" cy="{y:.1f}" r="9" fill="{col}" opacity="0.12"><animate attributeName="r" values="9;15;9" dur="{2.4 + (k%4)*0.4}s" begin="{(k%7)*0.3}s" repeatCount="indefinite"/></circle>'
                  f'<circle cx="{x}" cy="{y:.1f}" r="5.5" fill="{BG}" stroke="{col}" stroke-width="2"/>'
                  f'<circle cx="{x}" cy="{y:.1f}" r="2.2" fill="{col}"/>')
            k += 1
    for (x, lab) in [(650, "INPUT"), (745, "RETRIEVE"), (840, "REASON"), (930, "ACT")]:
        b += t(x, 372, lab, 10, DIM, 600, True, "middle", 'letter-spacing="1.5"')

    # left copy
    b += t(56, 70, "~/hil-kalathiya", 14, CY, 600, True, extra='letter-spacing="0.5"')
    b += f'<circle cx="43" cy="65.5" r="4" fill="{GR}"><animate attributeName="opacity" values="1;0.2;1" dur="1.8s" repeatCount="indefinite"/></circle>'
    b += f'<text x="52" y="168" font-size="92" font-weight="800" fill="url(#g2)" letter-spacing="-3">Hil</text>'
    b += f'<text x="52" y="252" font-size="92" font-weight="800" fill="{TXT}" letter-spacing="-3">Kalathiya</text>'
    phrases = ["Building agentic AI that reasons, retrieves & acts.",
               "Turning messy real-world data into decisions.",
               "RAG  ·  Reinforcement Learning  ·  Forecasting",
               "B.Tech ICT @ PDEU  ·  Class of 2027"]
    for i, ph in enumerate(phrases):
        b += (f'<text x="56" y="298" font-size="18" fill="{TXT}" class="m" opacity="{1 if i == 0 else 0}">{esc(ph)}'
              f'<animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;0.03;0.22;0.25;1" dur="16s" begin="{i*4}s" repeatCount="indefinite"/></text>')
    b += f'<rect x="56" y="312" width="64" height="3" rx="1.5" fill="url(#g2)"/>'
    x = 56
    for lab, col in [("AI / ML Engineer", CY), ("Agentic Systems", VI), ("Applied RAG", PK)]:
        p, w = pill(x, 340, lab, col, 12, False, 14, 28)
        b += p
        x += w + 10
    # open-to-work badge
    b += f'<g><rect x="56" y="378" width="292" height="26" rx="13" fill="{GR}" fill-opacity="0.10" stroke="{GR}" stroke-opacity="0.45"/>'
    b += f'<circle cx="74" cy="391" r="4" fill="{GR}"><animate attributeName="r" values="3.5;5.5;3.5" dur="1.6s" repeatCount="indefinite"/></circle>'
    b += t(88, 396, "Open to ML / AI internships · 2026–27", 11.5, GR, 600, True) + '</g>'
    b += "</g>"
    b += f'<rect x="0.75" y="0.75" width="{W-1.5}" height="{H-1.5}" rx="26" fill="none" stroke="{LINE}" stroke-width="1.5"/>'
    write("hero.svg", W, H, b)


# =====================================================================
# 2. METRIC STRIP
# =====================================================================
def metrics():
    W, H = 1000, 128
    items = [("2×", "Smart India Hackathon", "Top 25 · 2024 & 2025", CY),
             ("8.55", "CGPA", "B.Tech ICT · PDEU", VI),
             ("≥80%", "Anomaly recall", "MDT AI Copilot, injected set", PK),
             ("18", "Public repositories", "AI · ML · Full-stack · IoT", GR)]
    b = panel(W, H, 20, accent=False)
    cw = W / 4
    for i, (big, lab, sub, col) in enumerate(items):
        x = i * cw + 34
        if i:
            b += f'<line x1="{i*cw}" y1="26" x2="{i*cw}" y2="{H-26}" stroke="{LINE}"/>'
        b += (f'<g>'
              f'<text x="{x}" y="66" font-size="40" font-weight="800" fill="{col}" letter-spacing="-1">{esc(big)}</text>'
              + t(x, 90, lab, 13.5, TXT, 600) + t(x, 108, sub, 11, MUTED) + "</g>")
    write("metrics.svg", W, H, b)


# =====================================================================
# 3. SECTION HEADERS
# =====================================================================
def header(name, num, title, sub):
    W, H = 1000, 76
    b = f'<rect width="{W}" height="{H}" rx="16" fill="{PANEL2}"/>'
    b += f'<rect x="0.75" y="0.75" width="{W-1.5}" height="{H-1.5}" rx="16" fill="none" stroke="{LINE}" stroke-width="1.5"/>'
    b += f'<rect x="14" y="20" width="4" height="36" rx="2" fill="url(#g1)"/>'
    b += t(30, 33, f"{num} /", 12, CY, 700, True, extra='letter-spacing="2"')
    b += f'<text x="30" y="60" font-size="26" font-weight="800" fill="{TXT}" letter-spacing="-0.5">{esc(title)}</text>'
    b += t(W - 30, 46, sub, 12.5, MUTED, 400, True, "end")
    b += f'<rect x="{W-170}" y="62" width="140" height="2" rx="1" fill="url(#gline)"/>'
    write(name, W, H, b)


# =====================================================================
# 4. FLAGSHIP CARD
# =====================================================================
def flagship():
    W, H = 1000, 596
    b = panel(W, H, 24)
    # glow corner
    b += f'<circle cx="920" cy="40" r="140" fill="{VI}" opacity="0.10" filter="url(#blur)"/>'
    p, pw = pill(36, 30, "FLAGSHIP PROJECT", AM, 11, True, 12, 24)
    b += p
    p2, pw2 = pill(36 + pw + 8, 30, "5G / 6G RESEARCH × AI", CY, 11, True, 12, 24)
    b += p2
    b += f'<text x="36" y="100" font-size="44" font-weight="800" fill="url(#g2)" letter-spacing="-1.5">MDT AI Copilot</text>'
    b += t(36, 130, "Agentic RAG + ML analytics on a real 5G measurement pipeline (OpenAirInterface).", 16, TXT, 500)
    b += t(36, 154, "The base system kept signal reports only in gNB memory. I built the entire intelligence layer on top.", 13.5, MUTED)

    # pipeline
    nodes = [("UE samples", "3GPP MDT reports", CY), ("Export", "parser + synth data", CY),
             ("SQLite", "2 tables · indexed", VI), ("ML core", "z-score + GBR", VI),
             ("LangGraph agent", "ReAct · 5 tools", PK), ("Interfaces", "CLI·Streamlit·Web", GR)]
    nw, gap, x0, y0, nh = 134, 19, 36, 188, 76
    for i, (a, s, col) in enumerate(nodes):
        x = x0 + i * (nw + gap)
        b += f'<rect x="{x}" y="{y0}" width="{nw}" height="{nh}" rx="14" fill="{PANEL2}" stroke="{col}" stroke-opacity="0.55" stroke-width="1.5"/>'
        b += f'<rect x="{x}" y="{y0}" width="{nw}" height="4" rx="2" fill="{col}" opacity="0.9"/>'
        b += t(x + nw / 2, y0 + 32, a, 14, TXT, 700, False, "middle")
        b += t(x + nw / 2, y0 + 53, s, 10, MUTED, 400, True, "middle")
        b += t(x + 10, y0 - 8, f"0{i+1}", 10, col, 700, True)
        if i < len(nodes) - 1:
            xa, xb, yy = x + nw, x + nw + gap, y0 + nh / 2
            b += f'<line x1="{xa}" y1="{yy}" x2="{xb}" y2="{yy}" stroke="{col}" stroke-width="2" stroke-dasharray="3 4"><animate attributeName="stroke-dashoffset" from="14" to="0" dur="1s" repeatCount="indefinite"/></line>'
            b += f'<circle r="3" fill="{col}" filter="url(#glow)"><animateMotion dur="1.6s" begin="{i*0.25}s" repeatCount="indefinite" path="M{xa} {yy} L{xb} {yy}"/></circle>'
    # chroma store feeding agent
    ax = x0 + 4 * (nw + gap)
    cx = ax + nw / 2
    b += f'<rect x="{ax-6}" y="{y0+nh+40}" width="{nw+12}" height="40" rx="10" fill="{PANEL2}" stroke="{PK}" stroke-opacity="0.5" stroke-dasharray="4 3"/>'
    b += t(cx, y0 + nh + 56, "Chroma vector store", 11, TXT, 600, False, "middle")
    b += t(cx, y0 + nh + 71, "embed-v4.0 · 4 docs", 9.5, MUTED, 400, True, "middle")
    b += f'<line x1="{cx}" y1="{y0+nh+40}" x2="{cx}" y2="{y0+nh}" stroke="{PK}" stroke-width="2" stroke-dasharray="3 4"><animate attributeName="stroke-dashoffset" from="0" to="14" dur="1s" repeatCount="indefinite"/></line>'
    b += t(36, y0 + nh + 60, "Agent picks per question: SQL tools, doc retrieval, both, or neither.", 12.5, MUTED)
    b += t(36, y0 + nh + 78, "Not naive RAG: heterogeneous questions deserve routing.", 12.5, DIM)

    # gap -> fix columns
    cols = [("≥80%", "anomaly recall", "Per-UE rolling z-score replaces fixed −100 dBm / 3 dB thresholds.", CY),
            ("< naive", "forecast MAE", "Lag-feature GradientBoosting predicts RSRP and beats last-value baseline.", VI),
            ("5", "tools the agent routes", "Query, anomaly scan, cell summary, threshold advisor, doc retrieval.", PK),
            ("SQLite", "persistent data layer", "Export pipeline means reports survive gNB restarts.", GR)]
    cwid = (W - 72 - 3 * 14) / 4
    for i, (big, lab, desc, col) in enumerate(cols):
        x = 36 + i * (cwid + 14)
        yy = 400
        b += f'<rect x="{x}" y="{yy}" width="{cwid}" height="150" rx="16" fill="{PANEL2}" stroke="{LINE}" stroke-width="1.5"/>'
        b += f'<rect x="{x+16}" y="{yy}" width="{cwid-32}" height="2" fill="{col}" opacity="0.8"/>'
        b += t(x + 18, yy + 50, big, 32, col, 800)
        b += t(x + 18, yy + 72, lab, 12.5, TXT, 600)
        # wrap desc ~ 30 chars
        words, line, lines = desc.split(), "", []
        for w_ in words:
            if len(line) + len(w_) + 1 > 29:
                lines.append(line); line = w_
            else:
                line = (line + " " + w_).strip()
        lines.append(line)
        for k, ln in enumerate(lines[:4]):
            b += t(x + 18, yy + 98 + k * 16, ln, 11.5, MUTED)
    b += t(W - 36, 578, "Python · LangGraph · scikit-learn · FastAPI · SQLite · Chroma · Streamlit · Next.js", 11, DIM, 400, True, "end")
    b += t(36, 586, "", 10)
    write("flagship.svg", W, H, b)


# =====================================================================
# 5. PROJECT CARDS
# =====================================================================
def card_base(W, H, tag, tagcol, title, desc_lines, tags):
    b = panel(W, H, 20)
    p, pw = pill(24, 22, tag, tagcol, 10.5, True, 11, 22)
    b += p
    b += f'<text x="24" y="76" font-size="25" font-weight="800" fill="{TXT}" letter-spacing="-0.6">{esc(title)}</text>'
    for i, ln in enumerate(desc_lines):
        b += t(24, 100 + i * 18, ln, 12.5, MUTED)
    x = 24
    for tg in tags:
        pp, w = pill(x, H - 40, tg, DIM, 10.5, True, 9, 22, bg="#64748b", stroke="#64748b")
        b += pp.replace(f'fill="{DIM}"', f'fill="{MUTED}"')
        x += w + 6
    return b


def card_openenv():
    W, H = 490, 312
    b = card_base(W, H, "● LIVE ON HUGGING FACE", GR, "OpenEnv",
                  ["RL environment where an LLM agent learns how", "to clean data, instead of following rules."],
                  ["Llama 3", "FastAPI", "Docker", "RL"])
    # loop diagram
    ya = 150
    b += f'<rect x="40" y="{ya}" width="150" height="54" rx="12" fill="{PANEL2}" stroke="{PK}" stroke-opacity="0.6" stroke-width="1.5"/>'
    b += t(115, ya + 25, "LLM agent", 13, TXT, 700, False, "middle") + t(115, ya + 42, "Llama 3", 10, MUTED, 400, True, "middle")
    b += f'<rect x="300" y="{ya}" width="150" height="54" rx="12" fill="{PANEL2}" stroke="{CY}" stroke-opacity="0.6" stroke-width="1.5"/>'
    b += t(375, ya + 25, "Environment", 13, TXT, 700, False, "middle") + t(375, ya + 42, "shaped rewards", 10, MUTED, 400, True, "middle")
    b += f'<path d="M190 {ya+16} L300 {ya+16}" stroke="{PK}" stroke-width="2" stroke-dasharray="3 4"><animate attributeName="stroke-dashoffset" from="14" to="0" dur="1s" repeatCount="indefinite"/></path>'
    b += f'<path d="M300 {ya+38} L190 {ya+38}" stroke="{CY}" stroke-width="2" stroke-dasharray="3 4"><animate attributeName="stroke-dashoffset" from="0" to="14" dur="1s" repeatCount="indefinite"/></path>'
    b += f'<circle r="3.5" fill="{PK}" filter="url(#glow)"><animateMotion dur="1.8s" repeatCount="indefinite" path="M190 {ya+16} L300 {ya+16}"/></circle>'
    b += f'<circle r="3.5" fill="{CY}" filter="url(#glow)"><animateMotion dur="1.8s" begin="0.9s" repeatCount="indefinite" path="M300 {ya+38} L190 {ya+38}"/></circle>'
    b += t(245, ya + 11, "action", 9.5, PK, 600, True, "middle") + t(245, ya + 56, "reward + state", 9.5, CY, 600, True, "middle")
    # reward chips
    b += t(40, 236, "+1.0 missing fixed", 10.5, GR, 600, True) + t(185, 236, "+0.8 dedupe", 10.5, GR, 600, True) + t(285, 236, "−1.0 loop penalty", 10.5, PK, 600, True)
    write("card_openenv.svg", W, H, b)


def card_hospital():
    W, H = 490, 312
    b = card_base(W, H, "◐ IN PROGRESS", AM, "HospitalOps AI",
                  ["Operations decision-support: demand", "forecasting, simulation and optimization."],
                  ["FastAPI", "React", "MongoDB", "Prophet"])
    done, total = 9, 13
    sw, g = 28, 5
    x0, y = 40, 150
    for i in range(total):
        x = x0 + i * (sw + g)
        if i < done:
            b += f'<rect x="{x}" y="{y}" width="{sw}" height="14" rx="4" fill="url(#g1)">{'<animate attributeName="opacity" values="1;0.45;1" dur="2s" repeatCount="indefinite"/>' if i == done-1 else ''}</rect>'
        else:
            b += f'<rect x="{x}" y="{y}" width="{sw}" height="14" rx="4" fill="none" stroke="{LINE}" stroke-width="1.5" stroke-dasharray="3 3"/>'
    b += t(x0, y + 38, "9 / 13 build chunks shipped", 12, TXT, 700)
    b += t(x0, y + 56, "RBAC · ingestion · dashboard · ARIMA + Prophet", 10.5, MUTED, 400, True)
    b += t(x0, y + 74, "next → LSTM · what-if sim · MIP optimizer · agents", 10.5, AM, 400, True)
    write("card_hospital.svg", W, H, b)


def card_misinfo():
    W, H = 490, 312
    b = card_base(W, H, "▲ TEAM PROJECT · AI GYANI", VI, "Misinformation AI",
                  ["AI-powered tool for combating misinformation.", "Full-stack: TypeScript UI + Python backend."],
                  ["TypeScript", "Python", "NLP"])
    steps = [("Claim", CY), ("AI analysis", VI), ("Verdict", GR)]
    x, y = 40, 154
    for i, (s, col) in enumerate(steps):
        w = 112
        b += f'<rect x="{x}" y="{y}" width="{w}" height="50" rx="12" fill="{PANEL2}" stroke="{col}" stroke-opacity="0.6" stroke-width="1.5"/>'
        b += t(x + w / 2, y + 30, s, 13, TXT, 700, False, "middle")
        if i < 2:
            b += f'<path d="M{x+w} {y+25} L{x+w+30} {y+25}" stroke="{col}" stroke-width="2" stroke-dasharray="3 4"><animate attributeName="stroke-dashoffset" from="14" to="0" dur="1s" repeatCount="indefinite"/></path>'
            b += f'<circle r="3" fill="{col}" filter="url(#glow)"><animateMotion dur="1.2s" begin="{i*0.4}s" repeatCount="indefinite" path="M{x+w} {y+25} L{x+w+30} {y+25}"/></circle>'
        x += w + 30
    b += t(40, 232, "Truth is a pipeline problem: ingest, reason, explain.", 11, DIM, 400, True)
    write("card_misinfo.svg", W, H, b)


def card_crohn():
    W, H = 490, 312
    b = card_base(W, H, "◇ RESEARCH · ONGOING", CY, "Crohn's Severity ML",
                  ["Early prediction of Crohn's disease severity", "with machine learning. Dataset discovery stage."],
                  ["Healthcare AI", "ML", "Research"])
    steps = [("Dataset", True), ("Features", False), ("Model", False), ("Severity", False)]
    x, y = 40, 156
    for i, (s, now) in enumerate(steps):
        w = 84
        col = CY if now else "#334155"
        dash = "" if now else 'stroke-dasharray="4 3"'
        b += f'<rect x="{x}" y="{y}" width="{w}" height="46" rx="12" fill="{PANEL2}" stroke="{col}" stroke-opacity="0.9" stroke-width="1.5" {dash}/>'
        b += t(x + w / 2, y + 28, s, 12.5, TXT if now else MUTED, 700 if now else 500, False, "middle")
        if now:
            b += f'<rect x="{x}" y="{y}" width="{w}" height="46" rx="12" fill="none" stroke="{CY}" stroke-width="2" opacity="0"><animate attributeName="opacity" values="0;0.9;0" dur="2.2s" repeatCount="indefinite"/></rect>'
            b += t(x + w / 2, y - 8, "▼ now", 9.5, CY, 700, True, "middle")
        if i < 3:
            b += f'<path d="M{x+w+4} {y+23} L{x+w+16} {y+23}" stroke="#334155" stroke-width="2" stroke-dasharray="3 3"/>'
        x += w + 20
    b += t(40, 232, "Careful problem-framing before modelling.", 11, DIM, 400, True)
    write("card_crohn.svg", W, H, b)


# =====================================================================
# 6. STACK
# =====================================================================
def stack():
    W = 1000
    groups = [("AI / ML", CY, ["scikit-learn", "pandas", "NumPy", "LangGraph", "LangChain", "RAG", "Chroma", "Cohere", "Llama 3", "ARIMA", "Prophet", "Reinforcement Learning"]),
              ("BACKEND", VI, ["Python", "FastAPI", "Node.js", "Express", "REST", "MongoDB", "MySQL", "SQLite", "Redis", "Docker"]),
              ("FRONTEND", PK, ["React", "Next.js", "TypeScript", "Vite", "Tailwind", "Streamlit", "Plotly"]),
              ("FOUNDATIONS", GR, ["DSA", "OOP", "C++", "JavaScript", "SQL", "PHP", "Git"])]
    rows_y = 70
    b = ""
    body = ""
    y = 34
    for name, col, items in groups:
        body += t(34, y + 17, name, 11, col, 800, True, extra='letter-spacing="2"')
        x, ly = 170, y
        for it in items:
            w = int(len(it) * 7.4) + 26
            if x + w > W - 34:
                x, ly = 170, ly + 36
            body += (f'<g><rect x="{x}" y="{ly}" width="{w}" height="28" rx="14" fill="{col}" fill-opacity="0.09" stroke="{col}" stroke-opacity="0.4"/>'
                     f'<circle cx="{x+13}" cy="{ly+14}" r="3" fill="{col}"/>'
                     + t(x + 22, ly + 18.5, it, 12, TXT, 500, True) + "</g>")
            x += w + 8
        y = ly + 52
    H = y + 6
    b = panel(W, H, 20, accent=False) + body
    write("stack.svg", W, H, b)


# =====================================================================
# 7. NOW / NEXT / OPEN
# =====================================================================
def now_panel():
    W, H = 1000, 206
    b = panel(W, H, 20, accent=False)
    cols = [("NOW BUILDING", CY, ["HospitalOps AI: LSTM forecasting next,", "then simulation and optimization", "Crohn's severity ML: finding the dataset"]),
            ("EXPLORING", VI, ["Agentic systems: routing, guardrails,", "evaluation of tool-using agents", "Reinforcement learning for data pipelines"]),
            ("LOOKING FOR", GR, ["ML / AI internships, 2026–27", "Research collaborations in applied AI", "Teams that ship real-world AI systems"])]
    cw = W / 3
    for i, (h, col, lines) in enumerate(cols):
        x = i * cw + 34
        if i:
            b += f'<line x1="{i*cw}" y1="28" x2="{i*cw}" y2="{H-28}" stroke="{LINE}"/>'
        b += f'<circle cx="{x+4}" cy="42" r="4" fill="{col}"><animate attributeName="opacity" values="1;0.3;1" dur="2s" begin="{i*0.5}s" repeatCount="indefinite"/></circle>'
        b += t(x + 16, 47, h, 12, col, 800, True, extra='letter-spacing="2"')
        for k, ln in enumerate(lines):
            b += t(x, 92 + k * 28, ln, 13, TXT if k == 0 else MUTED, 600 if k == 0 else 400)
    write("now.svg", W, H, b)


# =====================================================================
# 8. BUTTONS + FOOTER
# =====================================================================
def button(name, label, sub, col):
    W, H = 300, 64
    b = f'<rect width="{W}" height="{H}" rx="16" fill="{PANEL}"/>'
    b += f'<rect x="0.75" y="0.75" width="{W-1.5}" height="{H-1.5}" rx="16" fill="none" stroke="{col}" stroke-opacity="0.6" stroke-width="1.5"/>'
    b += f'<rect width="{W}" height="{H}" rx="16" fill="{col}" opacity="0.06"/>'
    b += t(26, 28, label, 16, TXT, 800) + t(26, 47, sub, 11, MUTED, 400, True)
    b += f'<text x="{W-30}" y="40" font-size="22" fill="{col}" font-weight="800" text-anchor="end">→<animateTransform attributeName="transform" type="translate" values="0 0;5 0;0 0" dur="1.6s" repeatCount="indefinite"/></text>'
    write(name, W, H, b)


def footer():
    W, H = 1000, 150
    b = f'<rect width="{W}" height="{H}" rx="24" fill="{BG}"/>'
    b += f'<clipPath id="fc"><rect width="{W}" height="{H}" rx="24"/></clipPath><g clip-path="url(#fc)">'
    b += f'<g filter="url(#blur)" opacity="0.5"><circle cx="220" cy="150" r="110" fill="{CY}" opacity="0.5"/><circle cx="520" cy="170" r="120" fill="{VI}" opacity="0.55"/><circle cx="820" cy="150" r="110" fill="{PK}" opacity="0.45"/></g>'
    b += f'<rect width="{W}" height="{H}" fill="url(#grid)"/>'
    b += t(W / 2, 62, "Simplicity scales. Clarity wins. Engineering is responsibility.", 20, TXT, 700, False, "middle")
    b += t(W / 2, 92, "Thanks for stopping by. Let's build something that matters.", 13, MUTED, 400, True, "middle")
    b += f'<rect x="{W/2-60}" y="108" width="120" height="3" rx="1.5" fill="url(#g2)"/>'
    b += "</g>"
    b += f'<rect x="0.75" y="0.75" width="{W-1.5}" height="{H-1.5}" rx="24" fill="none" stroke="{LINE}" stroke-width="1.5"/>'
    write("footer.svg", W, H, b)


hero(); metrics()
header("h_work.svg", "01", "Flagship Work", "the project I'm proudest of")
header("h_more.svg", "02", "More Systems", "agents · forecasting · research")
header("h_stack.svg", "03", "Engineering Stack", "what I build with")
header("h_now.svg", "04", "Now · Next", "what I'm doing and what I want")
flagship(); card_openenv(); card_hospital(); card_misinfo(); card_crohn()
stack(); now_panel()
button("btn_portfolio.svg", "Portfolio", "hil-portfolio.vercel.app", CY)
button("btn_linkedin.svg", "LinkedIn", "in/hil-kalathiya", VI)
footer()
print("ok", sorted(os.listdir(OUT)))
