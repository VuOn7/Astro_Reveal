"""
astro_charts.py
===============
Drawings for Astro_Reveal, returned as SVG / HTML strings:

- natal_wheel_svg     the engraved zodiac wheel (Western chart)
- south_indian_svg    the Vedic rasi chart in the South Indian square layout
- pillars_html        the Chinese Four Pillars with their characters
- tzolkin_svg         the Maya bar-and-dot tone and the 260-day count
- big_three_html      Sun, Moon and Rising at a glance

Pure Python, no Streamlit, so every drawing can be previewed and tested alone.
"""

import math
from html import escape

# ---------------------------------------------------------------------------
# palette (keep in sync with .streamlit/config.toml)
# ---------------------------------------------------------------------------
LAPIS = "#0F1B36"
ENAMEL = "#17264A"
RULE = "#2C3D66"
IVORY = "#ECE5D2"
MUTED = "#9AA5C0"
BRASS = "#D4A94F"
VERDIGRIS = "#62B8A6"

GLYPH_FONT = "astroglyphs, 'Noto Sans Symbols', 'Segoe UI Symbol', 'Apple Symbols', 'DejaVu Sans', sans-serif"
TEXT_FONT = "instrument, 'Instrument Sans', system-ui, sans-serif"
SERIF_FONT = "imfell, 'IM Fell English', Georgia, serif"

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
VS = "︎"   # ask for the plain text form of a symbol, not an emoji
SIGN_GLYPHS = [chr(0x2648 + i) + VS for i in range(12)]
PLANET_GLYPHS = {
    "Sun": "☉", "Moon": "☽", "Mercury": "☿", "Venus": "♀",
    "Mars": "♂", "Jupiter": "♃", "Saturn": "♄", "Uranus": "♅",
    "Neptune": "♆", "Rahu": "☊", "Ketu": "☋",
}
PLANET_GLYPHS = {k: v + VS for k, v in PLANET_GLYPHS.items()}

ASPECTS = [  # name, angle, orb, harmonious?
    ("conjunction", 0, 8, None),
    ("sextile", 60, 5, True),
    ("square", 90, 7, False),
    ("trine", 120, 7, True),
    ("opposition", 180, 8, False),
]
ASPECT_BODIES = ["Sun", "Moon", "Mercury", "Venus", "Mars",
                 "Jupiter", "Saturn", "Uranus", "Neptune"]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def fmt_deg(d):
    """Degrees within a sign as 12°30′."""
    d = d % 30
    whole = int(d)
    minutes = int(round((d - whole) * 60))
    if minutes == 60:
        whole, minutes = whole + 1, 0
    return f"{whole}°{minutes:02d}′"


def sign_index(lon):
    return int((lon % 360) // 30)


def _sep(a, b):
    return abs((a - b + 180) % 360 - 180)


def find_aspects(positions):
    """Major aspects between the planets: list of (a, b, name, orb, harmonious)."""
    bodies = [b for b in ASPECT_BODIES if b in positions]
    found = []
    for i, a in enumerate(bodies):
        for b in bodies[i + 1:]:
            d = _sep(positions[a], positions[b])
            for name, angle, orb, harmonious in ASPECTS:
                if abs(d - angle) <= orb:
                    found.append((a, b, name, abs(d - angle), harmonious))
                    break
    return found


def house_of(lon, cusps):
    """House number (1-12) a longitude falls in, given cusps {'1': lon, ...}."""
    for h in range(1, 13):
        start = cusps[str(h)]
        end = cusps[str(h % 12 + 1)]
        if (lon - start) % 360 < (end - start) % 360:
            return h
    return 1


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def _spread(angles, min_sep):
    """Push apart angles (degrees) that are closer than min_sep, keeping order."""
    n = len(angles)
    if n < 2:
        return list(angles)
    order = sorted(range(n), key=lambda i: angles[i] % 360)
    pos = [angles[i] % 360 for i in order]
    for _ in range(400):
        moved = False
        for k in range(n):
            j = (k + 1) % n
            gap = (pos[j] - pos[k]) % 360
            if gap < min_sep - 1e-6:
                push = (min_sep - gap) / 2 + 0.01
                pos[k] -= push
                pos[j] += push
                moved = True
        if not moved:
            break
    out = [0.0] * n
    for k, i in enumerate(order):
        out[i] = pos[k]
    return out


# ---------------------------------------------------------------------------
# the natal wheel
# ---------------------------------------------------------------------------
def natal_wheel_svg(positions, cusps=None, asc=None, mc=None, retrograde=(),
                    title="Birth chart"):
    """Engraved zodiac wheel. With an ascendant it is drawn the Western way
    (Ascendant on the left, signs running anticlockwise); without one,
    0° Aries sits on the left."""
    size, c = 720, 360
    r_out, r_band, r_tick = 340, 290, 290
    r_planet, r_inner = 248, 160
    left = asc if asc is not None else 0.0

    def ang(lon):
        return math.radians(180 + (lon - left))

    def pt(lon, r):
        a = ang(lon)
        return c + r * math.cos(a), c - r * math.sin(a)

    def line(lon, r1, r2, **attrs):
        x1, y1 = pt(lon, r1)
        x2, y2 = pt(lon, r2)
        extra = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
        return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" {extra}/>'

    m = 44   # room for the Asc / MC labels outside the rim
    out = [f'<svg viewBox="{-m} {-m} {size + 2 * m} {size + 2 * m}" xmlns="http://www.w3.org/2000/svg" '
           f'role="img" aria-label="{escape(title)}" class="ar-wheel">',
           f'<title>{escape(title)}</title>']

    # rings
    out.append(f'<circle cx="{c}" cy="{c}" r="{r_out}" fill="{ENAMEL}" stroke="{BRASS}" stroke-width="1.4"/>')
    out.append(f'<circle cx="{c}" cy="{c}" r="{r_band}" fill="{LAPIS}" stroke="{BRASS}" stroke-width="1"/>')
    out.append(f'<circle cx="{c}" cy="{c}" r="{r_inner}" fill="none" stroke="{RULE}" stroke-width="1"/>')
    out.append(f'<circle cx="{c}" cy="{c}" r="{r_out + 8}" fill="none" stroke="{BRASS}" '
               f'stroke-opacity="0.35" stroke-width="0.8"/>')

    # degree scale: every degree, longer at 5 and 10 (the engraved limb)
    ticks = []
    for d in range(360):
        length = 13 if d % 10 == 0 else (8 if d % 5 == 0 else 4)
        ticks.append(line(d, r_tick, r_tick + length))
    out.append(f'<g stroke="{BRASS}" stroke-width="0.8" stroke-opacity="0.75">{"".join(ticks)}</g>')

    # sign boundaries and glyphs
    for i in range(12):
        out.append(line(i * 30, r_band, r_out, stroke=BRASS, stroke_width="1.1"))
        x, y = pt(i * 30 + 15, (r_band + 14 + r_out) / 2)
        out.append(f'<text x="{x:.1f}" y="{y:.1f}" fill="{BRASS}" font-size="27" '
                   f'font-family="{GLYPH_FONT}" text-anchor="middle" dominant-baseline="central">'
                   f'<title>{SIGNS[i]}</title>{SIGN_GLYPHS[i]}</text>')

    # houses
    if cusps:
        g = []
        for h in range(1, 13):
            lon = cusps[str(h)]
            if h in (1, 4, 7, 10):
                continue
            g.append(line(lon, r_inner, r_band, stroke=RULE, stroke_width="1"))
        out.append("".join(g))
        for h in range(1, 13):
            a, b = cusps[str(h)], cusps[str(h % 12 + 1)]
            mid = a + ((b - a) % 360) / 2
            x, y = pt(mid, r_inner + 16)
            out.append(f'<text x="{x:.1f}" y="{y:.1f}" fill="{MUTED}" font-size="12" '
                       f'font-family="{TEXT_FONT}" text-anchor="middle" '
                       f'dominant-baseline="central">{h}</text>')

    # angles: Ascendant-Descendant and MC-IC
    if asc is not None:
        out.append(line(asc, r_inner, r_out + 14, stroke=BRASS, stroke_width="1.8"))
        out.append(line(asc + 180, r_inner, r_out + 8, stroke=BRASS, stroke_width="1.2"))
        x, y = pt(asc, r_out + 28)
        out.append(f'<text x="{x:.1f}" y="{y:.1f}" fill="{BRASS}" font-size="15" font-family="{TEXT_FONT}" '
                   f'text-anchor="middle" dominant-baseline="central">Asc</text>')
    if mc is not None:
        out.append(line(mc, r_inner, r_out + 14, stroke=BRASS, stroke_width="1.8"))
        out.append(line(mc + 180, r_inner, r_out + 8, stroke=BRASS, stroke_width="1.2"))
        x, y = pt(mc, r_out + 28)
        out.append(f'<text x="{x:.1f}" y="{y:.1f}" fill="{BRASS}" font-size="15" font-family="{TEXT_FONT}" '
                   f'text-anchor="middle" dominant-baseline="central">MC</text>')

    # aspects in the centre
    for a, b, name, orb, harmonious in find_aspects(positions):
        if harmonious is None:
            continue
        x1, y1 = pt(positions[a], r_inner - 4)
        x2, y2 = pt(positions[b], r_inner - 4)
        colour = VERDIGRIS if harmonious else BRASS
        dash = ' stroke-dasharray="5 4"' if name == "sextile" else ""
        opacity = max(0.35, 0.9 - orb / 10)
        out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{colour}" '
                   f'stroke-width="1.3" stroke-opacity="{opacity:.2f}"{dash}>'
                   f'<title>{a} {name} {b}</title></line>')

    # planets
    names = [n for n in PLANET_GLYPHS if n in positions]
    lons = [positions[n] for n in names]
    screen = [180 + (lon - left) for lon in lons]
    spread = _spread(screen, 8.2)
    for name, lon, s in zip(names, lons, spread):
        shown = s - 180 + left
        # exact-degree mark on the scale, leader to the glyph if it was moved
        out.append(line(lon, r_tick - 9, r_tick, stroke=IVORY, stroke_width="1.6"))
        out.append(line(lon, r_tick - 9, r_planet + 20, stroke=IVORY, stroke_width="0.7", stroke_opacity="0.5")
                   if _sep(lon, shown) < 0.5 else
                   f'<polyline points="{"%.1f,%.1f" % pt(lon, r_tick - 9)} {"%.1f,%.1f" % pt(shown, r_planet + 20)}" '
                   f'fill="none" stroke="{IVORY}" stroke-width="0.7" stroke-opacity="0.5"/>')
        x, y = pt(shown, r_planet)
        big = name in ("Sun", "Moon")
        colour = MUTED if name in ("Rahu", "Ketu") else IVORY
        out.append(f'<text x="{x:.1f}" y="{y:.1f}" fill="{colour}" font-size="{30 if big else 25}" '
                   f'font-family="{GLYPH_FONT}" text-anchor="middle" dominant-baseline="central" '
                   f'stroke="{LAPIS}" stroke-width="5" paint-order="stroke">'
                   f'<title>{name} {fmt_deg(lon)} {SIGNS[sign_index(lon)]}</title>{PLANET_GLYPHS[name]}</text>')
        x, y = pt(shown, r_planet - 30)
        label = fmt_deg(lon).split("°")[0] + "°" + (" Rx" if name in retrograde else "")
        out.append(f'<text x="{x:.1f}" y="{y:.1f}" fill="{MUTED}" font-size="12" font-family="{TEXT_FONT}" '
                   f'text-anchor="middle" dominant-baseline="central" stroke="{LAPIS}" '
                   f'stroke-width="4" paint-order="stroke">{label}</text>')

    out.append("</svg>")
    return "".join(out)


# ---------------------------------------------------------------------------
# Vedic: South Indian rasi chart
# ---------------------------------------------------------------------------
SOUTH_INDIAN_CELLS = {11: (0, 0), 0: (0, 1), 1: (0, 2), 2: (0, 3),
                      10: (1, 0), 3: (1, 3),
                      9: (2, 0), 4: (2, 3),
                      8: (3, 0), 7: (3, 1), 6: (3, 2), 5: (3, 3)}
VEDIC_ABBR = {"Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me", "Jupiter": "Ju",
              "Venus": "Ve", "Saturn": "Sa", "Rahu": "Ra", "Ketu": "Ke"}
RASI = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
        "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena"]


def south_indian_svg(sidereal, lagna=None, ayanamsa=None):
    cell, pad = 118, 2
    size = cell * 4 + pad * 2
    out = [f'<svg viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg" role="img" '
           f'aria-label="Vedic rasi chart, South Indian style" class="ar-rasi">',
           f'<rect x="{pad}" y="{pad}" width="{cell * 4}" height="{cell * 4}" fill="{ENAMEL}" '
           f'stroke="{BRASS}" stroke-width="1.4"/>']
    occupants = {i: [] for i in range(12)}
    for name, abbr in VEDIC_ABBR.items():
        if name in sidereal:
            lon = sidereal[name]
            occupants[sign_index(lon)].append((lon % 30, abbr))
    lagna_sign = sign_index(lagna) if lagna is not None else None

    for sign, (row, col) in SOUTH_INDIAN_CELLS.items():
        x, y = pad + col * cell, pad + row * cell
        out.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="{LAPIS}" '
                   f'stroke="{BRASS}" stroke-opacity="0.7" stroke-width="1"/>')
        out.append(f'<text x="{x + 9}" y="{y + 18}" fill="{MUTED}" font-size="12" '
                   f'font-family="{TEXT_FONT}"><title>{SIGNS[sign]}</title>{RASI[sign]}</text>')
        out.append(f'<text x="{x + cell - 9}" y="{y + 18}" fill="{BRASS}" font-size="15" '
                   f'font-family="{GLYPH_FONT}" text-anchor="end">{SIGN_GLYPHS[sign]}</text>')
        rows = []
        if sign == lagna_sign:
            out.append(f'<line x1="{x + cell - 34}" y1="{y + cell}" x2="{x + cell}" y2="{y + cell - 34}" '
                       f'stroke="{BRASS}" stroke-width="1.6"/>')
            rows.append((lagna % 30, "Asc", BRASS))
        rows += [(d, a, IVORY) for d, a in occupants[sign]]
        rows.sort()
        for k, (deg, label, colour) in enumerate(rows[:8]):
            col_x = x + 12 + (k // 4) * 56
            row_y = y + 42 + (k % 4) * 19
            out.append(f'<text x="{col_x}" y="{row_y}" fill="{colour}" font-size="15" '
                       f'font-family="{TEXT_FONT}">{label} <tspan fill="{MUTED}" font-size="12">'
                       f'{int(deg)}°</tspan></text>')

    cx = cy = pad + cell * 2
    out.append(f'<text x="{cx}" y="{cy - 14}" fill="{IVORY}" font-size="24" font-family="{SERIF_FONT}" '
               f'text-anchor="middle">Rasi chart</text>')
    if lagna_sign is not None:
        out.append(f'<text x="{cx}" y="{cy + 14}" fill="{MUTED}" font-size="13" font-family="{TEXT_FONT}" '
                   f'text-anchor="middle">Lagna in {RASI[lagna_sign]} ({SIGNS[lagna_sign]})</text>')
    if ayanamsa is not None:
        out.append(f'<text x="{cx}" y="{cy + 34}" fill="{MUTED}" font-size="13" font-family="{TEXT_FONT}" '
                   f'text-anchor="middle">Lahiri ayanamsa {int(ayanamsa)}°{int(round((ayanamsa % 1) * 60)):02d}′</text>')
    out.append("</svg>")
    return "".join(out)


# ---------------------------------------------------------------------------
# Chinese Four Pillars
# ---------------------------------------------------------------------------
STEM_HANZI = {"Jia": "甲", "Yi": "乙", "Bing": "丙", "Ding": "丁", "Wu": "戊",
              "Ji": "己", "Geng": "庚", "Xin": "辛", "Ren": "壬", "Gui": "癸"}
BRANCH_HANZI = {"Zi": "子", "Chou": "丑", "Yin": "寅", "Mao": "卯", "Chen": "辰", "Si": "巳",
                "Wu": "午", "Wei": "未", "Shen": "申", "You": "酉", "Xu": "戌", "Hai": "亥"}
BRANCH_ELEMENT = {"Zi": "Water", "Chou": "Earth", "Yin": "Wood", "Mao": "Wood",
                  "Chen": "Earth", "Si": "Fire", "Wu": "Fire", "Wei": "Earth",
                  "Shen": "Metal", "You": "Metal", "Xu": "Earth", "Hai": "Water"}
ELEMENT_COLOURS = {"Wood": "#86B87A", "Fire": "#E8735F", "Earth": "#D9B465",
                   "Metal": "#DDE2EA", "Water": "#73A6E6"}


def pillars_html(pillars, hour_known=True):
    """Hour, Day, Month, Year from left to right, as they are traditionally read."""
    cols = []
    for key in ("hour", "day", "month", "year"):
        (stem, stem_el), (branch, animal) = pillars[key]
        unknown = key == "hour" and not hour_known
        element = stem_el.split()[-1]
        b_element = BRANCH_ELEMENT[branch]
        cls = "ar-pillar ar-daymaster" if key == "day" else "ar-pillar"
        if unknown:
            cols.append(f'<div class="{cls} ar-unknown"><div class="ar-pillar-name">Hour</div>'
                        f'<div class="ar-hanzi">?</div><div class="ar-pillar-sub">Needs a birth time</div>'
                        f'<div class="ar-hanzi">?</div><div class="ar-pillar-sub">&nbsp;</div></div>')
            continue
        note = "Day Master" if key == "day" else key.title()
        cols.append(
            f'<div class="{cls}"><div class="ar-pillar-name">{note}</div>'
            f'<div class="ar-hanzi" style="color:{ELEMENT_COLOURS[element]}" lang="zh">{STEM_HANZI[stem]}</div>'
            f'<div class="ar-pillar-sub">{stem}, {escape(stem_el)}</div>'
            f'<div class="ar-hanzi" style="color:{ELEMENT_COLOURS[b_element]}" lang="zh">{BRANCH_HANZI[branch]}</div>'
            f'<div class="ar-pillar-sub">{branch}, {escape(animal)}</div></div>')
    return f'<div class="ar-pillars">{"".join(cols)}</div>'


# ---------------------------------------------------------------------------
# Maya Tzolkin
# ---------------------------------------------------------------------------
DAY_SIGNS = ["Imix", "Ik", "Akbal", "Kan", "Chicchan", "Cimi", "Manik", "Lamat", "Muluc", "Oc",
             "Chuen", "Eb", "Ben", "Ix", "Men", "Cib", "Caban", "Etznab", "Cauac", "Ahau"]


def bar_dot_svg(n, scale=1.0):
    """A Maya numeral (1-19): dots on top, bars below."""
    bars, dots = divmod(n, 5)
    w = 84
    h = 22 + bars * 18 + 6
    out = [f'<svg viewBox="0 0 {w} {h}" width="{w * scale:.0f}" height="{h * scale:.0f}" '
           f'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Maya numeral {n}">']
    if dots:
        gap = 18
        start = w / 2 - (dots - 1) * gap / 2
        for i in range(dots):
            out.append(f'<circle cx="{start + i * gap:.1f}" cy="10" r="6.5" fill="{BRASS}"/>')
    for i in range(bars):
        y = (22 if dots else 4) + i * 18
        out.append(f'<rect x="4" y="{y}" width="{w - 8}" height="11" rx="5.5" fill="{BRASS}"/>')
    out.append("</svg>")
    return "".join(out)


def tzolkin_svg(kin):
    """The 260-day count as 13 columns of 20 day signs, with this kin marked."""
    cell, gap, label_w = 15, 3, 70
    w = label_w + 13 * (cell + gap)
    h = 20 * (cell + gap) + 22
    col, row = divmod(kin - 1, 20)
    out = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" role="img" '
           f'aria-label="Tzolkin count, kin {kin} marked" class="ar-tzolkin">']
    for r, name in enumerate(DAY_SIGNS):
        y = 22 + r * (cell + gap)
        colour = BRASS if r == row else MUTED
        out.append(f'<text x="{label_w - 8}" y="{y + cell - 3}" fill="{colour}" font-size="11.5" '
                   f'font-family="{TEXT_FONT}" text-anchor="end">{name}</text>')
        for c in range(13):
            x = label_w + c * (cell + gap)
            k = c * 20 + r + 1
            if k == kin:
                out.append(f'<rect x="{x - 1}" y="{y - 1}" width="{cell + 2}" height="{cell + 2}" rx="3" '
                           f'fill="{BRASS}"><title>Kin {k}</title></rect>')
            else:
                out.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2.5" fill="none" '
                           f'stroke="{RULE}" stroke-width="1"/>')
    for c in range(13):
        x = label_w + c * (cell + gap) + cell / 2
        colour = BRASS if c == col else MUTED
        out.append(f'<text x="{x}" y="12" fill="{colour}" font-size="10" font-family="{TEXT_FONT}" '
                   f'text-anchor="middle">{c * 20 + 1}</text>')
    out.append("</svg>")
    return "".join(out)


# ---------------------------------------------------------------------------
# Sun, Moon, Rising
# ---------------------------------------------------------------------------
def big_three_html(tropical, asc=None, cusps=None):
    rows = []
    items = [("Sun", tropical["Sun"], PLANET_GLYPHS["Sun"]),
             ("Moon", tropical["Moon"], PLANET_GLYPHS["Moon"])]
    if asc is not None:
        items.append(("Rising", asc, "Asc"))
    for name, lon, glyph in items:
        sign = SIGNS[sign_index(lon)]
        where = f"{name} at {fmt_deg(lon)}"
        if cusps and name != "Rising":
            where += f", {ordinal(house_of(lon, cusps))} house"
        glyph_cls = "ar-b3-glyph ar-b3-text" if glyph == "Asc" else "ar-b3-glyph"
        rows.append(f'<div class="ar-b3"><div class="{glyph_cls}">{glyph}</div>'
                    f'<div><div class="ar-b3-sign">{sign} '
                    f'<span class="ar-b3-signglyph">{SIGN_GLYPHS[sign_index(lon)]}</span></div>'
                    f'<div class="ar-b3-where">{where}</div></div></div>')
    if asc is None:
        rows.append('<p class="ar-note">Add a birth time to see your Rising sign and houses.</p>')
    return f'<div class="ar-big3">{"".join(rows)}</div>'


# ---------------------------------------------------------------------------
# styles for the HTML pieces (fonts come from the Streamlit theme)
# ---------------------------------------------------------------------------
STYLE = f"""
<style>
@font-face {{ font-family: astroglyphs; src: url(app/static/fonts/astro-glyphs.ttf) format("truetype");
  unicode-range: U+260A-260B, U+263D-2653; }}
@font-face {{ font-family: astroglyphs; src: url(app/static/fonts/astro-glyphs-sun.ttf) format("truetype");
  unicode-range: U+2609; }}
.ar-wheel, .ar-rasi {{ width: 100%; height: auto; display: block; }}
.ar-wheel {{ max-width: 640px; margin: 0 auto; }}
.ar-rasi {{ max-width: 520px; margin: 0 auto; }}
.ar-tzolkin {{ width: 100%; max-width: 300px; height: auto; display: block; }}
.ar-big3 {{ display: flex; flex-direction: column; gap: 1.4rem; margin-top: .5rem; }}
.ar-b3 {{ display: grid; grid-template-columns: 3.2rem 1fr; align-items: center; gap: .9rem; }}
.ar-b3-glyph {{ font-family: {GLYPH_FONT}; font-size: 2.3rem; line-height: 1; color: {BRASS};
  width: 3.2rem; height: 3.2rem; border: 1px solid {RULE}; border-radius: 50%;
  display: flex; align-items: center; justify-content: center; }}
.ar-b3-text {{ font-family: {TEXT_FONT}; font-size: .95rem; }}
.ar-b3-sign {{ font-family: {SERIF_FONT}; font-size: 2.1rem; line-height: 1.1; color: {IVORY}; }}
.ar-b3-signglyph {{ font-family: {GLYPH_FONT}; font-size: 1.3rem; color: {BRASS}; }}
.ar-b3-where {{ color: {MUTED}; font-size: .95rem; font-variant-numeric: tabular-nums; }}
.ar-note {{ color: {MUTED}; font-size: .95rem; margin: 0; }}
.ar-pillars {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .75rem; }}
.ar-pillar {{ border: 1px solid {RULE}; border-radius: .6rem; padding: 1rem .5rem 1.1rem;
  text-align: center; background: {ENAMEL}; }}
.ar-pillar.ar-daymaster {{ border-color: {BRASS}; }}
.ar-pillar.ar-unknown {{ opacity: .55; }}
.ar-pillar-name {{ color: {MUTED}; font-size: .9rem; margin-bottom: .4rem; }}
.ar-daymaster .ar-pillar-name {{ color: {BRASS}; }}
.ar-hanzi {{ font-size: 2.6rem; line-height: 1.25; font-family: 'Noto Serif CJK SC', 'Songti SC', 'SimSun', serif; }}
.ar-pillar-sub {{ color: {IVORY}; font-size: .85rem; margin-bottom: .5rem; }}
@media (max-width: 640px) {{
  .ar-pillars {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  .ar-b3-sign {{ font-size: 1.7rem; }}
}}
</style>
"""
