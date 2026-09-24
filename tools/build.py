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
        f'[<a href="#{i.lower()}">{e(i)}</a>]' for i in sorted(dict.fromkeys(ids), key=lambda x: int(x[1:]))
    ) + "</span>"


def conf_tag(conf):
    return f'<span class="conf">{e(conf)}</span>'


def gen_timeline():
    rows = "".join(
        f'<li><span class="tl-date">{e(t["date"])}</span> {e(t["event"])} {cites(t["source_ids"])}</li>'
        for t in load("timeline")
    )
    return f'<h3>Timeline</h3>\n<ol class="timeline">{rows}</ol>'


def release_html(r):
    kind = e(r["release_type"])
    meta = [e(r["release_date"] or "date unknown")]
    if r.get("label"):
        meta.append(e(r["label"]))
    if r.get("catalog_number"):
        meta.append("cat. " + e(r["catalog_number"]))
    head = ' <span class="sep">·</span> '.join(meta)
    tracks = ""
    if r["tracks"]:
        tracks = '<ol class="tracks">' + "".join(f"<li>{e(t)}</li>" for t in r["tracks"]) + "</ol>"
    lgi = f'<p class="srcnote">Let\'s Get It on this release: {e(r["lgi_track"])}</p>' if r.get("lgi_track") else ""
    listen = ""
    if r["links"]:
        listen = '<div class="listen">' + "".join(
            f'<a href="{e(l["url"])}">Listen — {e(l["label"])}</a>' for l in r["links"]
        ) + "</div>"
    fmt = f'<p class="srcnote">Formats: {e("; ".join(r["formats"]))}</p>' if r.get("formats") else ""
    credits = f'<p class="srcnote"><strong>Credits:</strong> {e("; ".join(r["credits"]))}</p>' if r["credits"] else ""
    return (
        f'<div class="release">\n<p class="rt">{e(r["title"])} <span class="src">— {kind}</span></p>\n'
        f'<p class="rmeta">{head} {cites(r["source_ids"])} {conf_tag(r["confidence"])}</p>\n'
        f'{tracks}\n{lgi}\n{listen}\n{fmt}\n{credits}\n<p class="srcnote">{e(r["notes"] or "")}</p>\n</div>'
    )


def gen_discography():
    rels = load("releases")
    main = [r for r in rels if not r["release_type"].startswith("Compilation")]
    comps = [r for r in rels if r["release_type"].startswith("Compilation")]
    out = [release_html(r) for r in main]
    if comps:
        out.append("<h3>Compilation appearances</h3>")
        out.append('<p class="srcnote">Various-artists releases that include a Let\'s Get It track (Discogs, S6).</p>')
        out += [release_html(r) for r in comps]
    out.append(gen_songs())
    return "\n".join(out)

def gen_members():
    portraits = {r["caption"]: r for r in load("member_portraits")}

    def pic(m):
        r = portraits.get(m["name"])
        if not r:
            return ""
        return f'<img class="mp" loading="lazy" src="{e(r["thumb"])}" width="{r["width"]}" height="{r["height"]}" alt="Portrait of {e(m["name"])}">'

    items = "".join(
        f'<li>{pic(m)}<div class="mtxt">{e(m["name"])} <span class="role">{e(m["role"])} {cites(m["sources"])} {conf_tag(m["confidence"])}'
        f'<br><span class="srcnote">{e(m["years"])}</span>'
        + (f'<br><span class="srcnote">{e(m["notes"])}</span>' if m["notes"] else "")
        + "</span></div></li>"
        for m in load("members")
    )
    conflict = next(c for c in load("conflicts") if c["id"] == "C1")
    now_items = []
    for n in load("members_now"):
        if n["text"]:
            now_items.append(f'<li><strong>{e(n["name"])}.</strong> {e(n["text"])} {cites(n["source_ids"])} {conf_tag(n["confidence"])}</li>')
    pending = ", ".join(n["name"] for n in load("members_now") if not n["text"])
    return (
        f'<ul class="plain memberlist">{items}</ul>\n'
        f'<p class="srcnote"><strong>Lineup:</strong> confirmed by a band member (S22): five members from 2008 to 2012, with no former or touring members. '
        f'Roles also match Discogs (S6), a 2010 press release repost (S15) and a community wiki (S17).</p>\n'
        f'<div class="conflict"><span class="label">NOTE — CORRECTED BY A BAND MEMBER</span>{e(conflict["summary"])} {cites(conflict["source_ids"])}</div>\n'
        f'<h3>Where are they now?</h3>\n<ul class="plain notes">{"".join(now_items)}</ul>\n'
        f'<div class="needed"><span class="label">ENTRY NEEDED</span>Nothing verifiable found yet for {e(pending)}. '
        'Each member can add what they are happy to have public.</div>'
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
        'The band owner considers the fan listings valid (S22); statuses still follow the evidence found so far, and confirmations from the band, videos or flyers upgrade them.</p>',
        f'<details class="archive" open><summary><span class="yr">Tour archive</span> <span class="src">all {len(events)} listings, open a year to see the shows</span></summary>',
        f'<h3>Tours and runs</h3><ul class="plain notes">{tour_rows}</ul>',
        "\n".join(year_blocks),
        "</details>",
        '<div class="needed"><span class="label">ENTRY NEEDED</span>Corrections and confirmations from band members: which dates were played, cancelled or wrong; '
        'plus 2011 and 2012 shows and anything missing.</div>',
    ])

def gen_media():
    m = load("media")
    listen = (
        '<div class="listen-row">'
        '<a href="https://open.spotify.com/artist/6PvtObzrQDw6LT6XoUALpf">Spotify — Artist</a>'
        '<a href="https://music.apple.com/us/artist/lets-get-it/289801706">Apple Music — Artist</a></div>'
    )

    def vrow(v, src):
        pub = f' <span class="src">{e(v["published"])}</span>' if v.get("published") else ""
        kind = f' <span class="src">· {e(v["kind"])}</span>' if v.get("kind") else ""
        who = f' <span class="src">· {e(v["channel"])}</span>' if v.get("channel") else ""
        views = f' <span class="src">· {v["views"]:,} views</span>' if v.get("views") else ""
        return f'<li><a href="{e(v["url"])}">{e(v["title"])}</a>{pub}{kind}{who}{views} {src}</li>'

    off = "".join(vrow(v, cites(v["source_ids"])) for v in m["official_videos"])
    bc = m["band_channel"]
    groups = OrderedDict()
    for v in bc["videos"]:
        groups.setdefault(v["kind"], []).append(v)
    order = ["Song video", "Live / performance", "Tour / event", "Behind the scenes"]
    det = "".join(
        f'<details class="year"><summary><span class="yr">{e(k)}</span> <span class="src">{len(groups[k])}</span></summary>'
        f'<ul class="plain notes">{"".join(vrow(v, "") for v in groups[k])}</ul></details>'
        for k in order if k in groups
    )
    links = "".join(
        f'<li><a href="{e(l["url"])}">{e(l["label"])}</a> <span class="src">· {e(l["kind"])}</span>'
        + (f'<br><span class="srcnote">{e(l["note"])}</span>' if l.get("note") else "")
        + f' {cites(l["source_ids"])}</li>'
        for l in m["links"]
    )
    photos = "".join(
        f'<li>{e(p["title"])} — {e(p["credit"])}, {e(p["date"])}. <a href="{e(p["url"])}">View at source</a> '
        f'<span class="src">· {e(p["license"])} · {e(p["usage_status"])}</span> {cites(p["source_ids"])}</li>'
        for p in m["photos"]
    )
    return (
        listen + "\n<h3>Videos</h3>\n"
        f'<ul class="plain notes">{off}</ul>\n'
        f'<details class="archive"><summary><span class="yr">Band YouTube channel</span> '
        f'<span class="src">{len(bc["videos"])} videos, 2009 to 2013 {cites(bc["source_ids"])}</span></summary>{det}'
        f'<p class="srcnote"><a href="{e(bc["url"])}">Open the channel</a>. Dates are shown only where the channel feed gave them.</p></details>\n'
        '<div class="needed"><span class="label">ENTRY NEEDED</span>Vimeo and other video links; a search of Vimeo found none so far.</div>\n'
        f'<h3>Links and historical web presence</h3>\n<ul class="plain notes">{links}</ul>\n'
        f'<h3>Photographs elsewhere on the web</h3>\n<ul class="plain notes">{photos}</ul>'
    )


PHOTO_STATUS = "Published with the band owner's authorization (S22); removal on request"


def figure(r, credit_key="photographer", extra=""):
    date = f' · {e(r["date"])}' if r.get("date") else ""
    return (
        f'<figure class="ph"><a href="{e(r["image"])}"><img loading="lazy" src="{e(r["thumb"])}" '
        f'width="{r["width"]}" height="{r["height"]}" alt="{e(r["caption"])}"></a>'
        f'<figcaption>{e(r["caption"])}<br><span class="src">{e(r[credit_key])}{date}{extra}</span></figcaption></figure>'
    )


def gen_photos():
    recs = load("photos")
    order = ["Portraits and press", "Live", "On tour", "Behind the scenes"]
    blocks = []
    for cat in order:
        items = [r for r in recs if r["category"] == cat]
        if not items:
            continue
        items.sort(key=lambda r: (r.get("date") or "", r["slug"]))
        blocks.append(f'<h3>{e(cat)} <span class="src">{len(items)}</span></h3><div class="photogrid">' + "".join(figure(r) for r in items) + "</div>")
    return (
        '<p>Photographs from the band\'s own archive, chosen from about 1,200. Dates are the camera dates embedded in the files, which can be off; '
        f'credits come from the camera data and file names {cites(["S40"])}. Location metadata was removed from every image. {e(PHOTO_STATUS)}. '
        'Tap a photo for the larger version.</p>' + "".join(blocks) +
        '<div class="needed"><span class="label">ENTRY NEEDED</span>Who is who in each group photo, venues for the live shots, and any photographer credits to correct.</div>'
    )


def gen_ephemera():
    recs = load("ephemera")
    cards = []
    for r in recs:
        cards.append(
            f'<figure class="ph flyer"><a href="{e(r["image"])}"><img loading="lazy" src="{e(r["thumb"])}" width="{r["width"]}" height="{r["height"]}" alt="{e(r["caption"])}"></a>'
            f'<figcaption><strong>{e(r["caption"])}</strong><br><span class="src">{e(r["kind"])} · {e(r["date"])} · {e(r["event"])}</span><br>'
            f'<span class="srcnote">{e(r["notes"])} Creator: {e(r["creator"])}. {cites(["S38"])}</span></figcaption></figure>'
        )
    return '<div class="flyergrid">' + "".join(cards) + '</div>' + (
        '<div class="needed"><span class="label">ENTRY NEEDED</span>More flyers, tickets, setlists and merchandise catalogs. '
        'More design files exist in the band archive (PSD files were skipped).</div>'
    )


def gen_songs():
    d = load("songs_archive")
    items = "".join(f'<li><strong>{e(g["title"])}.</strong> {e(g["text"])} {cites(g["source_ids"])}</li>' for g in d["groups"])
    return f'<h3>Demos, mixes and outtakes (from the band\'s files)</h3><p class="srcnote">{e(d["note"])}</p><ul class="plain notes">{items}</ul>'


def gen_numbers():
    d = load("numbers")
    rows = "".join(
        f'<tr><td>{e(n["metric"])}</td><td class="d">{e(n["value"])}</td><td class="d">{e(n["as_of"])}</td>'
        f'<td>{e(n["notes"])} {cites(n["source_ids"])} {conf_tag(n["confidence"])}</td></tr>'
        for n in d["items"]
    )
    return (
        '<h3>By the numbers</h3><div class="tablewrap"><table class="shows"><thead><tr><th>Measure</th><th>Figure</th><th>As of</th><th>Notes</th></tr></thead>'
        f"<tbody>{rows}</tbody></table></div>"
        f'<div class="needed"><span class="label">ENTRY NEEDED</span>{e(d["missing"])}</div>'
    )


def gen_achievements():
    items = "".join(
        f'<li><strong>{e(a["title"])}</strong> <span class="src">{e(a["date"])}</span><br><span class="srcnote">{e(a["detail"])}</span> {cites(a["source_ids"])} {conf_tag(a["confidence"])}</li>'
        for a in load("achievements")
    )
    return f'<h3>Placements and milestones</h3><ul class="plain notes">{items}</ul>'


def gen_sponsors():
    d = load("sponsors")
    rows = "".join(
        f'<li><strong>{e(x["name"])}</strong> <span class="src">· {e(x["kind"])} · {e(x["period"])}</span><br><span class="srcnote">{e(x["detail"])}</span> {cites(x["source_ids"])} {conf_tag(x["confidence"])}</li>'
        for x in d
    )
    return (
        '<p>Companies that supported the band with gear, clothing or deals, as recorded in the band\'s own emails and paperwork. Prices and account details are not published.</p>'
        f'<ul class="plain notes">{rows}</ul>'
        '<div class="needed"><span class="label">ENTRY NEEDED</span>Any other sponsors, and the Fender endorsement details (models, who arranged it, dates).</div>'
    )


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
    "media": gen_media,
    "numbers": gen_numbers,
    "sponsors": gen_sponsors,
    "achievements": gen_achievements,
    "photos": gen_photos,
    "ephemera": gen_ephemera,
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
