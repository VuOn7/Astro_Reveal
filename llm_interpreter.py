#!/usr/bin/env python3
"""
llm_interpreter.py
==================
Writes the personalised reading with Google Gemini, using only the standard
library (no SDK).

Notes:
- gemini-2.5-flash is a "thinking" model and its thinking tokens count against
  maxOutputTokens. Thinking is switched off (THINKING_BUDGET = 0) so the whole
  budget goes to the visible reading.
- Empty, truncated and safety-blocked responses are reported clearly.

Setup:
    export GEMINI_API_KEY="AIza..."        # key from aistudio.google.com
    (Windows: setx GEMINI_API_KEY "AIza...")
On Streamlit Cloud put it in the app's Secrets instead. Never commit the key.
"""

import os
import json
import urllib.request
import urllib.error

# gemini-2.5-flash is on the free tier. gemini-2.0-flash also works and is
# not a thinking model.
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

MAX_OUTPUT_TOKENS = 8192
THINKING_BUDGET = 0        # 0 = off; try 512 for a little reasoning
TEMPERATURE = 0.9


# ---------------------------------------------------------------------------
# 1. Structure the chart (unique numbers in => unique reading out).
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
# 2. Prompt: sectioned Markdown.
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are a warm, insightful, multi-tradition astrologer \
writing a single person's personalised reading. You are given ONE person's \
exact birth chart as JSON, combining Vedic (sidereal), Western (tropical), \
Chinese (Four Pillars / Bazi) and Mayan (Tzolkin) systems.

WRITE THE READING AS CLEAN MARKDOWN, using exactly this structure:

# Your Cosmic Portrait
A 3-4 sentence opening that captures the overall feel of this specific chart \
(name the Sun sign, the Ascendant if present, and the Moon's nakshatra).

## The Threads That Define You
2-3 short paragraphs weaving the four traditions into ONE coherent portrait. \
Explicitly note where systems AGREE and where they create interesting TENSION.

## Vedic & Western — Mind and Soul
A paragraph grounded in the exact placements: cite specific signs, degrees, \
the nakshatra + pada, and the rising sign.

## Chinese Four Pillars — Your Elemental Engine
A paragraph on the Day Master (day-pillar stem + element) as their core nature, \
plus how the surrounding pillars colour it.

## Mayan Signature — Your Spiritual Frequency
A short paragraph on the Tzolkin day-sign, galactic tone and kin.

## Living It Well
A practical, encouraging close: 3-4 concrete strengths to lean on and 2-3 \
growth edges, phrased as tendencies and choices — never fixed fate.

RULES:
- Ground EVERY claim in the actual data. Cite exact signs, degrees, nakshatra, \
day-master pillar and Tzolkin kin/tone. No generic sun-sign lines that would \
fit anyone.
- Warm, clear, plain language. Use **bold** for key terms. Keep paragraphs short.
- Be honest in framing: describe tendencies and themes, not predictions.
- Total length: about 600-800 words."""


def _build_prompt(chart, focus):
    focus_line = ""
    if focus and focus.lower() != "general":
        focus_line = (f"\nGive extra weight to the **{focus}** area of life, "
                      f"and add a short '## Focus: {focus.title()}' section near "
                      f"the end with specific guidance.\n")
    user = ("Here is the person's chart as JSON. Write their reading now, "
            "following the required Markdown structure.\n"
            f"{focus_line}\n```json\n"
            f"{json.dumps(chart, indent=2, default=str)}\n```")
    return SYSTEM_PROMPT, user


# ---------------------------------------------------------------------------
# 3. Call Gemini using only the standard library.
# ---------------------------------------------------------------------------
def _extract_text(payload):
    """Pull visible text out of a Gemini response, skipping 'thought' parts,
    and surface useful diagnostics instead of failing silently."""
    candidates = payload.get("candidates", [])
    if not candidates:
        # Almost always a blocked prompt.
        fb = payload.get("promptFeedback", {})
        reason = fb.get("blockReason")
        if reason:
            raise RuntimeError(f"Prompt blocked by safety filter ({reason}).")
        raise RuntimeError("Gemini returned no candidates: "
                           + json.dumps(payload)[:300])

    cand = candidates[0]
    finish = cand.get("finishReason")
    parts = cand.get("content", {}).get("parts", []) or []

    # Keep only real text parts (a thinking part may carry "thought": true).
    text = "".join(
        p.get("text", "")
        for p in parts
        if isinstance(p, dict) and not p.get("thought")
    ).strip()

    if not text and finish == "MAX_TOKENS":
        raise RuntimeError(
            "Gemini hit the token limit before writing any text. "
            "Lower THINKING_BUDGET or raise MAX_OUTPUT_TOKENS in llm_interpreter.py."
        )
    if not text and finish == "SAFETY":
        raise RuntimeError("Gemini blocked the response for safety reasons.")
    return text, finish


def _call_gemini(system, user):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "maxOutputTokens": MAX_OUTPUT_TOKENS,
            "temperature": TEMPERATURE,
            "thinkingConfig": {"thinkingBudget": THINKING_BUDGET},
        },
    }
    req = urllib.request.Request(
        GEMINI_URL,
        data=json.dumps(body).encode("utf-8"),
        # key in a header, not the URL, so it can't end up in logs
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    text, _finish = _extract_text(payload)
    return text


# ---------------------------------------------------------------------------
# 4. Public function the app calls.
# ---------------------------------------------------------------------------
def generate_llm_interpretation(structured_chart, focus="general", show_provider=True):
    try:
        text = _call_gemini(*_build_prompt(structured_chart, focus))
        if not text:
            return "Gemini returned an empty response. Please try again."
        if show_provider:
            text += "\n\n---\n*Generated by Google Gemini · for reflection and "
            text += "self-understanding, not fixed prediction.*"
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
    print(f"Model={GEMINI_MODEL}  max_out={MAX_OUTPUT_TOKENS}  "
          f"thinking_budget={THINKING_BUDGET}")