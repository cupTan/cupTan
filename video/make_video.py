"""Render 'Venture Capital in 3 Minutes' — a 180s captioned motion-graphics video with generated music."""
import math, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

W, H, FPS = 1280, 720, 30
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
OUT = "venture_capital_in_3_minutes.mp4"

FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_fc = {}
def font(size, bold=False):
    k = (size, bold)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(FB if bold else FR, size)
    return _fc[k]

BG1, BG2 = (11, 18, 38), (20, 34, 66)
WHITE = (240, 244, 250)
MUTED = (150, 164, 190)
ACC = (72, 202, 228)     # cyan
GOLD = (255, 196, 87)
GREEN = (98, 214, 142)
CORAL = (255, 117, 107)
PANEL = (30, 46, 84)

# background gradient + subtle grid
_bg = np.zeros((H, W, 3), np.float32)
t = np.linspace(0, 1, H)[:, None]
for i in range(3):
    _bg[:, :, i] = BG1[i] * (1 - t) + BG2[i] * t
_bg[::40, :, :] += 4
_bg[:, ::40, :] += 4
BG = np.clip(_bg, 0, 255).astype(np.uint8)

def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3

def prog(t, start, dur=0.8):
    return ease((t - start) / dur)

def mix(c, a, bg=BG1):
    return tuple(int(bg[i] + (c[i] - bg[i]) * a) for i in range(3))

def text(d, xy, s, size, color=WHITE, a=1.0, bold=False, anchor="la", dy=0):
    x, y = xy
    y += (1 - a) * 20 + dy
    d.text((x, y), s, font=font(size, bold), fill=mix(color, a), anchor=anchor)

def wrap(s, size, maxw, bold=False):
    f = font(size, bold); words = s.split(); lines = []; cur = ""
    for w in words:
        trial = (cur + " " + w).strip()
        if f.getlength(trial) <= maxw:
            cur = trial
        else:
            lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def rrect(d, box, fill, a=1.0, r=16, outline=None):
    d.rounded_rectangle(box, r, fill=mix(fill, a), outline=mix(outline, a) if outline else None, width=2)

def arrow(d, p0, p1, color, a, w=4):
    x0, y0 = p0; x1, y1 = p1
    xe = x0 + (x1 - x0) * a; ye = y0 + (y1 - y0) * a
    if a <= 0: return
    d.line([(x0, y0), (xe, ye)], fill=mix(color, 1), width=w)
    ang = math.atan2(ye - y0, xe - x0)
    for s in (2.6, -2.6):
        d.line([(xe, ye), (xe + 16 * math.cos(ang + s), ye + 16 * math.sin(ang + s))], fill=mix(color, 1), width=w)

def heading(d, t, kicker, title):
    a = prog(t, 0.1)
    text(d, (80, 60), kicker.upper(), 20, ACC, a, bold=True)
    text(d, (80, 92), title, 44, WHITE, prog(t, 0.25), bold=True)
    d.rectangle([80, 158, 80 + 90 * prog(t, 0.4), 162], fill=ACC)

# ---------------------------------------------------------------- scenes
def s_title(d, t, D):
    a = prog(t, 0.3, 1.2)
    text(d, (W // 2, 250), "VENTURE CAPITAL", 30, ACC, a, bold=True, anchor="mm")
    text(d, (W // 2, 330), "in 3 Minutes", 88, WHITE, prog(t, 0.8, 1.2), bold=True, anchor="mm")
    w = 360 * prog(t, 1.5, 1.2)
    d.rectangle([W // 2 - w / 2, 392, W // 2 + w / 2, 396], fill=GOLD)
    text(d, (W // 2, 440), "How startup money really works", 30, MUTED, prog(t, 2.2, 1.2), anchor="mm")

def s_what(d, t, D):
    heading(d, t, "Chapter 1", "What is venture capital?")
    items = [("$", "Capital", "from investors", GOLD), ("🚀", "Startup", "young, high-growth", ACC), ("%", "Equity", "ownership stake", GREEN)]
    xs = [220, 640, 1060]
    for i, (sym, t1, t2, c) in enumerate(items):
        a = prog(t, 1.2 + i * 1.6)
        cx, cy = xs[i], 360
        r = 80 * a
        if r > 1:
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=mix(PANEL, a), outline=mix(c, a), width=4)
        s = sym if sym != "🚀" else "▲"
        text(d, (cx, cy), s, 64, c, a, bold=True, anchor="mm")
        text(d, (cx, cy + 120), t1, 32, WHITE, a, bold=True, anchor="mm")
        text(d, (cx, cy + 158), t2, 22, MUTED, a, anchor="mm")
        if i < 2:
            arrow(d, (cx + 100, cy), (xs[i + 1] - 100, cy), MUTED, prog(t, 2.0 + i * 1.6))

def s_who(d, t, D):
    heading(d, t, "Chapter 2", "Who's involved?")
    boxes = [
        (90, 250, 400, 470, "LPs", "Limited Partners", ["Pension funds", "Endowments", "Family offices"], GOLD),
        (485, 250, 795, 470, "GPs", "The VC firm", ["Raise the fund", "Pick startups", "Sit on boards"], ACC),
        (880, 250, 1190, 470, "Startups", "Portfolio companies", ["Get capital", "Get advice", "Give equity"], GREEN),
    ]
    for i, (x0, y0, x1, y1, t1, t2, lines, c) in enumerate(boxes):
        a = prog(t, 1.0 + i * 1.8)
        rrect(d, (x0, y0 + (1 - a) * 30, x1, y1 + (1 - a) * 30), PANEL, a, outline=c)
        text(d, ((x0 + x1) // 2, y0 + 40), t1, 34, c, a, bold=True, anchor="mm")
        text(d, ((x0 + x1) // 2, y0 + 78), t2, 20, MUTED, a, anchor="mm")
        for j, ln in enumerate(lines):
            text(d, (x0 + 34, y0 + 112 + j * 32), "•  " + ln, 21, WHITE, prog(t, 1.4 + i * 1.8 + j * 0.3))
    fa = prog(t, 6.5, 1.0)
    if fa > 0:
        for k, (xa, xb) in enumerate([(400, 485), (795, 880)]):
            arrow(d, (xa + 5, 360), (xb - 5, 360), GOLD, fa)
        # flowing money dots
        for k in range(6):
            ph = ((t * 0.5 + k / 6) % 1.0)
            x = 400 + ph * 480
            if 400 < x < 485 or 795 < x < 880:
                d.ellipse([x - 5, 355, x + 5, 365], fill=GOLD)
        text(d, (W // 2, 540), "Money flows in  →   returns flow back when companies exit (IPO or acquisition)", 22, MUTED, fa, anchor="mm")

def s_fees(d, t, D):
    heading(d, t, "Chapter 3", "How VCs get paid: “2 and 20”")
    cards = [(160, "2%", "Management fee", "per year, on committed capital —\npays salaries & operations", ACC),
             (680, "20%", "Carried interest", "share of the profits above\nthe capital returned to LPs", GOLD)]
    for i, (x, big, t1, t2, c) in enumerate(cards):
        a = prog(t, 1.0 + i * 2.5)
        rrect(d, (x, 220, x + 440, 520), PANEL, a, outline=c)
        # count-up
        target = int(big[:-1]); val = int(round(target * prog(t, 1.2 + i * 2.5, 1.5)))
        text(d, (x + 220, 310), f"{val}%", 96, c, a, bold=True, anchor="mm")
        text(d, (x + 220, 395), t1, 30, WHITE, a, bold=True, anchor="mm")
        for j, ln in enumerate(t2.split("\n")):
            text(d, (x + 220, 440 + j * 28), ln, 20, MUTED, a, anchor="mm")
    text(d, (W // 2, 590), "Carry aligns incentives: GPs earn big only when LPs earn big.", 24, GREEN, prog(t, 7.5), anchor="mm")

STAGES = [("Pre-seed", "$0.1–1M", "Idea & founders"), ("Seed", "$1–4M", "Early product"),
          ("Series A", "$5–20M", "Product-market fit"), ("Series B", "$20–60M", "Scaling up"),
          ("Series C+", "$50M+", "Expansion & exit")]
def s_stages(d, t, D):
    heading(d, t, "Chapter 4", "Funding stages")
    y = 380; x0, x1 = 120, 1160
    d.line([(x0, y), (x0 + (x1 - x0) * prog(t, 0.8, 2.0), y)], fill=MUTED, width=4)
    for i, (nm, amt, desc) in enumerate(STAGES):
        a = prog(t, 1.5 + i * 2.2)
        x = x0 + 40 + i * ((x1 - x0 - 80) / 4)
        r = 12 + i * 5
        rr = r * a
        c = [ACC, ACC, GREEN, GOLD, CORAL][i]
        if rr > 0.5:
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=mix(c, a))
        text(d, (x, y - 80), nm, 26, WHITE, a, bold=True, anchor="mm")
        text(d, (x, y + 70), amt, 26, c, a, bold=True, anchor="mm")
        text(d, (x, y + 105), desc, 18, MUTED, a, anchor="mm")
    text(d, (W // 2, 600), "Each round: bigger checks, higher valuation, less risk. (Typical US ranges, illustrative.)", 20, MUTED, prog(t, 13), anchor="mm")

RETURNS = [0, 0, 0.2, 0, 0.5, 1.0, 0, 0.3, 2.5, 0, 1.2, 0, 0.8, 3.0, 0, 0.1, 55.0, 0, 1.5, 0.4]
def s_power(d, t, D):
    heading(d, t, "Chapter 5", "The power law")
    bx0, by = 120, 560; bw = 44; gap = 8; maxh = 330; scale = maxh / 55.0
    d.line([(bx0 - 10, by), (bx0 + 20 * (bw + gap), by)], fill=MUTED, width=2)
    for i, r in enumerate(RETURNS):
        a = prog(t, 1.0 + i * 0.25, 0.6)
        hgt = max(r * scale, 3) * a
        big = r > 10
        grow = prog(t, 7.0, 3.0) if big else 1
        if big: hgt = max(3, r * scale * grow) * a
        c = GOLD if big else (GREEN if r >= 1 else CORAL)
        x = bx0 + i * (bw + gap)
        d.rectangle([x, by - hgt, x + bw, by], fill=mix(c, a))
    text(d, (bx0, by + 16), "20 hypothetical investments  ·  return multiple on each check", 18, MUTED, prog(t, 1.0))
    ta = prog(t, 10.0)
    x_big = bx0 + 16 * (bw + gap) + bw // 2
    text(d, (x_big + 40, 250), "55×", 44, GOLD, ta, bold=True)
    text(d, (x_big + 40, 305), "one winner returns", 20, WHITE, ta)
    text(d, (x_big + 40, 332), "the entire fund", 20, WHITE, ta)
    text(d, (130, 200), "Most bets fail —", 24, CORAL, prog(t, 4.0))
    text(d, (130, 200 + 34), "outliers pay for everything.", 24, WHITE, prog(t, 4.5))

def s_jcurve(d, t, D):
    heading(d, t, "Chapter 6", "A fund's life: the J-curve")
    x0, x1, y0 = 140, 1140, 420
    d.line([(x0, 200), (x0, 620)], fill=MUTED, width=2)
    d.line([(x0, y0), (x1, y0)], fill=MUTED, width=2)
    for yr in range(11):
        x = x0 + yr * (x1 - x0) / 10
        text(d, (x, y0 + 12), str(yr), 16, MUTED, prog(t, 0.6))
    text(d, (x1, y0 + 40), "years", 16, MUTED, prog(t, 0.6), anchor="ra")
    p = prog(t, 1.5, 9.0)
    pts = []
    n = int(200 * p)
    for k in range(n + 1):
        u = k / 200 * 10
        v = -1.0 * math.sin(min(u, 4) / 4 * math.pi / 2) * math.exp(-max(0, u - 3) * 0) if u < 3 else None
        # smooth J: dip to -1 around year 3, cross zero ~year 5.5, rise to +2.2 by year 10
        v = -1.2 * math.exp(-((u - 2.8) ** 2) / 3.0) + 2.4 / (1 + math.exp(-(u - 6.5) * 1.1)) - 2.4 / (1 + math.exp(6.5 * 1.1))
        pts.append((x0 + u / 10 * (x1 - x0), y0 - v * 85))
    if len(pts) > 1:
        d.line(pts, fill=ACC, width=6, joint="curve")
    labels = [(1.2, "Invest: fees + early write-downs", CORAL, 2.0, 1), (5.3, "Winners emerge", WHITE, 7.0, -1),
              (8.6, "Exits return cash to LPs", GREEN, 10.5, 2)]
    for u, s, c, ts, side in labels:
        a = prog(t, ts)
        x = x0 + u / 10 * (x1 - x0)
        text(d, (x, {1: 560, -1: 240, 2: 495}[side]), s, 20, c, a, bold=True, anchor="mm")
    text(d, (x0 + 12, 200), "Net value to LPs", 16, MUTED, prog(t, 0.6))

def s_criteria(d, t, D):
    heading(d, t, "Chapter 7", "What VCs look for")
    items = [("Team", "Founders who can execute\nand attract talent", ACC),
             ("Market", "Big enough to build a\n$1B+ company", GOLD),
             ("Product", "Something customers love —\n10× better, not 10%", GREEN),
             ("Traction", "Evidence: growth, revenue,\nretention", CORAL)]
    for i, (t1, t2, c) in enumerate(items):
        a = prog(t, 1.2 + i * 2.5)
        col, row = i % 2, i // 2
        x = 130 + col * 530; y = 210 + row * 200
        rrect(d, (x, y + (1 - a) * 25, x + 490, y + 170 + (1 - a) * 25), PANEL, a, outline=c)
        d.rectangle([x, y + 20, x + 6, y + 150], fill=mix(c, a))
        text(d, (x + 36, y + 30), f"0{i + 1}  {t1}", 32, c, a, bold=True)
        for j, ln in enumerate(t2.split("\n")):
            text(d, (x + 36, y + 85 + j * 30), ln, 22, WHITE, a)

def s_valuation(d, t, D):
    heading(d, t, "Chapter 8", "Valuation math")
    a1, a2, a3 = prog(t, 1.0), prog(t, 3.0), prog(t, 5.0)
    text(d, (250, 280), "$8M", 72, WHITE, a1, bold=True, anchor="mm")
    text(d, (250, 340), "pre-money", 22, MUTED, a1, anchor="mm")
    text(d, (420, 280), "+", 64, MUTED, a2, anchor="mm")
    text(d, (590, 280), "$2M", 72, GOLD, a2, bold=True, anchor="mm")
    text(d, (590, 340), "investment", 22, MUTED, a2, anchor="mm")
    text(d, (760, 280), "=", 64, MUTED, a3, anchor="mm")
    text(d, (960, 280), "$10M", 72, ACC, a3, bold=True, anchor="mm")
    text(d, (960, 340), "post-money", 22, MUTED, a3, anchor="mm")
    # ownership bar
    a4 = prog(t, 8.0, 1.2)
    bx0, bx1, by0, by1 = 200, 1080, 430, 490
    if a4 > 0:
        mid = bx0 + (bx1 - bx0) * 0.8
        d.rectangle([bx0, by0, bx0 + (mid - bx0) * a4, by1], fill=ACC)
        d.rectangle([mid, by0, mid + (bx1 - mid) * a4, by1], fill=GOLD)
        text(d, ((bx0 + mid) / 2, (by0 + by1) / 2), "Existing owners 80%", 22, BG1, a4, bold=True, anchor="mm")
        text(d, ((mid + bx1) / 2, (by0 + by1) / 2), "VC 20%", 22, BG1, a4, bold=True, anchor="mm")
    text(d, (W // 2, 560), "Investor ownership = investment ÷ post-money = $2M ÷ $10M = 20%", 24, WHITE, prog(t, 11), anchor="mm")

def s_dilution(d, t, D):
    heading(d, t, "Chapter 9", "Dilution: a smaller slice of a bigger pie")
    rounds = [("Founding", 100), ("Seed", 80), ("Series A", 64), ("Series B", 51), ("Series C", 41)]
    base = 580; maxh = 300
    for i, (nm, pct) in enumerate(rounds):
        a = prog(t, 0.8 + i * 1.3)
        x = 170 + i * 200; w = 120
        h_f = maxh * pct / 100 * a; h_all = maxh * a
        d.rectangle([x, base - h_all, x + w, base], fill=mix(PANEL, a))
        d.rectangle([x, base - h_f, x + w, base], fill=mix(ACC, a))
        text(d, (x + w / 2, base - h_all - 28), f"{pct}%", 26, WHITE, a, bold=True, anchor="mm")
        text(d, (x + w / 2, base + 24), nm, 20, MUTED, a, anchor="mm")
    text(d, (80, 182), "Founders' stake after each round, ~20% sold per round (illustrative)", 20, MUTED, prog(t, 1.0))

def s_takeaways(d, t, D):
    heading(d, t, "Recap", "Three things to remember")
    pts = [("VC trades cash for equity in high-risk, high-growth companies.", ACC),
           ("Returns follow a power law — a few outliers drive everything.", GOLD),
           ("Founders sell ownership to grow the pie; valuation sets the price.", GREEN)]
    for i, (s, c) in enumerate(pts):
        a = prog(t, 1.0 + i * 1.8)
        y = 240 + i * 110
        d.ellipse([100, y, 150, y + 50], fill=mix(c, a))
        text(d, (125, y + 25), str(i + 1), 26, BG1, a, bold=True, anchor="mm")
        text(d, (180, y + 8), s, 28, WHITE, a)

def s_end(d, t, D):
    a = prog(t, 0.3, 1.0)
    text(d, (W // 2, 320), "Thanks for watching", 60, WHITE, a, bold=True, anchor="mm")
    text(d, (W // 2, 390), "Educational overview — not investment advice.", 22, MUTED, prog(t, 1.0), anchor="mm")

# (func, duration seconds, caption lines shown sequentially)
SCENES = [
    (s_title, 10, ["Venture capital funds most of the world's fastest-growing startups.",
                   "Here's how it works — in three minutes."]),
    (s_what, 16, ["Venture capital is money invested in young companies with the potential to grow very fast.",
                  "Investors don't get repaid like a loan. They get equity — a piece of ownership.",
                  "If the company succeeds, that stake can be worth many times the original check."]),
    (s_who, 18, ["Three players: Limited Partners supply the money — pension funds, endowments, family offices.",
                 "General Partners run the VC firm: they raise the fund, pick startups, and join boards.",
                 "Startups get capital and advice. When they exit through an IPO or acquisition, money flows back."]),
    (s_fees, 15, ["VC firms are typically paid on a “2 and 20” model.",
                  "A ~2% annual management fee keeps the lights on.",
                  "And ~20% of the fund's profits — carried interest — rewards real performance."]),
    (s_stages, 20, ["Startups raise money in stages.",
                    "Pre-seed and seed back an idea and a team. Series A backs a product that fits its market.",
                    "Series B and later rounds fund scaling, expansion, and eventually an exit.",
                    "Each round usually brings bigger checks at a higher valuation."]),
    (s_power, 20, ["Venture returns follow a power law.",
                   "Most investments fail or return little. A handful do okay.",
                   "But one breakout company can return the entire fund — and more.",
                   "That's why VCs swing for outliers, not safe bets."]),
    (s_jcurve, 18, ["A typical fund lives about ten years.",
                    "Early on, fees and write-downs push returns negative — the bottom of the “J”.",
                    "As winners grow and exit, cash flows back and the curve climbs."]),
    (s_criteria, 18, ["So what do VCs look for?",
                      "A team that can execute, and a market big enough for a billion-dollar company.",
                      "A product customers love, and traction that proves it."]),
    (s_valuation, 18, ["Valuation sets the price of a deal.",
                       "An $8M pre-money valuation plus a $2M investment gives a $10M post-money valuation.",
                       "The investor's $2M buys 2 ÷ 10 — or 20% — of the company."]),
    (s_dilution, 12, ["Every new round dilutes existing owners.",
                      "Founders own a smaller slice — but ideally of a much bigger pie."]),
    (s_takeaways, 10, ["Cash for equity. A power law of returns. And valuation that sets the price.",
                       "That's venture capital."]),
    (s_end, 5, [""]),
]

def draw_caption(d, s, a):
    if not s or a <= 0: return
    lines = wrap(s, 24, 1080)
    lh = 32; hbox = len(lines) * lh + 24
    y0 = H - 30 - hbox
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    return lines, y0, hbox

def render():
    total = sum(s[1] for s in SCENES)
    cmd = [FFMPEG, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", "music.wav", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    fi = 0
    for idx, (fn, dur, caps) in enumerate(SCENES):
        nf = dur * FPS
        for k in range(nf):
            t = k / FPS
            img = Image.fromarray(BG.copy())
            d = ImageDraw.Draw(img)
            fn(d, t, dur)
            # caption (sequential, evenly split)
            seg = dur / len(caps); ci = min(int(t // seg), len(caps) - 1); lt = t - ci * seg
            ca = min(1, lt / 0.35, (seg - lt) / 0.35) if len(caps) > 1 else min(1, lt / 0.35)
            s = caps[ci]
            if s:
                lines = wrap(s, 24, 1080)
                lh = 32; hbox = len(lines) * lh + 22; y0 = H - 26 - hbox
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
                od.rounded_rectangle((80, y0, W - 80, y0 + hbox), 12, fill=(5, 9, 20, int(190 * max(ca, 0))))
                for j, ln in enumerate(lines):
                    od.text((W // 2, y0 + 11 + j * lh + lh // 2), ln, font=font(24), fill=(240, 244, 250, int(255 * max(ca, 0))), anchor="mm")
                img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
            # scene fade in/out
            f = min(1, t / 0.5, (dur - t) / 0.5)
            arr = np.asarray(img)
            if f < 1:
                arr = (BG.astype(np.float32) * (1 - f) + arr.astype(np.float32) * f).astype(np.uint8)
            p.stdin.write(arr.tobytes())
            fi += 1
        print(f"scene {idx + 1}/{len(SCENES)} done", flush=True)
    p.stdin.close(); p.wait()
    print("wrote", OUT, "frames", fi, "seconds", total)

# ---------------------------------------------------------------- music
def music(total, sr=44100):
    n = int(total * sr); out = np.zeros((n, 2), np.float32)
    tt = np.arange(n) / sr
    def midi(m): return 440 * 2 ** ((m - 69) / 12)
    prog_ch = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]   # Am F C G
    bar = 4.0
    # pad
    for b in range(int(total / bar) + 1):
        ch = prog_ch[b % 4]; s0 = int(b * bar * sr); s1 = min(n, int((b + 1) * bar * sr + 0.8 * sr))
        if s0 >= n: break
        seg = np.arange(s1 - s0) / sr; L = len(seg)
        env = np.minimum(1, seg / 0.8) * np.minimum(1, (L / sr - seg) / 0.8)
        for m in ch + [ch[0] - 12]:
            f0 = midi(m)
            for det, pan in ((-0.15, 0.3), (0.15, 0.7)):
                w = np.sin(2 * np.pi * (f0 + det) * seg) + 0.25 * np.sin(2 * np.pi * 2 * (f0 + det) * seg)
                out[s0:s1, 0] += 0.022 * env * w * (1 - pan)
                out[s0:s1, 1] += 0.022 * env * w * pan
    # arpeggio plucks (8th notes at 120bpm = 0.25s), start after intro
    step = 0.25
    pattern = [0, 1, 2, 1, 0, 2, 1, 2]
    for i in range(int(total / step)):
        st = i * step
        if st < 6 or st > total - 6: continue
        b = int(st // bar); ch = prog_ch[b % 4]
        m = ch[pattern[i % 8]] + 12
        f0 = midi(m); s0 = int(st * sr); L = int(0.9 * sr); s1 = min(n, s0 + L)
        seg = np.arange(s1 - s0) / sr
        env = np.exp(-seg * 5.5) * np.minimum(1, seg / 0.005)
        w = np.sin(2 * np.pi * f0 * seg) + 0.3 * np.sin(2 * np.pi * 2 * f0 * seg) * np.exp(-seg * 8)
        pan = 0.35 + 0.3 * ((i % 4) / 3)
        out[s0:s1, 0] += 0.05 * env * w * (1 - pan)
        out[s0:s1, 1] += 0.05 * env * w * pan
    # soft kick + bass on each beat in the middle section
    for i in range(int(total / 0.5)):
        st = i * 0.5
        if st < 14 or st > total - 12: continue
        s0 = int(st * sr); s1 = min(n, s0 + int(0.35 * sr)); seg = np.arange(s1 - s0) / sr
        fsw = 90 * np.exp(-seg * 18) + 45
        kick = np.sin(2 * np.pi * np.cumsum(fsw) / sr) * np.exp(-seg * 12)
        out[s0:s1] += 0.10 * kick[:, None] * (1.0 if i % 2 == 0 else 0.55)
        b = int(st // bar); f0 = midi(prog_ch[b % 4][0] - 24)
        bass = np.sin(2 * np.pi * f0 * seg) * np.exp(-seg * 4)
        out[s0:s1] += 0.06 * bass[:, None]
    # simple reverb-ish echo
    dl = int(0.3 * sr)
    out[dl:, 0] += 0.25 * out[:-dl, 1]; out[dl:, 1] += 0.25 * out[:-dl, 0]
    fade = np.minimum(1, np.minimum(tt / 3.0, (total - tt) / 4.0))[:, None]
    out *= fade
    out /= max(1e-6, np.abs(out).max()) / 0.8
    pcm = (out * 32767).astype(np.int16)
    with wave.open("music.wav", "wb") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sr); wf.writeframes(pcm.tobytes())

if __name__ == "__main__":
    import sys
    total = sum(s[1] for s in SCENES)
    music(total)
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        # render stills for a quick visual check
        for idx, (fn, dur, caps) in enumerate(SCENES):
            img = Image.fromarray(BG.copy()); d = ImageDraw.Draw(img); fn(d, dur - 1.0, dur)
            img.save(f"preview_{idx:02d}.png")
    else:
        render()
