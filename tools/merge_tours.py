#!/usr/bin/env python3
"""Merge Concert Archives rows into data/tours.json.

Input:  research/raw/ca_rows.json  (parsed from the Concert Archives band pages; kept out of git)
        data/tours.json            (existing events; entries listing only S18 are rebuilt)
Output: data/tours.json

Status scheme
  VERIFIED          a contemporary eyewitness/press source says it was played
  CORROBORATED      two independent listings agree on date and city (e.g. the band's announced
                    schedule plus a fan-database entry); not eyewitness proof
  POSSIBLE          a single announcement or fan-database listing
  UNVERIFIED CLAIM  listed, but doubtful
"""
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOURS = ROOT / "data" / "tours.json"
BASE = ROOT / "research" / "raw" / "tours_base.json"
OVERRIDES = ROOT / "data" / "tour_overrides.json"
CA_ROWS = ROOT / "research" / "raw" / "ca_rows.json"

BAND = re.compile(r"let.?s get it", re.I)
CITY_FIX = {"saint paul": "st. paul", "st louis": "st. louis"}
BAND_SOURCES = {"S8", "S9", "S11", "S15", "S19", "S16"}
TOUR_NAMES = {
    "atticus metal tour": "Atticus Metal Tour (2009)",
    "no checkpoints in the jungle": "No Checkpoints in the Jungle Tour (2010)",
    "across the nation tour": "Across the Nation Tour (2010)",
    "hot over summer tour": "Hot Over Summer Tour (2010)",
}


def norm_city(c):
    c = c.strip().lower()
    return CITY_FIX.get(c, c)


def split_loc(loc):
    parts = [p.strip() for p in loc.split(",")]
    if len(parts) >= 3:
        return parts[0], ", ".join(parts[1:-1]) + (", " + parts[-1] if parts[-1] != "United States" else ", USA")
    return (parts[0] if parts else ""), ""


def clean_bill(text):
    names = [n.strip().strip('"').strip() for n in re.split(r"\s/\s", text)]
    out = []
    for n in names:
        if not n or BAND.fullmatch(n) or n.lower().startswith("transmission festival") or n.lower() in TOUR_NAMES:
            continue
        if re.search(r"\bat\b.*(cafe|café|creepy)|\.\.\.$", n):
            continue
        n = re.sub(r"\s*\(band\)$", "", n)
        if n not in out:
            out.append(n)
    return out


# Descriptive groups, assigned from the bill and date range. These are labels for browsing,
# not tour names, unless a source named the tour.
GROUP_RULES = [
    ("Jeffree Star tour (2009)", "2009-07-25", "2009-08-31", ["Jeffree Star"], "Jeffree Star"),
    ("Spring 2009 dates with Watchout! There's Ghosts", "2009-03-14", "2009-04-12", ["Watchout"], None),
    ("Atticus Metal Tour (2009)", "2009-10-01", "2009-11-30", ["Atticus", "Finch"], None),
    ("No Checkpoints in the Jungle Tour (2010)", "2010-02-01", "2010-03-10", ["Breathe Carolina"], None),
    ("Spring 2010 dates with VersaEmerge and I See Stars", "2010-04-20", "2010-05-20", ["Versa", "I See Stars"], None),
    ("July 2010 dates with Down With Webster", "2010-07-01", "2010-07-25", ["Down With Webster", "The Blue Pages"], None),
    ("August 2010 dates (with Stephen Jerzak, Call The Cops, Plug in Stereo)", "2010-08-01", "2010-08-20", ["Stephen Jerzak"], None),
    ("Fall 2010 (Blood On the Dance Floor bill)", "2010-09-30", "2010-11-10", ["Blood On the Dance Floor"], None),
    ("The Get Money Tour (with Brokencyde)", "2008-09-01", "2008-09-12", ["Brokencyde", "Brokencycle"], "Brokencyde"),
    ("November 2008 dates with Punchline and The Years Gone By", "2008-11-10", "2008-11-20", ["Punchline"], None),
]


def apply_groups(events):
    for ev in events:
        if ev.get("festival") and ev["festival"] != "Steel City Music Festival":
            continue
        text = " ".join(ev["supporting_artists_or_bill"]) + " " + (ev.get("tour") or "") + " " + (ev.get("notes") or "")
        for name, start, end, needles, headliner in GROUP_RULES:
            if start <= ev["date"] <= end and any(n.lower() in text.lower() for n in needles):
                ev["tour"] = name
                if headliner and not ev.get("headliner"):
                    ev["headliner"] = headliner
                break


def apply_overrides(events):
    """Band-owner confirmations and other corroboration, kept in data/tour_overrides.json."""
    for o in json.loads(OVERRIDES.read_text(encoding="utf-8")):
        m = o["match"]
        for ev in events:
            ok = True
            if "tour" in m: ok &= ev.get("tour") == m["tour"]
            if "date" in m: ok &= ev["date"] == m["date"]
            if "city" in m: ok &= norm_city(ev["city"]) == norm_city(m["city"])
            if "date_from" in m: ok &= ev["date"] >= m["date_from"]
            if "date_to" in m: ok &= ev["date"] <= m["date_to"]
            for ex in o.get("exclude", []):
                if ev["date"] == ex["date"] and norm_city(ev["city"]) == norm_city(ex["city"]):
                    ok = False
            if ok:
                ev["status"], ev["confidence"], ev["basis"] = o["status"], o["confidence"], o["basis"]
                for sid in o["add_sources"]:
                    if sid not in ev["source_ids"]:
                        ev["source_ids"].append(sid)


def main():
    events = json.loads(BASE.read_text(encoding="utf-8"))
    ca = json.loads(CA_ROWS.read_text(encoding="utf-8"))

    # strip S18 from existing events; drop events that only had S18
    kept = []
    for ev in events:
        ev["source_ids"] = [s for s in ev["source_ids"] if s != "S18"]
        if ev["source_ids"]:
            kept.append(ev)
    events = kept

    index = {}
    for ev in events:
        index.setdefault((ev["date"], norm_city(ev["city"])), []).append(ev)

    groups = {}
    for row in ca:
        iso = datetime.strptime(row["date"], "%b %d, %Y").strftime("%Y-%m-%d")
        if not row["loc"] or not row["mid"]:  # the 2015 row does not parse into venue/location
            continue
        city, state = split_loc(row["loc"])
        groups.setdefault((iso, norm_city(city)), []).append((row, city, state))

    for (iso, ckey), rows in sorted(groups.items()):
        venues, bills, tour, links = [], [], None, []
        for row, city, state in rows:
            venues.append(row["venue"].strip())
            title = row["mid"][0] if len(row["mid"]) == 2 else ""
            bill_txt = row["mid"][-1]
            for name in (title, bill_txt):
                key = re.sub(r'[\s"]+$|^["\s]+', "", name.lower())
                for k, v in TOUR_NAMES.items():
                    if k in key:
                        tour = v
            if "Steel City" in title or "Steel City" in bill_txt:
                tour = tour or None
            if "Unsilent Night 4" in title:
                tour = None
            if "Transmission Festival" in bill_txt or "Transmission Festival" in title:
                tour = "Transmission Festival, Scream It Like You Mean It (2010)"
            for n in clean_bill(bill_txt):
                if n not in bills:
                    bills.append(n)
            links.append("https://www.concertarchives.org" + row["link"])
        venue = max(set(venues), key=venues.count)
        alt = [v for v in dict.fromkeys(venues) if v != venue]
        note = f"{len(rows)} fan submission(s) on Concert Archives" + (f"; venue also spelled: {', '.join(alt)}" if alt else "")
        festival = "Steel City Music Festival" if any("Steel City" in " ".join(r["mid"]) for r, _, _ in rows) else None
        if any("Unsilent Night 4" in " ".join(r["mid"]) for r, _, _ in rows):
            festival = "Unsilent Night 4"
            bills = []  # three conflicting festival lineups; see notes
            note += "; the submissions carry different festival lineups, so no bill is shown"
        target = None
        for ev in index.get((iso, ckey), []):
            target = ev
            break
        if target:
            target["source_ids"].append("S18")
            target["source_urls"] = list(dict.fromkeys(target.get("source_urls", []) + links))
            target["notes"] = (target.get("notes") or "") + " | " + note
            if not target.get("tour") and tour:
                target["tour"] = tour
            if not target.get("supporting_artists_or_bill") and bills:
                target["supporting_artists_or_bill"] = bills
            if festival and not target.get("festival"):
                target["festival"] = festival
            if target["status"] == "POSSIBLE" and BAND_SOURCES & set(target["source_ids"]):
                target["status"] = "CORROBORATED"
                target["confidence"] = "MEDIUM"
                target["basis"] = "Date and city agree between an announced schedule/press source and a fan-submitted Concert Archives entry; no eyewitness account found"
            if target["status"] == "VERIFIED":
                target["basis"] += "; also listed on Concert Archives"
        else:
            city, state = rows[0][1], rows[0][2]
            events.append(dict(
                date=iso, time="", venue=venue, city=city, state_country=state, tour=tour,
                supporting_artists_or_bill=bills, headliner=None, festival=festival,
                status="POSSIBLE", basis="Listed on Concert Archives (fan-submitted, "
                + ("more than one submission" if len(rows) > 1 else "single submission") + "); no other source found",
                source_ids=["S18"], source_urls=links[:1], archive_url=None,
                confidence="LOW-MEDIUM", notes=note))
            index.setdefault((iso, ckey), []).append(events[-1])

    # the 2015 multi-band listing (kept as unverified)
    if not any(e["date"] == "2015-01-01" for e in events):
        events.append(dict(
            date="2015-01-01", time="", venue="(multi-band listing)", city="", state_country="", tour=None,
            supporting_artists_or_bill=[], headliner=None, festival=None, status="UNVERIFIED CLAIM",
            basis="Concert Archives lists a multi-band bill including Let's Get It on 2015-01-01; the band is recorded as ended in 2012",
            source_ids=["S18"], source_urls=[], archive_url=None, confidence="UNVERIFIED",
            notes="Likely a data-entry artifact. Do not present as a show."))

    # date conflicts: same date, different city, from different origins
    by_date = {}
    for ev in events:
        by_date.setdefault(ev["date"], []).append(ev)
    for d, evs in by_date.items():
        cities = {norm_city(e["city"]) for e in evs if e["city"]}
        if len(cities) > 1 and "/" not in d:
            for e in evs:
                e["notes"] = (e.get("notes") or "") + f" | CONFLICT: other listings for {d} name a different city ({', '.join(sorted(c.title() for c in cities))})"

    apply_groups(events)
    apply_overrides(events)
    events.sort(key=lambda e: (e["date"], e["city"]))
    for ev in events:
        ev.setdefault("source_urls", [])
    TOURS.write_text(json.dumps(events, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    from collections import Counter
    print(len(events), "events;", dict(Counter(e["status"] for e in events)))


if __name__ == "__main__":
    main()
