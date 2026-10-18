#!/usr/bin/env python3
"""
astro_engine.py
===============
All the chart maths for Astro_Reveal, in plain Python (no extra packages).

- Sun:      Meeus low-precision solar theory (~0.01 deg)
- Moon:     Meeus ch. 47, main periodic terms (~0.02 deg)
- Planets:  JPL Keplerian elements (Standish, valid 1800-2050), converted
            from heliocentric to geocentric, with light-time (~0.1-0.2 deg)
- Nodes:    mean lunar node (Rahu / Ketu)
- Houses:   Placidus, Regiomontanus, Porphyry, Equal, Whole Sign
- Lahiri ayanamsa, Moon nakshatra, Bazi four pillars (solar-term months),
  Mayan Tzolkin (GMT 584283)

Good enough for astrology; not an observatory ephemeris.
Run `python3 astro_engine.py` for the self-checks.
"""

import math
from datetime import date, datetime

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

NAKSHATRAS = [
    ("Ashwini", "Ketu", "New beginnings, quick action"),
    ("Bharani", "Venus", "Transformation, restraint"),
    ("Krittika", "Sun", "Cutting through illusion"),
    ("Rohini", "Moon", "Growth, fertility, beauty"),
    ("Mrigashira", "Mars", "Searching, curiosity"),
    ("Ardra", "Rahu", "Intensity, change"),
    ("Punarvasu", "Jupiter", "Renewal, optimism"),
    ("Pushya", "Saturn", "Nourishment, protection"),
    ("Ashlesha", "Mercury", "Mystical knowledge"),
    ("Magha", "Ketu", "Ancestral power, authority"),
    ("Purva Phalguni", "Venus", "Creativity, relationships"),
    ("Uttara Phalguni", "Sun", "Leadership, generosity"),
    ("Hasta", "Moon", "Skill, dexterity"),
    ("Chitra", "Mars", "Artistic creation"),
    ("Swati", "Rahu", "Independence, flexibility"),
    ("Vishakha", "Jupiter", "Determination, focus"),
    ("Anuradha", "Saturn", "Devotion, friendship"),
    ("Jyeshtha", "Mercury", "Seniority, protection"),
    ("Mula", "Ketu", "Root investigation"),
    ("Purva Ashadha", "Venus", "Invincibility, pride"),
    ("Uttara Ashadha", "Sun", "Victory, achievement"),
    ("Shravana", "Moon", "Learning, listening"),
    ("Dhanishta", "Mars", "Wealth, music"),
    ("Shatabhisha", "Rahu", "Healing, mystery"),
    ("Purva Bhadrapada", "Jupiter", "Spiritual intensity"),
    ("Uttara Bhadrapada", "Saturn", "Deep wisdom"),
    ("Revati", "Mercury", "Completion, journeys"),
]

HEAVENLY_STEMS = [
    ("Jia", "Yang Wood"), ("Yi", "Yin Wood"),
    ("Bing", "Yang Fire"), ("Ding", "Yin Fire"),
    ("Wu", "Yang Earth"), ("Ji", "Yin Earth"),
    ("Geng", "Yang Metal"), ("Xin", "Yin Metal"),
    ("Ren", "Yang Water"), ("Gui", "Yin Water"),
]

EARTHLY_BRANCHES = [
    ("Zi", "Rat"), ("Chou", "Ox"), ("Yin", "Tiger"), ("Mao", "Rabbit"),
    ("Chen", "Dragon"), ("Si", "Snake"), ("Wu", "Horse"), ("Wei", "Goat"),
    ("Shen", "Monkey"), ("You", "Rooster"), ("Xu", "Dog"), ("Hai", "Pig"),
]

MAYAN_DAY_SIGNS = [
    ("Imix", "Crocodile", "Primordial energy"),
    ("Ik", "Wind", "Spirit, breath"),
    ("Akbal", "Night", "Inner temple"),
    ("Kan", "Seed", "Growth potential"),
    ("Chicchan", "Serpent", "Life force"),
    ("Cimi", "Death", "Transformation"),
    ("Manik", "Deer", "Healing hands"),
    ("Lamat", "Rabbit", "Star seed"),
    ("Muluc", "Water", "Offering"),
    ("Oc", "Dog", "Loyalty, guidance"),
    ("Chuen", "Monkey", "Artistry"),
    ("Eb", "Grass", "Human experience"),
    ("Ben", "Reed", "Flowing waters"),
    ("Ix", "Jaguar", "Magical powers"),
    ("Men", "Eagle", "Planetary mind"),
    ("Cib", "Owl", "Ancient wisdom"),
    ("Caban", "Earth", "Sacred knowledge"),
    ("Etznab", "Flint", "Mirror of truth"),
    ("Cauac", "Storm", "Catalytic energy"),
    ("Ahau", "Sun", "Enlightenment"),
]

HOUSE_SYSTEMS = ["Placidus", "Regiomontanus", "Porphyry", "Equal", "Whole Sign"]

# Earliest / latest dates the planet elements are fitted for.
MIN_DATE = date(1800, 1, 1)
MAX_DATE = date(2050, 12, 31)


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def norm(x):
    return x % 360.0


def sind(x):
    return math.sin(math.radians(x))


def cosd(x):
    return math.cos(math.radians(x))


def tand(x):
    return math.tan(math.radians(x))


def atan2d(y, x):
    return math.degrees(math.atan2(y, x))


def sign_of(lon):
    """(sign name, degree inside the sign) for an ecliptic longitude."""
    lon = norm(lon)
    return SIGNS[int(lon // 30)], lon % 30


# ---------------------------------------------------------------------------
# time
# ---------------------------------------------------------------------------
def julian_day(year, month, day, hour=0, minute=0, second=0):
    """Julian Day for a Gregorian calendar date/time (UT)."""
    if month <= 2:
        year -= 1
        month += 12
    a = math.floor(year / 100)
    b = 2 - a + math.floor(a / 4)
    return (math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1))
            + day + b - 1524.5 + (hour + minute / 60 + second / 3600) / 24)


def delta_t_days(jd):
    """Rough TT-UT (Morrison & Stephenson parabola). Only matters for the Moon,
    and only by a fraction of an arcminute."""
    year = 2000 + (jd - 2451545.0) / 365.25
    u = (year - 1820) / 100
    return (32 * u * u - 20) / 86400.0


def centuries(jd):
    return (jd - 2451545.0) / 36525.0


# ---------------------------------------------------------------------------
# Sun and Moon (tropical, ecliptic of date)
# ---------------------------------------------------------------------------
def sun_longitude(jd_ut, apparent=True):
    t = centuries(jd_ut + delta_t_days(jd_ut))
    l0 = 280.46646 + 36000.76983 * t + 0.0003032 * t * t
    m = 357.52911 + 35999.05029 * t - 0.0001537 * t * t
    c = ((1.914602 - 0.004817 * t - 0.000014 * t * t) * sind(m)
         + (0.019993 - 0.000101 * t) * sind(2 * m)
         + 0.000289 * sind(3 * m))
    lon = l0 + c
    if apparent:
        omega = 125.04 - 1934.136 * t
        lon = lon - 0.00569 - 0.00478 * sind(omega)
    return norm(lon)


# Meeus table 47.A (longitude): D, M, M', F, coefficient (1e-6 deg)
_MOON_TERMS = [
    (0, 0, 1, 0, 6288774), (2, 0, -1, 0, 1274027), (2, 0, 0, 0, 658314),
    (0, 0, 2, 0, 213618), (0, 1, 0, 0, -185116), (0, 0, 0, 2, -114332),
    (2, 0, -2, 0, 58793), (2, -1, -1, 0, 57066), (2, 0, 1, 0, 53322),
    (2, -1, 0, 0, 45758), (0, 1, -1, 0, -40923), (1, 0, 0, 0, -34720),
    (0, 1, 1, 0, -30383), (2, 0, 0, -2, 15327), (0, 0, 1, 2, -12528),
    (0, 0, 1, -2, 10980), (4, 0, -1, 0, 10675), (0, 0, 3, 0, 10034),
    (4, 0, -2, 0, 8548), (2, 1, -1, 0, -7888), (2, 1, 0, 0, -6766),
    (1, 0, -1, 0, -5163), (1, 1, 0, 0, 4987), (2, -1, 1, 0, 4036),
    (2, 0, 2, 0, 3994), (4, 0, 0, 0, 3861), (2, 0, -3, 0, 3665),
    (0, 1, -2, 0, -2689), (2, 0, -1, 2, -2602), (2, -1, -2, 0, 2390),
    (1, 0, 1, 0, -2348), (2, -2, 0, 0, 2236), (0, 1, 2, 0, -2120),
    (0, 2, 0, 0, -2069), (2, -2, -1, 0, 2048), (2, 0, 1, -2, -1773),
    (2, 0, 0, 2, -1595), (4, -1, -1, 0, 1215), (0, 0, 2, 2, -1110),
    (3, 0, -1, 0, -892), (2, 1, 1, 0, -810), (4, -1, -2, 0, 759),
    (0, 2, -1, 0, -713), (2, 2, -1, 0, -700), (2, 1, -2, 0, 691),
    (2, -1, 0, -2, 596), (4, 0, 1, 0, 549), (0, 0, 4, 0, 537),
    (4, -1, 0, 0, 520), (1, 0, -2, 0, -487),
]


def moon_longitude_tt(jd_tt):
    """Geometric Moon longitude (Meeus ch. 47) for a TT Julian Day."""
    t = centuries(jd_tt)
    lp = 218.3164477 + 481267.88123421 * t - 0.0015786 * t * t
    d = 297.8501921 + 445267.1114034 * t - 0.0018819 * t * t
    m = 357.5291092 + 35999.0502909 * t - 0.0001536 * t * t
    mp = 134.9633964 + 477198.8675055 * t + 0.0087414 * t * t
    f = 93.2720950 + 483202.0175233 * t - 0.0036539 * t * t
    a1 = 119.75 + 131.849 * t
    a2 = 53.09 + 479264.290 * t
    e = 1 - 0.002516 * t - 0.0000074 * t * t

    total = 0.0
    for cd, cm, cmp_, cf, coef in _MOON_TERMS:
        term = coef * sind(cd * d + cm * m + cmp_ * mp + cf * f)
        if abs(cm) == 1:
            term *= e
        elif abs(cm) == 2:
            term *= e * e
        total += term
    total += 3958 * sind(a1) + 1962 * sind(lp - f) + 318 * sind(a2)
    return norm(lp + total / 1e6)


def moon_longitude(jd_ut):
    return moon_longitude_tt(jd_ut + delta_t_days(jd_ut))


def mean_lunar_node(jd_ut):
    """Mean ascending node of the Moon (Rahu)."""
    t = centuries(jd_ut + delta_t_days(jd_ut))
    return norm(125.0445479 - 1934.1362891 * t + 0.0020754 * t * t)


# ---------------------------------------------------------------------------
# Planets: JPL approximate Keplerian elements, table 1 (1800-2050 AD)
# a (AU), e, I, L, long. perihelion, long. node  (+ rates per century)
# ---------------------------------------------------------------------------
_ELEMENTS = {
    "Mercury": ((0.38709927, 0.20563593, 7.00497902, 252.25032350, 77.45779628, 48.33076593),
                (0.00000037, 0.00001906, -0.00594749, 149472.67411175, 0.16047689, -0.12534081)),
    "Venus": ((0.72333566, 0.00677672, 3.39467605, 181.97909950, 131.60246718, 76.67984255),
              (0.00000390, -0.00004107, -0.00078890, 58517.81538729, 0.00268329, -0.27769418)),
    "EarthMoon": ((1.00000261, 0.01671123, -0.00001531, 100.46457166, 102.93768193, 0.0),
                  (0.00000562, -0.00004392, -0.01294668, 35999.37244981, 0.32327364, 0.0)),
    "Mars": ((1.52371034, 0.09339410, 1.84969142, -4.55343205, -23.94362959, 49.55953891),
             (0.00001847, 0.00007882, -0.00813131, 19140.30268499, 0.44441088, -0.29257343)),
    "Jupiter": ((5.20288700, 0.04838624, 1.30439695, 34.39644051, 14.72847983, 100.47390909),
                (-0.00011607, -0.00013253, -0.00183714, 3034.74612775, 0.21252668, 0.20469106)),
    "Saturn": ((9.53667594, 0.05386179, 2.48599187, 49.95424423, 92.59887831, 113.66242448),
               (-0.00125060, -0.00050991, 0.00193609, 1222.49362201, -0.41897216, -0.28867794)),
    "Uranus": ((19.18916464, 0.04725744, 0.77263783, 313.23810451, 170.95427630, 74.01692503),
               (-0.00196176, -0.00004397, -0.00242939, 428.48202785, 0.40805281, 0.04240589)),
    "Neptune": ((30.06992276, 0.00859048, 1.77004347, -55.12002969, 44.96476227, 131.78422574),
                (0.00026291, 0.00005105, 0.00035372, 218.45945325, -0.32241464, -0.00508664)),
}

PLANETS = ["Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune"]


def _heliocentric(name, jd_tt):
    """Heliocentric ecliptic x, y, z (AU) in the J2000 ecliptic."""
    base, rate = _ELEMENTS[name]
    t = centuries(jd_tt)
    a, e, inc, mean_lon, peri, node = (b + r * t for b, r in zip(base, rate))
    w = peri - node
    m = (mean_lon - peri + 180) % 360 - 180

    # Kepler's equation, solved in radians
    m_r = math.radians(m)
    ecc = m_r + e * math.sin(m_r)
    for _ in range(30):
        delta = (ecc - e * math.sin(ecc) - m_r) / (1 - e * math.cos(ecc))
        ecc -= delta
        if abs(delta) < 1e-12:
            break

    xp = a * (math.cos(ecc) - e)
    yp = a * math.sqrt(1 - e * e) * math.sin(ecc)
    cw, sw = cosd(w), sind(w)
    cn, sn = cosd(node), sind(node)
    ci, si = cosd(inc), sind(inc)
    x = (cw * cn - sw * sn * ci) * xp + (-sw * cn - cw * sn * ci) * yp
    y = (cw * sn + sw * cn * ci) * xp + (-sw * sn + cw * cn * ci) * yp
    z = (sw * si) * xp + (cw * si) * yp
    return x, y, z


def _precession_since_j2000(jd_tt):
    """General precession in longitude, J2000 ecliptic -> ecliptic of date."""
    t = centuries(jd_tt)
    return 1.396971 * t + 0.0003086 * t * t


def planet_longitude(name, jd_ut):
    """Geocentric tropical longitude of a planet (ecliptic of date)."""
    jd_tt = jd_ut + delta_t_days(jd_ut)
    ex, ey, ez = _heliocentric("EarthMoon", jd_tt)
    px, py, pz = _heliocentric(name, jd_tt)
    dist = math.sqrt((px - ex) ** 2 + (py - ey) ** 2 + (pz - ez) ** 2)
    # light-time: where the planet was when the light left it
    px, py, pz = _heliocentric(name, jd_tt - 0.0057755183 * dist)
    lon = atan2d(py - ey, px - ex)
    return norm(lon + _precession_since_j2000(jd_tt))


def planetary_positions(jd_ut):
    """Tropical longitudes of the Sun, Moon, planets and lunar nodes."""
    pos = {"Sun": sun_longitude(jd_ut), "Moon": moon_longitude(jd_ut)}
    for p in PLANETS:
        pos[p] = planet_longitude(p, jd_ut)
    rahu = mean_lunar_node(jd_ut)
    pos["Rahu"] = rahu
    pos["Ketu"] = norm(rahu + 180)
    return pos


# ---------------------------------------------------------------------------
# Sidereal zodiac
# ---------------------------------------------------------------------------
_LAHIRI_EPOCH_JD = 2435553.5      # 21 March 1956, 0h
_LAHIRI_EPOCH_VALUE = 23.25       # 23 deg 15' 00" (Indian Calendar Reform Committee)


def lahiri_ayanamsa(jd_ut):
    t = centuries(jd_ut)
    t0 = centuries(_LAHIRI_EPOCH_JD)
    p = lambda x: 1.396971 * x + 0.0003086 * x * x
    return _LAHIRI_EPOCH_VALUE + p(t) - p(t0)


def to_sidereal(positions, ayanamsa):
    return {k: norm(v - ayanamsa) for k, v in positions.items()}


def nakshatra(sidereal_moon):
    span = 360 / 27
    lon = norm(sidereal_moon)
    idx = int(lon // span)
    rem = lon % span
    name, lord, meaning = NAKSHATRAS[idx]
    return {"name": name, "lord": lord, "meaning": meaning,
            "pada": int(rem // (span / 4)) + 1, "degree_in_nakshatra": rem}


# ---------------------------------------------------------------------------
# Angles and houses (tropical)
# ---------------------------------------------------------------------------
def obliquity(jd_ut):
    t = centuries(jd_ut)
    return 23.4392911 - 0.0130042 * t - 0.00000016 * t * t


def ramc(jd_ut, longitude):
    """Right ascension of the MC = local sidereal time, in degrees."""
    t = centuries(jd_ut)
    gmst = (280.46061837 + 360.98564736629 * (jd_ut - 2451545.0)
            + 0.000387933 * t * t - t ** 3 / 38710000)
    return norm(gmst + longitude)


def _cusp(ra, pole, eps):
    """Ecliptic longitude where a house circle crosses the ecliptic.
    ra = right ascension where the circle meets the equator, pole = its pole height."""
    return norm(atan2d(sind(ra), cosd(ra) * cosd(eps) - tand(pole) * sind(eps)))


def angles(jd_ut, latitude, longitude):
    eps = obliquity(jd_ut)
    r = ramc(jd_ut, longitude)
    mc = norm(atan2d(sind(r), cosd(r) * cosd(eps)))
    asc = norm(atan2d(cosd(r), -(sind(r) * cosd(eps) + tand(latitude) * sind(eps))))
    return asc, mc, r, eps


def _complete(c):
    """Given cusps 1, 2, 3, 10, 11, 12, fill in their opposites."""
    for i in (1, 2, 3, 10, 11, 12):
        c[(i + 5) % 12 + 1] = norm(c[i] + 180)
    return c


def _porphyry(asc, mc):
    arc = norm(asc - mc)                     # MC -> ASC (houses 10, 11, 12)
    c = {1: asc, 10: mc,
         11: norm(mc + arc / 3), 12: norm(mc + 2 * arc / 3)}
    rest = 180 - arc                         # ASC -> IC (houses 1, 2, 3)
    c[2] = norm(asc + rest / 3)
    c[3] = norm(asc + 2 * rest / 3)
    return _complete(c)


def _placidus(r, lat, eps, asc, mc):
    """Trisect each point's diurnal / nocturnal semi-arc (time-based)."""
    def solve(fraction, above):
        lon = norm(mc + 90 * fraction + (0 if above else 90))  # starting guess
        for _ in range(60):
            dec = math.degrees(math.asin(sind(eps) * sind(lon)))
            x = tand(lat) * tand(dec)
            if abs(x) > 1:
                raise ValueError("circumpolar")
            ad = math.degrees(math.asin(x))
            if above:
                ra = r + fraction * (90 + ad)
            else:
                ra = r + 180 - (1 - fraction) * (90 - ad)
            new = norm(atan2d(sind(ra), cosd(ra) * cosd(eps)))
            if abs((new - lon + 180) % 360 - 180) < 1e-7:
                return new
            lon = new
        return lon

    c = {1: asc, 10: mc,
         11: solve(1 / 3, True), 12: solve(2 / 3, True),
         2: solve(1 / 3, False), 3: solve(2 / 3, False)}
    return _complete(c)


def _regiomontanus(r, lat, eps, asc, mc):
    """Equal 30-degree divisions of the celestial equator."""
    c = {1: asc, 10: mc}
    for house, h in ((11, 30), (12, 60), (2, 120), (3, 150)):
        pole = math.degrees(math.atan(tand(lat) * sind(h)))
        c[house] = _cusp(r + h, pole, eps)
    return _complete(c)


def houses(jd_ut, latitude, longitude, system="Placidus"):
    """Return (cusps {'1'..'12': lon}, ascendant, mc, system actually used).
    Placidus can't be drawn inside the polar circles; Porphyry is used there."""
    asc, mc, r, eps = angles(jd_ut, latitude, longitude)
    used = system
    if system == "Whole Sign":
        start = int(asc // 30) * 30
        c = {i: norm(start + (i - 1) * 30) for i in range(1, 13)}
    elif system == "Equal":
        c = {i: norm(asc + (i - 1) * 30) for i in range(1, 13)}
    elif system == "Regiomontanus":
        c = _regiomontanus(r, latitude, eps, asc, mc)
    elif system == "Porphyry":
        c = _porphyry(asc, mc)
    else:
        try:
            c = _placidus(r, latitude, eps, asc, mc)
            used = "Placidus"
        except ValueError:
            c = _porphyry(asc, mc)
            used = "Porphyry (Placidus is undefined this close to the pole)"
    return {str(k): c[k] for k in range(1, 13)}, asc, mc, used


# ---------------------------------------------------------------------------
# Chinese Four Pillars (Bazi)
# ---------------------------------------------------------------------------
def _pillar(stem, branch):
    return HEAVENLY_STEMS[stem % 10], EARTHLY_BRANCHES[branch % 12]


def four_pillars(local_dt, jd_ut):
    """Year and month change on the solar terms (Lichun = Sun at 315 deg);
    day and hour use the local civil date and clock, with the day starting
    at midnight."""
    sun = sun_longitude(jd_ut)

    year = local_dt.year
    if local_dt.month <= 2 and 270 <= sun < 315:
        year -= 1                           # still before Lichun
    year_stem = (year - 4) % 10
    year_branch = (year - 4) % 12

    month_idx = int(((sun - 315) % 360) // 30)  # 0 = Tiger month (from Lichun)
    month_branch = (2 + month_idx) % 12
    month_stem = ((year_stem % 5) * 2 + 2 + month_idx) % 10

    jdn = int(round(julian_day(local_dt.year, local_dt.month, local_dt.day, 12)))
    day_idx = (jdn + 49) % 60                # 0 = Jia-Zi
    day_stem, day_branch = day_idx % 10, day_idx % 12

    hour_branch = ((local_dt.hour + 1) // 2) % 12
    hour_stem = ((day_stem % 5) * 2 + hour_branch) % 10

    return {
        "year": _pillar(year_stem, year_branch),
        "month": _pillar(month_stem, month_branch),
        "day": _pillar(day_stem, day_branch),
        "hour": _pillar(hour_stem, hour_branch),
    }


# ---------------------------------------------------------------------------
# Mayan Tzolkin (GMT correlation 584283: 13.0.0.0.0 = 4 Ahau)
# ---------------------------------------------------------------------------
GMT_CORRELATION = 584283


def tzolkin(local_date):
    jdn = int(round(julian_day(local_date.year, local_date.month, local_date.day, 12)))
    days = jdn - GMT_CORRELATION
    tone = (days + 3) % 13 + 1
    sign_idx = (days + 19) % 20             # 0 = Imix ... 19 = Ahau
    # kin 1..260: the number that has this tone and this day sign
    kin = next(k for k in range(1, 261)
               if (k - 1) % 13 + 1 == tone and (k - 1) % 20 == sign_idx)
    name, glyph, meaning = MAYAN_DAY_SIGNS[sign_idx]
    return {"kin": kin, "day_sign": name, "glyph": glyph,
            "meaning": meaning, "galactic_tone": tone}


# ---------------------------------------------------------------------------
# self-checks against published values and known events
# ---------------------------------------------------------------------------
def _sep(a, b):
    return abs((a - b + 180) % 360 - 180)


def _self_test():
    # Meeus example 47.a: Moon on 1992 Apr 12, 0h TD -> 133.162655
    assert _sep(moon_longitude_tt(2448724.5), 133.162655) < 0.002
    # Meeus example 25.a: Sun on 1992 Oct 13, 0h TD -> apparent 199.90895
    jd = 2448908.5 - delta_t_days(2448908.5)
    assert _sep(sun_longitude(jd), 199.90895) < 0.003

    # Equinox / solstice
    assert _sep(sun_longitude(julian_day(2000, 3, 20, 7, 35)), 0) < 0.02
    assert _sep(sun_longitude(julian_day(2000, 6, 21, 1, 48)), 90) < 0.02

    # Great conjunction 21 Dec 2020 ~18h UT, both at about 300.5 (0 deg 29' Aquarius)
    jd = julian_day(2020, 12, 21, 18)
    assert _sep(planet_longitude("Jupiter", jd), 300.5) < 0.25
    assert _sep(planet_longitude("Saturn", jd), 300.5) < 0.25

    # Transit of Venus 6 Jun 2012 and of Mercury 11 Nov 2019: on the Sun
    jd = julian_day(2012, 6, 6, 1, 30)
    assert _sep(planet_longitude("Venus", jd), sun_longitude(jd)) < 0.1
    jd = julian_day(2019, 11, 11, 15, 20)
    assert _sep(planet_longitude("Mercury", jd), sun_longitude(jd)) < 0.1

    # Mars opposition 28 Aug 2003: Mars opposite the Sun
    jd = julian_day(2003, 8, 28, 18)
    assert abs(_sep(planet_longitude("Mars", jd), sun_longitude(jd)) - 180) < 0.3

    # Mercury / Venus never far from the Sun; Mars retrogrades
    worst_me = worst_ve = 0
    for k in range(0, 365 * 40, 3):
        jd = 2447892.5 + k
        s = sun_longitude(jd)
        worst_me = max(worst_me, _sep(planet_longitude("Mercury", jd), s))
        worst_ve = max(worst_ve, _sep(planet_longitude("Venus", jd), s))
    assert worst_me < 28.5 and worst_ve < 47.5, (worst_me, worst_ve)

    # Lahiri: 23 deg 15' on 21 Mar 1956, ~23.15 in 1950, ~23.86 in 2000
    assert abs(lahiri_ayanamsa(_LAHIRI_EPOCH_JD) - 23.25) < 1e-9
    assert abs(lahiri_ayanamsa(julian_day(1950, 1, 1)) - 23.16) < 0.02
    assert abs(lahiri_ayanamsa(julian_day(2000, 1, 1)) - 23.86) < 0.02

    # Tzolkin: 21 Dec 2012 (13.0.0.0.0) = 4 Ahau, kin 160
    tz = tzolkin(date(2012, 12, 21))
    assert (tz["galactic_tone"], tz["day_sign"], tz["kin"]) == (4, "Ahau", 160), tz

    # Bazi: 1 Oct 1949 is a Jia-Zi day; 1 Jan 2000 is Wu-Wu
    p = four_pillars(datetime(1949, 10, 1, 12), julian_day(1949, 10, 1, 4))
    assert (p["day"][0][0], p["day"][1][0]) == ("Jia", "Zi")
    p = four_pillars(datetime(2000, 1, 1, 12), julian_day(2000, 1, 1, 12))
    assert (p["day"][0][0], p["day"][1][0]) == ("Wu", "Wu")
    # ...and it is still a Ji-Mao year (2000 Geng-Chen starts 4 Feb), Bing-Zi month
    assert (p["year"][0][0], p["year"][1][0]) == ("Ji", "Mao")
    assert (p["month"][0][0], p["month"][1][0]) == ("Bing", "Zi")
    # 10 Feb 2000: Geng-Chen year, Wu-Yin month
    p = four_pillars(datetime(2000, 2, 10, 12), julian_day(2000, 2, 10, 12))
    assert (p["year"][0][0], p["year"][1][0]) == ("Geng", "Chen")
    assert (p["month"][0][0], p["month"][1][0]) == ("Wu", "Yin")

    # Houses: MC on cusp 10, ASC on cusp 1, opposite cusps 180 apart,
    # and the quadrant systems agree on the equator.
    jd = julian_day(2000, 6, 1, 6)
    for system in HOUSE_SYSTEMS:
        c, asc, mc, _ = houses(jd, 51.5, -0.12, system)
        if system in ("Placidus", "Regiomontanus", "Porphyry"):
            assert _sep(c["10"], mc) < 1e-6 and _sep(c["1"], asc) < 1e-6
        for i in range(1, 7):
            assert _sep(c[str(i + 6)], c[str(i)]) > 179.999
        # cusps run in zodiac order
        steps = [norm(c[str(i % 12 + 1)] - c[str(i)]) for i in range(1, 13)]
        assert abs(sum(steps) - 360) < 1e-6, (system, steps)
    pl, *_ = houses(jd, 0.0, 10.0, "Placidus")
    rg, *_ = houses(jd, 0.0, 10.0, "Regiomontanus")
    assert all(_sep(pl[k], rg[k]) < 1e-5 for k in pl)
    # Placidus definition: cusp 11 sits 1/3 of its diurnal semi-arc past the MC
    c, asc, mc, _ = houses(jd, 51.5, -0.12, "Placidus")
    eps, r = obliquity(jd), ramc(jd, -0.12)
    lon = c["11"]
    dec = math.degrees(math.asin(sind(eps) * sind(lon)))
    ra = norm(atan2d(sind(lon) * cosd(eps), cosd(lon)))
    ad = math.degrees(math.asin(tand(51.5) * tand(dec)))
    assert _sep(ra, r + (90 + ad) / 3) < 1e-5
    # Regiomontanus cusps lie on their house circles: the great circle through
    # the north/south points of the horizon and the equator point RAMC + h
    c, *_ = houses(jd, 51.5, -0.12, "Regiomontanus")
    north = (-sind(51.5) * cosd(r), -sind(51.5) * sind(r), cosd(51.5))
    for house, h in (("11", 30), ("12", 60), ("2", 120), ("3", 150)):
        lon = c[house]
        v = (cosd(lon), sind(lon) * cosd(eps), sind(lon) * sind(eps))   # equatorial
        q = (cosd(r + h), sind(r + h), 0.0)
        n = (north[1] * q[2] - north[2] * q[1], north[2] * q[0] - north[0] * q[2],
             north[0] * q[1] - north[1] * q[0])
        assert abs(sum(a * b for a, b in zip(v, n))) < 1e-9, house
    # Polar latitude falls back cleanly
    _, _, _, used = houses(jd, 75.0, 20.0, "Placidus")
    assert used.startswith(("Placidus", "Porphyry"))

    print("astro_engine: all self-checks passed")


if __name__ == "__main__":
    _self_test()
