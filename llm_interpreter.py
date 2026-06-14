#!/usr/bin/env python3
"""
llm_interpreter.py  (Gemini-only version)
=========================================
Generates dynamic, chart-specific astrology readings using Google Gemini.

Why this version is simple:
- Talks to Gemini via Python's BUILT-IN urllib, so there are no extra libraries
  to install (no anthropic, no openai needed).
- Uses a Flash model, which is covered by Gemini's free tier.

SETUP:
    export GEMINI_API_KEY="AIza..."        # your NEW key from aistudio.google.com
    (Windows: setx GEMINI_API_KEY "AIza...")

Never put the key in this file or in your GitHub repo — only in the env var.
"""

import os
import json
import urllib.request
import urllib.error

GEMINI_MODEL = "gemini-2.5-flash"   # free-tier eligible; "gemini-2.0-flash" also works
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)


# ---------------------------------------------------------------------------
# 1. Structure the chart (unique numbers in => unique reading out).
#    Kept identical so the rest of your app and feedback_collector still work.
# ---------------------------------------------------------------------------
def build_chart_summary(birth_data, vedic_positions, tropical_positions,
                        four_pillars, tzolkin, nakshatra_info, ascendant=None):
    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
             "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

    def sign_of(lon):
        return signs[int(lon // 30)], round(lon % 30, 2)

    vedic = {}
    for p, lon in vedic_positions.items():
        s, d = sign_of(lon)
        vedic[p] = {"sign": s, "degree_in_sign": d, "longitude": round(lon, 2)}
    western = {}
    for p, lon in tropical_positions.items():
        s, d = sign_of(lon)
        western[p] = {"sign": s, "degree_in_sign": d, "longitude": round(lon, 2)}

    summary = {
        "birth": {
            "date": str(birth_data.get("date")), "time": str(birth_data.get("time")),
            "latitude": birth_data.get("lat"), "longitude": birth_data.get("lon"),
            "timezone": birth_data.get("timezone"),
        },
        "vedic_sidereal": vedic,
        "western_tropical": western,
        "moon_nakshatra": {"name": nakshatra_info.get("name"),
                           "lord": nakshatra_info.get("lord"),
                           "pada": nakshatra_info.get("pada")},
        "chinese_four_pillars": {k: {"stem": v[0][0], "element": v[0][1],
                                     "branch": v[1][0], "animal": v[1][1]}
                                 for k, v in four_pillars.items()},
        "mayan_tzolkin": {"kin": tzolkin.get("kin"),
                          "day_sign": tzolkin.get("day_sign"),
                          "galactic_tone": tzolkin.get("galactic_tone")},
    }
    if ascendant is not None:
        s, d = sign_of(ascendant)
        summary["ascendant"] = {"sign": s, "degree_in_sign": d}
    return summary


# ---------------------------------------------------------------------------
# 2. Prompt.
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are an experienced multi-tradition astrologer writing a \
personalised reading. You are given ONE person's exact chart as JSON.

Rules:
- Ground EVERY claim in the specific data: cite exact signs, degrees, the \
nakshatra + pada, the day-master pillar, and the Tzolkin kin/tone. Generic \
sun-sign statements that would apply to anyone are not allowed.
- Weave the four traditions (Vedic, Western, Chinese, Mayan) into one coherent \
portrait rather than four disconnected lists. Note where they agree or tension.
- Write in clear, warm, plain language. No jargon dumps.
- Be honest in framing: describe tendencies and themes, not fixed predictions.
- Length: about 500-700 words unless told otherwise."""


def _build_prompt(chart, focus):
    focus_line = (f"\nFocus the reading on: {focus}.\n"
                  if focus and focus.lower() != "general" else "")
    user = ("Here is the person's chart as JSON. Write their reading.\n"
            f"{focus_line}\n```json\n{json.dumps(chart, indent=2, default=str)}\n```")
    return SYSTEM_PROMPT, user


# ---------------------------------------------------------------------------
# 3. Call Gemini using only the standard library.
# ---------------------------------------------------------------------------
def _call_gemini(system, user):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"maxOutputTokens": 1500, "temperature": 0.85},
    }
    req = urllib.request.Request(
        f"{GEMINI_URL}?key={api_key}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    candidates = payload.get("candidates", [])
    if not candidates:
        # Usually means the prompt or output was blocked by a safety filter.
        raise RuntimeError("Gemini returned no candidates: "
                           + json.dumps(payload)[:300])
    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts).strip()


# ---------------------------------------------------------------------------
# 4. Public function the app calls.
# ---------------------------------------------------------------------------
def generate_llm_interpretation(structured_chart, focus="general", show_provider=True):
    try:
        text = _call_gemini(*_build_prompt(structured_chart, focus))
        if not text:
            return "Gemini returned an empty response — please try again."
        if show_provider:
            text += "\n\n---\n*Generated by Google Gemini.*"
        return text

    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:300]
        if e.code == 429:
            return ("Gemini's free-tier rate limit was hit (about 15 requests per "
                    "minute). Wait a minute and try again.")
        if e.code in (400, 401, 403):
            return ("Gemini rejected the request. Check that GEMINI_API_KEY is set, "
                    "valid, and starts with 'AIza'. "
                    f"Details: {detail}")
        return f"Gemini error {e.code}: {detail}"
    except urllib.error.URLError as e:
        return f"Could not reach Gemini (network/connection issue): {e.reason}"
    except RuntimeError as e:
        return f"AI interpretation unavailable: {e}"
    except Exception as e:
        return f"AI interpretation could not be generated ({type(e).__name__}: {e})."


# ---------------------------------------------------------------------------
# 5. Compatibility shim: if your app still calls the old consensus function,
#    it keeps working by just returning a single Gemini reading.
# ---------------------------------------------------------------------------
def generate_consensus_interpretation(structured_chart, focus="general",
                                      min_agreement="all"):
    return generate_llm_interpretation(structured_chart, focus)


if __name__ == "__main__":
    # Offline structure test (no network call).
    demo = build_chart_summary(
        {"date": "1990-01-01", "time": "12:00", "lat": 27.7, "lon": 85.3, "timezone": "UTC"},
        {"Sun": 280.0, "Moon": 45.0}, {"Sun": 280.0, "Moon": 45.0},
        {"year": (("Geng", "Yang Metal"), ("Wu", "Horse")),
         "month": (("Ji", "Yin Earth"), ("Chou", "Ox")),
         "day": (("Jia", "Yang Wood"), ("Zi", "Rat")),
         "hour": (("Bing", "Yang Fire"), ("Wu", "Horse"))},
        {"kin": 100, "day_sign": "Ahau", "galactic_tone": 9},
        {"name": "Rohini", "lord": "Moon", "pada": 2}, ascendant=130.0)
    print("build_chart_summary OK. Keys:", list(demo.keys()))
