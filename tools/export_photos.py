#!/usr/bin/env python3
"""Export the curated photos and flyers as web-size JPEGs with all metadata stripped.

Reads data/photo_picks.json (selection, captions, credits) and the band-archive copy under
"needs from you/from server" (local only). Writes img/photos, img/ephemera and data/photos.json,
data/ephemera.json (provenance records).
"""
import json, os, re, sys
from PIL import Image, ImageOps
from PIL.ExifTags import TAGS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "needs from you", "from server")
picks = json.load(open(os.path.join(ROOT, "data", "photo_picks.json"), encoding="utf-8"))

index = {}
for r, ds, fs in os.walk(SRC):
    for f in fs:
        index.setdefault(f.lower(), []).append(os.path.join(r, f))


def resolve(frag):
    if "/" in frag:
        for lst in index.values():
            for p in lst:
                if p.replace("\\", "/").endswith(frag):
                    return p
        return None
    hits = index.get(frag.lower(), [])
    return hits[0] if hits else None


def exif_info(path):
    try:
        im = Image.open(path)
        ex = im.getexif()
        d = {TAGS.get(k, k): v for k, v in ex.items()}
        sub = {TAGS.get(k, k): v for k, v in ex.get_ifd(0x8769).items()}
        dt = str(sub.get("DateTimeOriginal") or d.get("DateTime") or "")
        cam = (str(d.get("Make", "")) + " " + str(d.get("Model", ""))).strip()
        art = str(d.get("Artist", ""))
        return dt, cam, art
    except Exception:
        return "", "", ""


def trim_white(im, pad=12, thresh=245):
    g = ImageOps.invert(im.convert("L")).point(lambda v: 255 if v > 255 - thresh + 200 else 0)
    box = g.getbbox()
    if not box:
        return im
    l, t, r, b = box
    return im.crop((max(l - pad, 0), max(t - pad, 0), min(r + pad, im.width), min(b + pad, im.height)))


def export(path, out_base, long_edge, thumb=480, crop_top_half=False):
    im = Image.open(path)
    im = ImageOps.exif_transpose(im).convert("RGB")
    if crop_top_half:
        im = trim_white(im.crop((0, 0, im.width, im.height // 2)))
    big = im.copy(); big.thumbnail((long_edge, long_edge), Image.LANCZOS)
    small = im.copy(); small.thumbnail((thumb, thumb), Image.LANCZOS)
    big.save(out_base + ".jpg", "JPEG", quality=80, optimize=True, progressive=True)  # no exif passed => stripped
    small.save(out_base + "_t.jpg", "JPEG", quality=76, optimize=True, progressive=True)
    return big.size


def run(kind, outdir, outjson):
    os.makedirs(os.path.join(ROOT, outdir), exist_ok=True)
    records, missing = [], []
    for p in picks[kind]:
        path = resolve(p["file"])
        if not path:
            missing.append(p["file"]); continue
        dt, cam, art = exif_info(path)
        slug = p["slug"]
        w, h = export(path, os.path.join(ROOT, outdir, slug), p.get("long_edge", 1600), crop_top_half=p.get("crop_top_half", False))
        date = p.get("date") or (dt[:10].replace(":", "-") if dt else "")
        rec = dict(p)
        rec.update(slug=slug, image=f"{outdir}/{slug}.jpg", thumb=f"{outdir}/{slug}_t.jpg", width=w, height=h,
                   source_file=os.path.relpath(path, SRC).replace("\\", "/"),
                   exif_date=dt[:10].replace(":", "-") if dt else None, camera=cam or None, exif_artist=art or None,
                   date=date)
        records.append(rec)
    json.dump(records, open(os.path.join(ROOT, outjson), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(kind, len(records), "exported; missing:", missing)


if __name__ == "__main__":
    run("photos", "img/photos", "data/photos.json")
    run("ephemera", "img/ephemera", "data/ephemera.json")
    run("members", "img/members", "data/member_portraits.json")
