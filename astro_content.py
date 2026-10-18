"""
astro_content.py
================
The words and symbols Astro_Reveal shows: short, original lines written for
this app, plus traditional associations (signs, elements, nakshatra symbols,
Chinese animals, Maya day-sign meanings), which are cultural facts.
"""

import math

ELEMENTS = {
    # name: (emoji, base colour, light tint, dark ink for text)
    "Fire": ("🔥", "#F26B4F", "#FFE9E3", "#B23A1F"),
    "Earth": ("🌿", "#3FA06B", "#E3F5EA", "#1F6E45"),
    "Air": ("🌬️", "#F2B705", "#FFF4CC", "#8A6500"),
    "Water": ("💧", "#3B82F6", "#E3EEFF", "#1D4FB8"),
}

SIGNS = [
    # name, element, modality, emoji, keywords, one line
    ("Aries", "Fire", "Cardinal", "🐏", ["bold", "direct", "first to try"],
     "You go first and work it out on the way."),
    ("Taurus", "Earth", "Fixed", "🐂", ["steady", "sensual", "loyal"],
     "You build slowly and make things last."),
    ("Gemini", "Air", "Mutable", "👯", ["curious", "quick", "chatty"],
     "You collect ideas and people, then connect them."),
    ("Cancer", "Water", "Cardinal", "🦀", ["caring", "protective", "intuitive"],
     "You make places and people feel like home."),
    ("Leo", "Fire", "Fixed", "🦁", ["warm", "expressive", "generous"],
     "You light up a room and want everyone in it to shine."),
    ("Virgo", "Earth", "Mutable", "🌾", ["precise", "helpful", "thoughtful"],
     "You notice what others miss and quietly fix it."),
    ("Libra", "Air", "Cardinal", "⚖️", ["fair", "charming", "balanced"],
     "You look for harmony and the beauty in things."),
    ("Scorpio", "Water", "Fixed", "🦂", ["deep", "loyal", "intense"],
     "You go all in and see beneath the surface."),
    ("Sagittarius", "Fire", "Mutable", "🏹", ["free", "optimistic", "honest"],
     "You chase meaning, horizons and a good story."),
    ("Capricorn", "Earth", "Cardinal", "🐐", ["driven", "patient", "grounded"],
     "You climb step by step, and you get there."),
    ("Aquarius", "Air", "Fixed", "🏺", ["original", "independent", "kind"],
     "You think ahead and care about the bigger picture."),
    ("Pisces", "Water", "Mutable", "🐟", ["dreamy", "empathetic", "creative"],
     "You feel everything and turn it into something gentle."),
]
SIGN_NAMES = [s[0] for s in SIGNS]

PLACEMENTS = {
    "Sun": ("☀️", "Your Sun", "Who you are at heart."),
    "Moon": ("🌙", "Your Moon", "How you feel, and what comforts you."),
    "Rising": ("🌅", "Your Rising", "How you come across when people first meet you."),
}

PLANET_TOPICS = {
    "Sun": "who you are", "Moon": "how you feel", "Mercury": "how you think and talk",
    "Venus": "what you love", "Mars": "what drives you", "Jupiter": "where you grow",
    "Saturn": "where you work hardest", "Uranus": "where you break the rules",
    "Neptune": "where you dream", "Rahu": "what you're hungry for", "Ketu": "what you let go of",
}

NAKSHATRA_EMOJI = {
    "Ashwini": "🐴", "Bharani": "🌺", "Krittika": "🔥", "Rohini": "🛞", "Mrigashira": "🦌",
    "Ardra": "💧", "Punarvasu": "🏹", "Pushya": "🐄", "Ashlesha": "🐍", "Magha": "👑",
    "Purva Phalguni": "🛏️", "Uttara Phalguni": "🤝", "Hasta": "✋", "Chitra": "💎",
    "Swati": "🌱", "Vishakha": "🏛️", "Anuradha": "🌸", "Jyeshtha": "☂️", "Mula": "🌿",
    "Purva Ashadha": "🌊", "Uttara Ashadha": "🐘", "Shravana": "👂", "Dhanishta": "🥁",
    "Shatabhisha": "✨", "Purva Bhadrapada": "⚔️", "Uttara Bhadrapada": "⚓", "Revati": "🐟",
}

CHINESE_ANIMALS = {
    "Rat": ("🐀", ["quick-witted", "resourceful", "charming"]),
    "Ox": ("🐂", ["dependable", "patient", "strong"]),
    "Tiger": ("🐅", ["brave", "confident", "bold"]),
    "Rabbit": ("🐇", ["gentle", "elegant", "kind"]),
    "Dragon": ("🐉", ["ambitious", "energetic", "lucky"]),
    "Snake": ("🐍", ["wise", "intuitive", "graceful"]),
    "Horse": ("🐎", ["free-spirited", "active", "warm"]),
    "Goat": ("🐐", ["calm", "creative", "kind-hearted"]),
    "Monkey": ("🐒", ["clever", "playful", "inventive"]),
    "Rooster": ("🐓", ["observant", "hard-working", "honest"]),
    "Dog": ("🐕", ["loyal", "fair", "protective"]),
    "Pig": ("🐖", ["generous", "easygoing", "sincere"]),
}
ANIMAL_ORDER = ["Rat", "Ox", "Tiger", "Rabbit", "Dragon", "Snake",
                "Horse", "Goat", "Monkey", "Rooster", "Dog", "Pig"]

FIVE_ELEMENTS = {
    # Chinese element: (emoji, colour, tint, ink)
    "Wood": ("🌳", "#3FA06B", "#E3F5EA", "#1F6E45"),
    "Fire": ("🔥", "#F26B4F", "#FFE9E3", "#B23A1F"),
    "Earth": ("⛰️", "#D29A2E", "#FBF0D9", "#7A5410"),
    "Metal": ("🔔", "#8E95A8", "#EEF0F5", "#4A5164"),
    "Water": ("💧", "#3B82F6", "#E3EEFF", "#1D4FB8"),
}

MAYA_SIGNS = {
    # Maya name: (English glyph, emoji)
    "Imix": ("Crocodile", "🐊"), "Ik": ("Wind", "🌬️"), "Akbal": ("Night", "🌙"),
    "Kan": ("Seed", "🌱"), "Chicchan": ("Serpent", "🐍"), "Cimi": ("Transformer", "🦋"),
    "Manik": ("Deer", "🦌"), "Lamat": ("Star", "⭐"), "Muluc": ("Water", "💧"),
    "Oc": ("Dog", "🐕"), "Chuen": ("Monkey", "🐒"), "Eb": ("Road", "🌾"),
    "Ben": ("Reed", "🎋"), "Ix": ("Jaguar", "🐆"), "Men": ("Eagle", "🦅"),
    "Cib": ("Owl", "🦉"), "Caban": ("Earth", "🌍"), "Etznab": ("Flint", "🗡️"),
    "Cauac": ("Storm", "⛈️"), "Ahau": ("Sun", "☀️"),
}

MOON_PHASES = [  # (start of elongation range, name, emoji)
    (0, "New Moon", "🌑"), (22.5, "Waxing crescent", "🌒"), (67.5, "First quarter", "🌓"),
    (112.5, "Waxing gibbous", "🌔"), (157.5, "Full Moon", "🌕"), (202.5, "Waning gibbous", "🌖"),
    (247.5, "Last quarter", "🌗"), (292.5, "Waning crescent", "🌘"), (337.5, "New Moon", "🌑"),
]

TRANSIT_MOOD = {
    "Sun": "your energy", "Moon": "your mood", "Mercury": "conversations",
    "Venus": "love and pleasure", "Mars": "your drive", "Jupiter": "luck and growth",
    "Saturn": "focus and patience",
}


def sign(lon_or_index):
    """Sign tuple for a longitude (float) or an index (int)."""
    i = lon_or_index if isinstance(lon_or_index, int) else int((lon_or_index % 360) // 30)
    return SIGNS[i]


def element_of(sign_name):
    return SIGNS[SIGN_NAMES.index(sign_name)][1]


def moon_phase(sun_lon, moon_lon):
    e = (moon_lon - sun_lon) % 360
    name, emoji = MOON_PHASES[0][1:]
    for start, n, em in MOON_PHASES:
        if e >= start:
            name, emoji = n, em
    illum = (1 - math.cos(math.radians(e))) / 2
    return name, emoji, illum


# ---------------------------------------------------------------------------
# compatibility (for fun)
# ---------------------------------------------------------------------------
GOOD_ELEMENT_PAIRS = {frozenset(("Fire", "Air")), frozenset(("Earth", "Water"))}
HARD_ELEMENT_PAIRS = {frozenset(("Fire", "Water")), frozenset(("Earth", "Air"))}


def _aspect(a, b):
    d = abs((a - b + 180) % 360 - 180)
    for name, angle, orb, kind in (("conjunct", 0, 8, "meet"), ("sextile", 60, 5, "easy"),
                                   ("square", 90, 7, "spark"), ("trine", 120, 7, "easy"),
                                   ("opposite", 180, 8, "spark")):
        if abs(d - angle) <= orb:
            return name, kind
    return None, None


def compatibility(me, them, my_animal, their_animal):
    """me / them: tropical positions. Returns (score 0-100, verdict, highlights)."""
    notes, score = [], 0.0

    e1, e2 = element_of(sign(me["Sun"])[0]), element_of(sign(them["Sun"])[0])
    if e1 == e2:
        score += 25
        notes.append((ELEMENTS[e1][0], f"Both {e1} Suns: you get each other without trying."))
    elif frozenset((e1, e2)) in GOOD_ELEMENT_PAIRS:
        score += 22
        notes.append(("✨", f"{e1} and {e2} Suns feed each other's energy."))
    elif frozenset((e1, e2)) in HARD_ELEMENT_PAIRS:
        score += 10
        notes.append(("🌗", f"{e1} meets {e2}: different speeds, plenty to learn."))
    else:
        score += 15
        notes.append(("🤝", f"{e1} and {e2} Suns: different, and that's useful."))

    name, kind = _aspect(me["Moon"], them["Moon"])
    if kind in ("easy", "meet"):
        score += 25
        notes.append(("🌙", "Your Moons get along: you feel at ease together."))
    elif kind == "spark":
        score += 13
        notes.append(("🌙", f"Your Moons are {name}: moods can clash, then make up."))
    else:
        score += 17
        notes.append(("🌙", "Your Moons are independent: you give each other room."))

    chemistry = False
    for a, b, who in (("Venus", "Mars", "Your Venus and their Mars"),
                      ("Mars", "Venus", "Your Mars and their Venus")):
        name, kind = _aspect(me[a], them[b])
        if kind:
            score += 13 if kind != "spark" else 11
            if not chemistry:
                notes.append(("💘", f"{who} are {name}: real chemistry."))
            chemistry = True
        else:
            score += 6
    if not chemistry:
        notes.append(("🕯️", "The chemistry is a slow burn: it grows as you get to know each other."))

    a, b = ANIMAL_ORDER.index(my_animal), ANIMAL_ORDER.index(their_animal)
    ea, eb = CHINESE_ANIMALS[my_animal][0], CHINESE_ANIMALS[their_animal][0]
    if a == b:
        score += 15
        notes.append((ea, f"Both born in a {my_animal} year: same wavelength."))
    elif (a - b) % 4 == 0:
        score += 25
        notes.append((ea + eb, f"{my_animal} and {their_animal} are a classic best-match trio."))
    elif (a + b) % 12 == 1:
        score += 22
        notes.append((ea + eb, f"{my_animal} and {their_animal} are secret friends in Chinese astrology."))
    elif (a - b) % 12 == 6:
        score += 6
        notes.append((ea + eb, f"{my_animal} and {their_animal} are opposite signs: hot and cold."))
    else:
        score += 14
        notes.append((ea + eb, f"{my_animal} and {their_animal}: no clash, just curiosity."))

    score = max(5, min(99, round(score)))
    verdict = ("Written in the stars" if score >= 85 else "Easy flow" if score >= 70
               else "Good together" if score >= 55 else "Sparks and lessons" if score >= 40
               else "Opposites attract")
    return score, verdict, notes[:4]


def transit_notes(now, natal, natal_rising=None, limit=3):
    """Today's planets touching your Sun, Moon and Rising."""
    targets = {"Sun": natal["Sun"], "Moon": natal["Moon"]}
    if natal_rising is not None:
        targets["Rising"] = natal_rising
    found = []
    for t in ("Moon", "Sun", "Venus", "Mars", "Mercury", "Jupiter", "Saturn"):
        for n, lon in targets.items():
            name, kind = _aspect(now[t], lon)
            if not name:
                continue
            d = abs(abs((now[t] - lon + 180) % 360 - 180) - {"conjunct": 0, "sextile": 60, "square": 90,
                                                              "trine": 120, "opposite": 180}[name])
            if kind == "easy":
                line = f"{t} {name} your {n}: {TRANSIT_MOOD[t]} flows easily."
                icon = "🌈"
            elif kind == "meet":
                line = f"{t} is on your {n}: {TRANSIT_MOOD[t]} is turned up."
                icon = "⚡"
            else:
                line = f"{t} {name} your {n}: a little friction around {TRANSIT_MOOD[t]}."
                icon = "🌀"
            found.append((d, icon, line))
    found.sort()
    return [(icon, line) for _, icon, line in found[:limit]]
