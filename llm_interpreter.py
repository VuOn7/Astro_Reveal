#!/usr/bin/env python3
"""
llm_interpreter.py  (multi-provider: fallback OR consensus)
===========================================================
Two ways to generate a chart reading:

  generate_llm_interpretation(...)        -> FALLBACK chain (fast, 1 model)
        Tries Claude -> DeepSeek -> Gemini, returns the first that works.

  generate_consensus_interpretation(...)  -> PANEL consensus (slower, N models)
        Asks Claude, ChatGPT (OpenAI), Gemini, and DeepSeek to each read the
        chart, then a judge model writes ONE reading keeping only what enough
        of them independently agreed on, plus a "where they disagreed" note.

Only the providers whose API keys are set participate; missing ones are skipped.

------------------------------------------------------------------------------
SETUP
------------------------------------------------------------------------------
    pip install anthropic openai

    export ANTHROPIC_API_KEY="sk-ant-..."   # console.anthropic.com  (paid)
    export OPENAI_API_KEY="sk-..."          # platform.openai.com    (paid; no free API)
    export DEEPSEEK_API_KEY="sk-..."        # platform.deepseek.com  (cheap)
    export GEMINI_API_KEY="AIza..."         # aistudio.google.com    (FREE, no card)

Note: ChatGPT's *free* version is a website, not an API. Using "ChatGPT" from
code means OpenAI's paid API. Consensus needs >=2 keys set to do anything useful.
------------------------------------------------------------------------------
"""

import os
import json

# --- Model names (current as of 2026; update if a provider renames one) -----
ANTHROPIC_MODEL = "claude-sonnet-4-6"      # cheaper: "claude-haiku-4-5-20251001"
OPENAI_MODEL    = "gpt-4o-mini"            # cheap OpenAI model
DEEPSEEK_MODEL  = "deepseek-chat"
GEMINI_MODEL    = "gemini-2.5-flash"       # free-tier eligible

OPENAI_BASE_URL   = "https://api.openai.com/v1"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
GEMINI_BASE_URL   = "https://generativelanguage.googleapis.com/v1beta/openai/"


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
# 2. Prompts.
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

JUDGE_SYSTEM = """You are the editor of a panel of {n} astrologers who each \
independently read the SAME chart. Produce ONE final reading.

- Include ONLY interpretations that AT LEAST {k} of the {n} astrologers express \
(the same theme/trait, even if worded differently).
- Drop any claim only one astrologer made (unless {k} is 1).
- Keep the concrete chart references (signs, degrees, nakshatra, pillars, kin) \
that the agreeing astrologers cite, so it stays specific to this person.
- End with a short section titled "Where the astrologers disagreed:" listing \
2-4 points of divergence, one line each. If they were broadly aligned, say so.
- Plain, warm language. Honest framing: tendencies, not fixed predictions.
- About 400-600 words."""


def _build_messages(chart, focus):
    focus_line = (f"\nFocus the reading on: {focus}.\n"
                  if focus and focus.lower() != "general" else "")
    user = ("Here is the person's chart as JSON. Write their reading.\n"
            f"{focus_line}\n```json\n{json.dumps(chart, indent=2, default=str)}\n```")
    return SYSTEM_PROMPT, user


# ---------------------------------------------------------------------------
# 3. Provider call functions.
# ---------------------------------------------------------------------------
def _call_anthropic(system, user):
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = client.messages.create(model=ANTHROPIC_MODEL, max_tokens=1500,
                                  system=system,
                                  messages=[{"role": "user", "content": user}])
    return "".join(b.text for b in resp.content if b.type == "text")


def _call_openai_compatible(system, user, *, api_key_env, base_url, model):
    from openai import OpenAI
    client = OpenAI(api_key=os.environ[api_key_env], base_url=base_url)
    resp = client.chat.completions.create(
        model=model, max_tokens=1500,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}])
    return resp.choices[0].message.content


# Full panel, in priority order (also used as the fallback order).
PANEL = [
    ("Claude", "ANTHROPIC_API_KEY",
     lambda s, u: _call_anthropic(s, u)),
    ("ChatGPT (OpenAI)", "OPENAI_API_KEY",
     lambda s, u: _call_openai_compatible(s, u, api_key_env="OPENAI_API_KEY",
                                          base_url=OPENAI_BASE_URL, model=OPENAI_MODEL)),
    ("Gemini", "GEMINI_API_KEY",
     lambda s, u: _call_openai_compatible(s, u, api_key_env="GEMINI_API_KEY",
                                          base_url=GEMINI_BASE_URL, model=GEMINI_MODEL)),
    ("DeepSeek", "DEEPSEEK_API_KEY",
     lambda s, u: _call_openai_compatible(s, u, api_key_env="DEEPSEEK_API_KEY",
                                          base_url=DEEPSEEK_BASE_URL, model=DEEPSEEK_MODEL)),
]


def _run_panel(system, user):
    """Call every provider whose key is set. Returns (readings, notes)."""
    readings, notes = [], []
    for name, key_env, call in PANEL:
        if not os.environ.get(key_env):
            notes.append(f"{name}: skipped (no {key_env})")
            continue
        try:
            t = call(system, user)
            if t and t.strip():
                readings.append((name, t.strip()))
            else:
                notes.append(f"{name}: empty response")
        except ImportError as e:
            notes.append(f"{name}: library not installed ({e})")
        except Exception as e:
            notes.append(f"{name}: {type(e).__name__} - {e}")
    return readings, notes


# ---------------------------------------------------------------------------
# 4a. FALLBACK mode: first provider that works.
# ---------------------------------------------------------------------------
def generate_llm_interpretation(structured_chart, focus="general", show_provider=True):
    system, user = _build_messages(structured_chart, focus)
    notes = []
    for name, key_env, call in PANEL:
        if not os.environ.get(key_env):
            notes.append(f"{name}: no key ({key_env})")
            continue
        try:
            t = call(system, user)
            if t and t.strip():
                return t + (f"\n\n---\n*Generated by {name}.*" if show_provider else "")
            notes.append(f"{name}: empty response")
        except ImportError as e:
            notes.append(f"{name}: library not installed ({e})")
        except Exception as e:
            notes.append(f"{name}: {type(e).__name__} - {e}")
    return ("Could not generate a reading. Providers tried:\n- "
            + "\n- ".join(notes)
            + "\n\nSet at least one key (the free GEMINI_API_KEY works).")


# ---------------------------------------------------------------------------
# 4b. CONSENSUS mode: panel reads, judge keeps what they agree on.
# ---------------------------------------------------------------------------
def generate_consensus_interpretation(structured_chart, focus="general",
                                      min_agreement="all"):
    """
    min_agreement : "all" (default) keeps only what every available model said.
                    An integer keeps claims made by at least that many models
                    (e.g. 2 or 3 -> richer, less generic).
    """
    system, user = _build_messages(structured_chart, focus)
    readings, notes = _run_panel(system, user)

    if not readings:
        return "No models were available:\n- " + "\n- ".join(notes)

    if len(readings) == 1:
        name, text = readings[0]
        return (text + f"\n\n---\n*Only {name} responded, so this is a single "
                "reading — not a consensus. Add more API keys to cross-check.*")

    n = len(readings)
    k = n if min_agreement in ("all", None) else max(1, min(int(min_agreement), n))

    labels = "ABCDEFGH"
    panel_text = "\n\n".join(f"=== Astrologer {labels[i]} ({nm}) ===\n{tx}"
                             for i, (nm, tx) in enumerate(readings))
    judge_system = JUDGE_SYSTEM.format(n=n, k=k)
    judge_user = ("Independent readings of the same chart follow. Produce the "
                  "consensus reading.\n\n" + panel_text)

    # Judge = first available panel provider (prefers Claude).
    judge_call = judge_name = None
    for nm, key_env, call in PANEL:
        if os.environ.get(key_env):
            judge_call, judge_name = call, nm
            break
    try:
        final = judge_call(judge_system, judge_user)
    except Exception as e:
        return f"Got {n} readings but the consensus step failed: {type(e).__name__} - {e}"

    participants = ", ".join(nm for nm, _ in readings)
    agree_desc = "all agreed on" if k == n else f"at least {k} of {n} agreed on"
    header = (f"*Consensus of {n} models ({participants}) — keeping what "
              f"{agree_desc}. Synthesised by {judge_name}.*\n\n")
    if notes:
        header += "*(Skipped/failed: " + "; ".join(notes) + ")*\n\n"
    return header + final
