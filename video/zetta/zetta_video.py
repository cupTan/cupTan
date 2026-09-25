"""Render the Zetta Semiconductor introduction video (captioned motion graphics + generated music).

Setup: unzip the company deck (.pptx) and point ./assets at its ppt/media folder, e.g.
  unzip deck.pptx -d deck && ln -s deck/ppt/media assets
Then: pip install pillow numpy imageio-ffmpeg && python3 zetta_video.py  (or `preview` for stills).
"""
import math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import imageio_ffmpeg

W, H, FPS = 1280, 720, 30
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
HERE = os.path.dirname(os.path.abspath(__file__))
MEDIA = os.path.join(HERE, "assets")
OUT = os.path.join(HERE, "zetta_introduction.mp4")

FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FCJK = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
_fc = {}
def font(size, bold=False, cjk=False):
    k = (size, bold, cjk)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(FCJK if cjk else (FB if bold else FR), size)
    return _fc[k]

# Zetta brand: navy + logo blue + logo pink
BG1, BG2 = (8, 14, 36), (16, 28, 64)
WHITE = (240, 244, 250)
MUTED = (150, 164, 196)
BLUE = (52, 140, 230)
CYAN = (80, 200, 240)
PINK = (255, 70, 160)
GOLD = (255, 196, 87)
GREEN = (98, 214, 142)
PANEL = (24, 38, 80)

_bg = np.zeros((H, W, 3), np.float32)
tt = np.linspace(0, 1, H)[:, None]
for i in range(3):
    _bg[:, :, i] = BG1[i] * (1 - tt) + BG2[i] * tt
_bg[::40, :, :] += 3
_bg[:, ::40, :] += 3
BG = np.clip(_bg, 0, 255).astype(np.uint8)

def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3

def prog(t, start, dur=0.8):
    return ease((t - start) / dur)

def mix(c, a, bg=BG1):
    return tuple(int(bg[i] + (c[i] - bg[i]) * a) for i in range(3))

def text(d, xy, s, size, color=WHITE, a=1.0, bold=False, anchor="la", cjk=False):
    if a <= 0: return
    x, y = xy
    d.text((x, y + (1 - a) * 18), s, font=font(size, bold, cjk), fill=mix(color, a), anchor=anchor)

def wrap(s, size, maxw, bold=False):
    f = font(size, bold); lines = []; cur = ""
    for w in s.split():
        trial = (cur + " " + w).strip()
        if f.getlength(trial) <= maxw: cur = trial
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def para(d, xy, s, size, maxw, color=WHITE, a=1.0, lh=None, bold=False):
    lh = lh or int(size * 1.35)
    for j, ln in enumerate(wrap(s, size, maxw, bold)):
        text(d, (xy[0], xy[1] + j * lh), ln, size, color, a, bold)

def rrect(d, box, fill, a=1.0, r=14, outline=None, width=2):
    if a <= 0: return
    d.rounded_rectangle(box, r, fill=mix(fill, a), outline=mix(outline, a) if outline else None, width=width)

def heading(d, t, kicker, title):
    text(d, (70, 44), kicker.upper(), 18, PINK, prog(t, 0.1), bold=True)
    text(d, (70, 72), title, 40, WHITE, prog(t, 0.25), bold=True)
    d.rectangle([70, 130, 70 + 80 * prog(t, 0.4), 134], fill=BLUE)

# ---------------------------------------------------------------- images
_img = {}
def load(name):
    return Image.open(os.path.join(MEDIA, name)).convert("RGBA")

def logo_rgba(name, recolor_dark=True):
    """Turn a logo on white into RGBA; paint the dark wordmark white so it reads on navy."""
    a = np.asarray(Image.open(os.path.join(MEDIA, name)).convert("RGB")).astype(np.float32)
    alpha = np.clip((255 - a.min(axis=2)) * 1.25, 0, 255)
    al = np.maximum(alpha / 255, 1e-3)[..., None]
    rgb = np.clip((a - 255 * (1 - al)) / al, 0, 255)
    if recolor_dark:
        sat = rgb.max(axis=2) - rgb.min(axis=2)
        dark = (sat < 60)
        rgb[dark] = WHITE
    out = np.dstack([rgb, alpha]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")

def fitted(key, name, size, mode="cover", radius=12, src=None):
    k = (key, size, mode, radius)
    if k in _img: return _img[k]
    im = src if src is not None else load(name)
    tw, th = size
    if mode == "cover":
        s = max(tw / im.width, th / im.height)
        im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
        l = (im.width - tw) // 2; tp = (im.height - th) // 2
        im = im.crop((l, tp, l + tw, tp + th))
    else:
        s = min(tw / im.width, th / im.height)
        im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    if radius:
        m = Image.new("L", im.size, 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius, fill=255)
        im.putalpha(Image.fromarray(np.minimum(np.asarray(im.split()[3]), np.asarray(m))))
    _img[k] = im
    return im

def paste(canvas, im, xy, a=1.0, anchor="la"):
    if a <= 0: return
    x, y = xy
    if anchor == "mm": x -= im.width // 2; y -= im.height // 2
    y = int(y + (1 - a) * 18)
    if a < 1:
        im = im.copy(); al = np.asarray(im.split()[3]).astype(np.float32) * a
        im.putalpha(Image.fromarray(al.astype(np.uint8)))
    canvas.paste(im, (int(x), y), im)

def photo(canvas, key, name, box, a, mode="cover", radius=12, border=None):
    x0, y0, x1, y1 = box
    im = fitted(key, name, (x1 - x0, y1 - y0), mode, radius)
    if mode == "contain":
        x0 += ((x1 - x0) - im.width) // 2; y0 += ((y1 - y0) - im.height) // 2
    paste(canvas, im, (x0, y0), a)
    if border and a > 0:
        ImageDraw.Draw(canvas).rounded_rectangle((x0, y0 + (1 - a) * 18, x0 + im.width, y0 + im.height + (1 - a) * 18), radius, outline=mix(border, a), width=2)

LOGO = None
ICON = None
def brand():
    global LOGO, ICON
    if LOGO is None:
        LOGO = logo_rgba("image2.png")
        ICON = logo_rgba("image7.png", recolor_dark=False)

def circle_crop(key, name, d):
    k = ("circ", key, d)
    if k in _img: return _img[k]
    im = load(name)
    s = max(d / im.width, d / im.height)
    im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS)
    l = (im.width - d) // 2; tp = max(0, (im.height - d) // 2 - int(d * 0.04))
    im = im.crop((l, tp, l + d, tp + d))
    m = Image.new("L", (d, d), 0); ImageDraw.Draw(m).ellipse((0, 0, d - 1, d - 1), fill=255)
    im.putalpha(m)
    _img[k] = im
    return im

# ---------------------------------------------------------------- scenes
def s_intro(c, d, t, D):
    brand()
    bg = fitted("bgnet", "image9.png", (W, H), "cover", 0)
    paste(c, bg, (0, 0), 0.55 * prog(t, 0, 1.5))
    d = ImageDraw.Draw(c)
    lg = fitted("logo", None, (620, 181), "contain", 0, src=LOGO)
    paste(c, lg, (W // 2, 270), prog(t, 0.6, 1.4), anchor="mm")
    text(d, (W // 2, 420), "High-speed & high-power InP laser chips", 30, WHITE, prog(t, 2.0, 1.2), anchor="mm")
    text(d, (W // 2, 462), "for AI  ·  Data Center  ·  Coherent Optics", 24, CYAN, prog(t, 2.6, 1.2), anchor="mm")
    text(d, (W // 2, 540), "Company introduction  ·  2026", 18, MUTED, prog(t, 3.4, 1.2), anchor="mm")

def s_whynow(c, d, t, D):
    heading(d, t, "Why now", "AI is driving an optical bandwidth race")
    rows = [("400G", 4, 100, MUTED), ("800G", 8, 100, CYAN), ("1.6T", 8, 200, PINK)]
    for i, (nm, n, lane, col) in enumerate(rows):
        a = prog(t, 1.0 + i * 2.2)
        y = 200 + i * 100
        text(d, (90, y + 12), nm, 40, col, a, bold=True)
        text(d, (90, y + 58), f"{n} × {lane}G lanes", 17, MUTED, a)
        for k in range(n):
            ak = prog(t, 1.3 + i * 2.2 + k * 0.12, 0.5)
            x = 290 + k * 62; w = 52 if lane == 100 else 52
            hgt = 30 if lane == 100 else 60
            if ak > 0:
                d.rounded_rectangle((x, y + 45 - hgt / 2 * ak, x + w, y + 45 + hgt / 2 * ak), 6, fill=mix(col, ak))
    text(d, (290, 505), "bar height = speed per lane", 15, MUTED, prog(t, 3.0))
    # right-hand callouts
    pts = [("Every lane needs a laser.", "200G/lane is driving demand for faster EML chips.", PINK, 7.5),
           ("Few suppliers.", "High-end InP laser chips come from only a handful of makers worldwide.", GOLD, 10.5),
           ("New architectures.", "Co-packaged optics (CPO) needs high-power CW lasers.", CYAN, 13.5)]
    for j, (h, s, col, ts) in enumerate(pts):
        a = prog(t, ts)
        y = 190 + j * 118
        rrect(d, (830, y, 1210, y + 100), PANEL, a, outline=col)
        text(d, (852, y + 14), h, 22, col, a, bold=True)
        para(d, (852, y + 46), s, 16, 340, WHITE, a, lh=21)

def s_about(c, d, t, D):
    heading(d, t, "About Zetta", "Japanese expertise, built in Hangzhou")
    photo(c, "bld", "image15.jpeg", (70, 170, 560, 498), prog(t, 0.8, 1.0), border=BLUE)
    d = ImageDraw.Draw(c)
    stats = [("2021", "Founded in Hangzhou", PINK), ("58", "People on the team", CYAN),
             ("25+", "in R&D", GOLD), ("30+ yrs", "Founders' laser-chip experience", GREEN)]
    for i, (big, small, col) in enumerate(stats):
        a = prog(t, 2.0 + i * 1.6)
        x = 620 + (i % 2) * 300; y = 165 + (i // 2) * 120
        text(d, (x, y), big, 52, col, a, bold=True)
        para(d, (x, y + 70), small, 19, 260, WHITE, a, lh=24)
    photo(c, "grp", "image16.jpeg", (620, 420, 1000, 590), prog(t, 8.5, 1.0), border=PINK)
    d = ImageDraw.Draw(c)
    text(d, (1016, 575), "Team Zetta", 15, MUTED, prog(t, 9.0))

TEAM = [
    ("木村有", "CEO", "image13", ["30+ years in semiconductor lasers",
      "Led one of the few teams worldwide able to design, make", "and mass-produce EML chips for 400G modules",
      "Former GM, optoelectronics at Neo Japan; OKI", "M.S. EE Princeton · B.S. Applied Physics, U. Tokyo"], PINK),
    ("堀川英明", "CTO / Epitaxy", "image11.jpeg", ["Former head of InP epitaxy R&D, NeoPhotonics",
      "Former GM, OKI optical division", "B.S. Physics, Kyoto University"], CYAN),
    ("和田浩", "Chip Design", "image12.jpeg", ["~20 years in high-speed InP optical devices",
      "Former R&D lead for InP devices at OKI", "B.S. Applied Physics, U. Tokyo · UCSB visiting scholar"], GOLD),
    ("角谷昌纪", "Process & Equipment", "image10.jpeg", ["Former head of wafer process, NeoPhotonics",
      "High-speed III-V wafer process R&D at OKI", "B.S. EE, Osaka University"], GREEN),
]
def s_team(c, d, t, D):
    heading(d, t, "Leadership", "A founding team from Japan's laser industry")
    for i, (nm, role, img, lines, col) in enumerate(TEAM):
        a = prog(t, 1.0 + i * 1.5)
        x = 70 + (i % 2) * 575; y = 160 + (i // 2) * 190
        rrect(d, (x, y + (1 - a) * 18, x + 555, y + 175 + (1 - a) * 18), PANEL, a, outline=col)
        cx, cy = x + 70, y + 88
        if img.endswith(".jpeg"):
            paste(c, circle_crop(img, img, 104), (cx, cy), a, anchor="mm")
            d = ImageDraw.Draw(c)
        else:
            if a > 0:
                d.ellipse((cx - 52, cy - 52 + (1 - a) * 18, cx + 52, cy + 52 + (1 - a) * 18), fill=mix(col, a * 0.9))
            text(d, (cx, cy - 2), nm[:2], 34, BG1, a, anchor="mm", cjk=True)
        d.ellipse((cx - 53, cy - 53 + (1 - a) * 18, cx + 53, cy + 53 + (1 - a) * 18), outline=mix(col, a), width=3) if a > 0 else None
        text(d, (x + 140, y + 16), nm, 26, WHITE, a, cjk=True)
        text(d, (x + 140 + font(26, cjk=True).getlength(nm) + 14, y + 22), role, 18, col, a, bold=True)
        for j, ln in enumerate(lines):
            text(d, (x + 140, y + 56 + j * 22), ln, 14, WHITE if j == 0 else MUTED, a)

MILES = [("2001–19", "Team heritage", "40G EML (2001) · 25G EML (2012)\nSOA (2017) · 50G EML (2019)", MUTED),
         ("2021.8", "Founded", "Zetta established\nin Hangzhou", PINK),
         ("2023.5", "Fab online", "Full process: epi → FE → BE\n2 × MOCVD", CYAN),
         ("2024.9", "100G EML", "CWDM4 released\nhermetic chip EML", BLUE),
         ("2024.10", "Gain chip & SOA", "Released; passed Tier-1\nqualification & won PO", GOLD),
         ("2026", "Next wave", "25G LWDM4 · 100mW CW\n200G EML", GREEN)]
def s_milestones(c, d, t, D):
    heading(d, t, "Milestones", "From decades of know-how to volume orders")
    y = 360; x0, x1 = 160, 1120
    d.line([(x0, y), (x0 + (x1 - x0) * prog(t, 0.6, 3.0), y)], fill=MUTED, width=3)
    n = len(MILES)
    for i, (dt, h, s, col) in enumerate(MILES):
        a = prog(t, 1.2 + i * 2.2)
        x = x0 + i * (x1 - x0) / (n - 1)
        up = i % 2 == 0
        if a > 0:
            r = 10 * a; d.ellipse((x - r, y - r, x + r, y + r), fill=mix(col, a))
            d.line([(x, y + (-14 if up else 14)), (x, y + (-44 if up else 44))], fill=mix(col, a), width=2)
        ty = 186 if up else 420
        text(d, (x, ty), dt, 24, col, a, bold=True, anchor="ma")
        text(d, (x, ty + 34), h, 18, WHITE, a, bold=True, anchor="ma")
        for j, ln in enumerate(s.split("\n")):
            text(d, (x, ty + 62 + j * 20), ln, 14, MUTED, a, anchor="ma")

FAB = [("image14.jpeg", "Epitaxy", "2 × MOCVD · 3\" InP", CYAN),
       ("image35.jpeg", "Front-end", "Litho · CVD · Etching", PINK),
       ("image38.jpeg", "Back-end", "Cleave · AR coating", GOLD),
       ("image43.png", "Test", "Chip & wafer test", GREEN)]
def s_fab(c, d, t, D):
    heading(d, t, "Our fab", "Every step in-house, under one roof")
    for i, (img, h, s, col) in enumerate(FAB):
        a = prog(t, 1.0 + i * 1.6)
        x = 70 + i * 290
        photo(c, "fab" + img, img, (x, 165, x + 270, 395), a, border=col)
        d = ImageDraw.Draw(c)
        text(d, (x + 4, 410), f"0{i + 1}  {h}", 22, col, a, bold=True)
        text(d, (x + 4, 442), s, 16, MUTED, a)
        if i < 3 and a > 0.5:
            d.polygon([(x + 276, 272), (x + 286, 280), (x + 276, 288)], fill=MUTED)
    facts = [("2,300 m²", "Class 100/1000 cleanroom"), ("ISO 9001", "Quality system certified (2024)"),
             ("JP / EU", "Key tools from Japan & Europe"), ("~6 months", "R&D lead time for a new chip")]
    for i, (big, small) in enumerate(facts):
        a = prog(t, 8.0 + i * 1.2)
        x = 70 + i * 290
        text(d, (x, 500), big, 30, WHITE, a, bold=True)
        text(d, (x, 542), small, 16, MUTED, a)

def s_tech(c, d, t, D):
    heading(d, t, "Core technology", "Precision where it matters")
    cols = [("Wavelength control", "image51.png",
             ["Highly uniform MOCVD epitaxy, 12 × 3\" wafers per run",
              "PL std. dev. 0.12 nm (25G DML) · 1.14 nm (50G EML)"], CYAN),
            ("Grating & butt-joint EML", "image53.jpeg",
             ["~200 nm-pitch gratings by e-beam writing",
              "Stable multi-step regrowth joins laser and modulator"], PINK),
            ("Back-end & reliability", "image50.jpg",
             ["AR coating reflectivity < 0.1% for better RF yield",
              "Hermetic chip technology for non-hermetic packages"], GOLD)]
    for i, (h, img, lines, col) in enumerate(cols):
        a = prog(t, 1.0 + i * 3.0)
        x = 70 + i * 390
        rrect(d, (x, 160 + (1 - a) * 18, x + 370, 590 + (1 - a) * 18), PANEL, a, outline=col)
        photo(c, "tech" + img, img, (x + 16, 176, x + 354, 372), a, mode="cover", radius=10)
        d = ImageDraw.Draw(c)
        text(d, (x + 20, 392), h, 22, col, a, bold=True)
        for j, ln in enumerate(lines):
            para(d, (x + 20, 436 + j * 66), "•  " + ln, 16, 330, WHITE, a, lh=22)

PRODUCTS = [("100G / 200G PAM4 EML", "Data center & AI transceivers", "100G now · 200G 2026", PINK),
            ("CW-DFB 100 mW", "Silicon photonics light source", "2026", CYAN),
            ("C/L-band SOA & Gain Chip", "Coherent optics for DCI", "Available", GOLD),
            ("High-power DFB 400 mW", "Co-packaged optics (CPO)", "2026 plan", GREEN),
            ("100G / 200G EML + SOA", "Very-high-speed PON, telecom ER4, 6G backbone", "2026 plan", BLUE)]
def s_products(c, d, t, D):
    heading(d, t, "Products", "High-speed and high-power laser chips")
    photo(c, "chip", "image32.jpg", (70, 165, 450, 486), prog(t, 0.8, 1.0), mode="cover", border=PINK)
    d = ImageDraw.Draw(c)
    text(d, (260, 506), "Zetta EML chip", 16, MUTED, prog(t, 1.2), anchor="ma")
    for i, (h, s, st, col) in enumerate(PRODUCTS):
        a = prog(t, 2.0 + i * 1.8)
        y = 160 + i * 82
        rrect(d, (490, y + (1 - a) * 18, 1210, y + 70 + (1 - a) * 18), PANEL, a)
        if a > 0: d.rectangle((490, y + 10 + (1 - a) * 18, 496, y + 60 + (1 - a) * 18), fill=mix(col, a))
        text(d, (516, y + 10), h, 22, WHITE, a, bold=True)
        text(d, (516, y + 42), s, 16, MUTED, a)
        tw = font(15, True).getlength(st) + 24
        rrect(d, (1190 - tw, y + 20 + (1 - a) * 18, 1190, y + 50 + (1 - a) * 18), col, a * 0.25, r=15)
        text(d, (1190 - tw / 2, y + 27), st, 15, col, a, bold=True, anchor="ma")

def s_perf(c, d, t, D):
    heading(d, t, "Performance", "Measured results")
    cards = [("100G EML (CWDM4)", [("55 GHz", "typ. bandwidth"), ("≥ 35 dB", "SMSR"), ("10 mW", "typ. output")], PINK, None),
             ("200G PAM4 EML", [("62 GHz", "bandwidth"), ("C0–C3", "4 wavelengths")], CYAN, "image62.png"),
             ("L-band SOA", [("~21 dBm", "output power"), ("4 dBm", "input · 45 °C")], GOLD, "image75.png")]
    for i, (h, kv, col, img) in enumerate(cards):
        a = prog(t, 1.0 + i * 3.0)
        x = 70 + i * 390
        rrect(d, (x, 160 + (1 - a) * 18, x + 370, 590 + (1 - a) * 18), PANEL, a, outline=col)
        text(d, (x + 20, 178), h, 22, col, a, bold=True)
        if img:
            photo(c, "perf" + img, img, (x + 16, 220, x + 354, 420), a, mode="contain", radius=8)
            d = ImageDraw.Draw(c)
            for j, (big, small) in enumerate(kv):
                text(d, (x + 20 + j * 175, 450), big, 30, WHITE, a, bold=True)
                text(d, (x + 20 + j * 175, 492), small, 15, MUTED, a)
        else:
            for j, (big, small) in enumerate(kv):
                text(d, (x + 20, 230 + j * 110), big, 44, WHITE, a, bold=True)
                text(d, (x + 20, 286 + j * 110), small, 16, MUTED, a)
        if i == 0:
            text(d, (x + 20, 560), "1271 / 1291 / 1311 / 1331 nm", 14, MUTED, a)
    text(d, (W - 70, 604), "Data from Zetta test reports, 2026", 13, MUTED, prog(t, 9.0), anchor="ra")

def s_apps(c, d, t, D):
    heading(d, t, "Applications", "Inside and between AI data centers")
    # two DC boxes linked by DCI
    for k, x in enumerate((130, 700)):
        a = prog(t, 1.0 + k * 0.6)
        rrect(d, (x, 250, x + 450, 540), PANEL, a, outline=MUTED)
        text(d, (x + 225, 268), "AI data center", 18, WHITE, a, bold=True, anchor="ma")
        for r in range(3):
            for q in range(6):
                aa = prog(t, 1.5 + k * 0.6 + (r * 6 + q) * 0.03, 0.4)
                if aa > 0:
                    xx = x + 30 + q * 68; yy = 320 + r * 60
                    d.rounded_rectangle((xx, yy, xx + 52, yy + 36), 5, fill=mix((50, 70, 120), aa))
                    if r == 2:
                        text(d, (xx + 26, yy + 18), "GPU", 12, WHITE, aa, bold=True, anchor="mm")
        # mesh lines
        la = prog(t, 3.0 + k * 0.4)
        if la > 0:
            for q in range(6):
                for q2 in range(6):
                    if abs(q - q2) <= 1:
                        d.line([(x + 56 + q * 68, 356), (x + 56 + q2 * 68, 380)], fill=mix(PINK, la * 0.7), width=2)
                        d.line([(x + 56 + q * 68, 416), (x + 56 + q2 * 68, 440)], fill=mix(PINK, la * 0.7), width=2)
    la = prog(t, 5.0, 1.5)
    if la > 0:
        pts = [(355 + (925 - 355) * u, 250 - 70 * math.sin(math.pi * u)) for u in np.linspace(0, la, 40)]
        d.line(pts, fill=CYAN, width=5)
    labels = [("Coherent DCI", "SOA · Gain chip", CYAN, (640, 196), 6.0),
              ("DC & AI links", "100G / 200G EML", PINK, (355, 560), 8.5),
              ("Silicon photonics · CPO", "CW-DFB 100 mW · 400 mW", GREEN, (925, 560), 11.0)]
    for h, s, col, (x, y), ts in labels:
        a = prog(t, ts)
        text(d, (x, y), h, 20, col, a, bold=True, anchor="ma")
        text(d, (x, y + 28), s, 16, WHITE, a, anchor="ma")

def s_why(c, d, t, D):
    heading(d, t, "Why Zetta", "What sets us apart")
    pts = [("Japan + China", "Japanese know-how and experience, combined with China's talent, fab capacity and market.", PINK),
           ("Full in-house IDM", "Epi, front-end, back-end and test under one roof — we control quality, cost and lead time.", CYAN),
           ("Speed to market", "About 6 months from design to a new product sample.", GOLD),
           ("Proven with Tier-1", "Qualified by a Tier-1 customer, with production orders won.", GREEN)]
    for i, (h, s, col) in enumerate(pts):
        a = prog(t, 1.0 + i * 2.5)
        x = 70 + (i % 2) * 575; y = 170 + (i // 2) * 200
        rrect(d, (x, y + (1 - a) * 18, x + 555, y + 175 + (1 - a) * 18), PANEL, a, outline=col)
        text(d, (x + 28, y + 24), h, 28, col, a, bold=True)
        para(d, (x + 28, y + 76), s, 19, 500, WHITE, a, lh=27)

def s_partner(c, d, t, D):
    heading(d, t, "Partner with us", "Flexible ways to work together")
    items = [("Bare die / CoC", "Standard chips, ready for your packages", PINK),
             ("Epi cooperation", "Help you build in-house chip capability", CYAN),
             ("Strategic co-design", "New chips for new applications", GOLD),
             ("Custom InP design", "Tailored laser chips on our platform", GREEN)]
    for i, (h, s, col) in enumerate(items):
        a = prog(t, 1.0 + i * 1.6)
        x = 70 + i * 290
        rrect(d, (x, 180 + (1 - a) * 18, x + 270, 400 + (1 - a) * 18), PANEL, a, outline=col)
        if a > 0:
            d.ellipse((x + 24, 204 + (1 - a) * 18, x + 72, 252 + (1 - a) * 18), fill=mix(col, a))
        text(d, (x + 48, 228), str(i + 1), 24, BG1, a, bold=True, anchor="mm")
        text(d, (x + 24, 276), h, 22, WHITE, a, bold=True)
        para(d, (x + 24, 314), s, 16, 225, MUTED, a, lh=22)
    text(d, (W // 2, 480), "Your partner for AI · Data Center · Coherent DCI", 30, WHITE, prog(t, 8.5, 1.0), bold=True, anchor="mm")

def s_outro(c, d, t, D):
    brand()
    bg = fitted("bgnet", "image9.png", (W, H), "cover", 0)
    paste(c, bg, (0, 0), 0.45)
    d = ImageDraw.Draw(c)
    lg = fitted("logo", None, (620, 181), "contain", 0, src=LOGO)
    paste(c, lg, (W // 2, 290), prog(t, 0.3, 1.2), anchor="mm")
    text(d, (W // 2, 430), "Lighting up AI infrastructure", 30, WHITE, prog(t, 1.2), anchor="mm")
    text(d, (W // 2, 480), "Hangzhou, China", 20, MUTED, prog(t, 1.8), anchor="mm")

SCENES = [
    (s_intro, 10, ["Meet Zetta Semiconductor.",
                   "We design and manufacture high-speed and high-power laser chips for AI, data centers and coherent optics."]),
    (s_whynow, 18, ["AI clusters link thousands of GPUs with light. Optical modules are moving from 800G to 1.6T.",
                    "That means faster lanes — 200G each — and every lane needs a high-performance laser, typically an EML.",
                    "But few companies can make these InP chips, and co-packaged optics needs new high-power lasers."]),
    (s_about, 14, ["Zetta was founded in Hangzhou in 2021 by a team of Japanese laser-chip veterans.",
                   "Today we are 58 people — more than 25 in R&D — running our own InP chip fab."]),
    (s_team, 20, ["Our leaders bring more than 30 years of experience from OKI, NeoPhotonics and Japan's laser industry.",
                  "CEO 木村有 led one of the few teams worldwide that designed and mass-produced EML chips for 400G modules.",
                  "Together, the team covers epitaxy, chip design, and wafer process — the whole chain."]),
    (s_milestones, 20, ["This team shipped 40G EMLs in 2001, and 25G and 50G generations after that.",
                        "Zetta was founded in 2021, and our fab came online in 2023.",
                        "In 2024 we released 100G EML, gain chips and SOAs, passed Tier-1 qualification and won orders.",
                        "Next: 25G LWDM4, 100 mW CW lasers and 200G EML in 2026."]),
    (s_fab, 20, ["We control every step in-house: epitaxy, front-end, back-end and test.",
                 "Two MOCVD reactors on 3-inch InP, with key equipment from Japan and Europe.",
                 "A 2,300 m² class 100/1000 cleanroom, ISO 9001 certified — and about 6 months to develop a new chip."]),
    (s_tech, 20, ["Precise wavelength control starts with highly uniform epitaxy.",
                  "E-beam gratings and stable butt-joint regrowth combine the laser and modulator on one EML chip.",
                  "Ultra-low-reflection AR coating and hermetic chip technology improve yield and reliability."]),
    (s_products, 20, ["Our portfolio covers high-speed and high-power laser chips.",
                      "100G and 200G PAM4 EMLs for AI and data center links, and 100 mW CW lasers for silicon photonics.",
                      "C and L-band SOAs and gain chips for coherent optics, and 400 mW lasers for co-packaged optics next."]),
    (s_perf, 18, ["Our 100G EML reaches 55 GHz of bandwidth across all four CWDM4 lanes.",
                  "Our 200G PAM4 EML reaches 62 GHz of bandwidth — built for 1.6T modules.",
                  "Our L-band SOA delivers about 21 dBm of output power at 45 °C."]),
    (s_apps, 16, ["Zetta chips work inside AI data centers and on the links between them.",
                  "EMLs for DC and AI links, SOAs and gain chips for coherent DCI, CW lasers for silicon photonics and CPO."]),
    (s_why, 18, ["Why Zetta? Japanese know-how combined with China's talent, scale and market.",
                 "A full in-house IDM — so we control quality, cost and lead time.",
                 "Fast development, and proven with Tier-1 customers."]),
    (s_partner, 16, ["Work with us your way: bare die or chip-on-carrier, epi cooperation, co-design, or custom InP chips.",
                     "Zetta — your partner for AI, data center and coherent optics."]),
    (s_outro, 8, ["Zetta Semiconductor. Thank you."]),
]

def caption(img, s, ca):
    if not s or ca <= 0: return img
    lines = []
    for part in [s]:
        lines += wrap_cjk(part, 22, 1060)
    lh = 30; hbox = len(lines) * lh + 20; y0 = H - 22 - hbox
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    od.rounded_rectangle((90, y0, W - 90, y0 + hbox), 12, fill=(4, 8, 22, int(200 * ca)))
    for j, ln in enumerate(lines):
        od.text((W // 2, y0 + 10 + j * lh + lh // 2), ln, font=font(22, cjk=has_cjk(ln)), fill=(240, 244, 250, int(255 * ca)), anchor="mm")
    return Image.alpha_composite(img.convert("RGBA"), ov)

def has_cjk(s):
    return any("぀" <= ch <= "鿿" for ch in s)

def wrap_cjk(s, size, maxw):
    f = font(size, cjk=has_cjk(s)); lines = []; cur = ""
    for w in s.split():
        trial = (cur + " " + w).strip()
        if f.getlength(trial) <= maxw: cur = trial
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def frame(fn, dur, caps, t, with_caption=True):
    img = Image.fromarray(BG.copy()).convert("RGBA")
    d = ImageDraw.Draw(img)
    fn(img, d, t, dur)
    if with_caption:
        seg = dur / len(caps); ci = min(int(t // seg), len(caps) - 1); lt = t - ci * seg
        ca = min(1, lt / 0.35, (seg - lt) / 0.35 if len(caps) > 1 else 1)
        img = caption(img, caps[ci], max(0, ca))
    arr = np.asarray(img.convert("RGB"))
    f = min(1, t / 0.5, (dur - t) / 0.5)
    if f < 1:
        arr = (BG.astype(np.float32) * (1 - f) + arr.astype(np.float32) * f).astype(np.uint8)
    return arr

def render():
    cmd = [FFMPEG, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", os.path.join(HERE, "zetta_music.wav"), "-c:v", "libx264", "-preset", "medium", "-crf", "19",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    for idx, (fn, dur, caps) in enumerate(SCENES):
        for k in range(dur * FPS):
            p.stdin.write(frame(fn, dur, caps, k / FPS).tobytes())
        print(f"scene {idx + 1}/{len(SCENES)} done", flush=True)
    p.stdin.close(); p.wait()
    print("wrote", OUT, "seconds", sum(s[1] for s in SCENES))

# ---------------------------------------------------------------- music
def music(total, path, sr=44100):
    n = int(total * sr); out = np.zeros((n, 2), np.float32)
    ts = np.arange(n) / sr
    def midi(m): return 440 * 2 ** ((m - 69) / 12)
    chords = [[52, 59, 64, 67], [48, 55, 60, 64], [55, 62, 67, 71], [50, 57, 62, 66]]   # Em  C  G  D (add9-ish voicing)
    bar = 3.2   # 75 bpm, 4 beats
    for b in range(int(total / bar) + 1):
        ch = chords[b % 4]; s0 = int(b * bar * sr); s1 = min(n, int((b + 1) * bar * sr + 0.8 * sr))
        if s0 >= n: break
        seg = np.arange(s1 - s0) / sr; L = len(seg) / sr
        env = np.minimum(1, seg / 0.9) * np.minimum(1, (L - seg) / 0.9)
        for m in ch + [ch[0] - 12]:
            f0 = midi(m)
            for det, pan in ((-0.2, 0.25), (0.2, 0.75)):
                w = np.sin(2 * np.pi * (f0 + det) * seg) + 0.2 * np.sin(2 * np.pi * 2 * (f0 + det) * seg + 0.3)
                out[s0:s1, 0] += 0.016 * env * w * (1 - pan)
                out[s0:s1, 1] += 0.016 * env * w * pan
    step = bar / 16
    pat = [0, 2, 3, 1, 2, 3, 0, 3, 1, 2, 3, 2, 0, 3, 2, 1]
    for i in range(int(total / step)):
        st = i * step
        if st < 4 or st > total - 5: continue
        ch = chords[int(st // bar) % 4]
        f0 = midi(ch[pat[i % 16]] + 12); s0 = int(st * sr); s1 = min(n, s0 + int(0.7 * sr))
        seg = np.arange(s1 - s0) / sr
        env = np.exp(-seg * 6) * np.minimum(1, seg / 0.004)
        w = np.sin(2 * np.pi * f0 * seg) + 0.35 * np.sin(2 * np.pi * 3 * f0 * seg) * np.exp(-seg * 10)
        pan = 0.3 + 0.4 * ((i % 5) / 4)
        g = 0.04 if i % 4 == 0 else 0.03
        out[s0:s1, 0] += g * env * w * (1 - pan); out[s0:s1, 1] += g * env * w * pan
    beat = bar / 4
    for i in range(int(total / beat)):
        st = i * beat
        if st < 10 or st > total - 8: continue
        s0 = int(st * sr); s1 = min(n, s0 + int(0.35 * sr)); seg = np.arange(s1 - s0) / sr
        fsw = 85 * np.exp(-seg * 18) + 45
        kick = np.sin(2 * np.pi * np.cumsum(fsw) / sr) * np.exp(-seg * 12)
        out[s0:s1] += 0.09 * kick[:, None] * (1.0 if i % 2 == 0 else 0.5)
        f0 = midi(chords[int(st // bar) % 4][0] - 12)
        out[s0:s1] += 0.05 * (np.sin(2 * np.pi * f0 * seg) * np.exp(-seg * 4))[:, None]
        # soft hat on off-beats
        hs0 = int((st + beat / 2) * sr); hs1 = min(n, hs0 + int(0.05 * sr))
        if hs1 > hs0:
            hseg = np.arange(hs1 - hs0) / sr
            out[hs0:hs1] += 0.012 * (np.random.randn(hs1 - hs0) * np.exp(-hseg * 80))[:, None]
    dl = int(0.28 * sr)
    out[dl:, 0] += 0.25 * out[:-dl, 1]; out[dl:, 1] += 0.25 * out[:-dl, 0]
    out *= np.minimum(1, np.minimum(ts / 2.5, (total - ts) / 4.0))[:, None]
    out /= max(1e-6, np.abs(out).max()) / 0.8
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes((out * 32767).astype(np.int16).tobytes())

if __name__ == "__main__":
    np.random.seed(7)
    total = sum(s[1] for s in SCENES)
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        ims = []
        for idx, (fn, dur, caps) in enumerate(SCENES):
            ims.append(Image.fromarray(frame(fn, dur, caps, dur - 1.2)).resize((640, 360)))
        sheet = Image.new("RGB", (1920, 360 * math.ceil(len(ims) / 3)))
        for i, im in enumerate(ims): sheet.paste(im, ((i % 3) * 640, (i // 3) * 360))
        sheet.save(os.path.join(HERE, "zetta_preview.png"))
        for i in [int(a) for a in sys.argv[2:]]:
            fn, dur, caps = SCENES[i]
            Image.fromarray(frame(fn, dur, caps, dur - 1.2)).save(os.path.join(HERE, f"zp_{i:02d}.png"))
        print("total seconds", total)
    else:
        music(total, os.path.join(HERE, "zetta_music.wav"))
        render()
