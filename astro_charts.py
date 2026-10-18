"""
astro_charts.py
===============
Every drawing in Astro_Reveal, returned as SVG / HTML strings (no Streamlit
here, so each one can be previewed and tested on its own):

- big_three_cards     Sun, Moon and Rising as flip cards with constellation art
- world_cards         Chinese, Vedic and Maya signs as flip cards
- natal_wheel_svg     the chart wheel, with hover details
- sky_map_svg         the real sky above the birthplace at the birth moment
- rising_band_svg     how the Rising sign changes through the birth day
- score_ring_svg      the compatibility score
- south_indian_svg, pillars_html, tzolkin_svg, bar_dot_svg   detail views

Star positions and constellation figures come from d3-celestial (BSD
licence), see sky_data.py.
"""

import math
from html import escape

import astro_content as C
import astro_engine as ae
import sky_data

# ---------------------------------------------------------------------------
# palette (keep in sync with .streamlit/config.toml)
# ---------------------------------------------------------------------------
PAPER = "#F6F4FF"
CARD = "#FFFFFF"
INK = "#221E52"
MUTED = "#5F5B8A"
LINE = "#E2DEF5"
LINE_STRONG = "#CFC9EC"
VIOLET = "#5B47E0"
GOLD = "#F4B63F"
CORAL = "#F26B4F"

GLYPH_FONT = "astroglyphs, 'Noto Sans Symbols', 'Segoe UI Symbol', 'Apple Symbols', 'DejaVu Sans', sans-serif"
TEXT_FONT = "instrument, 'Instrument Sans', system-ui, sans-serif"
SERIF_FONT = "fraunces, Fraunces, Georgia, serif"

SIGNS = C.SIGN_NAMES
VS = "︎"  # plain-text form of a symbol rather than an emoji
SIGN_GLYPHS = [chr(0x2648 + i) + VS for i in range(12)]
PLANET_GLYPHS = {k: v + VS for k, v in {
    "Sun": "☉", "Moon": "☽", "Mercury": "☿", "Venus": "♀",
    "Mars": "♂", "Jupiter": "♃", "Saturn": "♄", "Uranus": "♅",
    "Neptune": "♆", "Rahu": "☊", "Ketu": "☋"}.items()}
ZODIAC_IDS = ["Ari", "Tau", "Gem", "Cnc", "Leo", "Vir", "Lib", "Sco", "Sgr", "Cap", "Aqr", "Psc"]

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
    for h in range(1, 13):
        start, end = cusps[str(h)], cusps[str(h % 12 + 1)]
        if (lon - start) % 360 < (end - start) % 360:
            return h
    return 1


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def element_colours(sign_i):
    return C.ELEMENTS[C.SIGNS[sign_i][1]]


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


def chips(items, cls="ar-chip"):
    return "".join(f'<span class="{cls}">{escape(str(t))}</span>' for t in items)


# ---------------------------------------------------------------------------
# constellation art
# ---------------------------------------------------------------------------
def constellation_svg(sign_i, width=280, height=150):
    """The constellation a sign is named after, as a little star drawing."""
    base, tint, ink = element_colours(sign_i)[1:]
    polys = sky_data.LINES[ZODIAC_IDS[sign_i]]
    pts = [p for poly in polys for p in poly]
    sx = sum(math.cos(math.radians(r)) for r, _ in pts)
    sy = sum(math.sin(math.radians(r)) for r, _ in pts)
    ra0 = math.degrees(math.atan2(sy, sx))
    d0 = sum(d for _, d in pts) / len(pts)

    def proj(r, d):
        dr = math.radians(r - ra0)
        dd, dc = math.radians(d), math.radians(d0)
        cosc = math.sin(dc) * math.sin(dd) + math.cos(dc) * math.cos(dd) * math.cos(dr)
        x = math.cos(dd) * math.sin(dr) / cosc
        y = (math.cos(dc) * math.sin(dd) - math.sin(dc) * math.cos(dd) * math.cos(dr)) / cosc
        return -x, -y          # east to the left, north up (y down on screen)

    xy = [proj(r, d) for r, d in pts]
    minx, maxx = min(p[0] for p in xy), max(p[0] for p in xy)
    miny, maxy = min(p[1] for p in xy), max(p[1] for p in xy)
    pad = 18
    scale = min((width - 2 * pad) / max(maxx - minx, 1e-6), (height - 2 * pad) / max(maxy - miny, 1e-6))
    ox = (width - (maxx - minx) * scale) / 2
    oy = (height - (maxy - miny) * scale) / 2

    def screen(r, d):
        x, y = proj(r, d)
        return ox + (x - minx) * scale, oy + (y - miny) * scale

    out = [f'<svg viewBox="0 0 {width} {height}" class="ar-const" role="img" '
           f'aria-label="The stars of {SIGNS[sign_i]}" xmlns="http://www.w3.org/2000/svg">']
    # faint neighbouring stars, so the figure sits in a real patch of sky
    for r, d, mag in sky_data.STARS:
        if abs(d - d0) > 40 or _sep(r, ra0) > 60:
            continue
        x, y = screen(r, d)
        if 4 < x < width - 4 and 4 < y < height - 4:
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{max(0.8, 2.6 - mag * 0.45):.1f}" '
                       f'fill="{ink}" fill-opacity=".28"/>')
    for poly in polys:
        p = " ".join("%.1f,%.1f" % screen(r, d) for r, d in poly)
        out.append(f'<polyline points="{p}" fill="none" stroke="{ink}" stroke-width="2.2" '
                   f'stroke-opacity=".7" stroke-linejoin="round" stroke-linecap="round"/>')
    seen = set()
    for r, d in pts:
        if (r, d) in seen:
            continue
        seen.add((r, d))
        mag = sky_data.VERTEX_MAG.get(f"{r},{d}", 4.5)
        rad = max(2.2, 6.6 - mag * 1.05)
        x, y = screen(r, d)
        if mag < 2.0:
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad * 2.6:.1f}" fill="{base}" fill-opacity=".22"/>')
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad:.1f}" fill="{CARD}" stroke="{ink}" stroke-width="1.6"/>')
    out.append("</svg>")
    return "".join(out)


# ---------------------------------------------------------------------------
# flip cards
# ---------------------------------------------------------------------------
def flip_card(front, back, colours, label):
    _, base, tint, ink = colours
    return (f'<label class="ar-flip" style="--base:{base};--tint:{tint};--ink:{ink}" '
            f'title="Tap to turn over" aria-label="{escape(label)}. Tap to turn over.">'
            f'<input type="checkbox"><div class="ar-flip-inner">'
            f'<div class="ar-face ar-front">{front}<span class="ar-turn" aria-hidden="true">↻</span></div>'
            f'<div class="ar-face ar-back">{back}<span class="ar-turn" aria-hidden="true">↻</span></div>'
            f'</div></label>')


def big_three_cards(tropical, asc=None, cusps=None):
    cards = []
    items = [("Sun", tropical["Sun"]), ("Moon", tropical["Moon"])]
    items.append(("Rising", asc))
    for key, lon in items:
        emoji, tag, meaning = C.PLACEMENTS[key]
        if lon is None:
            cards.append(
                f'<div class="ar-flip ar-locked"><div class="ar-flip-inner"><div class="ar-face ar-front">'
                f'<span class="ar-tag">{emoji} {tag}</span><div class="ar-lock">🔒</div>'
                f'<div class="ar-sign">Unknown</div>'
                f'<p class="ar-locked-text">Add your birth time to see it.</p></div></div></div>')
            continue
        i = sign_index(lon)
        name, element, modality, sign_emoji, keywords, line = C.SIGNS[i]
        colours = C.ELEMENTS[element]
        where = f"{fmt_deg(lon)} {name}"
        if cusps and key != "Rising":
            where += f", {ordinal(house_of(lon, cusps))} house"
        front = (f'<span class="ar-tag">{emoji} {tag}</span>'
                 f'<div class="ar-art">{constellation_svg(i)}</div>'
                 f'<div class="ar-sign">{name} <span class="ar-sign-emoji">{sign_emoji}</span></div>'
                 f'<div class="ar-chips">{chips([colours[0] + " " + element] + keywords)}</div>')
        back = (f'<span class="ar-tag">{emoji} {tag}</span>'
                f'<div class="ar-back-big">{escape(meaning)}</div>'
                f'<p class="ar-back-text">{escape(line)}</p>'
                f'<p class="ar-back-meta">{where} · {modality} {element.lower()}</p>')
        cards.append(flip_card(front, back, colours, f"{tag}: {name}"))
    return f'<div class="ar-cards">{"".join(cards)}</div>'


def world_cards(four_pillars, nakshatra, tzolkin, birth_year_label):
    (y_stem, y_el), (y_branch, animal) = four_pillars["year"]
    (d_stem, d_el), _ = four_pillars["day"]
    year_element = y_el.split()[-1]
    animal_emoji, animal_words = C.CHINESE_ANIMALS[animal]
    dm_element = d_el.split()[-1]
    c_year = C.FIVE_ELEMENTS[year_element]
    dm = C.FIVE_ELEMENTS[dm_element]
    chinese = flip_card(
        f'<span class="ar-tag">🏮 Chinese year</span><div class="ar-emoji">{animal_emoji}</div>'
        f'<div class="ar-sign">{year_element} {animal}</div>'
        f'<div class="ar-chips">{chips(animal_words)}</div>',
        f'<span class="ar-tag">🏮 Chinese year</span>'
        f'<div class="ar-back-big">Born in a {year_element} {animal} year.</div>'
        f'<p class="ar-back-text">Your Day Master, the element of the day you were born, '
        f'is {d_el.lower()} {dm[0]}.</p>'
        f'<p class="ar-back-meta">{escape(birth_year_label)}</p>',
        c_year, f"Chinese year: {year_element} {animal}")

    nak_emoji = C.NAKSHATRA_EMOJI.get(nakshatra["name"], "✨")
    vedic = flip_card(
        f'<span class="ar-tag">🪔 Moon star</span><div class="ar-emoji">{nak_emoji}</div>'
        f'<div class="ar-sign">{nakshatra["name"]}</div>'
        f'<div class="ar-chips">{chips([w.strip() for w in nakshatra["meaning"].split(",")])}</div>',
        f'<span class="ar-tag">🪔 Moon star</span>'
        f'<div class="ar-back-big">Your Moon was in {nakshatra["name"]}.</div>'
        f'<p class="ar-back-text">One of the 27 lunar mansions of Vedic astrology. '
        f'Ruled by {nakshatra["lord"]}, pada {nakshatra["pada"]} of 4.</p>'
        f'<p class="ar-back-meta">Sidereal zodiac, Lahiri</p>',
        ("🪔", "#9B6BE8", "#F0E8FF", "#5B2DB0"), f"Moon star: {nakshatra['name']}")

    glyph, maya_emoji = C.MAYA_SIGNS.get(tzolkin["day_sign"], (tzolkin["glyph"], "✨"))
    maya = flip_card(
        f'<span class="ar-tag">🌽 Maya day sign</span><div class="ar-emoji">{maya_emoji}</div>'
        f'<div class="ar-sign">{tzolkin["galactic_tone"]} {glyph}</div>'
        f'<div class="ar-maya-row">{bar_dot_svg(tzolkin["galactic_tone"], colour="#0F8A7E", scale=.6)}'
        f'<span class="ar-chip">{escape(tzolkin["meaning"])}</span></div>',
        f'<span class="ar-tag">🌽 Maya day sign</span>'
        f'<div class="ar-back-big">{tzolkin["galactic_tone"]} {tzolkin["day_sign"]} ({glyph}).</div>'
        f'<p class="ar-back-text">Day {tzolkin["kin"]} of the 260-day sacred count. The number is '
        f'written the Maya way: a dot is one, a bar is five.</p>'
        f'<p class="ar-back-meta">GMT correlation 584283</p>',
        ("🌽", "#14B8A6", "#DDF7F3", "#0F6B62"), f"Maya day sign: {glyph}")
    return f'<div class="ar-cards">{chinese}{vedic}{maya}</div>'


# ---------------------------------------------------------------------------
# the chart wheel
# ---------------------------------------------------------------------------
def natal_wheel_svg(positions, cusps=None, asc=None, mc=None, retrograde=(), title="Birth chart"):
    size, c = 720, 360
    r_out, r_band, r_planet, r_inner = 340, 286, 244, 158
    left = asc if asc is not None else 0.0

    def pt(lon, r):
        a = math.radians(180 + (lon - left))
        return c + r * math.cos(a), c - r * math.sin(a)

    def line(lon, r1, r2, **attrs):
        x1, y1 = pt(lon, r1)
        x2, y2 = pt(lon, r2)
        extra = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
        return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" {extra}/>'

    def sector(a1, a2, r1, r2):
        x1, y1 = pt(a1, r2)
        x2, y2 = pt(a2, r2)
        x3, y3 = pt(a2, r1)
        x4, y4 = pt(a1, r1)
        return (f"M{x1:.1f},{y1:.1f} A{r2},{r2} 0 0 0 {x2:.1f},{y2:.1f} "
                f"L{x3:.1f},{y3:.1f} A{r1},{r1} 0 0 1 {x4:.1f},{y4:.1f} Z")

    m = 46
    out = [f'<svg viewBox="{-m} {-m} {size + 2 * m} {size + 2 * m}" xmlns="http://www.w3.org/2000/svg" '
           f'role="img" aria-label="{escape(title)}" class="ar-wheel"><title>{escape(title)}</title>',
           f'<circle cx="{c}" cy="{c}" r="{r_out + 10}" fill="{CARD}"/>']

    for i in range(12):
        _, base, tint, ink = element_colours(i)
        out.append(f'<path d="{sector(i * 30, i * 30 + 30, r_band, r_out)}" fill="{tint}" '
                   f'stroke="{CARD}" stroke-width="3"><title>{SIGNS[i]}</title></path>')
        x, y = pt(i * 30 + 15, (r_band + 12 + r_out) / 2)
        out.append(f'<text x="{x:.1f}" y="{y:.1f}" fill="{ink}" font-size="27" font-family="{GLYPH_FONT}" '
                   f'text-anchor="middle" dominant-baseline="central">{SIGN_GLYPHS[i]}</text>')
    ticks = []
    for d in range(360):
        length = 9 if d % 10 == 0 else (6 if d % 5 == 0 else 3)
        ticks.append(line(d, r_band, r_band + length))
    out.append(f'<g stroke="{INK}" stroke-width="0.8" stroke-opacity="0.35">{"".join(ticks)}</g>')
    out.append(f'<circle cx="{c}" cy="{c}" r="{r_inner}" fill="{PAPER}" stroke="{LINE_STRONG}"/>')

    if cusps:
        for h in range(1, 13):
            if h not in (1, 4, 7, 10):
                out.append(line(cusps[str(h)], r_inner, r_band, stroke=LINE_STRONG, stroke_width="1.2"))
        for h in range(1, 13):
            a, b = cusps[str(h)], cusps[str(h % 12 + 1)]
            x, y = pt(a + ((b - a) % 360) / 2, r_inner + 15)
            out.append(f'<text x="{x:.1f}" y="{y:.1f}" fill="{MUTED}" font-size="12" font-family="{TEXT_FONT}" '
                       f'text-anchor="middle" dominant-baseline="central">{h}</text>')
    for lon, label in ((asc, "Asc"), (mc, "MC")):
        if lon is None:
            continue
        out.append(line(lon, r_inner, r_out + 14, stroke=VIOLET, stroke_width="2.2"))
        out.append(line(lon + 180, r_inner, r_out + 6, stroke=VIOLET, stroke_width="1.2", stroke_opacity=".6"))
        x, y = pt(lon, r_out + 30)
        out.append(f'<text x="{x:.1f}" y="{y:.1f}" fill="{VIOLET}" font-size="16" font-weight="600" '
                   f'font-family="{TEXT_FONT}" text-anchor="middle" dominant-baseline="central">{label}</text>')

    for a, b, name, orb, harmonious in find_aspects(positions):
        if harmonious is None:
            continue
        x1, y1 = pt(positions[a], r_inner - 4)
        x2, y2 = pt(positions[b], r_inner - 4)
        colour = VIOLET if harmonious else CORAL
        dash = ' stroke-dasharray="5 4"' if name == "sextile" else ""
        out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{colour}" '
                   f'stroke-width="1.6" stroke-opacity="{max(0.35, 0.85 - orb / 10):.2f}"{dash} class="ar-asp">'
                   f'<title>{a} {name} {b}</title></line>')

    names = [n for n in PLANET_GLYPHS if n in positions]
    lons = [positions[n] for n in names]
    spread = _spread([180 + (lon - left) for lon in lons], 8.4)
    tips = []
    for k, (name, lon, s) in enumerate(zip(names, lons, spread)):
        shown = s - 180 + left
        out.append(line(lon, r_band - 9, r_band, stroke=INK, stroke_width="1.8"))
        x0, y0 = pt(lon, r_band - 9)
        x1, y1 = pt(shown, r_planet + 20)
        out.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{INK}" '
                   f'stroke-width="0.8" stroke-opacity=".35"/>')
        x, y = pt(shown, r_planet)
        lx, ly = pt(shown, r_planet - 30)
        colour = MUTED if name in ("Rahu", "Ketu") else INK
        big = name in ("Sun", "Moon")
        label = fmt_deg(lon).split("°")[0] + "°" + (" Rx" if name in retrograde else "")
        sign = SIGNS[sign_index(lon)]
        tip = f"{name} in {sign} {fmt_deg(lon)}" + (", retrograde" if name in retrograde else "")
        tx, ty = pt(shown, r_planet - 62)
        tw = len(tip) * 7.4 + 24
        out.append(
            f'<g class="ar-pl" tabindex="0" data-k="{k}" style="--i:{k}">'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="19" fill="{CARD}" class="ar-pl-hit"/>'
            f'<text x="{x:.1f}" y="{y:.1f}" fill="{colour}" font-size="{30 if big else 25}" '
            f'font-family="{GLYPH_FONT}" text-anchor="middle" dominant-baseline="central">{PLANET_GLYPHS[name]}</text>'
            f'<text x="{lx:.1f}" y="{ly:.1f}" fill="{MUTED}" font-size="12" font-family="{TEXT_FONT}" '
            f'text-anchor="middle" dominant-baseline="central">{label}</text></g>')
        tips.append(
            f'<g class="ar-tip" data-for="{k}"><rect x="{tx - tw / 2:.1f}" y="{ty - 16:.1f}" width="{tw:.1f}" '
            f'height="32" rx="16" fill="{INK}"/><text x="{tx:.1f}" y="{ty:.1f}" fill="{CARD}" font-size="13.5" '
            f'font-family="{TEXT_FONT}" text-anchor="middle" dominant-baseline="central">{escape(tip)}</text></g>')
    # tooltips go last so they sit on top; CSS shows the one whose planet is hovered
    out.append(f'<g class="ar-tips">{"".join(tips)}</g>')
    out.append("</svg>")
    return "".join(out)


def wheel_tip_css(count=11):
    """Show tooltip k while planet k is hovered or focused."""
    rules = [f".ar-wheel:has(.ar-pl[data-k='{k}']:hover) .ar-tip[data-for='{k}'],"
             f".ar-wheel:has(.ar-pl[data-k='{k}']:focus) .ar-tip[data-for='{k}']{{opacity:1}}"
             for k in range(count)]
    return "\n".join(rules)


# ---------------------------------------------------------------------------
# the sky above you
# ---------------------------------------------------------------------------
def _altaz(ra, dec, lst, lat):
    h = math.radians(lst - ra)
    d, p = math.radians(dec), math.radians(lat)
    sin_alt = math.sin(p) * math.sin(d) + math.cos(p) * math.cos(d) * math.cos(h)
    alt = math.degrees(math.asin(max(-1.0, min(1.0, sin_alt))))
    az = math.degrees(math.atan2(-math.sin(h) * math.cos(d),
                                 math.sin(d) * math.cos(p) - math.cos(d) * math.cos(h) * math.sin(p)))
    return alt, az % 360


def _ecl_to_eq(lon):
    eps = math.radians(23.4393)
    l = math.radians(lon)
    ra = math.degrees(math.atan2(math.sin(l) * math.cos(eps), math.cos(l))) % 360
    dec = math.degrees(math.asin(math.sin(eps) * math.sin(l)))
    return ra, dec


def sky_map_svg(jd_ut, lat, lon, tropical):
    """Stereographic view of the whole sky above the horizon: zenith in the
    middle, north up, east on the left (as when you lie back and look up)."""
    size, c, R = 640, 320, 290
    prec = 1.396971 * ae.centuries(jd_ut)          # bring planets to the J2000 star frame
    lst = ae.ramc(jd_ut, lon) - prec

    def place(ra, dec):
        alt, az = _altaz(ra, dec, lst, lat)
        if alt < -0.5:
            return None, alt
        r = R * math.tan(math.radians(90 - alt) / 2)
        return (c - r * math.sin(math.radians(az)), c - r * math.cos(math.radians(az))), alt

    sun_ra, sun_dec = _ecl_to_eq(tropical["Sun"] - prec)
    _, sun_alt = place(sun_ra, sun_dec)
    day = sun_alt > -6
    top, bottom = ("#DCEBFF", "#F4F8FF") if day else ("#E4E0FF", "#F7F5FF")

    out = [f'<svg viewBox="0 0 {size} {size}" class="ar-sky" role="img" '
           f'aria-label="The sky above the birthplace at the moment of birth" xmlns="http://www.w3.org/2000/svg">',
           f'<defs><radialGradient id="ar-skyfill" cx="50%" cy="50%" r="50%">'
           f'<stop offset="0%" stop-color="{bottom}"/><stop offset="100%" stop-color="{top}"/></radialGradient>'
           f'<clipPath id="ar-skyclip"><circle cx="{c}" cy="{c}" r="{R}"/></clipPath></defs>',
           f'<circle cx="{c}" cy="{c}" r="{R}" fill="url(#ar-skyfill)" stroke="{LINE_STRONG}" stroke-width="2"/>',
           f'<g clip-path="url(#ar-skyclip)">']
    for alt in (30, 60):
        r = R * math.tan(math.radians(90 - alt) / 2)
        out.append(f'<circle cx="{c}" cy="{c}" r="{r:.1f}" fill="none" stroke="{LINE_STRONG}" '
                   f'stroke-dasharray="2 5" stroke-width="1"/>')

    zodiac = set(ZODIAC_IDS)
    for cid, polys in sky_data.LINES.items():
        is_z = cid in zodiac
        if is_z:
            ink = C.ELEMENTS[C.SIGNS[ZODIAC_IDS.index(cid)][1]][3]
        for poly in polys:
            seg = []
            for ra, dec in poly:
                p, _ = place(ra, dec)
                if p is None:
                    if len(seg) > 1:
                        out.append(_poly(seg, ink if is_z else "#B5ADE3", 1.8 if is_z else 1.0, .85 if is_z else .7))
                    seg = []
                    continue
                seg.append(p)
            if len(seg) > 1:
                out.append(_poly(seg, ink if is_z else "#B5ADE3", 1.8 if is_z else 1.0, .85 if is_z else .7))

    for ra, dec, mag in sky_data.STARS:
        p, _ = place(ra, dec)
        if p is None:
            continue
        r = max(0.7, 3.4 - 0.62 * mag)
        out.append(f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="{r:.2f}" fill="{INK}" '
                   f'fill-opacity="{max(0.35, 1 - mag * 0.13):.2f}"/>')

    for cid, (ra, dec) in sky_data.ZODIAC_LABELS.items():
        p, alt = place(ra, dec)
        if p is None or alt < 4:
            continue
        i = ZODIAC_IDS.index(cid)
        out.append(f'<text x="{p[0]:.1f}" y="{p[1]:.1f}" fill="{C.ELEMENTS[C.SIGNS[i][1]][3]}" font-size="14" '
                   f'font-weight="600" font-family="{TEXT_FONT}" text-anchor="middle" class="ar-halo">{SIGNS[i]}</text>')

    for name in ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"):
        ra, dec = _ecl_to_eq(tropical[name] - prec)
        p, alt = place(ra, dec)
        if p is None:
            continue
        if name == "Sun":
            out.append(f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="22" fill="{GOLD}" fill-opacity=".25"/>')
            fill, stroke = GOLD, "#C98A10"
        else:
            fill, stroke = CARD, VIOLET
        out.append(f'<g class="ar-sky-pl"><circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="14" fill="{fill}" '
                   f'stroke="{stroke}" stroke-width="2"/><text x="{p[0]:.1f}" y="{p[1]:.1f}" fill="{INK}" '
                   f'font-size="17" font-family="{GLYPH_FONT}" text-anchor="middle" dominant-baseline="central">'
                   f'{PLANET_GLYPHS[name]}</text><title>{name}</title></g>')
    out.append("</g>")
    for label, az in (("N", 0), ("E", 90), ("S", 180), ("W", 270)):
        x = c - (R + 18) * math.sin(math.radians(az))
        y = c - (R + 18) * math.cos(math.radians(az))
        out.append(f'<text x="{x:.1f}" y="{y:.1f}" fill="{MUTED}" font-size="15" font-weight="600" '
                   f'font-family="{TEXT_FONT}" text-anchor="middle" dominant-baseline="central">{label}</text>')
    out.append("</svg>")
    return "".join(out), day


def _poly(points, colour, width, opacity):
    p = " ".join("%.1f,%.1f" % q for q in points)
    return (f'<polyline points="{p}" fill="none" stroke="{colour}" stroke-width="{width}" '
            f'stroke-opacity="{opacity}" stroke-linejoin="round" stroke-linecap="round"/>')


# ---------------------------------------------------------------------------
# birth-time explorer
# ---------------------------------------------------------------------------
def rising_band_svg(samples, chosen_minute, birth_minute=None):
    """samples: [(minute_of_day, ascendant_longitude)] every few minutes, 0..1440."""
    w, h, top, bar = 1000, 132, 30, 56
    step = w / 1440
    runs = []
    for minute, lon in samples:
        i = sign_index(lon)
        if runs and runs[-1][0] == i:
            runs[-1][2] = minute
        else:
            runs.append([i, minute, minute])
    out = [f'<svg viewBox="0 0 {w} {h}" class="ar-band" role="img" '
           f'aria-label="Rising sign through the day" xmlns="http://www.w3.org/2000/svg">']
    for k, (i, start, end) in enumerate(runs):
        if k + 1 < len(runs):
            end = runs[k + 1][1]
        _, base, tint, ink = element_colours(i)
        x0, x1 = start * step, max(start * step + 1, end * step)
        out.append(f'<rect x="{x0:.1f}" y="{top}" width="{x1 - x0:.1f}" height="{bar}" fill="{tint}" '
                   f'stroke="{CARD}" stroke-width="2"><title>{SIGNS[i]} rising</title></rect>')
        if x1 - x0 > 44:
            out.append(f'<text x="{(x0 + x1) / 2:.1f}" y="{top + bar / 2:.1f}" fill="{ink}" font-size="22" '
                       f'font-family="{GLYPH_FONT}" text-anchor="middle" dominant-baseline="central">'
                       f'{SIGN_GLYPHS[i]}</text>')
    for hr in range(0, 25, 3):
        anchor = "start" if hr == 0 else "end" if hr == 24 else "middle"
        out.append(f'<text x="{hr * 60 * step:.1f}" y="{top + bar + 26}" fill="{MUTED}" font-size="14" '
                   f'font-family="{TEXT_FONT}" text-anchor="{anchor}">{hr:02d}:00</text>')
    if birth_minute is not None:
        x = birth_minute * step
        out.append(f'<circle cx="{x:.1f}" cy="{top + bar + 6}" r="5" fill="{GOLD}" stroke="{INK}"/>')
    x = chosen_minute * step
    out.append(f'<line x1="{x:.1f}" y1="{top - 8}" x2="{x:.1f}" y2="{top + bar + 4}" stroke="{VIOLET}" stroke-width="3"/>'
               f'<path d="M{x - 8:.1f},{top - 18} L{x + 8:.1f},{top - 18} L{x:.1f},{top - 6} Z" fill="{VIOLET}"/>')
    out.append("</svg>")
    return "".join(out)


# ---------------------------------------------------------------------------
# compatibility
# ---------------------------------------------------------------------------
def score_ring_svg(score):
    r, w = 78, 16
    circ = 2 * math.pi * r
    return (f'<svg viewBox="0 0 200 200" class="ar-ring" role="img" aria-label="{score} percent match" '
            f'xmlns="http://www.w3.org/2000/svg"><circle cx="100" cy="100" r="{r}" fill="none" '
            f'stroke="{LINE}" stroke-width="{w}"/><circle cx="100" cy="100" r="{r}" fill="none" stroke="{VIOLET}" '
            f'stroke-width="{w}" stroke-linecap="round" stroke-dasharray="{circ * score / 100:.1f} {circ:.1f}" '
            f'transform="rotate(-90 100 100)" class="ar-ring-arc"/><text x="100" y="98" fill="{INK}" font-size="48" '
            f'font-family="{SERIF_FONT}" font-weight="600" text-anchor="middle" dominant-baseline="central">{score}'
            f'<tspan font-size="24">%</tspan></text><text x="100" y="134" fill="{MUTED}" font-size="14" '
            f'font-family="{TEXT_FONT}" text-anchor="middle">match</text></svg>')


# ---------------------------------------------------------------------------
# detail views
# ---------------------------------------------------------------------------
SOUTH_INDIAN_CELLS = {11: (0, 0), 0: (0, 1), 1: (0, 2), 2: (0, 3), 10: (1, 0), 3: (1, 3),
                      9: (2, 0), 4: (2, 3), 8: (3, 0), 7: (3, 1), 6: (3, 2), 5: (3, 3)}
VEDIC_ABBR = {"Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me", "Jupiter": "Ju",
              "Venus": "Ve", "Saturn": "Sa", "Rahu": "Ra", "Ketu": "Ke"}
RASI = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
        "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena"]


def south_indian_svg(sidereal, lagna=None, ayanamsa=None):
    cell, pad = 118, 2
    size = cell * 4 + pad * 2
    out = [f'<svg viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg" role="img" '
           f'aria-label="Vedic rasi chart, South Indian style" class="ar-rasi">',
           f'<rect x="{pad}" y="{pad}" width="{cell * 4}" height="{cell * 4}" fill="{PAPER}" '
           f'stroke="{LINE_STRONG}" stroke-width="2" rx="14"/>']
    occupants = {i: [] for i in range(12)}
    for name, abbr in VEDIC_ABBR.items():
        if name in sidereal:
            occupants[sign_index(sidereal[name])].append((sidereal[name] % 30, abbr))
    lagna_sign = sign_index(lagna) if lagna is not None else None
    for s, (row, col) in SOUTH_INDIAN_CELLS.items():
        x, y = pad + col * cell, pad + row * cell
        _, base, tint, ink = element_colours(s)
        out.append(f'<rect x="{x + 3}" y="{y + 3}" width="{cell - 6}" height="{cell - 6}" rx="10" fill="{tint}"/>')
        out.append(f'<text x="{x + 12}" y="{y + 22}" fill="{ink}" font-size="12" font-family="{TEXT_FONT}">'
                   f'<title>{SIGNS[s]}</title>{RASI[s]}</text>')
        out.append(f'<text x="{x + cell - 12}" y="{y + 22}" fill="{ink}" font-size="15" '
                   f'font-family="{GLYPH_FONT}" text-anchor="end">{SIGN_GLYPHS[s]}</text>')
        rows = []
        if s == lagna_sign:
            out.append(f'<line x1="{x + cell - 36}" y1="{y + cell - 3}" x2="{x + cell - 3}" y2="{y + cell - 36}" '
                       f'stroke="{VIOLET}" stroke-width="2"/>')
            rows.append((lagna % 30, "Asc", VIOLET))
        rows += [(d, a, INK) for d, a in occupants[s]]
        rows.sort()
        for k, (deg, label, colour) in enumerate(rows[:8]):
            out.append(f'<text x="{x + 14 + (k // 4) * 54}" y="{y + 46 + (k % 4) * 19}" fill="{colour}" '
                       f'font-size="15" font-weight="600" font-family="{TEXT_FONT}">{label} '
                       f'<tspan fill="{MUTED}" font-size="12" font-weight="400">{int(deg)}°</tspan></text>')
    cx = cy = pad + cell * 2
    out.append(f'<text x="{cx}" y="{cy - 12}" fill="{INK}" font-size="24" font-family="{SERIF_FONT}" '
               f'text-anchor="middle">Rasi chart</text>')
    if lagna_sign is not None:
        out.append(f'<text x="{cx}" y="{cy + 16}" fill="{MUTED}" font-size="13" font-family="{TEXT_FONT}" '
                   f'text-anchor="middle">Lagna in {RASI[lagna_sign]} ({SIGNS[lagna_sign]})</text>')
    if ayanamsa is not None:
        out.append(f'<text x="{cx}" y="{cy + 36}" fill="{MUTED}" font-size="13" font-family="{TEXT_FONT}" '
                   f'text-anchor="middle">Lahiri {int(ayanamsa)}°{int(round((ayanamsa % 1) * 60)):02d}′</text>')
    out.append("</svg>")
    return "".join(out)


STEM_HANZI = {"Jia": "甲", "Yi": "乙", "Bing": "丙", "Ding": "丁", "Wu": "戊",
              "Ji": "己", "Geng": "庚", "Xin": "辛", "Ren": "壬", "Gui": "癸"}
BRANCH_HANZI = {"Zi": "子", "Chou": "丑", "Yin": "寅", "Mao": "卯", "Chen": "辰", "Si": "巳",
                "Wu": "午", "Wei": "未", "Shen": "申", "You": "酉", "Xu": "戌", "Hai": "亥"}
BRANCH_ELEMENT = {"Zi": "Water", "Chou": "Earth", "Yin": "Wood", "Mao": "Wood", "Chen": "Earth",
                  "Si": "Fire", "Wu": "Fire", "Wei": "Earth", "Shen": "Metal", "You": "Metal",
                  "Xu": "Earth", "Hai": "Water"}


def pillars_html(pillars, hour_known=True):
    cols = []
    for key in ("hour", "day", "month", "year"):
        (stem, stem_el), (branch, animal) = pillars[key]
        cls = "ar-pillar ar-daymaster" if key == "day" else "ar-pillar"
        if key == "hour" and not hour_known:
            cols.append(f'<div class="{cls} ar-unknown"><div class="ar-pillar-name">Hour</div>'
                        f'<div class="ar-hanzi">?</div><div class="ar-pillar-sub">Needs a birth time</div>'
                        f'<div class="ar-hanzi">?</div></div>')
            continue
        e1 = C.FIVE_ELEMENTS[stem_el.split()[-1]]
        e2 = C.FIVE_ELEMENTS[BRANCH_ELEMENT[branch]]
        note = "Day Master" if key == "day" else key.title()
        cols.append(
            f'<div class="{cls}"><div class="ar-pillar-name">{note}</div>'
            f'<div class="ar-hanzi" style="color:{e1[3]};background:{e1[2]}" lang="zh">{STEM_HANZI[stem]}</div>'
            f'<div class="ar-pillar-sub">{stem}, {escape(stem_el)}</div>'
            f'<div class="ar-hanzi" style="color:{e2[3]};background:{e2[2]}" lang="zh">{BRANCH_HANZI[branch]}</div>'
            f'<div class="ar-pillar-sub">{branch}, {escape(animal)} {C.CHINESE_ANIMALS[animal][0]}</div></div>')
    return f'<div class="ar-pillars">{"".join(cols)}</div>'


DAY_SIGNS = ["Imix", "Ik", "Akbal", "Kan", "Chicchan", "Cimi", "Manik", "Lamat", "Muluc", "Oc",
             "Chuen", "Eb", "Ben", "Ix", "Men", "Cib", "Caban", "Etznab", "Cauac", "Ahau"]


def bar_dot_svg(n, colour="#0F8A7E", scale=1.0):
    bars, dots = divmod(n, 5)
    w = 84
    h = 22 + bars * 18 + 6
    out = [f'<svg viewBox="0 0 {w} {h}" width="{w * scale:.0f}" height="{h * scale:.0f}" '
           f'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Maya numeral {n}">']
    if dots:
        start = w / 2 - (dots - 1) * 9
        for i in range(dots):
            out.append(f'<circle cx="{start + i * 18:.1f}" cy="10" r="6.5" fill="{colour}"/>')
    for i in range(bars):
        out.append(f'<rect x="4" y="{(22 if dots else 4) + i * 18}" width="{w - 8}" height="11" rx="5.5" fill="{colour}"/>')
    out.append("</svg>")
    return "".join(out)


def tzolkin_svg(kin):
    cell, gap, label_w = 15, 3, 70
    w = label_w + 13 * (cell + gap)
    h = 20 * (cell + gap) + 22
    col, row = divmod(kin - 1, 20)
    out = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" role="img" '
           f'aria-label="Tzolkin count, kin {kin} marked" class="ar-tzolkin">']
    for r, name in enumerate(DAY_SIGNS):
        y = 22 + r * (cell + gap)
        out.append(f'<text x="{label_w - 8}" y="{y + cell - 3}" fill="{"#0F6B62" if r == row else MUTED}" '
                   f'font-size="11.5" font-family="{TEXT_FONT}" text-anchor="end">{name}</text>')
        for c in range(13):
            x = label_w + c * (cell + gap)
            if c * 20 + r + 1 == kin:
                out.append(f'<rect x="{x - 1}" y="{y - 1}" width="{cell + 2}" height="{cell + 2}" rx="4" fill="#14B8A6"/>')
            else:
                out.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3.5" fill="{PAPER}" '
                           f'stroke="{LINE_STRONG}"/>')
    for c in range(13):
        out.append(f'<text x="{label_w + c * (cell + gap) + cell / 2}" y="12" fill="{"#0F6B62" if c == col else MUTED}" '
                   f'font-size="10" font-family="{TEXT_FONT}" text-anchor="middle">{c * 20 + 1}</text>')
    out.append("</svg>")
    return "".join(out)


# ---------------------------------------------------------------------------
# styles for all the pieces above (fonts come from the Streamlit theme)
# ---------------------------------------------------------------------------
STYLE = f"""
<style>
@font-face {{ font-family: astroglyphs; src: url(app/static/fonts/astro-glyphs.ttf) format("truetype");
  unicode-range: U+260A-260B, U+263D-2653; }}
@font-face {{ font-family: astroglyphs; src: url(app/static/fonts/astro-glyphs-sun.ttf) format("truetype");
  unicode-range: U+2609; }}
.ar-cards {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1.4rem; }}
.ar-flip {{ display: block; perspective: 1400px; cursor: pointer; position: relative; }}
.ar-flip input {{ position: absolute; opacity: 0; width: 1px; height: 1px; }}
.ar-flip-inner {{ position: relative; min-height: 27rem; transition: transform .7s cubic-bezier(.2,.75,.25,1);
  transform-style: preserve-3d; }}
.ar-flip input:checked + .ar-flip-inner {{ transform: rotateY(180deg); }}
.ar-flip input:focus-visible + .ar-flip-inner {{ outline: 3px solid {VIOLET}; outline-offset: 5px; border-radius: 1.6rem; }}
.ar-face {{ position: absolute; inset: 0; border-radius: 1.6rem; padding: 1.4rem 1.5rem 1.5rem;
  display: flex; flex-direction: column; backface-visibility: hidden; -webkit-backface-visibility: hidden;
  background: var(--tint); box-shadow: 0 1px 0 rgba(34,30,82,.04), 0 12px 32px -18px rgba(34,30,82,.35); }}
.ar-back {{ transform: rotateY(180deg); background: {CARD}; border: 2px solid var(--tint); }}
.ar-flip:hover .ar-front {{ box-shadow: 0 1px 0 rgba(34,30,82,.04), 0 18px 40px -16px rgba(34,30,82,.45); }}
.ar-tag {{ align-self: flex-start; background: {CARD}; color: var(--ink, {INK}); border-radius: 999px;
  padding: .3rem .8rem; font-size: .9rem; font-weight: 600; }}
.ar-back .ar-tag {{ background: var(--tint); }}
.ar-turn {{ position: absolute; top: 1.15rem; right: 1.25rem; width: 2.1rem; height: 2.1rem; border-radius: 50%;
  background: {CARD}; color: var(--ink); display: flex; align-items: center; justify-content: center;
  font-size: 1.1rem; }}
.ar-back .ar-turn {{ background: var(--tint); }}
.ar-art {{ flex: 1; display: flex; align-items: center; justify-content: center; min-height: 9rem; }}
.ar-const {{ width: 100%; max-width: 300px; height: auto; }}
.ar-emoji {{ flex: 1; display: flex; align-items: center; justify-content: center; font-size: 6.2rem; line-height: 1; }}
.ar-sign {{ font-family: {SERIF_FONT}; font-weight: 600; font-size: 2.7rem; line-height: 1.05; color: {INK};
  margin: .4rem 0 .8rem; letter-spacing: -.01em; }}
.ar-sign-emoji {{ font-size: 2rem; }}
.ar-chips {{ display: flex; flex-wrap: wrap; gap: .4rem; }}
.ar-chip {{ background: {CARD}; color: var(--ink, {INK}); border-radius: 999px; padding: .28rem .75rem;
  font-size: .95rem; }}
.ar-back-big {{ font-family: {SERIF_FONT}; font-weight: 600; font-size: 1.9rem; line-height: 1.15; color: {INK};
  margin: 1.4rem 0 .8rem; }}
.ar-back-text {{ font-size: 1.12rem; line-height: 1.5; color: {INK}; margin: 0; }}
.ar-back-meta {{ margin-top: auto; color: {MUTED}; font-size: .92rem; }}
.ar-locked .ar-face {{ background: {CARD}; border: 2px dashed {LINE_STRONG}; box-shadow: none; }}
.ar-locked {{ cursor: default; }}
.ar-lock {{ flex: 1; display: flex; align-items: center; justify-content: center; font-size: 4rem; opacity: .6; }}
.ar-locked-text {{ color: {MUTED}; margin: 0; }}
.ar-maya-row {{ display: flex; align-items: center; gap: .8rem; flex-wrap: wrap; }}
.ar-wheel {{ width: 100%; height: auto; display: block; max-width: 640px; margin: 0 auto; }}
.ar-pl {{ cursor: pointer; outline: none; animation: ar-pop .5s cubic-bezier(.2,.8,.3,1.3) both;
  animation-delay: calc(var(--i) * 70ms + 150ms); transform-box: fill-box; transform-origin: center; }}
.ar-pl:hover .ar-pl-hit, .ar-pl:focus .ar-pl-hit {{ fill: {PAPER}; stroke: {VIOLET}; stroke-width: 2; }}
.ar-tip {{ opacity: 0; transition: opacity .15s; pointer-events: none; }}
{wheel_tip_css()}
@keyframes ar-pop {{ from {{ opacity: 0; transform: scale(.4); }} to {{ opacity: 1; transform: scale(1); }} }}
.ar-sky {{ width: 100%; height: auto; display: block; max-width: 600px; margin: 0 auto; }}
.ar-halo {{ paint-order: stroke; stroke: {CARD}; stroke-width: 4px; stroke-opacity: .85; }}
.ar-band {{ width: 100%; height: auto; display: block; }}
.ar-ring {{ width: 100%; max-width: 230px; height: auto; display: block; margin: 0 auto; }}
.ar-ring-arc {{ animation: ar-ring 1.1s cubic-bezier(.2,.8,.2,1) both; }}
@keyframes ar-ring {{ from {{ stroke-dasharray: 0 999; }} }}
.ar-rasi {{ width: 100%; max-width: 520px; height: auto; display: block; margin: 0 auto; }}
.ar-tzolkin {{ width: 100%; max-width: 300px; height: auto; display: block; }}
.ar-pillars {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .9rem; }}
.ar-pillar {{ border-radius: 1.2rem; padding: 1rem .6rem 1.1rem; text-align: center; background: {CARD};
  border: 2px solid {LINE}; }}
.ar-pillar.ar-daymaster {{ border-color: {VIOLET}; }}
.ar-pillar.ar-unknown {{ opacity: .55; }}
.ar-pillar-name {{ color: {MUTED}; font-size: .9rem; margin-bottom: .5rem; font-weight: 600; }}
.ar-daymaster .ar-pillar-name {{ color: {VIOLET}; }}
.ar-hanzi {{ font-size: 2.4rem; line-height: 1.5; border-radius: .8rem; margin: 0 auto .3rem; width: 3.6rem;
  font-family: 'Noto Serif CJK SC', 'Songti SC', 'SimSun', serif; }}
.ar-pillar-sub {{ color: {INK}; font-size: .85rem; margin-bottom: .6rem; }}
@media (max-width: 900px) {{
  .ar-cards {{ grid-template-columns: 1fr; }}
  .ar-flip-inner {{ min-height: 23rem; }}
  .ar-pillars {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
}}
@media (prefers-reduced-motion: reduce) {{
  .ar-flip-inner, .ar-tip {{ transition: none; }}
  .ar-pl, .ar-ring-arc {{ animation: none; }}
}}
</style>
"""
