"""PBS weekly SPI: discover, download, parse Annex (city prices, fertilizer) + Report (index, national averages)."""
import urllib.error
import io, re, os, json, time, datetime, urllib.request
import xlsx_lite  # stdlib-only xlsx reader (no openpyxl needed)
BASE = "https://www.pbs.gov.pk/wp-content/uploads/2020/07/"
PAGE = "https://www.pbs.gov.pk/price-statistics/"
HERE = os.path.dirname(os.path.abspath(__file__)); FC = os.path.join(HERE, "cache", "spi_files"); os.makedirs(FC, exist_ok=True)

def _get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 PakTradeHub/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r: return r.read()
def _num(v):
    if isinstance(v, (int, float)): return float(v)
    try: return float(str(v).replace(",", ""))
    except Exception: return None

def parse_annex(b):
    W = xlsx_lite.sheets(b)
    A = W[0]
    items, cities, date, cols, nat_i = {}, [], None, [], None
    for r in A:
        if r and r[0] == "SL." and len(r) > 3 and r[3]:
            nat_i = next((i for i in range(3, len(r)) if r[i] and str(r[i]).strip() == "National Average"), None)
            cols = [(i, re.sub(r"\s*\(\d+\)", "", str(r[i])).strip()) for i in range(3, (nat_i or len(r) - 1), 3) if r[i] and str(r[i]).strip() != "SL."]
            cities += [c for _, c in cols if c not in cities]; continue
        if r and len(r) > 3 and isinstance(r[3], str) and r[3].startswith("PRICES ON"):
            date = re.search(r"(\d{2})-(\d{2})-(\d{4})", r[3]).groups(); continue
        if r and isinstance(r[0], (int, float)) and isinstance(r[1], str) and cols:
            it = items.setdefault(int(r[0]), {"no": int(r[0]), "name": r[1].strip(), "unit": str(r[2]).strip(), "cities": {}})
            if nat_i:
                v = [_num(x) for x in r[nat_i:nat_i + 7]]
                it["national"] = {"min": v[0], "avg": v[1], "max": v[2], "prev": v[3], "yago": v[4], "wow": v[5], "yoy": v[6]}
            for i, c in cols:
                mn, av, mx = _num(r[i]), _num(r[i + 1]), _num(r[i + 2])
                # PBS uses 0 where an item is not available in a city
                it["cities"][c] = None if not av else {"min": mn, "avg": av, "max": mx}
    fert = None
    if len(W) > 1:
        B = W[1]
        for k, r in enumerate(B):
            if r and r[1] == "Description" and any(isinstance(x, str) and "Average" in x for x in r if x):
                ai = next(i for i, x in enumerate(r) if isinstance(x, str) and "Average" in x)
                fc = [(i, str(r[i]).replace("-", "")) for i in range(2, ai) if r[i]]
                title = next((str(x[0]) for x in B[max(0, k - 3):k] if x and x[0] and "Fertili" in str(x[0])), "Fertilizers")
                rows = []
                for x in B[k + 1:]:
                    if not x or not isinstance(x[0], (int, float)): break
                    rows.append({"name": str(x[1]).strip(), "cities": {c: _num(x[i]) for i, c in fc},
                                 "avg": _num(x[ai]), "avgPrev": _num(x[ai + 1]), "avgYago": _num(x[ai + 2]), "wow": _num(x[ai + 3]), "yoy": _num(x[ai + 4])})
                fert = {"title": title.split(" for the")[0], "unit": "Rs per 50 kg bag", "cities": [c for _, c in fc], "rows": rows}; break
    return {"date": "-".join(reversed(date)) if date else None, "cities": cities, "items": list(items.values()), "fert": fert}

def parse_report(b):
    W = xlsx_lite.sheets(b)
    P1 = W[0]
    idx, trend = [], []
    for r in P1:
        lab = str(r[1]).strip() if len(r) > 1 and r[1] else ""
        if (lab.startswith("Q") and "Rs" in lab or lab == "Combined") and _num(r[3]) is not None:
            idx.append({"group": lab, "cur": _num(r[3]), "prev": _num(r[4]), "yago": _num(r[5]), "wow": _num(r[6]), "yoy": _num(r[7])})
        if re.fullmatch(r"\d{2}-\d{2}-\d{4}", lab) and _num(r[5]) is not None:
            d = lab.split("-"); trend.append({"week": f"{d[2]}-{d[1]}-{d[0]}", "q1": _num(r[2]), "combined": _num(r[5]), "combWow": _num(r[6]), "combYoy": _num(r[7])})
    P2 = W[1] if len(W) > 1 else []
    nat, cat = {}, None
    for r in P2:
        if len(r) > 1 and isinstance(r[1], str) and "registered" in r[1]: cat = "increase" if "INCREASE" in r[1] else "decrease" if "DECREASE" in r[1] else "unchanged"
        if len(r) > 8 and isinstance(r[1], (int, float)) and isinstance(r[2], str):
            nat[r[2].strip()] = {"unit": str(r[3]).strip(), "avg": _num(r[4]), "prev": _num(r[5]), "yago": _num(r[6]), "wow": _num(r[7]), "yoy": _num(r[8]),
                                 "wLowest": _num(r[9]), "wCombined": _num(r[10]), "move": cat}
    return {"index": idx, "trend": trend, "national": nat}

def _cached_file(kind, d):
    p = os.path.join(FC, f"{kind}_{d}.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f: return json.load(f)
    fname = (f"Annex_{d}.xlsx" if kind == "annex" else f"3.-SPI-Report-{d}.xlsx"); url = BASE + fname
    try: v = {"url": url, **(parse_annex if kind == "annex" else parse_report)(_get(url))}
    except urllib.error.HTTPError as e:
        v = {"url": url, "missing": e.code}
        if (datetime.date.today() - datetime.datetime.strptime(d, "%d.%m.%Y").date()).days < 21:
            return v  # recent 404: not cached, the file may still be published
    except Exception as e:
        return {"url": url, "error": str(e)}  # not cached; retried next refresh
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(v, f)
    os.replace(tmp, p)
    return v

def spi(weeks=26):
    html = _get(PAGE).decode("utf-8", "ignore")
    found = sorted(set(re.findall(r"Annex_(\d{2}\.\d{2}\.\d{4})\.xlsx", html)), key=lambda s: s[6:] + s[3:5] + s[:2])
    if not found: raise RuntimeError("No SPI Annex link found on " + PAGE)
    latest = datetime.datetime.strptime(found[-1], "%d.%m.%Y").date()
    out = []
    for k in range(weeks):
        base = latest - datetime.timedelta(days=7 * k); got = None
        for off in (0, -1, 1, -2):  # releases occasionally shift around holidays
            d = (base + datetime.timedelta(days=off)).strftime("%d.%m.%Y"); a = _cached_file("annex", d)
            if not a.get("missing") and not a.get("error"): got = (d, a); break
        if not got: out.append({"week": base.isoformat(), "missing": True}); continue
        d, a = got; r = _cached_file("report", d)
        out.append({"week": a["date"] or d, "file": d, "annex": a, "report": r if not r.get("missing") and not r.get("error") else None,
                    "reportUrl": r["url"], "reportMissing": bool(r.get("missing") or r.get("error"))})
    return out, found[-1]
