#!/usr/bin/env python3
"""Render data/*.json into the GEN blocks of index.html.

Usage: python3 tools/build.py
Only text between <!--GEN:name--> and <!--/GEN:name--> markers is replaced.
Edit the JSON in data/, not the generated HTML.
"""
import json
import re
import sys
from collections import OrderedDict
from html import escape as e
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
INDEX = ROOT / "index.html"


def load(name):
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))


def cites(ids):
    return '<span class="src">' + " ".join(
        f'[<a href="#{i.lower()}">{e(i)}</a>]' for i in ids
    ) + "</span>"


def conf_tag(conf):
    return f'<span class="conf">{e(conf)}</span>'


def gen_timeline():
    rows = "".join(
        f'<li><span class="tl-date">{e(t["date"])}</span> {e(t["event"])} {cites(t["source_ids"])}</li>'
        for t in load("timeline")
    )
    return f'<h3>Timeline</h3>\n<ol class="timeline">{rows}</ol>'


def gen_discography():
    out = []
    for r in load("releases"):
        kind = e(r["release_type"])
        meta = [e(r["release_date"] or "date unknown")]
        if r.get("label"):
            meta.append(e(r["label"]))
        head = ' <span class="sep">·</span> '.join(meta)
        tracks = ""
        if r["tracks"]:
            tracks = '<ol class="tracks">' + "".join(f"<li>{e(t)}</li>" for t in r["tracks"]) + "</ol>"
        listen = ""
        if r["links"]:
            listen = '<div class="listen">' + "".join(
                f'<a href="{e(l["url"])}">Listen — {e(l["label"])}</a>' for l in r["links"]
            ) + "</div>"
        credits = ""
        if r["credits"]:
            credits = "<p class=\"srcnote\">Credits: " + e("; ".join(r["credits"])) + "</p>"
        out.append(
            f'<div class="release">\n<p class="rt">{e(r["title"])} <span class="src">— {kind}</span></p>\n'
            f'<p class="rmeta">{head} {cites(r["source_ids"])} {conf_tag(r["confidence"])}</p>\n'
            f'{tracks}\n{listen}\n{credits}\n<p class="srcnote">{e(r["notes"] or "")}</p>\n</div>'
        )
    return "\n".join(out)


def gen_members():
    items = "".join(
        f'<li>{e(m["name"])} <span class="role">{e(m["role"])} {cites(m["sources"])} {conf_tag(m["confidence"])}'
        + (f'<br><span class="srcnote">{e(m["notes"])}</span>' if m["notes"] else "")
        + "</span></li>"
        for m in load("members")
    )
    conflict = next(c for c in load("conflicts") if c["id"] == "C1")
    return (
        f'<ul class="plain">{items}</ul>\n'
        f'<p class="srcnote"><strong>Lineup source:</strong> a 2010 press release repost (S15) and a community wiki (S17); '
        f'Tyler Smyth and Taylor Foiles are confirmed by a band member (S22). Membership dates and touring/former members are not yet documented.</p>\n'
        f'<div class="conflict"><span class="label">NOTE — CORRECTED BY A BAND MEMBER</span>{e(conflict["summary"])} {cites(conflict["source_ids"])}</div>\n'
        '<div class="needed"><span class="label">ENTRY NEEDED</span>'
        'Years each member was in the band, and any touring or former members.</div>'
    )

def gen_team():
    items = []
    for t in load("team"):
        org = f' <span class="src">· {e(t["org"])}</span>' if t.get("org") else ""
        era = f'<br><span class="srcnote">{e(t["era"])}</span>' if t.get("era") else ""
        status = f'<br><span class="srcnote"><strong>{e(t["status"])}</strong></span>' if t.get("status") else ""
        notes = f'<br><span class="srcnote">{e(t["notes"])}</span>' if t.get("notes") else ""
        items.append(
            f'<li>{e(t["name"])} <span class="role">{e(t["role"])}{org} {cites(t["source_ids"])} {conf_tag(t["confidence"])}'
            f"{era}{status}{notes}</span></li>"
        )
    return (
        '<p>The people around the band. Roles come from the band owner (S22) and are checked against public sources where any exist; '
        'the label beside each name says how well the sources support it. Contact details are deliberately not published.</p>\n'
        f'<ul class="plain">{"".join(items)}</ul>\n'
        '<div class="needed"><span class="label">ENTRY NEEDED</span>'
        'Years each person worked with the band, and the companies for David Marsh, Jamie Irvine and Billy Adams.</div>'
    )


def show_row(ev):
    headline = ev.get("headliner") or ""
    skip = {"tba", "more", "+more", "more tba", "many more!!!", "and many more!!!"}
    bill = ", ".join(x for x in ev["supporting_artists_or_bill"] if x.lower() not in skip and x != headline)
    bill_txt = "; ".join(x for x in [("headliner: " + headline) if headline else "", ("with " + bill) if bill else ""] if x)
    loc = ", ".join(x for x in [ev["city"], ev["state_country"]] if x)
    fest = f' <span class="src">({e(ev["festival"])})</span>' if ev.get("festival") else ""
    status_cls = ev["status"].split()[0].lower()
    link = "".join(f' <a class="ext" href="{e(u)}" title="Concert Archives entry">↗</a>' for u in ev.get("source_urls", [])[:1])
    note = "CONFLICT" in (ev.get("notes") or "")
    flag = ' <span class="tag st-unverified" title="Sources disagree; see Archive notes">check</span>' if note else ""
    return (
        f'<tr><td class="d">{e(ev["date"])}</td>'
        f'<td>{e(ev["venue"])}{fest}</td><td>{e(loc)}</td><td>{e(bill_txt)}</td>'
        f'<td><span class="tag st-{status_cls}" title="{e(ev["basis"])}">{e(ev["status"])}</span>{flag} {cites(ev["source_ids"])}{link}</td></tr>'
    )

def gen_tours():
    events = load("tours")
    order = ["VERIFIED", "CORROBORATED", "POSSIBLE", "UNVERIFIED CLAIM"]
    counts = {k: sum(1 for x in events if x["status"] == k) for k in order}
    summary = ", ".join(f"{n} {k.lower()}" for k, n in counts.items() if n)
    years = sorted({x["date"][:4] for x in events})
    by_year = OrderedDict((y, [x for x in events if x["date"][:4] == y]) for y in years)
    tours = OrderedDict()
    for x in events:
        if x.get("tour"):
            t = tours.setdefault(x["tour"], [0, x["date"], x["date"]])
            t[0] += 1
            t[1] = min(t[1], x["date"])
            t[2] = max(t[2], x["date"][:10])
    tour_rows = "".join(
        f'<li><strong>{e(name)}</strong> <span class="src">{n} {"date" if n == 1 else "dates"}, {e(a)} to {e(b)}</span></li>'
        for name, (n, a, b) in sorted(tours.items(), key=lambda kv: kv[1][1])
    )
    year_blocks = []
    for year, evs in by_year.items():
        rows = "".join(show_row(x) for x in evs)
        year_blocks.append(
            f'<details class="year"><summary><span class="yr">{e(year)}</span> '
            f'<span class="src">{len(evs)} {"listing" if len(evs) == 1 else "listings"}</span></summary>'
            f'<div class="tablewrap"><table class="shows"><thead><tr><th>Date</th><th>Venue</th><th>City</th><th>Bill</th><th>Status</th></tr></thead>'
            f"<tbody>{rows}</tbody></table></div></details>"
        )
    return "\n".join([
        '<p>Every show found so far, 2008 to 2011. The band\'s own archived schedule (S8, S9, S11), press (S15, S16, S19) and the fan-built '
        'Concert Archives list (S18) were merged; where they agree on date and city the entries are combined. The Fearless bio (S1) mentions a '
        'summer tour with Jeffree Star, Artist Vs Poet and Watch Out! There\'s Ghosts, which the schedules place in <strong>2009</strong>.</p>',
        f'<p class="srcnote">{len(events)} entries: {e(summary)}. '
        '<strong>VERIFIED</strong> = a contemporary source says the show happened. '
        '<strong>CORROBORATED</strong> = two independent listings agree on date and city, with no eyewitness account. '
        '<strong>POSSIBLE</strong> = a single announcement or fan listing. '
        '<strong>UNVERIFIED CLAIM</strong> = listed, but doubtful. Hover a status for its basis; “check” marks dates where sources disagree. '
        'Band members can promote a status by confirming a date (see Archive notes).</p>',
        f'<details class="archive" open><summary><span class="yr">Tour archive</span> <span class="src">all {len(events)} listings, open a year to see the shows</span></summary>',
        f'<h3>Tours and runs</h3><ul class="plain notes">{tour_rows}</ul>',
        "\n".join(year_blocks),
        "</details>",
        '<div class="needed"><span class="label">ENTRY NEEDED</span>Corrections and confirmations from band members: which dates were played, cancelled or wrong; '
        'plus 2011 and 2012 shows and anything missing.</div>',
    ])

def gen_press():
    items = []
    for p in load("press"):
        links = f'<a href="{e(p["url"])}">Read source</a>'
        if p.get("archive_url"):
            links += f' <a href="{e(p["archive_url"])}">Archived copy</a>'
        quote = f'<blockquote>“{e(p["quote"])}”</blockquote>' if p.get("quote") else ""
        items.append(
            f'<article class="pressitem"><p class="pyear">{e(p["year"])}</p>'
            f'<p class="ppub">{e(p["publication"])}</p>'
            f'<p class="ptitle">“{e(p["title"])}”</p>'
            f'<p class="pmeta">{e(p["article_type"])}'
            + (f' · {e(p["author"])}' if p.get("author") else "")
            + (f' · {e(p["date"])}' if p.get("date") else "")
            + f' · <span class="src">{e(p["link_kind"])}</span> {cites(p["source_ids"])}</p>'
            f"{quote}<p class=\"srcnote\">{e(p['notes'] or '')}</p><p class=\"plinks\">{links}</p></article>"
        )
    return "\n".join(items) + (
        '\n<div class="needed"><span class="label">ENTRY NEEDED</span>'
        'More press: clippings, magazine scans, interviews, radio and podcast appearances.</div>'
    )


def gen_sources():
    lis = []
    for s in load("sources"):
        url = s["url"]
        label = url if len(url) <= 70 else url[:67] + "…"
        parts = [f'{e(s["title"])} — {e(s["publisher"])}']
        if s.get("date"):
            parts.append(e(s["date"]))
        line = ", ".join(parts) + f' — <a href="{e(url)}">{e(label)}</a>'
        if s.get("archive_url"):
            line += f' (<a href="{e(s["archive_url"])}">archived copy</a>)'
        line += f' <span class="tag st-type">{e(s["source_type"])}</span>'
        line += " — accessed " + s["access_date"] if s.get("access_date") else " — not read by the researcher"
        lis.append(f'<li id="{s["id"].lower()}">{line}<br><span class="srcnote">{e(s["reliability"])}</span></li>')
    return '<ul class="cite">' + "".join(lis) + "</ul>"


def gen_notes():
    conflicts = "".join(
        f'<li><strong>{e(c["topic"])}.</strong> {e(c["summary"])} {cites(c["source_ids"])}</li>' for c in load("conflicts")
    )
    unverified = "".join(
        f'<li><strong>{e(u["claim"])}</strong> — {e(u["basis"])} {cites(u["source_ids"])}</li>' for u in load("unverified")
    )
    return (
        "<h3>Conflicting information</h3>"
        f'<ul class="plain notes">{conflicts}</ul>'
        "<h3>Unverified — not stated as fact on this page</h3>"
        f'<ul class="plain notes">{unverified}</ul>'
    )

BLOCKS = {
    "timeline": gen_timeline,
    "discography": gen_discography,
    "members": gen_members,
    "team": gen_team,
    "tours": gen_tours,
    "press": gen_press,
    "sources": gen_sources,
    "notes": gen_notes,
}


def main():
    html = INDEX.read_text(encoding="utf-8")
    for name, fn in BLOCKS.items():
        pat = re.compile(rf"(<!--GEN:{name}-->)(.*?)(<!--/GEN:{name}-->)", re.S)
        if not pat.search(html):
            sys.exit(f"missing GEN markers for {name}")
        html = pat.sub(lambda m: f"{m.group(1)}\n{fn()}\n{m.group(3)}", html)
    INDEX.write_text(html, encoding="utf-8")
    print("built", ", ".join(BLOCKS))


if __name__ == "__main__":
    main()
