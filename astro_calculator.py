#!/usr/bin/env python3
"""
Astro_Reveal - one birth chart, four traditions
===============================================
Streamlit app: Western (tropical), Vedic (sidereal), Chinese Four Pillars and
Maya Tzolkin from one birth date, time and place.

- astro_engine.py   the chart maths (run it for its self-checks)
- astro_charts.py   the wheel, rasi chart, pillars and Tzolkin drawings
- places.py         offline birthplace search and timezone lookup
- this file         the page itself

The look (colours, fonts, corners) lives in .streamlit/config.toml.
Run:  streamlit run astro_calculator.py
"""

import hmac
import os
from html import escape
from datetime import date, datetime, time

import pandas as pd
import pytz
import streamlit as st

import astro_charts as ac
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

st.set_page_config(page_title="Astro Reveal", page_icon="✦", layout="wide",
                   initial_sidebar_state="collapsed")


# ===========================================================================
#  STYLE: everything else comes from the theme in .streamlit/config.toml
# ===========================================================================
APP_CSS = f"""
<style>
[data-testid="stMainBlockContainer"], .block-container {{
  max-width: 1160px; padding-top: 2.2rem; padding-bottom: 4rem; }}
[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stBaseButton-primary"], button[kind="primary"] {{ color: {ac.LAPIS} !important; }}
[data-testid="stBaseButton-primary"] p, button[kind="primary"] p {{ color: {ac.LAPIS} !important; font-weight: 600; }}
iframe[title="streamlit_folium.st_folium"] {{ border-radius: .6rem; border: 1px solid {ac.RULE}; }}
.ar-wordmark {{ font-family: {ac.SERIF_FONT}; font-size: 1.55rem; color: {ac.IVORY};
  display: flex; align-items: center; gap: .55rem; margin-bottom: 1.6rem; }}
.ar-wordmark span {{ color: {ac.BRASS}; font-size: 1.1rem; }}
.ar-lede {{ color: {ac.MUTED}; font-size: 1.08rem; max-width: 34rem; margin: -.4rem 0 1.4rem; }}
.ar-place {{ border-left: 2px solid {ac.BRASS}; padding: .35rem 0 .35rem .9rem; margin: .4rem 0 1rem;
  color: {ac.IVORY}; line-height: 1.5; }}
.ar-place small {{ color: {ac.MUTED}; font-size: .9rem; display: block; }}
.ar-summary {{ color: {ac.MUTED}; font-size: 1.02rem; margin: .3rem 0 1rem; }}
.ar-summary b {{ color: {ac.IVORY}; font-weight: 500; }}
.ar-facts {{ margin-top: 1.8rem; border-top: 1px solid {ac.RULE}; padding-top: 1.1rem; }}
.ar-facts div {{ display: grid; grid-template-columns: 9.5rem 1fr; gap: .8rem; padding: .3rem 0; }}
.ar-facts dt {{ color: {ac.MUTED}; }}
.ar-facts dd {{ margin: 0; color: {ac.IVORY}; }}
.ar-maya {{ display: flex; gap: 1.4rem; align-items: center; margin: .5rem 0 1rem; }}
.ar-maya-name {{ font-family: {ac.SERIF_FONT}; font-size: 2.1rem; color: {ac.IVORY}; line-height: 1.1; }}
.ar-maya-sub {{ color: {ac.MUTED}; }}
.ar-footer {{ color: {ac.MUTED}; font-size: .85rem; margin-top: 3rem; border-top: 1px solid {ac.RULE};
  padding-top: 1rem; }}
</style>
"""


def inject_css():
    st.markdown(ac.STYLE + APP_CSS, unsafe_allow_html=True)


def html(markup):
    st.markdown(markup, unsafe_allow_html=True)


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
#  BIRTH DETAILS
# ===========================================================================
FORM_KEYS = ("bd", "bt", "bt_unknown", "place_query", "house_system")


def init_state():
    s = st.session_state
    s.setdefault("place", dict(DEFAULT_PLACE))
    s.setdefault("map_origin", [s.place["lat"], s.place["lon"]])
    s.setdefault("map_center", list(s.map_origin))
    s.setdefault("map_zoom", 6)
    s.setdefault("form_memory", {"bd": date(2000, 1, 1), "bt": time(12, 0), "bt_unknown": False,
                                 "place_query": "", "house_system": "Placidus"})
    # widgets forget their values while hidden; bring them back from memory
    for k in FORM_KEYS:
        if k not in s:
            s[k] = s.form_memory[k]


def place_search():
    s = st.session_state
    ix = place_index()
    query = st.text_input("Place of birth", key="place_query",
                          placeholder="Town or city, for example Pokhara or Portland, Maine")
    if ix is None:
        st.caption("Place search isn't available here. Click the map, or enter "
                   "coordinates under Chart settings.")
        return
    if not query.strip():
        return
    results = ix.search(query)
    if not results:
        st.caption("No town by that name in the list. Try the nearest larger town, "
                   "then click the map to move the pin.")
        return
    labels = [p.label for p in results]
    dupes = {lab for lab in labels if labels.count(lab) > 1}
    pick = st.selectbox(
        "Matches", range(len(results)), key="place_pick_" + places.fold(query),
        format_func=lambda i: labels[i] + (f" ({fmt_place(results[i].lat, results[i].lon)})"
                                           if labels[i] in dupes else ""),
        label_visibility="collapsed")
    chosen = results[pick]
    # only act when the search or the choice changes, so a later click on the
    # map isn't undone by the same search result on the next run
    pick_id = (places.fold(query), chosen.gid)
    if s.get("applied_pick") != pick_id:
        s.applied_pick = pick_id
        set_place(place_from(chosen), recentre=True, zoom=10)


def birth_map():
    s = st.session_state
    if not FOLIUM_AVAILABLE:
        st.info("The map needs the folium and streamlit-folium packages.")
        return
    pin = folium.FeatureGroup(name="Birthplace")
    folium.CircleMarker([s.place["lat"], s.place["lon"]], radius=9, color=ac.IVORY, weight=2,
                        fill=True, fill_color=ac.BRASS, fill_opacity=1,
                        tooltip=s.place["label"]).add_to(pin)
    base = folium.Map(location=s.map_origin, zoom_start=6, tiles="CartoDB dark_matter",
                      control_scale=True)
    out = st_folium(base, key="birth_map", center=s.map_center, zoom=s.map_zoom,
                    feature_group_to_add=pin, returned_objects=["last_clicked"],
                    height=430, use_container_width=True)
    click = (out or {}).get("last_clicked")
    if click:
        point = (round(click["lat"], 4), round((click["lng"] + 180) % 360 - 180, 4))
        if point != s.get("last_click"):
            s.last_click = point
            set_place(place_from_point(*point))
            st.rerun()
    st.caption("Click the map to move the pin to the exact spot.")


def chart_settings():
    s = st.session_state
    with st.expander("Chart settings"):
        st.selectbox("House system", ae.HOUSE_SYSTEMS, key="house_system",
                     help="Placidus is the most widely used. Whole Sign is the "
                          "traditional choice in Vedic astrology.")
        zones = pytz.common_timezones
        detected = s.place.get("tz") or "UTC"
        st.selectbox("Timezone", zones, index=zones.index(detected) if detected in zones else 0,
                     key="tz_" + detected,
                     help="Set automatically from the birthplace. Daylight saving and "
                          "historical changes are handled for you.")
        st.write("Or enter coordinates")
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
    left, right = st.columns([1, 1.05], gap="large")
    with left:
        st.title("When and where were you born?")
        html('<p class="ar-lede">Your chart is the sky at the moment you were born, '
             'seen from where you were born. The more exact the time, the more of it we can draw.</p>')
        unknown = s.get("bt_unknown", False)
        c1, c2 = st.columns(2)
        c1.date_input("Date of birth", key="bd", min_value=ae.MIN_DATE, max_value=ae.MAX_DATE)
        c2.time_input("Time of birth", key="bt", step=60, disabled=unknown)
        st.checkbox("I don't know my birth time", key="bt_unknown",
                    help="We'll use midday. Your Rising sign, houses and hour pillar "
                         "need a time, so they'll be left out.")
        place_search()
        p = s.place
        tz = chosen_timezone()
        source = f" (from {p['tz_from']})" if p.get("tz_from") and tz == p.get("tz") else ""
        html(f'<div class="ar-place">{escape(p["label"])}<small>{fmt_place(p["lat"], p["lon"])}. '
             f'Timezone {escape(tz)}{escape(source)}.</small></div>')
        chart_settings()
        if s.get("editing") and s.get("calculation_results"):
            b1, b2 = st.columns(2)
            if b1.button("Reveal my chart", type="primary", width="stretch"):
                reveal()
            if b2.button("Back to my chart", width="stretch"):
                s.editing = False
                st.rerun()
        elif st.button("Reveal my chart", type="primary", width="stretch"):
            reveal()
    with right:
        birth_map()


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
        if key.startswith("fb_") or key in ("ai_reading", "quiz_saved"):
            del s[key]
    s.quiz_done = False
    st.rerun()


def birth_summary(r):
    when = long_date(r["date_obj"])
    when += f" at {r['birth_data']['time']}" if r["time_known"] else ", time unknown"
    c1, c2 = st.columns([4, 1])
    c1.markdown(f'<p class="ar-summary">Born <b>{when}</b> in <b>{escape(r["place_label"])}</b> '
                f'({escape(r["birth_data"]["timezone"])}).</p>', unsafe_allow_html=True)
    if c2.button("Change birth details", width="stretch"):
        st.session_state.editing = True
        st.rerun()


# ===========================================================================
#  BLIND TEST
# ===========================================================================
def render_quiz(chart):
    st.title("Before you see your chart")
    html('<p class="ar-lede">Each question has one description from your chart and three '
         'from other charts, with no labels. Pick the one that sounds most like you. Across '
         'many people this shows whether the descriptions beat guessing, which would be 25%. '
         'It takes a minute, and you can skip it.</p>')
    form = build_feedback_form(chart, n_options=4)
    answers = {}
    for i, q in enumerate(form):
        with st.container(border=True):
            answers[i] = st.radio(
                f"Question {i + 1} of {len(form)}: which fits you best?",
                options=list(range(len(q["options"]))),
                format_func=lambda x, q=q: q["options"][x],
                index=None, key=f"fb_{i}")
    consent = st.checkbox("Save my answers anonymously. No birth details are stored.",
                          key="fb_consent")
    c1, c2, _ = st.columns([1.3, 1.3, 2])
    if c1.button("Save answers and show my chart", type="primary", key="fb_submit",
                 width="stretch"):
        if not consent:
            st.warning("Tick the box to save your answers, or choose Skip.")
            return
        cid = chart_id_for(chart)
        saved = 0
        for i, q in enumerate(form):
            if answers.get(i) is not None:
                record_response(FEEDBACK_LOG, cid, q, answers[i])
                saved += 1
        st.session_state.quiz_done = True
        st.session_state.quiz_saved = saved
        st.rerun()
    if c2.button("Skip and show my chart", key="fb_skip", width="stretch"):
        st.session_state.quiz_done = True
        st.rerun()


# ===========================================================================
#  RESULTS
# ===========================================================================
def render_results(r):
    s = st.session_state
    if s.get("quiz_saved"):
        st.toast(f"Saved {s.quiz_saved} answers. Thank you.")
        s.quiz_saved = 0
    trop, nak, fp, tz = r["tropical_positions"], r["nakshatra"], r["four_pillars"], r["tzolkin"]

    left, right = st.columns([1.3, 1], gap="large")
    with left:
        html(ac.natal_wheel_svg(trop, r["houses"], r["ascendant"], r["mc"], r["retrograde"],
                                title=f"Birth chart for {long_date(r['date_obj'])}"))
    with right:
        st.title("Your chart")
        html(ac.big_three_html(trop, r["ascendant"], r["houses"]))
        dm = fp["day"][0]
        html(f'<dl class="ar-facts">'
             f'<div><dt>Moon nakshatra</dt><dd>{nak["name"]}, pada {nak["pada"]}</dd></div>'
             f'<div><dt>Day Master</dt><dd>{dm[0]}, {dm[1]}</dd></div>'
             f'<div><dt>Maya day sign</dt><dd>{tz["galactic_tone"]} {tz["day_sign"]}</dd></div>'
             f'</dl>')

    tabs = st.tabs(["Western", "Vedic", "Chinese", "Maya", "Side by side"])

    with tabs[0]:
        c1, c2 = st.columns([1.2, 1], gap="large")
        with c1:
            st.subheader("Planets")
            st.dataframe(positions_table(trop, r["houses"], r["retrograde"]),
                         hide_index=True, width="stretch")
        with c2:
            st.subheader("Aspects")
            aspects = ac.find_aspects(trop)
            if aspects:
                st.dataframe(pd.DataFrame([{"Between": f"{a} and {b}", "Aspect": name.title(),
                                            "Orb": f"{orb:.1f}°"} for a, b, name, orb, _ in aspects]),
                             hide_index=True, width="stretch")
            else:
                st.write("No major aspects.")
            st.caption("Green lines in the wheel are flowing aspects (trines, and dashed sextiles); "
                       "brass lines are tense ones (squares and oppositions).")
        if r["time_known"]:
            st.subheader(f"Houses ({r['house_system_used']})")
            st.dataframe(pd.DataFrame([{"House": h, "Sign": ac.SIGNS[ac.sign_index(r["houses"][str(h)])],
                                        "Cusp": ac.fmt_deg(r["houses"][str(h)])} for h in range(1, 13)]),
                         hide_index=True, width="stretch")

    with tabs[1]:
        c1, c2 = st.columns([1, 1], gap="large")
        with c1:
            html(ac.south_indian_svg(r["vedic_positions"], r["vedic_ascendant"], r["ayanamsa"]))
        with c2:
            st.subheader(f"Moon in {nak['name']}")
            st.write(f"Pada {nak['pada']}, ruled by {nak['lord']}. {nak['meaning']}.")
            st.dataframe(positions_table(r["vedic_positions"]), hide_index=True,
                         width="stretch")
            st.caption("Sidereal positions with the Lahiri ayanamsa. The chart uses the "
                       "South Indian layout, where each sign keeps a fixed square.")

    with tabs[2]:
        html(ac.pillars_html(fp, r["time_known"]))
        dm = fp["day"][0][1]
        st.subheader(f"Day Master: {fp['day'][0][0]}, {dm}")
        st.write(ELEMENT_TRAITS.get(dm, ""))
        st.caption("Read from the right: year, month, day, hour. The year starts at Lichun "
                   "(about 4 February) and each month on a solar term. The colours show the "
                   "five elements.")

    with tabs[3]:
        c1, c2 = st.columns([1.2, 1], gap="large")
        with c1:
            html(f'<div class="ar-maya">{ac.bar_dot_svg(tz["galactic_tone"])}<div>'
                 f'<div class="ar-maya-name">{tz["galactic_tone"]} {tz["day_sign"]}</div>'
                 f'<div class="ar-maya-sub">{tz["glyph"]}, kin {tz["kin"]} of 260</div></div></div>')
            st.write(f"{tz['meaning']}. The number is your galactic tone, written the Maya way: "
                     "a dot for one and a bar for five.")
        with c2:
            html(ac.tzolkin_svg(tz["kin"]))
            st.caption("The 260-day count: 13 tones across, 20 day signs down.")

    with tabs[4]:
        vedic_primary = (ac.SIGNS[ac.sign_index(r["vedic_ascendant"])] + " rising"
                         if r["time_known"] else ac.SIGNS[ac.sign_index(r["vedic_positions"]["Moon"])] + " Moon")
        western_primary = (ac.SIGNS[ac.sign_index(r["ascendant"])] + " rising"
                           if r["time_known"] else ac.SIGNS[ac.sign_index(trop["Sun"])] + " Sun")
        st.dataframe(pd.DataFrame({
            "Tradition": ["Western", "Vedic", "Chinese", "Maya"],
            "Key placement": [western_primary, vedic_primary,
                              f"{fp['day'][0][1]} Day Master", f"{tz['galactic_tone']} {tz['day_sign']}"],
            "Measured against": ["The seasons (tropical zodiac)", "The stars (sidereal zodiac)",
                                 "The solar terms and the 60-day cycle", "The 260-day count"],
            "Speaks to": ["Personality and psychology", "Karma and life direction",
                          "Balance of the five elements", "Purpose and spiritual tone"],
        }), hide_index=True, width="stretch")

    report = generate_report_text(r)
    c1, c2 = st.columns([1, 3])
    c1.download_button("Download the full report", data=report,
                       file_name=f"astro_reveal_{r['birth_data']['date'].replace('-', '')}.txt",
                       mime="text/plain", width="stretch")
    with c2.expander("Read the full report here"):
        st.text(report)


def render_ai(chart):
    st.subheader("A written reading")
    st.write("Gemini writes a reading from your exact placements. It takes about half a minute.")
    c1, c2 = st.columns([2, 1])
    focus = c1.selectbox("Focus", ["general", "career", "relationships", "health", "spiritual path"],
                         key="ai_focus", format_func=str.capitalize)
    c2.write("")
    if c2.button("Write my reading", type="primary", key="ai_btn", width="stretch"):
        with st.spinner("Writing your reading…"):
            st.session_state.ai_reading = generate_llm_interpretation(chart, focus=focus)
    if "ai_reading" in st.session_state:
        with st.container(border=True):
            st.markdown(st.session_state.ai_reading)


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
    html('<div class="ar-wordmark"><span>✦</span>Astro Reveal</div>')

    s = st.session_state
    r = s.get("calculation_results")
    if r is None or s.get("editing"):
        birth_form()
    else:
        birth_summary(r)
        chart = chart_summary(r)
        if not s.get("quiz_done"):
            render_quiz(chart)
        else:
            render_results(r)
            st.divider()
            render_ai(chart)

    render_admin()
    html('<div class="ar-footer">Places from GeoNames (CC BY 4.0). Map data © OpenStreetMap '
         'contributors, tiles © CARTO. Astrology describes tendencies, not fate.</div>')


if __name__ == "__main__":
    main()
