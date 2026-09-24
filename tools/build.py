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
        f'<p class="srcnote"><strong>Lineup source:</strong> a 2010 press release repost (S15), agreeing with a community wiki (S17). '
        f'Membership dates and touring/former members are not yet documented.</p>\n'
        f'<div class="conflict"><span class="label">CONFLICT</span>{e(conflict["summary"])} {cites(conflict["source_ids"])}</div>\n'
        '<div class="needed"><span class="label">ENTRY NEEDED</span>'
        'Years each member was in the band, any touring or former members, and confirmation of the lineup above.</div>'
    )


def show_row(ev):
    bill = ", ".join(ev["supporting_artists_or_bill"])
    headline = f'{ev["headliner"]}' if ev.get("headliner") else ""
    bill_txt = "; ".join(x for x in [("headliner: " + headline) if headline else "", ("with " + bill) if bill else ""] if x)
    loc = ", ".join(x for x in [ev["city"], ev["state_country"]] if x)
    fest = f' <span class="src">({e(ev["festival"])})</span>' if ev.get("festival") else ""
    status_cls = ev["status"].split()[0].lower()
    return (
        f'<tr><td class="d">{e(ev["date"])}</td>'
        f'<td>{e(ev["venue"])}{fest}</td><td>{e(loc)}</td><td>{e(bill_txt)}</td>'
        f'<td><span class="tag st-{status_cls}" title="{e(ev["basis"])}">{e(ev["status"])}</span> {cites(ev["source_ids"])}</td></tr>'
    )


def gen_tours():
    events = load("tours")
    counts = OrderedDict()
    for ev in events:
        counts[ev["status"]] = counts.get(ev["status"], 0) + 1
    summary = ", ".join(f"{n} {s.lower()}" for s, n in counts.items())
    by_year = OrderedDict()
    for ev in events:
        by_year.setdefault(ev["date"][:4], []).append(ev)
    parts = [
        '<p>The Fearless bio (S1) mentions a nationwide summer tour with Jeffree Star, Artist Vs Poet and Watch Out! There\'s Ghosts; '
        'the archived MySpace schedule (S11) places it in <strong>2009</strong>, from late July to late August.</p>',
        f'<p class="srcnote">{len(events)} entries: {e(summary)}. '
        '<strong>VERIFIED</strong> = a contemporary source says the show happened. '
        '<strong>POSSIBLE</strong> = the date was announced or listed (archived band page, press release, fan database) but no source yet confirms it was played. '
        '<strong>UNVERIFIED CLAIM</strong> = listed, but doubtful. Hover a status for the basis. Where sources disagree, the disagreement is kept.</p>',
    ]
    for year, evs in by_year.items():
        rows = "".join(show_row(x) for x in evs)
        parts.append(
            f'<details class="year"><summary><span class="yr">{e(year)}</span> <span class="src">{len(evs)} {"entry" if len(evs)==1 else "entries"}</span></summary>'
            f'<div class="tablewrap"><table class="shows"><thead><tr><th>Date</th><th>Venue</th><th>City</th><th>Bill</th><th>Status</th></tr></thead>'
            f"<tbody>{rows}</tbody></table></div></details>"
        )
    parts.append(
        '<div class="needed"><span class="label">ENTRY NEEDED</span>Corrections and confirmations from band members: which dates were actually played, '
        'plus 2011 and 2012 shows. Concert Archives lists 192 entries; only the first page was readable.</div>'
    )
    return "\n".join(parts)


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
