<div align="center">

# ✦ Astro_Reveal ✦

**One birth chart, four ancient lenses.**
Read your cosmic alignment through Vedic, Western, Chinese, and Mayan astrology — with AI-written readings grounded in your *exact* placements.

[![Open in Streamlit](https://img.shields.io/badge/Launch%20the%20App-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://astroreveal-yfm2dfst8rhdijrdgfm25j.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue?style=for-the-badge)](./LICENSE)

[**🌌 Open the live app →**](https://astroreveal-yfm2dfst8rhdijrdgfm25j.streamlit.app/)

</div>

---

## What is this?

Astro_Reveal takes a single birth date, time, and location and computes a full chart across **four independent astrological traditions** — then weaves them into one coherent, AI-written portrait. Where most apps hand you a recycled sun-sign blurb, this one cites your actual signs, degrees, nakshatra, day-master, and Tzolkin kin.

It also does something unusual for an astrology app: it **honestly measures whether its own readings carry any signal above random chance.** More on that below.

## ✨ Features

- **Four traditions, one chart**
  - 🕉 **Vedic (sidereal)** — Lahiri ayanamsa, planetary positions, Moon nakshatra + pada, Lagna
  - ♋ **Western (tropical)** — Sun/Moon/rising, planetary placements, multiple house systems
  - ☯ **Chinese Four Pillars (Bazi)** — Year/Month/Day/Hour pillars and your Day Master
  - 🌞 **Mayan Tzolkin** — day-sign, galactic tone, and kin (GMT 584283 correlation)
- **🤖 AI-powered readings** — dynamic, chart-specific interpretations via Google Gemini, written to ground every claim in your real data
- **🗺 Interactive birth-location map** — click anywhere, or pick from major cities / manual coordinates
- **📊 Cross-system comparison** — see where the traditions agree and where they tension
- **📄 Downloadable report** — export a full text analysis
- **🔬 Built-in honesty check** — a blind feedback system that tests prediction accuracy (see below)

## 🔬 The honesty layer (what makes this different)

Astrology readings are famously vulnerable to the [Barnum effect](https://en.wikipedia.org/wiki/Barnum_effect) — vague statements that feel personal but apply to everyone. `feedback_collector.py` is designed to cut straight through that.

For each chart factor (Sun sign, Ascendant, Moon nakshatra, Day Master, Tzolkin sign), the app shows your *real* description shuffled blindly among descriptions for **other** values of that same factor — no labels. You pick the one that fits you best. The app logs whether you picked the "correct" one.

Then it compares your hit-rate against pure chance:

> If hit-rate ≈ chance-rate, the predictions don't actually discriminate — and the app says so, instead of pretending otherwise.

It's an astrology tool that's willing to keep score against itself.

## 🛠 Tech stack

| Layer | Tools |
|-------|-------|
| App / UI | [Streamlit](https://streamlit.io/) + custom cosmic CSS theme |
| Maps | `folium` + `streamlit-folium` |
| Data | `pandas`, `pytz` |
| AI readings | Google **Gemini** (`gemini-2.5-flash`) via the standard-library `urllib` — no heavy SDK |
| Ephemeris | Self-contained planetary series, Lahiri ayanamsa, Bazi & Tzolkin math (pure Python) |

## 🚀 Run it locally

```bash
# 1. Clone
git clone https://github.com/<your-username>/Astro_Reveal.git
cd Astro_Reveal

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your Gemini API key (free from https://aistudio.google.com)
export GEMINI_API_KEY="AIza..."          # macOS / Linux
# setx GEMINI_API_KEY "AIza..."          # Windows (then reopen terminal)

# 4. Launch
streamlit run astro_calculator.py
```

The app opens at `http://localhost:8501`.

> **Deploying on Streamlit Cloud?** Don't use an env var — add your key under **App settings → Secrets** instead:
> ```toml
> GEMINI_API_KEY = "AIza..."
> ```
> 🔐 **Never commit your API key.** Keep it in the env var or in `secrets.toml` only.

## 📁 Project structure

```
Astro_Reveal/
├── astro_calculator.py     # Main Streamlit app: chart math, UI, theme
├── llm_interpreter.py      # Gemini reading generator (chart → personalised text)
├── feedback_collector.py   # Blind MCQ accuracy test (the honesty layer)
├── requirements.txt        # Dependencies
├── LICENSE                 # GNU GPL v3
└── README.md               # You are here
```

## ⚠️ Notes & disclaimer

- The planetary calculations use **simplified analytic series** — accurate enough for an exploratory, reflective tool, but not observatory-grade ephemeris precision. Treat exact degrees as approximate.
- Astrology describes **tendencies and themes, not fixed fate.** Use Astro_Reveal for self-reflection and curiosity — not as a basis for major life decisions.

## 📜 License

Released under the **GNU General Public License v3.0**. See [`LICENSE`](./LICENSE) for the full text. You're free to use, study, share, and modify it — derivative works must stay open under the same license.

---

<div align="center">

*Made with curiosity about the stars — and honesty about what they can and can't tell us.* ✦

</div>