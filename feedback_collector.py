#!/usr/bin/env python3
"""
feedback_collector.py
=====================
Turns each chart factor into a BLIND multiple-choice question and records the
user's pick, so you can (a) collect labelled data and (b) honestly measure
whether the predictions carry any signal above random chance.

Design that avoids the Barnum effect:
- For each factor (Sun sign, Ascendant, Moon nakshatra, Day Master, Tzolkin),
  the user's REAL description is shuffled together with descriptions from OTHER
  values of the same factor. No labels, so they can't tell which is "theirs".
- We log which option was correct and which they chose -> a "hit" or "miss".
- Compare hit-rate to chance (1/n_options). If hit-rate is not clearly above
  chance, the predictions don't discriminate, and there's nothing to train on.

All trait descriptions below are copied from your existing calculator data
(sign/nakshatra/tzolkin meanings) or are standard published associations
(five-element day-master). Nothing here is invented.
"""

import os
import json
import hashlib
import random
import datetime
from collections import defaultdict

# --- Option pools (sourced from your calculator's own data) -----------------
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
    """Append one labelled data point as JSON-lines. Only run with consent."""
    if not consent:
        return
    rec = {
        "ts": datetime.datetime.utcnow().isoformat(timespec="seconds"),
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
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
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
