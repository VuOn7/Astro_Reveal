#!/usr/bin/env python3
"""
Astro_Reveal - one birth chart, four traditions
===============================================
Streamlit app: Vedic (sidereal), Western (tropical), Chinese Four Pillars and
Mayan Tzolkin from one birth date, time and place.

The chart maths lives in astro_engine.py (run it directly for its self-checks).
This file is the UI, the text report and the theme.

Run:  streamlit run astro_calculator.py
"""

import hmac
import os
from datetime import date, datetime, time

import pandas as pd
import pytz
import streamlit as st

import astro_engine as ae
from llm_interpreter import build_chart_summary, generate_llm_interpretation
from feedback_collector import (build_feedback_form, record_response,
                                chart_id_for, summarize_log)

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

st.set_page_config(
    page_title="Astro Reveal",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===========================================================================
#  COSMIC THEME
#  All visual styling lives here; it only changes how the app looks.
# ===========================================================================
COSMIC_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@500;600;700&family=Spectral:ital,wght@0,300;0,400;0,500;1,400&display=swap');

/* ---- App background: deep space with drifting star-glows ---- */
.stApp {
    background:
        radial-gradient(circle at 18% 18%, rgba(124, 92, 255, 0.18), transparent 42%),
        radial-gradient(circle at 82% 12%, rgba(233, 196, 106, 0.10), transparent 40%),
        radial-gradient(circle at 60% 85%, rgba(72, 149, 239, 0.14), transparent 45%),
        linear-gradient(160deg, #0a0a1a 0%, #12102b 45%, #0d0b1f 100%);
    background-attachment: fixed;
    color: #e9e7f5;
    font-family: 'Spectral', Georgia, serif;
}

/* readable body text everywhere */
.stApp, .stApp p, .stApp li, .stApp label, .stApp span, .stMarkdown {
    color: #e3e0f2;
}

/* ---- Headings ---- */
h1, h2, h3, h4 {
    font-family: 'Cinzel', serif !important;
    letter-spacing: 0.5px;
    color: #f4d58d !important;
}
h2 { border-bottom: 1px solid rgba(244, 213, 141, 0.18); padding-bottom: 0.3em; }

/* ---- Hero banner ---- */
.cosmic-hero {
    text-align: center;
    padding: 2.2rem 1rem 1.4rem 1rem;
    margin-bottom: 0.5rem;
}
.cosmic-hero h1 {
    font-size: 2.7rem;
    margin: 0;
    background: linear-gradient(92deg, #f4d58d 0%, #e9c46a 30%, #a98bff 75%, #7c5cff 100%);
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: 0 0 30px rgba(169, 139, 255, 0.25);
}
.cosmic-hero p {
    font-style: italic;
    color: #b9b3d6 !important;
    font-size: 1.05rem;
    margin-top: 0.4rem;
    letter-spacing: 1px;
}
.cosmic-hero .rule {
    width: 120px; height: 2px; margin: 0.9rem auto 0 auto;
    background: linear-gradient(90deg, transparent, #f4d58d, transparent);
}

/* ---- Sidebar ---- */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(20, 16, 42, 0.96), rgba(13, 11, 31, 0.96));
    border-right: 1px solid rgba(244, 213, 141, 0.12);
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #f4d58d !important;
}

/* ---- Metric cards ---- */
[data-testid="stMetric"] {
    background: rgba(255, 255, 255, 0.035);
    border: 1px solid rgba(244, 213, 141, 0.18);
    border-radius: 14px;
    padding: 14px 16px;
    backdrop-filter: blur(6px);
    transition: border-color .2s ease, transform .2s ease;
}
[data-testid="stMetric"]:hover {
    border-color: rgba(244, 213, 141, 0.5);
    transform: translateY(-2px);
}
[data-testid="stMetricValue"] { color: #f4d58d !important; font-weight: 600; }
[data-testid="stMetricLabel"] { color: #b9b3d6 !important; }

/* ---- Buttons ---- */
.stButton > button {
    background: linear-gradient(92deg, #7c5cff, #a98bff);
    color: #fff;
    border: none;
    border-radius: 10px;
    padding: 0.55rem 1.1rem;
    font-family: 'Cinzel', serif;
    letter-spacing: 0.5px;
    font-weight: 600;
    box-shadow: 0 6px 20px rgba(124, 92, 255, 0.35);
    transition: transform .15s ease, box-shadow .15s ease, filter .15s ease;
}
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 28px rgba(124, 92, 255, 0.5);
    filter: brightness(1.07);
}
.stDownloadButton > button {
    background: rgba(244, 213, 141, 0.12);
    color: #f4d58d;
    border: 1px solid rgba(244, 213, 141, 0.4);
    border-radius: 10px;
    font-family: 'Cinzel', serif;
}

/* ---- Tabs ---- */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    background: rgba(255,255,255,0.03);
    padding: 6px;
    border-radius: 12px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    color: #b9b3d6;
    border-radius: 8px;
    padding: 8px 16px;
    font-family: 'Cinzel', serif;
    font-size: 0.9rem;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(92deg, rgba(124,92,255,0.35), rgba(169,139,255,0.35)) !important;
    color: #f4d58d !important;
    box-shadow: inset 0 0 0 1px rgba(244,213,141,0.3);
}

/* ---- Bordered containers used as 'cards' ---- */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(255, 255, 255, 0.035);
    border: 1px solid rgba(244, 213, 141, 0.18) !important;
    border-radius: 16px;
    backdrop-filter: blur(6px);
}

/* ---- The AI reading card: extra-special treatment ---- */
.reading-card h1 { font-size: 1.9rem; }
.reading-card h2 { font-size: 1.3rem; margin-top: 1.1rem; }
.reading-card { line-height: 1.7; }

/* ---- Inputs ---- */
.stTextInput input, .stNumberInput input, .stDateInput input,
[data-baseweb="select"] > div, .stTimeInput input {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(244,213,141,0.2) !important;
    color: #e9e7f5 !important;
    border-radius: 8px;
}

/* ---- Dataframes ---- */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(244, 213, 141, 0.15);
    border-radius: 12px;
    overflow: hidden;
}

/* ---- Alert boxes (info/success/warning) ---- */
[data-testid="stAlert"] {
    border-radius: 12px;
    backdrop-filter: blur(4px);
}

/* ---- Expanders ---- */
.streamlit-expanderHeader, [data-testid="stExpander"] summary {
    font-family: 'Cinzel', serif;
    color: #f4d58d !important;
}
[data-testid="stExpander"] {
    border: 1px solid rgba(244,213,141,0.15);
    border-radius: 12px;
    background: rgba(255,255,255,0.02);
}

/* hide the default Streamlit chrome for a cleaner look */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
</style>
"""


def inject_css():
    st.markdown(COSMIC_CSS, unsafe_allow_html=True)



def cosmic_hero():
    st.markdown(
        """
        <div class="cosmic-hero">
            <h1>&#10022; Astro Reveal &#10022;</h1>
            <p>Vedic &bull; Western &bull; Chinese &bull; Mayan &mdash; one chart, four ancient lenses</p>
            <div class="rule"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ===========================================================================
#  DATA
# ===========================================================================
MAJOR_CITIES = {
    "Kathmandu, Nepal": (27.7172, 85.3240),
    "New York, USA": (40.7128, -74.0060),
    "London, UK": (51.5074, -0.1278),
    "Tokyo, Japan": (35.6762, 139.6503),
    "Mumbai, India": (19.0760, 72.8777),
    "Sydney, Australia": (-33.8688, 151.2093),
    "Los Angeles, USA": (34.0522, -118.2437),
    "Paris, France": (48.8566, 2.3522),
    "Beijing, China": (39.9042, 116.4074),
    "Cairo, Egypt": (30.0444, 31.2357),
}

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


# ===========================================================================
#  HELPERS
# ===========================================================================
def fmt_deg(d):
    """12.5 -> 12°30'"""
    d = d % 360
    whole = int(d)
    minutes = int(round((d - whole) * 60))
    if minutes == 60:
        whole, minutes = whole + 1, 0
    return f"{whole}°{minutes:02d}'"


def fmt_place(lat, lon):
    return (f"{abs(lat):.4f}°{'N' if lat >= 0 else 'S'}, "
            f"{abs(lon):.4f}°{'E' if lon >= 0 else 'W'}")


def positions_table(positions):
    rows = []
    for planet, lon in positions.items():
        sign, deg = ae.sign_of(lon)
        rows.append({"Planet": planet, "Sign": sign,
                     "Degree in sign": fmt_deg(deg), "Longitude": f"{lon:.2f}°"})
    return pd.DataFrame(rows)


def compute_chart(birth_date, birth_time, tz_name, lat, lon, house_system, include_houses):
    local = pytz.timezone(tz_name).localize(datetime.combine(birth_date, birth_time))
    utc = local.astimezone(pytz.UTC)
    jd = ae.julian_day(utc.year, utc.month, utc.day, utc.hour, utc.minute, utc.second)

    tropical = ae.planetary_positions(jd)
    ayanamsa = ae.lahiri_ayanamsa(jd)
    vedic = ae.to_sidereal(tropical, ayanamsa)

    r = {
        "birth_data": {"date": str(birth_date), "time": birth_time.strftime("%H:%M"),
                       "lat": lat, "lon": lon, "timezone": tz_name},
        "utc": utc.strftime("%Y-%m-%d %H:%M UTC"),
        "jd": jd,
        "tropical_positions": tropical,
        "vedic_positions": vedic,
        "ayanamsa": ayanamsa,
        "nakshatra": ae.nakshatra(vedic["Moon"]),
        "four_pillars": ae.four_pillars(local, jd),
        "tzolkin": ae.tzolkin(birth_date),
        "include_houses": include_houses,
        "house_system": house_system,
        "houses": None, "ascendant": None, "mc": None,
        "vedic_ascendant": None, "house_system_used": None,
    }
    if include_houses:
        cusps, asc, mc, used = ae.houses(jd, lat, lon, house_system)
        r.update(houses=cusps, ascendant=asc, mc=mc, house_system_used=used,
                 vedic_ascendant=(asc - ayanamsa) % 360)
    return r


def chart_summary(r):
    """The structured chart handed to the AI reading and the blind test."""
    return build_chart_summary(r["birth_data"], r["vedic_positions"],
                               r["tropical_positions"], r["four_pillars"],
                               r["tzolkin"], r["nakshatra"], ascendant=r["ascendant"])


# ===========================================================================
#  TEXT REPORT
# ===========================================================================
def generate_report_text(r):
    b = r["birth_data"]
    fp, tz = r["four_pillars"], r["tzolkin"]
    nak = r["nakshatra"]
    sun_sign, _ = ae.sign_of(r["tropical_positions"]["Sun"])
    moon_sign, _ = ae.sign_of(r["tropical_positions"]["Moon"])

    out = [
        "ASTRO REVEAL - MULTI-SYSTEM CHART REPORT",
        "=" * 43, "",
        "Birth information:",
        f"- Date: {b['date']}",
        f"- Time: {b['time']} ({b['timezone']}) = {r['utc']}",
        f"- Place: {fmt_place(b['lat'], b['lon'])}",
    ]
    if r["include_houses"]:
        out.append(f"- House system: {r['house_system_used']}")
    out += ["", "=" * 79, "VEDIC (SIDEREAL) ASTROLOGY", "=" * 79, "",
            f"Ayanamsa (Lahiri): {r['ayanamsa']:.4f}°", ""]

    if r["include_houses"]:
        sign, deg = ae.sign_of(r["vedic_ascendant"])
        out += [f"ASCENDANT (LAGNA): {sign} {fmt_deg(deg)}",
                "Your rising sign shows how others see you and how you approach life.",
                f"With {sign} rising: {SIGN_MEANINGS[sign]}", ""]

    out.append("PLANETARY POSITIONS (sidereal):")
    out.append("")
    for planet, lon in r["vedic_positions"].items():
        sign, deg = ae.sign_of(lon)
        out += [f"* {planet}: {sign} {fmt_deg(deg)} ({lon:.2f}°)",
                f"  Planet: {PLANET_MEANINGS.get(planet, '')}",
                f"  In {sign}: {SIGN_MEANINGS[sign]}", ""]

    out += [f"MOON'S NAKSHATRA: {nak['name']} (Lord: {nak['lord']}) - Pada {nak['pada']}",
            f"Theme: {nak['meaning']}", "",
            "=" * 79, "WESTERN (TROPICAL) ASTROLOGY", "=" * 79, ""]

    if r["include_houses"]:
        sign, deg = ae.sign_of(r["ascendant"])
        mc_sign, mc_deg = ae.sign_of(r["mc"])
        out += [f"ASCENDANT: {sign} {fmt_deg(deg)}",
                f"Traits: {SIGN_MEANINGS[sign]}",
                f"MIDHEAVEN (MC): {mc_sign} {fmt_deg(mc_deg)}", ""]

    out += [f"SUN SIGN: {sun_sign}", f"Core identity: {SIGN_MEANINGS[sun_sign]}", "",
            f"MOON SIGN: {moon_sign}", f"Emotional nature: {SIGN_MEANINGS[moon_sign]}", "",
            "PLANETARY POSITIONS (tropical):"]
    for planet, lon in r["tropical_positions"].items():
        sign, deg = ae.sign_of(lon)
        out.append(f"* {planet}: {sign} {fmt_deg(deg)}")
    out.append("")

    if r["include_houses"]:
        out.append(f"HOUSE CUSPS ({r['house_system_used']}):")
        for h in range(1, 13):
            sign, deg = ae.sign_of(r["houses"][str(h)])
            out.append(f"  House {h:>2}: {sign} {fmt_deg(deg)}")
        out.append("")

    def pillar(name):
        (stem, element), (branch, animal) = fp[name]
        return f"{stem} {element} / {branch} {animal}"

    out += ["=" * 79, "CHINESE FOUR PILLARS (BAZI)", "=" * 79, "",
            f"YEAR PILLAR (ancestry, early life):   {pillar('year')}",
            f"MONTH PILLAR (career, parents):       {pillar('month')}",
            f"DAY PILLAR (self, partnership):       {pillar('day')}",
            f"HOUR PILLAR (children, later life):   {pillar('hour')}", "",
            f"DAY MASTER: {fp['day'][0][0]} ({fp['day'][0][1]}) - your core nature", "",
            "=" * 79, "MAYAN TZOLKIN", "=" * 79, "",
            f"DAY SIGN: {tz['day_sign']} ({tz['glyph']}) - {tz['meaning']}",
            f"GALACTIC TONE: {tz['galactic_tone']}",
            f"KIN: {tz['kin']}", "",
            "=" * 79, "SUMMARY", "=" * 79, "",
            f"- Vedic Moon nakshatra: {nak['name']}",
            f"- Western Sun sign: {sun_sign}",
            f"- Chinese Day Master: {fp['day'][0][1]}",
            f"- Mayan day sign: {tz['day_sign']}", "",
            "=" * 79, "HOW THIS WAS CALCULATED", "=" * 79, "",
            "- Sun and Moon: Meeus algorithms; planets: JPL Keplerian elements",
            "  (1800-2050), geocentric. Expect roughly 0.01-0.2° accuracy.",
            "- Rahu/Ketu: mean lunar node. Ayanamsa: Lahiri.",
            "- Bazi year and month change on the solar terms (year at Lichun).",
            "- Tzolkin: GMT correlation 584283.", "",
            "Astrology describes tendencies and themes, not fixed fate.",
            "Use it for reflection, not for major life decisions.", ""]
    return "\n".join(out)


# ===========================================================================
#  UI PIECES
# ===========================================================================
def create_clickable_map(lat, lon):
    """Map you can click to pick the birth place."""
    m = folium.Map(location=[lat, lon], zoom_start=8)
    folium.Marker(
        [lat, lon],
        popup=f"Selected location\nLat: {lat:.4f}\nLon: {lon:.4f}",
        tooltip="Current selection",
        icon=folium.Icon(color="red", icon="star"),
    ).add_to(m)
    m.add_child(folium.LatLngPopup())
    map_data = st_folium(m, width=700, height=400, key="location_map")

    if map_data and map_data.get("last_clicked"):
        lat = map_data["last_clicked"]["lat"]
        lon = map_data["last_clicked"]["lng"]
        st.success(f"Selected: {fmt_place(lat, lon)}")
    return lat, lon


def render_quiz(chart):
    """Blind test, shown BEFORE the chart so nobody can recognise their own text."""
    st.header("✦ Before you see your chart: a quick blind test")
    st.write(
        "Each question below has one description that belongs to your chart and "
        "three that belong to other charts. Pick the one that sounds most like you. "
        "Over many people this tells us whether the descriptions beat pure guessing "
        "(25%). It takes a minute, and you can skip it."
    )
    consent = st.checkbox("Save my answers anonymously (no birth data is stored)",
                          key="fb_consent")
    form = build_feedback_form(chart, n_options=4)
    answers = {}
    for i, q in enumerate(form):
        answers[i] = st.radio(
            f"**{i + 1}.** Which fits you best?",
            options=list(range(len(q["options"]))),
            format_func=lambda x, q=q: q["options"][x],
            index=None,
            key=f"fb_{i}",
        )

    c1, c2 = st.columns(2)
    if c1.button("Submit and show my chart", type="primary", key="fb_submit"):
        if not consent:
            st.warning("Tick the box to save your answers, or use Skip.")
            return
        cid = chart_id_for(chart)
        saved = 0
        for i, q in enumerate(form):
            if answers.get(i) is not None:
                record_response(FEEDBACK_LOG, cid, q, answers[i])
                saved += 1
        st.session_state["quiz_done"] = True
        st.session_state["quiz_saved"] = saved
        st.rerun()
    if c2.button("Skip and show my chart", key="fb_skip"):
        st.session_state["quiz_done"] = True
        st.rerun()


def render_results(r):
    st.header("✦ Complete Astrological Analysis")
    if st.session_state.get("quiz_saved"):
        st.success(f"Thanks — {st.session_state['quiz_saved']} answer(s) saved.")
    st.caption(f"Birth moment: {r['birth_data']['date']} {r['birth_data']['time']} "
               f"{r['birth_data']['timezone']} = {r['utc']} · "
               f"{fmt_place(r['birth_data']['lat'], r['birth_data']['lon'])}")

    tabs = st.tabs(["🕉 Vedic", "♋ Western", "☯ Chinese", "🌞 Mayan", "✦ Comparative"])
    nak, fp, tz = r["nakshatra"], r["four_pillars"], r["tzolkin"]

    with tabs[0]:
        st.subheader("Vedic (Sidereal) Astrology")
        c1, c2 = st.columns(2)
        if r["include_houses"]:
            sign, deg = ae.sign_of(r["vedic_ascendant"])
            c1.metric("Ascendant (Lagna)", sign, fmt_deg(deg), delta_color="off")
        c2.metric("Ayanamsa (Lahiri)", fmt_deg(r["ayanamsa"]))
        st.write("**Planetary positions (sidereal):**")
        st.dataframe(positions_table(r["vedic_positions"]), hide_index=True)
        st.write("**Moon's Nakshatra:**")
        c1, c2, c3 = st.columns(3)
        c1.metric("Nakshatra", nak["name"])
        c2.metric("Lord", nak["lord"])
        c3.metric("Pada", str(nak["pada"]))
        st.info(f"**Meaning:** {nak['meaning']}")

    with tabs[1]:
        st.subheader("Western (Tropical) Astrology")
        if r["include_houses"]:
            c1, c2 = st.columns(2)
            sign, deg = ae.sign_of(r["ascendant"])
            c1.metric("Ascendant", sign, fmt_deg(deg), delta_color="off")
            sign, deg = ae.sign_of(r["mc"])
            c2.metric("Midheaven (MC)", sign, fmt_deg(deg), delta_color="off")
        st.write("**Planetary positions (tropical):**")
        st.dataframe(positions_table(r["tropical_positions"]), hide_index=True)
        if r["include_houses"]:
            st.write(f"**House cusps ({r['house_system_used']}):**")
            rows = []
            for h in range(1, 13):
                sign, deg = ae.sign_of(r["houses"][str(h)])
                rows.append({"House": h, "Sign": sign, "Cusp": fmt_deg(deg)})
            st.dataframe(pd.DataFrame(rows), hide_index=True)

    with tabs[2]:
        st.subheader("Chinese Four Pillars (Bazi)")
        rows = [{"Pillar": name.title(),
                 "Heavenly Stem": f"{stem[0]} ({stem[1]})",
                 "Earthly Branch": f"{branch[0]} ({branch[1]})"}
                for name, (stem, branch) in fp.items()]
        st.dataframe(pd.DataFrame(rows), hide_index=True)
        dm = fp["day"][0]
        st.success(f"**Day Master:** {dm[0]} ({dm[1]}) — your core essence")
        st.caption("Year and month change on the solar terms (the year starts at "
                   "Lichun, around 4 February); the day starts at midnight local time.")

    with tabs[3]:
        st.subheader("Mayan Tzolkin Calendar")
        c1, c2, c3 = st.columns(3)
        c1.metric("Day Sign", tz["day_sign"])
        c2.metric("Galactic Tone", str(tz["galactic_tone"]))
        c3.metric("Kin Number", str(tz["kin"]))
        st.write(f"**Glyph:** {tz['glyph']}")
        st.info(f"**Meaning:** {tz['meaning']}")

    with tabs[4]:
        st.subheader("Cross-System Analysis")
        if r["include_houses"]:
            vedic_primary = ae.sign_of(r["vedic_ascendant"])[0] + " rising"
            western_primary = ae.sign_of(r["ascendant"])[0] + " rising"
        else:
            vedic_primary = ae.sign_of(r["vedic_positions"]["Moon"])[0] + " Moon"
            western_primary = ae.sign_of(r["tropical_positions"]["Sun"])[0] + " Sun"
        st.dataframe(pd.DataFrame({
            "System": ["Vedic", "Western", "Chinese", "Mayan"],
            "Primary Sign": [vedic_primary, western_primary,
                             f"{fp['day'][0][1]} ({fp['day'][1][1]})", tz["day_sign"]],
            "Calculation Base": ["Sidereal zodiac", "Tropical zodiac",
                                 "Four Pillars / Bazi", "Tzolkin calendar"],
            "Key Focus": ["Karma & dharma", "Psychological traits",
                          "Life balance & timing", "Spiritual frequency"],
        }), hide_index=True)

    st.header("Calculation Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Julian Day", f"{r['jd']:.4f}")
    c2.metric("Ayanamsa", f"{r['ayanamsa']:.4f}°")
    c3.metric("House System", r["house_system_used"] or "—")
    c4.metric("Systems Calculated", "4")

    st.header("Full Report")
    report = generate_report_text(r)
    st.download_button(
        "Download report (TXT)", data=report,
        file_name=f"astro_reveal_{r['birth_data']['date'].replace('-', '')}.txt",
        mime="text/plain",
    )
    with st.expander("View full report"):
        st.text(report)


def render_ai(chart):
    st.header("✦ AI-Powered Personalized Reading")
    st.caption("Written from your exact placements — not a recycled sun-sign blurb.")
    c1, c2 = st.columns([3, 1])
    focus = c1.selectbox("Focus area",
                         ["general", "career", "relationships", "health", "spiritual path"],
                         key="ai_focus")
    c2.write("")
    c2.write("")
    if c2.button("Generate Reading ✨", type="primary", key="ai_btn"):
        with st.spinner("Writing your reading…"):
            st.session_state["ai_reading"] = generate_llm_interpretation(chart, focus=focus)
    if "ai_reading" in st.session_state:
        with st.container(border=True):
            st.markdown(st.session_state["ai_reading"])


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
                st.write("No answers yet (the log resets when the app restarts).")


# ===========================================================================
#  MAIN
# ===========================================================================
def reset_for_new_chart():
    for key in list(st.session_state.keys()):
        if key.startswith("fb_") or key in ("ai_reading", "quiz_saved"):
            del st.session_state[key]
    st.session_state["quiz_done"] = False


def main():
    inject_css()
    cosmic_hero()

    if "lat_value" not in st.session_state:
        st.session_state.lat_value = 27.7172
        st.session_state.lon_value = 85.3240

    with st.sidebar:
        st.header("Birth Details")
        location_method = st.radio("Location input:",
                                   ["Interactive Map", "Manual Coordinates", "Major Cities"])

        if location_method == "Manual Coordinates":
            st.session_state.lat_value = st.number_input(
                "Latitude", min_value=-90.0, max_value=90.0,
                value=float(st.session_state.lat_value), step=0.0001, format="%.4f")
            st.session_state.lon_value = st.number_input(
                "Longitude", min_value=-180.0, max_value=180.0,
                value=float(st.session_state.lon_value), step=0.0001, format="%.4f")
        elif location_method == "Major Cities":
            city = st.selectbox("City", list(MAJOR_CITIES))
            st.session_state.lat_value, st.session_state.lon_value = MAJOR_CITIES[city]
            st.info(f"Coordinates: {fmt_place(*MAJOR_CITIES[city])}")

        st.subheader("Birth Date & Time")
        birth_date = st.date_input("Birth date", value=date(2000, 1, 1),
                                   min_value=ae.MIN_DATE, max_value=ae.MAX_DATE)
        birth_time = st.time_input("Birth time (local clock)", value=time(12, 0), step=60)
        zones = pytz.common_timezones
        timezone = st.selectbox("Timezone of the birthplace", zones,
                                index=zones.index("Asia/Kathmandu"))
        st.caption("Daylight saving and old timezone rules are applied automatically.")

        st.subheader("Calculation Settings")
        house_system = st.selectbox("House system", ae.HOUSE_SYSTEMS, index=0,
                                    help="Placidus is the most common; Whole Sign is "
                                         "the traditional choice in Vedic astrology.")
        include_houses = st.checkbox("Calculate houses", value=True)
        calculate = st.button("Calculate Complete Chart", type="primary")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Birth Location")
        if location_method == "Interactive Map":
            if FOLIUM_AVAILABLE:
                st.info("Click on the map to select the birth place")
                lat, lon = create_clickable_map(st.session_state.lat_value,
                                                st.session_state.lon_value)
                st.session_state.lat_value, st.session_state.lon_value = lat, lon
            else:
                st.error("The interactive map needs: pip install folium streamlit-folium")
                st.info("Use Manual Coordinates or Major Cities instead.")
        else:
            st.map(pd.DataFrame({"lat": [st.session_state.lat_value],
                                 "lon": [st.session_state.lon_value]}), zoom=8)
    with col2:
        st.subheader("Summary")
        st.metric("Latitude", f"{st.session_state.lat_value:.4f}°")
        st.metric("Longitude", f"{st.session_state.lon_value:.4f}°")
        st.metric("Date", str(birth_date))
        st.metric("Time", birth_time.strftime("%H:%M"))

    if calculate:
        try:
            st.session_state["calculation_results"] = compute_chart(
                birth_date, birth_time, timezone,
                st.session_state.lat_value, st.session_state.lon_value,
                house_system, include_houses)
            reset_for_new_chart()
        except Exception as e:
            st.error(f"Calculation error: {e}")
            st.info("Please check your birth details and try again.")

    # Everything below renders on every rerun once a chart exists, so its
    # buttons keep working.
    r = st.session_state.get("calculation_results")
    if r:
        chart = chart_summary(r)
        if not st.session_state.get("quiz_done"):
            render_quiz(chart)
        else:
            render_results(r)
            render_ai(chart)

    render_admin()


if __name__ == "__main__":
    main()
