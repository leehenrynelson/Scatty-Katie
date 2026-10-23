"""Fetch every Wetherspoon pub and Poundland store in England into data/*.json.
Runs on GitHub Actions (weekly) so the app's lists stay current."""
import json, time, urllib.request, urllib.parse, html, math, sys

UA = {"User-Agent": "ScattyKatie/1.0 (github.com/Leehenrynelson/scatty-katie)"}

def get(url, data=None, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=UA)
            with urllib.request.urlopen(req, timeout=240) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code == 400:
                return 400, b"[]"
            print("HTTP", e.code, url, file=sys.stderr)
        except Exception as e:
            print("ERR", e, url, file=sys.stderr)
        time.sleep(10 * (i + 1))
    raise SystemExit("failed: " + url)

# ---------- Wetherspoon ----------
STATUS = {48: "", 75: "Opening soon", 227: "Temporarily closed", 233: None}
spoons, page = [], 1
while True:
    q = urllib.parse.urlencode({"per_page": 100, "page": page, "_fields": "title,acf,pub-status,link"})
    code, body = get("https://www.jdwetherspoon.com/wp-json/wp/v2/pubs?" + q)
    rows = json.loads(body)
    if code == 400 or not rows:
        break
    for p in rows:
        a = p.get("acf") or {}
        if (a.get("country") or "").strip().lower() != "england":
            continue
        st = (p.get("pub-status") or [48])[0]
        flag = STATUS.get(st, "")
        if flag is None:
            continue
        try:
            lat, lng = float(a["latitude"]), float(a["longitude"])
        except Exception:
            continue
        name = html.unescape(p["title"]["rendered"]).strip()
        addr = html.unescape(a.get("full_address") or "").strip()
        town = html.unescape(a.get("towncity") or "").strip()
        spoons.append([name, addr, round(lat, 6), round(lng, 6), flag, town])
    page += 1
    time.sleep(1)
print("spoons", len(spoons))

# ---------- Poundland (OpenStreetMap) ----------
OQ = """[out:json][timeout:220];
area["ISO3166-2"="GB-ENG"]->.e;
(nwr["brand:wikidata"="Q1434528"](area.e);
 nwr["shop"]["name"~"^Poundland",i](area.e););
out center tags;"""
pound = []
for ep in ["https://overpass-api.de/api/interpreter",
           "https://overpass.kumi.systems/api/interpreter",
           "https://overpass.private.coffee/api/interpreter"]:
    try:
        code, body = get(ep, data=urllib.parse.urlencode({"data": OQ}).encode(), tries=2)
        els = json.loads(body)["elements"]
        if els:
            break
    except SystemExit:
        continue
else:
    raise SystemExit("overpass failed")

def near_town(lat, lng):
    best, bd = "", 1e9
    for s in spoons:
        if not s[5]:
            continue
        d = (s[2] - lat) ** 2 + ((s[3] - lng) * math.cos(math.radians(lat))) ** 2
        if d < bd:
            bd, best = d, s[5]
    return best

seen = set()
for e in els:
    t = e.get("tags", {})
    if any(k in t for k in ("disused:shop", "was:shop")):
        continue
    lat = e.get("lat") or e.get("center", {}).get("lat")
    lng = e.get("lon") or e.get("center", {}).get("lon")
    if lat is None:
        continue
    key = (round(lat, 3), round(lng, 3))
    if key in seen:
        continue
    seen.add(key)
    town = t.get("addr:city") or t.get("addr:town") or t.get("addr:suburb") or near_town(lat, lng)
    street = " ".join(x for x in [t.get("addr:housenumber", ""), t.get("addr:street", "")] if x)
    place = t.get("addr:place", "")
    parts = [p for p in [street or place, town, t.get("addr:postcode", "")] if p]
    addr = ", ".join(parts) if (street or place) else ("Near " + town if town else "")
    name = "Poundland " + town if town else "Poundland"
    pound.append([name, addr, round(lat, 6), round(lng, 6), "", town])
print("poundland", len(pound))

if len(spoons) < 300 or len(pound) < 200:
    raise SystemExit("suspiciously few results, not overwriting")

json.dump(spoons, open("data/spoons.json", "w"), ensure_ascii=False, separators=(",", ":"))
json.dump(pound, open("data/poundland.json", "w"), ensure_ascii=False, separators=(",", ":"))
json.dump({"updated": time.strftime("%Y-%m-%d"), "spoons": len(spoons), "poundland": len(pound)},
          open("data/meta.json", "w"))
