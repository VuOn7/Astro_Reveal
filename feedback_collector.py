#!/usr/bin/env python3
"""
feedback_collector.py
=====================
The blind test. Each chart factor becomes a multiple-choice question: the
person's real description is shuffled in with descriptions of OTHER values of
the same factor, with no labels. The app shows it before revealing the chart,
so people can't just recognise their own text.

Each answer is logged as a hit or a miss. If the hit-rate across many people
is not clearly above chance (1 / number of options), the descriptions don't
really discriminate - and the stats will say so.

The descriptions are the calculator's own sign / nakshatra / Tzolkin meanings,
plus the standard five-element Day Master descriptions.
"""

import os
import json
import hashlib
import random
import datetime
from collections import defaultdict

# --- Option pools ------------------------------------------------------------
SIGN_TRAITS = {
    "Aries": "Dynamic, pioneering, leadership-driven, courageous, impulsive, competitive",
    "Taurus": "Stable, practical, determined, artistic, security-focused, stubborn",
    "Gemini": "Intellectual, communicative, versatile, curious, dual-natured, restless",
    "Cancer": "Emotional, nurturing, intuitive, protective, family-oriented, moody",
    "Leo": "Creative, confident, dramatic, generous, attention-seeking, performer",
    "Virgo": "Analytical, perfectionist, service-oriented, practical, critical, health-conscious",
    "Libra": "Harmonious, diplomatic, artistic, relationship-focused, indecisive, beauty-loving",
    "Scorpio": "Intense, transformative, mysterious, passionate, secretive, regenerative",
    "Sagittarius": "Philosophical, adventurous, optimistic, truth-seeking, freedom-loving, blunt",
    "Capricorn": "Ambitious, disciplined, traditional, responsible, status-conscious, persistent",
    "Aquarius": "Independent, innovative, humanitarian, unconventional, detached, visionary",
    "Pisces": "Intuitive, compassionate, spiritual, dreamy, escapist, artistic",
}

NAKSHATRA_TRAITS = {
    "Ashwini": "New beginnings, quick action", "Bharani": "Transformation, restraint",
    "Krittika": "Cutting through illusion", "Rohini": "Growth, fertility, beauty",
    "Mrigashira": "Searching, curiosity", "Ardra": "Intensity, change",
    "Punarvasu": "Renewal, optimism", "Pushya": "Nourishment, protection",
    "Ashlesha": "Mystical knowledge", "Magha": "Ancestral power, authority",
    "Purva Phalguni": "Creativity, relationships", "Uttara Phalguni": "Leadership, generosity",
    "Hasta": "Skill, dexterity", "Chitra": "Artistic creation",
    "Swati": "Independence, flexibility", "Vishakha": "Determination, focus",
    "Anuradha": "Devotion, friendship", "Jyeshtha": "Seniority, protection",
    "Mula": "Root investigation", "Purva Ashadha": "Invincibility, pride",
    "Uttara Ashadha": "Victory, achievement", "Shravana": "Learning, listening",
    "Dhanishta": "Wealth, music", "Shatabhisha": "Healing, mystery",
    "Purva Bhadrapada": "Spiritual intensity", "Uttara Bhadrapada": "Deep wisdom",
    "Revati": "Completion, journeys",
}

TZOLKIN_TRAITS = {
    "Imix": "Primordial energy", "Ik": "Spirit, breath", "Akbal": "Inner temple",
    "Kan": "Growth potential", "Chicchan": "Life force", "Cimi": "Transformation",
    "Manik": "Healing hands", "Lamat": "Star seed", "Muluc": "Offering",
    "Oc": "Loyalty, guidance", "Chuen": "Artistry", "Eb": "Human experience",
    "Ben": "Flowing waters", "Ix": "Magical powers", "Men": "Planetary mind",
    "Cib": "Ancient wisdom", "Caban": "Sacred knowledge", "Etznab": "Mirror of truth",
    "Cauac": "Catalytic energy", "Ahau": "Enlightenment",
}

# Standard Bazi day-master (five-element + polarity) descriptions.
ELEMENT_TRAITS = {
    "Yang Wood": "Like a tall tree: upright, ambitious, principled, steady",
    "Yin Wood": "Like a vine: adaptable, cooperative, flexible, resourceful",
    "Yang Fire": "Like the sun: outgoing, warm, expressive, energetic",
    "Yin Fire": "Like a candle: focused, sensitive, attentive, intuitive",
    "Yang Earth": "Like a mountain: stable, reliable, protective, stubborn",
    "Yin Earth": "Like a field: nurturing, supportive, careful, accommodating",
    "Yang Metal": "Like an axe: decisive, strong, direct, justice-driven",
    "Yin Metal": "Like jewellery: refined, precise, elegant, detail-oriented",
    "Yang Water": "Like the ocean: dynamic, sociable, adventurous, persuasive",
    "Yin Water": "Like a stream: gentle, imaginative, intuitive, persistent",
}


# --- Build blind MCQs -------------------------------------------------------
def _seed_for(chart):
    raw = json.dumps(chart.get("birth", {}), sort_keys=True)
    return int(hashlib.sha256(raw.encode()).hexdigest(), 16) % (2 ** 32)


def chart_id_for(chart):
    """Anonymised, stable id for a chart (no raw birth data stored in logs)."""
    raw = json.dumps(chart.get("birth", {}), sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _make_mcq(factor, true_value, pool, n_options, rng):
    correct = pool.get(true_value)
    if correct is None:
        return None
    others = [v for k, v in pool.items() if k != true_value]
    distractors = rng.sample(others, min(n_options - 1, len(others)))
    options = distractors + [correct]
    rng.shuffle(options)
    return {
        "factor": factor,
        "chart_value": true_value,
        "options": options,                 # shown to user, UNLABELLED
        "correct_index": options.index(correct),  # kept server-side, hidden
    }


def build_feedback_form(chart, n_options=4):
    """Return a list of blind MCQ items for the chart's key factors."""
    rng = random.Random(_seed_for(chart))
    items = []

    sun = chart.get("western_tropical", {}).get("Sun", {}).get("sign")
    if sun:
        items.append(_make_mcq("Sun sign", sun, SIGN_TRAITS, n_options, rng))

    asc = chart.get("ascendant", {}).get("sign")
    if asc:
        items.append(_make_mcq("Ascendant", asc, SIGN_TRAITS, n_options, rng))

    nak = chart.get("moon_nakshatra", {}).get("name")
    if nak:
        items.append(_make_mcq("Moon nakshatra", nak, NAKSHATRA_TRAITS, n_options, rng))

    elem = chart.get("chinese_four_pillars", {}).get("day", {}).get("element")
    if elem:
        items.append(_make_mcq("Day Master", elem, ELEMENT_TRAITS, n_options, rng))

    ds = chart.get("mayan_tzolkin", {}).get("day_sign")
    if ds:
        items.append(_make_mcq("Mayan day sign", ds, TZOLKIN_TRAITS, n_options, rng))

    return [i for i in items if i]


# --- Record + analyse -------------------------------------------------------
def record_response(path, chart_id, item, chosen_index, consent=True):
    """Append one labelled data point as JSON-lines. Only call with consent."""
    if not consent:
        return
    rec = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "shown_before_chart": True,
        "chart_id": chart_id,
        "factor": item["factor"],
        "chart_value": item["chart_value"],
        "n_options": len(item["options"]),
        "chosen_text": item["options"][chosen_index] if chosen_index is not None else None,
        "correct_index": item["correct_index"],
        "chosen_index": chosen_index,
        "hit": int(chosen_index == item["correct_index"]),
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def summarize_log(path):
    """Hit-rate vs chance per factor. hit_rate ~ chance_rate => no signal."""
    if not os.path.exists(path):
        return {}
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    if not rows:
        return {}
    agg = defaultdict(lambda: {"hits": 0, "total": 0, "chance": 0.0})
    for r in rows:
        a = agg[r["factor"]]
        a["hits"] += r["hit"]; a["total"] += 1; a["chance"] += 1.0 / r["n_options"]
    out = {}
    th = tt = tc = 0
    for f, a in agg.items():
        out[f] = {"responses": a["total"],
                  "hit_rate": round(a["hits"] / a["total"], 3),
                  "chance_rate": round(a["chance"] / a["total"], 3)}
        th += a["hits"]; tt += a["total"]; tc += a["chance"]
    out["_overall"] = {"responses": tt,
                       "hit_rate": round(th / tt, 3),
                       "chance_rate": round(tc / tt, 3)}
    return out


if __name__ == "__main__":
    # tiny self-test
    demo = {
        "birth": {"date": "1990-01-01"},
        "western_tropical": {"Sun": {"sign": "Capricorn"}},
        "ascendant": {"sign": "Leo"},
        "moon_nakshatra": {"name": "Rohini"},
        "chinese_four_pillars": {"day": {"element": "Yang Wood"}},
        "mayan_tzolkin": {"day_sign": "Ahau"},
    }
    form = build_feedback_form(demo)
    print(f"Built {len(form)} questions:")
    for q in form:
        print(" -", q["factor"], "->", len(q["options"]), "options")
