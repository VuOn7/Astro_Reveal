<div align="center">

# ✦ Astro_Reveal ✦

*By [Bhuwan Awasthi](https://github.com/VuOn7).*

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

- **🎂 Three taps to start** — birthday, time (or *I don't know*), and town. Type your town and pick it (works offline, ~50,000 places); the timezone sets itself, daylight saving included. Your Sun sign pops up the moment you pick a date.
- **🎮 A 60-second game** — pick the description that feels like you, one tap per round, before you see anything. It quietly tests whether astrology beats guessing (see below).
- **🃏 Flip cards** — your Sun, Moon and Rising, each drawn with the real stars of its constellation. Tap to turn over.
- **🎡 The chart wheel** — colour-coded by element; hover a planet to see where it was.
- **🌌 The sky above you** — the actual stars, constellations and planets over your birthplace at the moment you were born.
- **🌏 Around the world** — your Chinese year animal, Vedic Moon star (nakshatra) and Maya day sign, as cards.
- **💞 Match with someone** — add anyone's birthday for a fun compatibility score (Sun elements, Moons, Venus and Mars, Chinese animals).
- **⏳ Birth-time explorer** — slide through your birth day to watch your Rising sign change. Handy if you're not sure of the time.
- **🌙 Today's sky** — the Moon's phase and sign today, and what it's touching in your chart.
- **✍️ A written reading** by Google Gemini, grounded in your exact placements.
- **🔭 All the details** — planet tables, aspects, houses (Placidus, Regiomontanus, Porphyry, Equal, Whole Sign), a South Indian rasi chart, the Four Pillars in Chinese characters, the 260-day Tzolkin count, and a downloadable report.

## 🔬 The honesty layer (what makes this different)

Astrology readings are famously vulnerable to the [Barnum effect](https://en.wikipedia.org/wiki/Barnum_effect) — vague statements that feel personal but apply to everyone. `feedback_collector.py` is designed to cut straight through that.

Right after you enter your details, **before your chart is revealed**, the app plays a short game of up to four rounds. For each chart factor (Ascendant, Moon nakshatra, Day Master, Tzolkin sign; the Sun sign is left out because most people already know theirs) it shows your *real* description shuffled among descriptions for **other** values of that same factor — no labels. You pick the one that fits you best, and (only if you agree) the app logs whether you picked your own. Because you haven't seen your chart yet, you can't just recognise the text. You can also skip it.

Then it compares your hit-rate against pure chance:

> If hit-rate ≈ chance-rate, the predictions don't actually discriminate — and the app says so, instead of pretending otherwise.

It's an astrology tool that's willing to keep score against itself.

To see the running numbers, set `FEEDBACK_ADMIN_PASSWORD` in the app's Secrets; an admin panel then appears at the bottom of the page. (On Streamlit Cloud the log file resets whenever the app restarts.)

## 🛠 Tech stack

| Layer | Tools |
|-------|-------|
| App / UI | [Streamlit](https://streamlit.io/) with a native theme (`.streamlit/config.toml`) and self-hosted fonts |
| Maps & places | `folium` + `streamlit-folium` with OpenStreetMap tiles, `geonamescache` (GeoNames) |
| Stars | Constellation figures and star positions from [d3-celestial](https://github.com/ofrohn/d3-celestial) (BSD) |
| Data | `pandas`, `pytz` |
| AI readings | Google **Gemini** (`gemini-2.5-flash`) via the standard-library `urllib` — no heavy SDK |
| Ephemeris | `astro_engine.py`, pure Python: Meeus Sun & Moon, JPL Keplerian elements for the planets, house systems, Lahiri ayanamsa, Bazi & Tzolkin |

## 🚀 Run it locally

```bash
# 1. Clone
git clone https://github.com/VuOn7/Astro_Reveal.git
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
├── astro_calculator.py     # Streamlit app: the pages
├── astro_engine.py         # All the chart maths (python3 astro_engine.py runs its self-checks)
├── astro_charts.py         # Every drawing: cards, wheel, sky map, explorer, score ring (SVG)
├── astro_content.py        # Short texts, symbols and the compatibility game
├── sky_data.py             # Stars and constellation figures (from d3-celestial, BSD)
├── places.py               # Offline birthplace search and timezone lookup
├── .streamlit/config.toml  # Theme: colours, fonts, corners
├── static/fonts/           # Fraunces, Instrument Sans, Noto Sans Symbols (OFL)
├── llm_interpreter.py      # Gemini reading generator (chart → personalised text)
├── feedback_collector.py   # Blind MCQ accuracy test (the honesty layer)
├── requirements.txt        # Dependencies
├── LICENSE                 # GNU GPL v3
└── README.md               # You are here
```

## ⚠️ Notes & disclaimer

- Positions come from published low-precision methods (Meeus for the Sun and Moon, JPL's approximate Keplerian elements for the planets). They're typically within 0.01–0.2° and are checked against known events (equinoxes, the 2020 Jupiter–Saturn conjunction, transits of Venus and Mercury, Mars' 2003 opposition). That's plenty for astrology, but it isn't an observatory ephemeris.
- Supported birth dates: 1800–2050 (the range the planet elements are fitted for).
- Placidus houses can't be drawn inside the polar circles; there the app falls back to Porphyry and says so.
- Astrology describes **tendencies and themes, not fixed fate.** Use Astro_Reveal for self-reflection and curiosity — not as a basis for major life decisions.

## 📜 License

Released under the **GNU General Public License v3.0**. See [`LICENSE`](./LICENSE) for the full text. You're free to use, study, share, and modify it — derivative works must stay open under the same license.

---

<div align="center">

*Made with curiosity about the stars — and honesty about what they can and can't tell us.* ✦

</div>