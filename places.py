"""
places.py
=========
Offline birthplace search and timezone lookup, using the GeoNames city list
that ships inside the `geonamescache` package (no web requests, no API key).

- PlaceIndex.search("pokhara")    -> best matching towns and cities
- PlaceIndex.nearest(lat, lon)    -> the closest listed town (used to pick a
                                     timezone after a click on the map)

City data: GeoNames (geonames.org), CC BY 4.0.
"""

import math
import unicodedata
from dataclasses import dataclass


def fold(text):
    """Lower-case and strip accents: 'São Paulo' -> 'sao paulo'."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.casefold().replace("-", " ").replace("'", "").split())


@dataclass(frozen=True)
class Place:
    gid: int
    name: str
    country: str
    region: str
    lat: float
    lon: float
    timezone: str
    population: int

    @property
    def label(self):
        parts = [self.name] + ([self.region] if self.region else []) + [self.country]
        return ", ".join(p for p in parts if p)


class PlaceIndex:
    def __init__(self, cities, countries, us_states=None):
        """cities / countries / us_states in geonamescache's dict format."""
        country_names = {code: c.get("name", code) for code, c in (countries or {}).items()}
        state_names = {code: s.get("name", code) for code, s in (us_states or {}).items()}
        self.places = []
        self._keys = []          # (folded name, set of folded alternate names, folded qualifiers)
        self._grid = {}
        for rec in cities.values():
            cc = rec.get("countrycode", "")
            region = state_names.get(rec.get("admin1code", "")) if cc == "US" else ""
            p = Place(int(rec.get("geonameid", 0)), rec["name"], country_names.get(cc, cc),
                      region or "", float(rec["latitude"]), float(rec["longitude"]),
                      rec.get("timezone") or "UTC", int(rec.get("population") or 0))
            alts = set()
            for alt in rec.get("alternatenames") or []:
                f = fold(alt)
                if f and f.isascii() and len(f) <= 40:
                    alts.add(f)
            qual = fold(p.country) + " " + fold(p.region) + " " + cc.casefold()
            self._keys.append((fold(p.name), alts, qual))
            self.places.append(p)
            self._grid.setdefault((math.floor(p.lat), math.floor(p.lon)), []).append(len(self.places) - 1)

    def __len__(self):
        return len(self.places)

    def search(self, query, limit=8):
        """Rank: exact name, exact alternate name, name starts with, alternate
        starts with, contains. Larger places first within each rank.
        'portland, oregon' or 'perth australia' narrow by region / country."""
        q = fold(query)
        if len(q) < 2:
            return []
        if "," in query:
            name_q, _, qual_q = (fold(x) for x in query.partition(","))
        else:
            name_q, qual_q = q, ""
        scored = []
        for i, (name, alts, qual) in enumerate(self._keys):
            if name == name_q:
                rank = 0
            elif name_q in alts:
                rank = 1
            elif name.startswith(name_q):
                rank = 2
            elif any(a.startswith(name_q) for a in alts):
                rank = 3
            elif len(name_q) >= 4 and name_q in name:
                rank = 4
            else:
                # "perth australia" without a comma: try the last word as a qualifier
                if not qual_q and " " in name_q:
                    head, tail = name_q.rsplit(" ", 1)
                    if (name == head or name.startswith(head)) and tail in qual:
                        scored.append((1 if name == head else 2, -self.places[i].population, i))
                continue
            if qual_q and qual_q not in qual:
                continue
            scored.append((rank, -self.places[i].population, i))
        scored.sort()
        seen, out = set(), []
        for _, _, i in scored:
            p = self.places[i]
            key = (p.name, p.country, p.region, round(p.lat, 1), round(p.lon, 1))
            if key in seen:
                continue
            seen.add(key)
            out.append(p)
            if len(out) == limit:
                break
        return out

    def nearest(self, lat, lon, max_rings=12):
        """Closest listed place to a point (great-circle distance), or None."""
        best, best_d = None, float("inf")
        cy, cx = math.floor(lat), math.floor(lon)
        for ring in range(max_rings + 1):
            for dy in range(-ring, ring + 1):
                for dx in range(-ring, ring + 1):
                    if max(abs(dy), abs(dx)) != ring:
                        continue
                    gx = (cx + dx + 180) % 360 - 180
                    for i in self._grid.get((cy + dy, gx), ()):
                        d = distance_km(lat, lon, self.places[i].lat, self.places[i].lon)
                        if d < best_d:
                            best, best_d = self.places[i], d
            # anything outside this ring is at least `ring` grid cells away; a degree of
            # longitude shrinks towards the poles, so use the narrowest one in reach
            narrowest = math.cos(math.radians(min(89.0, abs(lat) + ring + 1)))
            if best is not None and best_d < ring * 111.0 * narrowest:
                return best
        # far from everything (open ocean): check every place
        return min(self.places, key=lambda p: distance_km(lat, lon, p.lat, p.lon), default=None)


def distance_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371.0 * 2 * math.asin(min(1.0, math.sqrt(h)))


def load_index(min_population=5000):
    """Build the index from geonamescache, or return None if it isn't installed."""
    try:
        import geonamescache
    except ImportError:
        return None
    for size in (min_population, 15000):
        try:
            gc = geonamescache.GeonamesCache(min_city_population=size)
            cities = gc.get_cities()
            break
        except (OSError, ValueError, TypeError):
            continue
    else:
        return None
    try:
        states = gc.get_us_states()
    except Exception:
        states = {}
    return PlaceIndex(cities, gc.get_countries(), states)
