#!/usr/bin/env python3
"""
Astro_Reveal - your sky, the moment you arrived
===============================================
Streamlit app: Western, Vedic, Chinese and Maya astrology from one birth date,
time and place, made to be tapped and played with rather than read.

- astro_engine.py    the chart maths (run it for its self-checks)
- astro_charts.py    every drawing: cards, wheel, sky map, explorer, score ring
- astro_content.py   the words, symbols and the compatibility game
- places.py          offline birthplace search and timezone lookup
- sky_data.py        stars and constellation figures (d3-celestial, BSD)
- this file          the pages

The look (colours, fonts, corners) lives in .streamlit/config.toml.
Run:  streamlit run astro_calculator.py
"""

import hmac
import os
from datetime import date, datetime, time, timedelta, timezone
from html import escape

import pandas as pd
import pytz
import streamlit as st

import astro_charts as ac
import astro_content as C
import astro_engine as ae
import places
from feedback_collector import (ELEMENT_TRAITS, build_feedback_form, chart_id_for,
                                record_response, summarize_log)
from llm_interpreter import build_chart_summary, generate_llm_interpretation

try:
    if "GEMINI_API_KEY" in st.secrets:
        os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
except Exception:
    pass

try:
    import folium
    from streamlit_folium import st_folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

FEEDBACK_LOG = "feedback_log.jsonl"
DEFAULT_PLACE = {"label": "Kathmandu, Nepal", "lat": 27.7017, "lon": 85.3206,
                 "tz": "Asia/Kathmandu", "tz_from": "Kathmandu"}
TILE_SHAPES = ["✦", "☾", "✺", "❖"]

st.set_page_config(page_title="Astro Reveal", page_icon="✨", layout="wide",
                   initial_sidebar_state="collapsed")


# ===========================================================================
#  STYLE: colours and fonts come from .streamlit/config.toml; this adds the
#  card shapes and sizes Streamlit can't express on its own
# ===========================================================================
APP_CSS = f"""
<style>
[data-testid="stMainBlockContainer"], .block-container {{
  max-width: 1360px; padding-top: 1.6rem; padding-bottom: 5rem; }}
[data-testid="stHeader"] {{ background: transparent; }}
.ar-wordmark {{ font-family: {ac.SERIF_FONT}; font-weight: 600; font-size: 1.5rem; color: {ac.INK};
  display: flex; align-items: center; gap: .5rem; }}
.ar-hero-title {{ font-family: {ac.SERIF_FONT}; font-weight: 650; font-size: clamp(2.6rem, 5.2vw, 4.6rem);
  line-height: 1.02; letter-spacing: -.025em; color: {ac.INK}; margin: 1.4rem 0 .6rem; text-wrap: balance; }}
.ar-hero-sub {{ font-size: 1.25rem; color: {ac.MUTED}; margin: 0 0 1.8rem; }}
.ar-section {{ font-family: {ac.SERIF_FONT}; font-weight: 600; font-size: 2.1rem; color: {ac.INK};
  margin: 3rem 0 1rem; letter-spacing: -.01em; }}
.ar-section small {{ display: block; font-family: {ac.TEXT_FONT}; font-weight: 400; font-size: 1.05rem;
  color: {ac.MUTED}; margin-top: .3rem; letter-spacing: 0; }}
[class*="st-key-card_"], [class*="st-key-panel_"] {{ background: {ac.CARD}; border-radius: 1.6rem;
  padding: 1.3rem 1.4rem 1.4rem; box-shadow: 0 12px 32px -20px rgba(34,30,82,.35); }}
[class*="st-key-card_"] {{ min-height: 13rem; }}
.ar-mini-art {{ display: flex; justify-content: center; margin-top: .4rem; }}
.ar-mini-art svg {{ width: 100%; max-width: 260px; height: auto; }}
.ar-card-title {{ font-family: {ac.SERIF_FONT}; font-weight: 600; font-size: 1.55rem; color: {ac.INK};
  display: flex; align-items: center; gap: .6rem; margin-bottom: .2rem; }}
.ar-card-title span {{ font-size: 2rem; }}
.ar-pill {{ display: inline-flex; align-items: center; gap: .45rem; border-radius: 999px;
  padding: .45rem 1rem; font-weight: 600; font-size: 1.05rem; }}
.ar-hint {{ color: {ac.MUTED}; font-size: .98rem; margin: .2rem 0 0; }}
.st-key-cta button {{ min-height: 4.2rem; border-radius: 999px; }}
.st-key-cta button p {{ font-size: 1.3rem; font-weight: 650; }}
.st-key-game button {{ min-height: 9.5rem; border-radius: 1.6rem; background: {ac.CARD};
  border: 2px solid {ac.LINE}; box-shadow: 0 10px 28px -20px rgba(34,30,82,.4);
  transition: transform .15s ease, border-color .15s ease; }}
.st-key-game button:hover {{ transform: translateY(-3px); border-color: {ac.VIOLET}; color: {ac.INK}; }}
.st-key-game button p {{ font-size: 1.5rem; line-height: 1.35; font-weight: 600; text-align: center; }}
.ar-pips {{ display: flex; gap: .5rem; margin: .4rem 0 1.4rem; }}
.ar-pips i {{ width: 2.6rem; height: .55rem; border-radius: 999px; background: {ac.LINE}; }}
.ar-pips i.on {{ background: {ac.VIOLET}; }}
.ar-summary {{ font-size: 1.05rem; color: {ac.MUTED}; text-align: right; margin-top: .4rem; }}
.ar-summary b {{ color: {ac.INK}; }}
.ar-cap {{ color: {ac.MUTED}; text-align: center; font-size: 1rem; margin: .6rem 0 0; }}
.ar-big-line {{ font-family: {ac.SERIF_FONT}; font-weight: 600; font-size: 2rem; line-height: 1.15;
  color: {ac.INK}; margin: .2rem 0 .6rem; }}
.ar-note-list {{ display: flex; flex-direction: column; gap: .7rem; margin-top: .4rem; }}
.ar-note {{ display: flex; gap: .8rem; align-items: center; background: {ac.PAPER}; border-radius: 1.1rem;
  padding: .8rem 1rem; font-size: 1.08rem; color: {ac.INK}; }}
.ar-note b {{ font-size: 1.6rem; line-height: 1; min-width: 2.4rem; text-align: center; }}
.ar-moon {{ font-size: 6rem; line-height: 1; text-align: center; }}
.ar-ticket {{ font-size: 1.12rem; color: {ac.INK}; line-height: 1.7; margin: .3rem 0 1rem; }}
.ar-ticket span {{ color: {ac.MUTED}; }}
iframe[title="streamlit_folium.st_folium"] {{ border-radius: 1.4rem; }}
.ar-footer {{ color: {ac.MUTED}; font-size: .88rem; margin-top: 4rem; border-top: 1px solid {ac.LINE};
  padding-top: 1rem; }}
/* Preserve the existing visual design while making keyboard focus easier to see. */
.st-key-game button:focus-visible, .st-key-cta button:focus-visible {{ outline: 3px solid {ac.VIOLET}; outline-offset: 3px; }}
/* Respect OS-level reduced-motion settings without changing normal interactions. */
@media (prefers-reduced-motion: reduce) {{
  .st-key-game button, .st-key-cta button {{ transition: none !important; }}
  .st-key-game button:hover {{ transform: none !important; }}
}}
@media (max-width: 900px) {{ .ar-summary {{ text-align: left; }} }}
</style>
"""


def inject_css():
    st.html(ac.STYLE + APP_CSS)


def html(markup):
    st.html(markup)


def section(title, sub=None):
    html(f'<div class="ar-section">{title}{f"<small>{sub}</small>" if sub else ""}</div>')


# ===========================================================================
#  TEXT
# ===========================================================================
SIGN_MEANINGS = {
    "Aries": "Dynamic, pioneering, leadership qualities, courageous, impulsive, competitive nature",
    "Taurus": "Stable, practical, determined, artistic, material security focus, stubborn tendencies",
    "Gemini": "Intellectual, communicative, versatile, curious, dual nature, restless mind",
    "Cancer": "Emotional, nurturing, intuitive, protective, family-oriented, moody fluctuations",
    "Leo": "Creative, confident, dramatic, generous, attention-seeking, natural performer",
    "Virgo": "Analytical, perfectionist, service-oriented, practical, critical, health-conscious",
    "Libra": "Harmonious, diplomatic, artistic, relationship-focused, indecisive, beauty-loving",
    "Scorpio": "Intense, transformative, mysterious, passionate, secretive, powerful regeneration",
    "Sagittarius": "Philosophical, adventurous, optimistic, truth-seeking, freedom-loving, blunt",
    "Capricorn": "Ambitious, disciplined, traditional, responsible, status-conscious, persistent",
    "Aquarius": "Independent, innovative, humanitarian, unconventional, detached, visionary",
    "Pisces": "Intuitive, compassionate, spiritual, dreamy, escapist tendencies, artistic",
}

PLANET_MEANINGS = {
    "Sun": "Core identity, ego, vitality, father figure, leadership, self-expression",
    "Moon": "Emotions, mind, mother figure, intuition, habits, subconscious patterns",
    "Mercury": "Communication, intellect, learning, siblings, short travels, adaptability",
    "Venus": "Love, beauty, relationships, creativity, luxury, feminine energy",
    "Mars": "Energy, action, courage, conflict, passion, masculine drive",
    "Jupiter": "Wisdom, spirituality, expansion, good fortune, higher learning, optimism",
    "Saturn": "Discipline, limitations, karma, hard work, structure, life lessons",
    "Uranus": "Change, independence, originality, sudden breaks, invention",
    "Neptune": "Imagination, ideals, spirituality, dissolving boundaries, illusion",
    "Rahu": "North node: hunger for growth, ambition, the unfamiliar",
    "Ketu": "South node: detachment, old talents, letting go",
}


def fmt_place(lat, lon):
    return (f"{abs(lat):.4f}° {'N' if lat >= 0 else 'S'}, "
            f"{abs(lon):.4f}° {'E' if lon >= 0 else 'W'}")


def long_date(d):
    return f"{d.day} {d.strftime('%B %Y')}"


# ===========================================================================
#  PLACES
# ===========================================================================
@st.cache_resource(show_spinner="Loading the list of places…")
def place_index():
    return places.load_index()


def place_from(p):
    return {"label": p.label, "lat": p.lat, "lon": p.lon, "tz": p.timezone, "tz_from": p.name}


def place_from_point(lat, lon):
    """A clicked or typed point: timezone from the nearest listed town."""
    ix = place_index()
    near = ix.nearest(lat, lon) if ix else None
    if near:
        km = places.distance_km(lat, lon, near.lat, near.lon)
        label = f"Near {near.label}" if km > 3 else near.label
        return {"label": label, "lat": lat, "lon": lon, "tz": near.timezone, "tz_from": near.name}
    return {"label": "Chosen point", "lat": lat, "lon": lon, "tz": None, "tz_from": None}


def set_place(place, recentre=False, zoom=None):
    s = st.session_state
    s.place = place
    if recentre:
        s.map_center = [place["lat"], place["lon"]]
        if zoom:
            s.map_zoom = zoom


# ===========================================================================
#  CHART
# ===========================================================================
def compute_chart(birth_date, birth_time, time_known, tz_name, place, house_system):
    local = pytz.timezone(tz_name).localize(datetime.combine(birth_date, birth_time))
    utc = local.astimezone(pytz.UTC)
    jd = ae.julian_day(utc.year, utc.month, utc.day, utc.hour, utc.minute, utc.second)

    tropical = ae.planetary_positions(jd)
    tomorrow = ae.planetary_positions(jd + 1)
    retrograde = [p for p in ae.PLANETS
                  if ((tomorrow[p] - tropical[p] + 540) % 360 - 180) < 0]
    ayanamsa = ae.lahiri_ayanamsa(jd)
    vedic = ae.to_sidereal(tropical, ayanamsa)

    r = {
        "birth_data": {"date": str(birth_date),
                       "time": birth_time.strftime("%H:%M") if time_known else "unknown",
                       "lat": place["lat"], "lon": place["lon"], "timezone": tz_name},
        "place_label": place["label"],
        "date_obj": birth_date,
        "time_known": time_known,
        "utc": utc.strftime("%Y-%m-%d %H:%M UTC"),
        "jd": jd,
        "tropical_positions": tropical,
        "vedic_positions": vedic,
        "retrograde": retrograde,
        "ayanamsa": ayanamsa,
        "nakshatra": ae.nakshatra(vedic["Moon"]),
        "four_pillars": ae.four_pillars(local, jd),
        "tzolkin": ae.tzolkin(birth_date),
        "include_houses": time_known,
        "house_system": house_system,
        "houses": None, "ascendant": None, "mc": None,
        "vedic_ascendant": None, "house_system_used": None,
    }
    if time_known:
        cusps, asc, mc, used = ae.houses(jd, place["lat"], place["lon"], house_system)
        r.update(houses=cusps, ascendant=asc, mc=mc, house_system_used=used,
                 vedic_ascendant=(asc - ayanamsa) % 360)
    return r


def chart_summary(r):
    """The structured chart handed to the AI reading and the blind test."""
    return build_chart_summary(r["birth_data"], r["vedic_positions"],
                               r["tropical_positions"], r["four_pillars"],
                               r["tzolkin"], r["nakshatra"], ascendant=r["ascendant"])


def positions_table(positions, cusps=None, retrograde=()):
    rows = []
    for planet, lon in positions.items():
        row = {"Planet": planet, "Sign": ac.SIGNS[ac.sign_index(lon)],
               "Position": ac.fmt_deg(lon) + (" Rx" if planet in retrograde else "")}
        if cusps:
            row["House"] = ac.house_of(lon, cusps)
        rows.append(row)
    return pd.DataFrame(rows)


# ===========================================================================
#  TEXT REPORT
# ===========================================================================
def generate_report_text(r):
    b = r["birth_data"]
    fp, tz = r["four_pillars"], r["tzolkin"]
    nak = r["nakshatra"]
    sun_sign = ac.SIGNS[ac.sign_index(r["tropical_positions"]["Sun"])]
    moon_sign = ac.SIGNS[ac.sign_index(r["tropical_positions"]["Moon"])]
    rule = "=" * 72

    out = ["ASTRO REVEAL - BIRTH CHART REPORT", "", "Birth details",
           f"  Date:     {b['date']}"]
    if r["time_known"]:
        out.append(f"  Time:     {b['time']} ({b['timezone']}) = {r['utc']}")
    else:
        out.append("  Time:     unknown (positions worked out for 12:00 local time;")
        out.append("            the Moon may be up to about 7 degrees off, and there")
        out.append("            is no Rising sign, houses or hour pillar)")
    out.append(f"  Place:    {r['place_label']} ({fmt_place(b['lat'], b['lon'])})")
    if r["time_known"]:
        out.append(f"  Houses:   {r['house_system_used']}")

    out += ["", rule, "WESTERN (TROPICAL)", rule, ""]
    if r["time_known"]:
        asc_sign = ac.SIGNS[ac.sign_index(r["ascendant"])]
        mc_sign = ac.SIGNS[ac.sign_index(r["mc"])]
        out += [f"Rising:     {asc_sign} {ac.fmt_deg(r['ascendant'])}",
                f"            {SIGN_MEANINGS[asc_sign]}",
                f"Midheaven:  {mc_sign} {ac.fmt_deg(r['mc'])}", ""]
    out += [f"Sun sign:   {sun_sign}", f"            {SIGN_MEANINGS[sun_sign]}",
            f"Moon sign:  {moon_sign}", f"            {SIGN_MEANINGS[moon_sign]}", "",
            "Planets:"]
    for planet, lon in r["tropical_positions"].items():
        line = f"  {planet:<8} {ac.SIGNS[ac.sign_index(lon)]:<12} {ac.fmt_deg(lon):>7}"
        if planet in r["retrograde"]:
            line += "  retrograde"
        if r["time_known"]:
            line += f"  {ac.ordinal(ac.house_of(lon, r['houses']))} house"
        out.append(line)
    aspects = ac.find_aspects(r["tropical_positions"])
    if aspects:
        out += ["", "Aspects:"]
        for a, bb, name, orb, _ in aspects:
            out.append(f"  {a} {name} {bb} (orb {orb:.1f} deg)")
    if r["time_known"]:
        out += ["", f"House cusps ({r['house_system_used']}):"]
        for h in range(1, 13):
            lon = r["houses"][str(h)]
            out.append(f"  {h:>2}  {ac.SIGNS[ac.sign_index(lon)]:<12} {ac.fmt_deg(lon):>7}")

    out += ["", rule, "VEDIC (SIDEREAL, LAHIRI)", rule, "",
            f"Ayanamsa:   {r['ayanamsa']:.4f} deg"]
    if r["time_known"]:
        lagna = ac.SIGNS[ac.sign_index(r["vedic_ascendant"])]
        out.append(f"Lagna:      {lagna} {ac.fmt_deg(r['vedic_ascendant'])}")
    out.append(f"Nakshatra:  {nak['name']} (lord {nak['lord']}), pada {nak['pada']}: {nak['meaning']}")
    out += ["", "Planets:"]
    for planet, lon in r["vedic_positions"].items():
        out.append(f"  {planet:<8} {ac.SIGNS[ac.sign_index(lon)]:<12} {ac.fmt_deg(lon):>7}")
        out.append(f"           {PLANET_MEANINGS.get(planet, '')}")

    def pillar(name):
        if name == "hour" and not r["time_known"]:
            return "unknown (needs a birth time)"
        (stem, element), (branch, animal) = fp[name]
        return f"{stem} {element} / {branch} {animal}"

    dm = fp["day"][0][1]
    out += ["", rule, "CHINESE FOUR PILLARS (BAZI)", rule, "",
            f"Year:   {pillar('year')}", f"Month:  {pillar('month')}",
            f"Day:    {pillar('day')}", f"Hour:   {pillar('hour')}", "",
            f"Day Master: {fp['day'][0][0]} ({dm}). {ELEMENT_TRAITS.get(dm, '')}",
            "", rule, "MAYA TZOLKIN", rule, "",
            f"{tz['galactic_tone']} {tz['day_sign']} ({tz['glyph']}), kin {tz['kin']}: {tz['meaning']}",
            "", rule, "HOW THIS WAS WORKED OUT", rule, "",
            "Sun and Moon from Meeus' algorithms, planets from JPL's Keplerian",
            "elements (1800-2050), typically within 0.01-0.2 degrees. Rahu/Ketu are",
            "the mean lunar nodes. Bazi years and months change on the solar terms.",
            "The Tzolkin uses the GMT correlation (584283).", "",
            "Astrology describes tendencies and themes, not fixed fate. Use it for",
            "reflection, not for major life decisions.", ""]
    return "\n".join(out)


# ===========================================================================
#  STEP 1: BIRTH DETAILS
# ===========================================================================
FORM_KEYS = ("bd", "bt", "bt_unknown", "place_query", "house_system")


def init_state():
    s = st.session_state
    s.setdefault("place", dict(DEFAULT_PLACE))
    s.setdefault("map_origin", [s.place["lat"], s.place["lon"]])
    s.setdefault("map_center", list(s.map_origin))
    s.setdefault("map_zoom", 6)
    s.setdefault("form_memory", {"bd": None, "bt": time(12, 0), "bt_unknown": False,
                                 "place_query": "", "house_system": "Placidus"})
    # widgets forget their values while hidden; bring them back from memory
    for k in FORM_KEYS:
        if k not in s:
            s[k] = s.form_memory[k]


def sun_sign_on(d):
    """Sun sign for a date (at midday UTC; close enough for a preview)."""
    return C.sign(ae.sun_longitude(ae.julian_day(d.year, d.month, d.day, 12)))


def pill(text, colours):
    _, base, tint, ink = colours
    return f'<span class="ar-pill" style="background:{tint};color:{ink}">{text}</span>'


def date_card():
    with st.container(key="card_date"):
        html('<div class="ar-card-title"><span>🎂</span>Birthday</div>')
        d = st.date_input("Birthday", key="bd", min_value=ae.MIN_DATE, max_value=ae.MAX_DATE,
                          label_visibility="collapsed", format="DD/MM/YYYY")
        if d:
            name, element, _, emoji, _, _ = sun_sign_on(d)
            html(pill(f"☀️ That makes you a {name} {emoji}", C.ELEMENTS[element]))
            html(f'<div class="ar-mini-art">{ac.constellation_svg(C.SIGN_NAMES.index(name), 280, 110)}</div>')
        else:
            html('<p class="ar-hint">Pick the day you were born.</p>')


def time_card():
    s = st.session_state
    with st.container(key="card_time"):
        html('<div class="ar-card-title"><span>⏰</span>Time</div>')
        unknown = s.get("bt_unknown", False)
        st.time_input("Time of birth", key="bt", step=60, disabled=unknown,
                      label_visibility="collapsed")
        st.toggle("I don't know the time", key="bt_unknown")
        html('<p class="ar-hint">' + ("No problem. We'll use midday and skip your Rising sign."
                                      if unknown else "Even roughly helps: it sets your Rising sign.")
             + '</p>')


def place_card():
    s = st.session_state
    ix = place_index()
    with st.container(key="card_place"):
        html('<div class="ar-card-title"><span>📍</span>Birthplace</div>')
        query = st.text_input("Birthplace", key="place_query", label_visibility="collapsed",
                              placeholder="Type a town, e.g. Pokhara")
        if ix is None:
            html('<p class="ar-hint">Place search isn\'t available. Tap the map instead.</p>')
        elif query.strip():
            results = ix.search(query)
            if results:
                labels = [p.label for p in results]
                dupes = {lab for lab in labels if labels.count(lab) > 1}
                pick = st.selectbox(
                    "Matches", range(len(results)), key="place_pick_" + places.fold(query),
                    format_func=lambda i: labels[i] + (f" ({fmt_place(results[i].lat, results[i].lon)})"
                                                       if labels[i] in dupes else ""),
                    label_visibility="collapsed")
                chosen = results[pick]
                # only act when the search or the choice changes, so a later tap on
                # the map isn't undone by the same search result on the next run
                pick_id = (places.fold(query), chosen.gid)
                if s.get("applied_pick") != pick_id:
                    s.applied_pick = pick_id
                    set_place(place_from(chosen), recentre=True, zoom=10)
            else:
                html('<p class="ar-hint">Not in the list. Try a nearby bigger town, then tap the map.</p>')
        p = s.place
        html(f'<p class="ar-hint">📌 {escape(p["label"])}<br>Timezone {escape(chosen_timezone())}</p>')


def birth_map():
    s = st.session_state
    if not FOLIUM_AVAILABLE:
        st.info("The map needs the folium and streamlit-folium packages.")
        return
    pin = folium.FeatureGroup(name="Birthplace")
    folium.CircleMarker([s.place["lat"], s.place["lon"]], radius=11, color=ac.CARD, weight=3,
                        fill=True, fill_color=ac.VIOLET, fill_opacity=1,
                        tooltip=s.place["label"]).add_to(pin)
    base = folium.Map(location=s.map_origin, zoom_start=6, tiles="OpenStreetMap",
                      control_scale=True)
    base.get_root().header.add_child(folium.Element(
        "<style>.leaflet-tile-pane{filter:saturate(.5) brightness(1.04) hue-rotate(-10deg)}"
        f".leaflet-container{{background:{ac.PAPER};cursor:crosshair}}</style>"))
    out = st_folium(base, key="birth_map", center=s.map_center, zoom=s.map_zoom,
                    feature_group_to_add=pin, returned_objects=["last_clicked"],
                    height=360, use_container_width=True)
    click = (out or {}).get("last_clicked")
    if click:
        point = (round(click["lat"], 4), round((click["lng"] + 180) % 360 - 180, 4))
        if point != s.get("last_click"):
            s.last_click = point
            set_place(place_from_point(*point))
            st.rerun()


def chart_settings():
    s = st.session_state
    with st.expander("More options"):
        st.selectbox("House system", ae.HOUSE_SYSTEMS, key="house_system",
                     help="Placidus is the most widely used. Whole Sign is traditional in Vedic astrology.")
        zones = pytz.common_timezones
        detected = s.place.get("tz") or "UTC"
        st.selectbox("Timezone", zones, index=zones.index(detected) if detected in zones else 0,
                     key="tz_" + detected, help="Set from the birthplace, daylight saving included.")
        c1, c2 = st.columns(2)
        lat = c1.number_input("Latitude", -90.0, 90.0, float(s.place["lat"]), 0.0001,
                              format="%.4f", key="lat_input")
        lon = c2.number_input("Longitude", -180.0, 180.0, float(s.place["lon"]), 0.0001,
                              format="%.4f", key="lon_input")
        if st.button("Use these coordinates"):
            set_place(place_from_point(lat, lon), recentre=True, zoom=10)
            st.rerun()


def chosen_timezone():
    s = st.session_state
    detected = s.place.get("tz") or "UTC"
    return s.get("tz_" + detected, detected)


def birth_form():
    s = st.session_state
    html('<div class="ar-hero-title">Your sky, the moment you arrived.</div>'
         '<p class="ar-hero-sub">Three quick answers, then a little game, then your chart.</p>')
    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        date_card()
    with c2:
        time_card()
    with c3:
        place_card()
    st.write("")
    left, right = st.columns([1.7, 1], gap="large")
    with left:
        birth_map()
        st.caption("Tap the map to put the pin exactly where you were born.")
    with right:
        with st.container(key="panel_ticket"):
            html('<div class="ar-card-title"><span>🎟️</span>Ready?</div>')
            when = (long_date(s.bd) if s.bd else "Birthday not set") + (
                "" if s.bt_unknown else f", {s.bt.strftime('%H:%M')}")
            html(f'<div class="ar-ticket">{escape(when)}<br><span>{escape(s.place["label"])}</span></div>')
            with st.container(key="cta"):
                go = st.button("Show me my sky ✨", type="primary", width="stretch",
                               disabled=s.bd is None)
            if s.get("editing") and s.get("calculation_results"):
                if st.button("Back to my chart", width="stretch"):
                    s.editing = False
                    st.rerun()
            chart_settings()
    if go:
        reveal()


def reveal():
    s = st.session_state
    time_known = not s.bt_unknown
    try:
        r = compute_chart(s.bd, s.bt if time_known else time(12, 0), time_known,
                          chosen_timezone(), s.place, s.house_system)
    except Exception as e:
        st.error(f"Couldn't work out the chart: {e}. Check the date, time and place.")
        return
    s.form_memory = {k: s[k] for k in FORM_KEYS}
    s.calculation_results = r
    s.editing = False
    for key in list(s.keys()):
        if key.startswith(("fb_", "game_", "match_", "explore_")) or key in ("ai_reading",):
            del s[key]
    s.game = {"round": 0, "answers": {}, "done": False}
    st.rerun()


# ===========================================================================
#  STEP 2: THE GAME (a blind test, played as taps)
# ===========================================================================
def game_rounds(chart):
    # people usually know their Sun sign already, so it can't be tested blind
    form = [q for q in build_feedback_form(chart, n_options=4) if q["factor"] != "Sun sign"]
    for q in form:
        q["short"] = [", ".join(opt.split(", ")[:3]) for opt in q["options"]]
    return form


def render_game(chart):
    s = st.session_state
    g = s.game
    rounds = game_rounds(chart)
    total = len(rounds)
    if g["round"] < total:
        q = rounds[g["round"]]
        html('<div class="ar-hero-title">Which one feels like you?</div>'
             f'<p class="ar-hero-sub">Round {g["round"] + 1} of {total}. Go with your gut.</p>'
             '<div class="ar-pips">' + "".join(f'<i class="{"on" if i <= g["round"] else ""}"></i>'
                                               for i in range(total)) + '</div>')
        tints = [C.ELEMENTS[e][2] for e in ("Fire", "Air", "Water", "Earth")]
        html("<style>" + "".join(f".st-key-game_{g['round']}_{k} button{{background:{tints[k]}}}"
                                 for k in range(4)) + "</style>")
        with st.container(key="game"):
            for row in (0, 2):
                cols = st.columns(2, gap="medium")
                for k in (row, row + 1):
                    if k < len(q["short"]) and cols[k - row].button(
                            f"{TILE_SHAPES[k]}  {q['short'][k]}", key=f"game_{g['round']}_{k}",
                            width="stretch"):
                        g["answers"][g["round"]] = k
                        g["round"] += 1
                        st.rerun()
        st.write("")
        if st.button("Skip the game", key="game_skip"):
            g["done"] = True
            st.rerun()
        return

    html('<div class="ar-hero-title">Nice. One last tap.</div>'
         '<p class="ar-hero-sub">Can we keep your answers to test whether astrology beats guessing? '
         'No birth details are saved.</p>')
    c1, c2, _ = st.columns([1, 1, 1.4], gap="medium")
    with c1.container(key="cta"):
        share = st.button("Yes, use my answers", type="primary", width="stretch", key="game_yes")
    keep_private = c2.button("No thanks", width="stretch", key="game_no")
    if share:
        cid = chart_id_for(chart)
        for i, choice in g["answers"].items():
            record_response(FEEDBACK_LOG, cid, rounds[i], choice)
        s.toast_msg = f"Thanks! Saved {len(g['answers'])} answers."
    if share or keep_private:
        g["done"] = True
        st.rerun()


# ===========================================================================
#  STEP 3: THE REVEAL
# ===========================================================================
def headline(r):
    trop = r["tropical_positions"]
    parts = [f"{C.sign(trop['Sun'])[0]} Sun", f"{C.sign(trop['Moon'])[0]} Moon"]
    if r["time_known"]:
        parts.append(f"{C.sign(r['ascendant'])[0]} rising")
        return f"{parts[0]}, {parts[1]},<br>{parts[2]}."
    return f"{parts[0]},<br>{parts[1]}."


def top_bar(r):
    c1, c2 = st.columns([3, 1])
    with c1:
        when = long_date(r["date_obj"]) + (f", {r['birth_data']['time']}" if r["time_known"] else "")
        html(f'<p class="ar-summary" style="text-align:left">Born <b>{escape(when)}</b> in '
             f'<b>{escape(r["place_label"])}</b></p>')
    if c2.button("✏️ Change details", width="stretch"):
        st.session_state.editing = True
        st.rerun()


def render_results(r):
    trop = r["tropical_positions"]
    msg = st.session_state.pop("toast_msg", None)
    if msg:
        st.toast(msg, icon="💜")
    top_bar(r)
    html(f'<div class="ar-hero-title">{headline(r)}</div>'
         '<p class="ar-hero-sub">Tap any card to turn it over.</p>')
    html(ac.big_three_cards(trop, r["ascendant"], r["houses"]))

    section("Your chart and your sky", "Hover a planet on the wheel. The map shows what was overhead.")
    c1, c2 = st.columns(2, gap="medium")
    with c1.container(key="panel_wheel"):
        html(ac.natal_wheel_svg(trop, r["houses"], r["ascendant"], r["mc"], r["retrograde"],
                                title=f"Birth chart for {long_date(r['date_obj'])}"))
    with c2.container(key="panel_sky"):
        sky, day = ac.sky_map_svg(r["jd"], r["birth_data"]["lat"], r["birth_data"]["lon"], trop)
        html(sky)
        html(f'<p class="ar-cap">{"☀️ It was daytime, so these stars were hidden by the light." if day else "🌌 It was night: this is the sky you arrived under."}'
             f'{"" if r["time_known"] else " Shown for midday."}</p>')

    section("Around the world", "The same moment, read by three other traditions.")
    html(ac.world_cards(r["four_pillars"], r["nakshatra"], r["tzolkin"], long_date(r["date_obj"])))

    section("Play", "Compare with someone, try other birth times, or check today's sky.")
    play(r)

    section("A reading, written for you")
    render_ai(chart_summary(r))
    details(r)


@st.fragment
def play(r):
    modes = ["💞 Match with someone", "⏳ Birth-time explorer", "🌙 Today's sky"]
    mode = st.segmented_control("Play", modes, default=modes[0], key="play_mode",
                                label_visibility="collapsed") or modes[0]
    with st.container(key="panel_play"):
        if mode == modes[0]:
            match_panel(r)
        elif mode == modes[1]:
            explorer_panel(r)
        else:
            today_panel(r)


def match_panel(r):
    left, right = st.columns([1, 1.5], gap="large")
    with left:
        html('<div class="ar-big-line">Who are you curious about?</div>')
        name = st.text_input("Their name", key="match_name", placeholder="Their name (optional)")
        their_day = st.date_input("Their birthday", value=None, key="match_date",
                                  min_value=ae.MIN_DATE, max_value=ae.MAX_DATE, format="DD/MM/YYYY")
        html('<p class="ar-hint">Just for fun. A birthday is enough.</p>')
    with right:
        if not their_day:
            html('<div class="ar-moon">💞</div><p class="ar-cap">Add a birthday to see how you two fit.</p>')
            return
        jd = ae.julian_day(their_day.year, their_day.month, their_day.day, 12)
        them = ae.planetary_positions(jd)
        their_animal = ae.four_pillars(datetime.combine(their_day, time(12, 0)), jd)["year"][1][1]
        my_animal = r["four_pillars"]["year"][1][1]
        score, verdict, notes = C.compatibility(r["tropical_positions"], them, my_animal, their_animal)
        who = escape(name.strip()) if name.strip() else "them"
        ring, text = st.columns([1, 1.6])
        with ring:
            html(ac.score_ring_svg(score))
        with text:
            html(f'<div class="ar-big-line">{verdict}</div>'
                 f'<p class="ar-hint">You and {who}: {C.sign(them["Sun"])[0]} {C.sign(them["Sun"])[3]}, '
                 f'{their_animal} {C.CHINESE_ANIMALS[their_animal][0]}</p>')
        html('<div class="ar-note-list">' + "".join(
            f'<div class="ar-note"><b>{icon}</b>{escape(line)}</div>' for icon, line in notes) + '</div>')


def rising_samples(r):
    """Ascendant every 10 minutes through the local birth day."""
    s = st.session_state
    key = ("explore_cache", r["jd"], r["birth_data"]["lat"], r["birth_data"]["lon"])
    if s.get("explore_cache_key") == key:
        return s.explore_cache
    tz = pytz.timezone(r["birth_data"]["timezone"])
    day = r["date_obj"]
    out = []
    for minute in range(0, 1441, 10):
        local = tz.localize(datetime.combine(day, time(0, 0)) + timedelta(minutes=minute))
        utc = local.astimezone(pytz.UTC)
        jd = ae.julian_day(utc.year, utc.month, utc.day, utc.hour, utc.minute)
        out.append((minute, ae.angles(jd, r["birth_data"]["lat"], r["birth_data"]["lon"])[0]))
    s.explore_cache_key, s.explore_cache = key, out
    return out


def explorer_panel(r):
    samples = rising_samples(r)
    birth_min = None
    start = time(12, 0)
    if r["time_known"]:
        hh, mm = map(int, r["birth_data"]["time"].split(":"))
        birth_min, start = hh * 60 + mm, time(hh, mm)
    t = st.slider("Slide through the day you were born", value=start, step=timedelta(minutes=10),
                  format="HH:mm", key="explore_time")
    minute = t.hour * 60 + t.minute
    lon = min(samples, key=lambda x: abs(x[0] - minute))[1]
    name, element, _, emoji, keywords, _ = C.sign(lon)
    html(f'<div class="ar-big-line">At {t.strftime("%H:%M")} you\'d be {name} rising {emoji}</div>'
         f'<p class="ar-hint">{", ".join(keywords).capitalize()}. '
         + ("The gold dot is the time you gave." if birth_min is not None
            else "Not sure of your time? See which Rising sign feels right.") + '</p>')
    html(ac.rising_band_svg(samples, minute, birth_min))


def today_panel(r):
    now = datetime.now(timezone.utc)
    jd = ae.julian_day(now.year, now.month, now.day, now.hour, now.minute)
    sky_now = ae.planetary_positions(jd)
    phase, emoji, illum = C.moon_phase(sky_now["Sun"], sky_now["Moon"])
    moon_sign = C.sign(sky_now["Moon"])
    left, right = st.columns([1, 1.6], gap="large")
    with left:
        html(f'<div class="ar-moon">{emoji}</div>'
             f'<p class="ar-cap"><b>{phase}</b>, {round(illum * 100)}% lit<br>'
             f'Moon in {moon_sign[0]} {moon_sign[3]}</p>')
    with right:
        notes = C.transit_notes(sky_now, r["tropical_positions"], r["ascendant"])
        html(f'<div class="ar-big-line">Today, for you</div>')
        if not notes:
            notes = [("🌤️", "A quiet sky for you today. Good for getting on with things.")]
        html('<div class="ar-note-list">' + "".join(
            f'<div class="ar-note"><b>{icon}</b>{escape(line)}</div>' for icon, line in notes) + '</div>')
        html(f'<p class="ar-hint">Sky worked out for {now.strftime("%d %b %Y, %H:%M")} UTC.</p>')


def render_ai(chart):
    c1, c2 = st.columns([2, 1], gap="medium")
    focus = c1.segmented_control("Focus", ["general", "career", "relationships", "health", "spiritual path"],
                                 default="general", key="ai_focus", format_func=str.capitalize,
                                 label_visibility="collapsed") or "general"
    if c2.button("✍️ Write my reading", type="primary", key="ai_btn", width="stretch"):
        with st.spinner("Writing your reading…"):
            st.session_state.ai_reading = generate_llm_interpretation(chart, focus=focus)
    if "ai_reading" in st.session_state:
        with st.container(key="panel_ai"):
            st.markdown(st.session_state.ai_reading)


def details(r):
    trop, nak, fp, tz = r["tropical_positions"], r["nakshatra"], r["four_pillars"], r["tzolkin"]
    st.write("")
    with st.expander("🔭 All the details, for the curious"):
        tabs = st.tabs(["Planets", "Vedic chart", "Four Pillars", "Maya count", "Report"])
        with tabs[0]:
            c1, c2 = st.columns([1.2, 1], gap="large")
            c1.dataframe(positions_table(trop, r["houses"], r["retrograde"]), hide_index=True, width="stretch")
            aspects = ac.find_aspects(trop)
            if aspects:
                c2.dataframe(pd.DataFrame([{"Aspect": f"{a} {name} {b}", "Orb": f"{orb:.1f}°"}
                                           for a, b, name, orb, _ in aspects]), hide_index=True, width="stretch")
            if r["time_known"]:
                st.dataframe(pd.DataFrame([{"House": h, "Sign": ac.SIGNS[ac.sign_index(r["houses"][str(h)])],
                                            "Cusp": ac.fmt_deg(r["houses"][str(h)])} for h in range(1, 13)]),
                             hide_index=True, width="stretch")
                st.caption(f"Houses: {r['house_system_used']}")
        with tabs[1]:
            c1, c2 = st.columns(2, gap="large")
            with c1:
                html(ac.south_indian_svg(r["vedic_positions"], r["vedic_ascendant"], r["ayanamsa"]))
            c2.dataframe(positions_table(r["vedic_positions"]), hide_index=True, width="stretch")
        with tabs[2]:
            html(ac.pillars_html(fp, r["time_known"]))
            dm = fp["day"][0][1]
            st.write(f"**Day Master: {fp['day'][0][0]}, {dm}.** {ELEMENT_TRAITS.get(dm, '')}")
        with tabs[3]:
            c1, c2 = st.columns(2)
            with c1:
                html(ac.bar_dot_svg(tz["galactic_tone"]))
                st.write(f"**{tz['galactic_tone']} {tz['day_sign']}**, kin {tz['kin']} of 260. {tz['meaning']}.")
            with c2:
                html(ac.tzolkin_svg(tz["kin"]))
        with tabs[4]:
            report = generate_report_text(r)
            st.download_button("Download the full report", data=report,
                               file_name=f"astro_reveal_{r['birth_data']['date'].replace('-', '')}.txt",
                               mime="text/plain")
            st.text(report)


def render_admin():
    """Accuracy numbers, only if FEEDBACK_ADMIN_PASSWORD is set in Secrets."""
    try:
        password = st.secrets.get("FEEDBACK_ADMIN_PASSWORD")
    except Exception:
        password = None
    if not password:
        return
    with st.expander("Admin: blind-test accuracy"):
        entered = st.text_input("Password", type="password", key="admin_pw")
        if entered and hmac.compare_digest(entered, password):
            stats = summarize_log(FEEDBACK_LOG)
            if stats:
                st.json(stats)
            else:
                st.write("No answers yet. The log resets when the app restarts.")


# ===========================================================================
#  MAIN
# ===========================================================================
def main():
    inject_css()
    init_state()
    html('<div class="ar-wordmark">✨ Astro Reveal</div>')

    s = st.session_state
    r = s.get("calculation_results")
    if r is None or s.get("editing"):
        birth_form()
    elif not s.get("game", {}).get("done"):
        render_game(chart_summary(r))
    else:
        render_results(r)

    render_admin()
    html('<div class="ar-footer">Places from GeoNames (CC BY 4.0). Map © OpenStreetMap contributors. '
         'Stars and constellation figures from d3-celestial by Olaf Frohn (BSD). '
         'Astrology describes tendencies, not fate.</div>')


if __name__ == "__main__":
    main()
