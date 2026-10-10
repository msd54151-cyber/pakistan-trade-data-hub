#!/usr/bin/env python3
"""Pakistan Trade Data Hub v1 - proxy + cache for live official APIs/files. No data values are hardcoded; on fetch failure the panel gets an error, never cached-stale or sample data."""
import refresh_sched as SCHED
import json, os, re, time, threading, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
TTL = 24*3600
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(HERE, "cache"); os.makedirs(CACHE_DIR, exist_ok=True)
LOCK = threading.RLock()

_CT_LAST = [0.0]
def fetch(url, timeout=90):
    if "comtradeapi.un.org/public" in url:  # be polite to the preview API
        with LOCK:
            w = 1.2 - (time.time() - _CT_LAST[0])
            if w > 0: time.sleep(w)
            _CT_LAST[0] = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": "PakTradeHub/1.0", "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r: return r.read()

SCHEDULED = {"pmex", "spi", "mandi", "fao_crops", "fao_pp"}  # refreshed only by the scheduler (or when no cache exists)
def stamp(): return SCHED.datetime.datetime.now(SCHED.PKT).strftime("%Y-%m-%d %H:%M PKT")
def write_cache(key, v):
    v["meta"]["fetched_at"] = stamp(); p = os.path.join(CACHE_DIR, key + ".json"); tmp = p + f".{threading.get_ident()}.tmp"
    with LOCK:
        with open(tmp, "w", encoding="utf-8") as f: json.dump(v, f)
        os.replace(tmp, p)  # atomic on Windows and POSIX
def cached(key, fn, ttl=None):
    p = os.path.join(CACHE_DIR, key + ".json")
    if key in SCHEDULED and os.path.exists(p):
        with open(p, encoding="utf-8") as f: return json.load(f)
    if os.path.exists(p) and time.time() - os.path.getmtime(p) < (ttl or TTL):
        with open(p, encoding="utf-8") as f: return json.load(f)
    with LOCK:
        try:
            v = fn(); write_cache(key, v)
            return v
        except Exception:
            raise  # no stale/sample fallback: the API error is returned to the panel

# ---------- reference lookups (names only, not data) ----------
def ct_partners():
    def f():
        d = json.loads(fetch("https://comtradeapi.un.org/files/v1/app/reference/partnerAreas.json"))
        return {"data": d["results"], "meta": {}}
    return cached("ref_partners", f)["data"]
def ct_hs():
    def f():
        d = json.loads(fetch("https://comtradeapi.un.org/files/v1/app/reference/HS.json"))
        return {"data": {r["id"]: r["text"] for r in d["results"] if len(r["id"]) == 2}, "meta": {}}
    return cached("ref_hs2", f)["data"]

# ---------- IMF IMTS ----------
IMF = "https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.STA/IMTS/+/"
IMF_PAGE = "https://data.imf.org/en/datasets/IMF.STA:IMTS"
IMF_DEF = {"XG_FOB_USD": "Goods exports, FOB, US$ (IMF IMTS; partner = World)",
           "MG_CIF_USD": "Goods imports, CIF, US$ (IMF IMTS; partner = World)"}
def imf_series(ind, n=400, iso="G001", freq="M"):
    url = IMF + f"PAK.{ind}.{iso}.{freq}?lastNObservations={n}"
    d = json.loads(fetch(url))["data"]
    if not d["dataSets"][0].get("series"): raise RuntimeError(f"IMF IMTS has no {freq} series for partner {iso}")
    periods = [v["value"] for v in d["structures"][0]["dimensions"]["observation"][0]["values"]]
    obs = list(d["dataSets"][0]["series"].values())[0]["observations"]
    pts = sorted((periods[int(k)], float(v[0])) for k, v in obs.items() if v[0] is not None)
    return pts, url
def iso_of(ptn):
    if str(ptn) in ("0", ""): return "G001", "World"
    p = next((p for p in ct_partners() if str(p["PartnerCode"]) == str(ptn)), None)
    if not p or not p.get("PartnerCodeIsoAlpha3"): raise RuntimeError(f"No ISO3 code for partner {ptn}")
    return p["PartnerCodeIsoAlpha3"], p["text"]
def imf_annual(ptn="0"):
    iso, nm = iso_of(ptn)
    x, ux = imf_series("XG_FOB_USD", 60, iso, "A"); m, um = imf_series("MG_CIF_USD", 60, iso, "A")
    return {"data": {"exports": x, "imports": m, "partner": nm}, "meta": {"source": "IMF International Trade in Goods (IMTS)",
        "dataset": f"IMF.STA:IMTS — PAK.XG_FOB_USD.{iso}.A / PAK.MG_CIF_USD.{iso}.A", "period": f"{x[0][0]} – {x[-1][0]}", "official_url": IMF_PAGE, "raw_urls": [ux, um],
        "definition": f"Annual goods trade with {nm}, US$. Balance = exports (FOB) − imports (CIF). CIF includes freight & insurance, so this balance is more negative than a FOB/FOB balance."}}
def imf_monthly(ptn="0"):
    iso, nm = iso_of(ptn)
    x, ux = imf_series("XG_FOB_USD", 400, iso); m, um = imf_series("MG_CIF_USD", 400, iso)
    return {"data": {"exports": x, "imports": m}, "meta": {
        "source": "IMF International Trade in Goods (IMTS)", "dataset": f"IMF.STA:IMTS — PAK.XG_FOB_USD.{iso}.M / PAK.MG_CIF_USD.{iso}.M", "partner": nm,
        "period": f"{x[0][0]} – {x[-1][0]}", "official_url": IMF_PAGE, "raw_urls": [ux, um],
        "definition": f"Monthly merchandise (goods only) trade with {nm}, US$. Exports valued FOB, imports CIF. Excludes services."}}
def imf_partners(ind, year=None):
    url = IMF + f"PAK.{ind}.*.A" if year else IMF + f"PAK.{ind}.*.A?lastNObservations=1"
    d = json.loads(fetch(url))["data"]; s = d["structures"][0]["dimensions"]
    cps = [v["id"] for v in s["series"][2]["values"]]; per = [v["value"] for v in s["observation"][0]["values"]]
    rows = []
    for k, v in d["dataSets"][0]["series"].items():
        cp = cps[int(k.split(":")[2])]
        for oi, o in v.get("observations", {}).items():
            if o[0] is not None and re.fullmatch(r"[A-Z]{3}", cp): rows.append((cp, per[int(oi)], float(o[0])))
    if not rows: raise RuntimeError(f"IMF IMTS has no partner data for {year}")
    yr = str(year) if year and any(r[1] == str(year) for r in rows) else None
    if yr is None: raise RuntimeError(f"IMF IMTS has no partner data for {year}")
    rows = [r for r in rows if r[1] == yr]
    names = {}
    for p in ct_partners():
        if "..." not in p["text"]: names.setdefault(p.get("PartnerCodeIsoAlpha3"), p["text"])
    rows.sort(key=lambda r: -r[2])
    return {"data": [{"partner": names.get(c, c), "iso3": c, "value": v} for c, _, v in rows[:10]], "meta": {
        "source": "IMF International Trade in Goods (IMTS)", "dataset": f"IMF.STA:IMTS — PAK.{ind}.*.A",
        "period": yr, "official_url": IMF_PAGE, "raw_urls": [url],
        "definition": IMF_DEF[ind].replace("partner = World", "by partner country, annual") + ". Country aggregates excluded."}}

# ---------- World Bank WDI ----------
WDI_IND = {"TX.VAL.MRCH.CD.WT": "Merchandise exports (current US$)", "TM.VAL.MRCH.CD.WT": "Merchandise imports (current US$)",
           "NE.EXP.GNFS.CD": "Exports of goods AND services (current US$, national accounts)",
           "NE.IMP.GNFS.CD": "Imports of goods AND services (current US$, national accounts)", "NE.TRD.GNFS.ZS": "Trade (% of GDP)"}
def wdi():
    out, urls = {}, []
    for ind in WDI_IND:
        url = f"https://api.worldbank.org/v2/country/PAK/indicator/{ind}?format=json&date=1990:2030&per_page=100"
        meta, rows = json.loads(fetch(url)); urls.append(url)
        out[ind] = {"label": WDI_IND[ind], "points": sorted((r["date"], r["value"]) for r in rows if r["value"] is not None),
                    "lastupdated": meta.get("lastupdated")}
    yrs = [p[0] for v in out.values() for p in v["points"]]
    return {"data": out, "meta": {"source": "World Bank World Development Indicators (WDI)", "dataset": ", ".join(WDI_IND),
        "period": f"{min(yrs)} – {max(yrs)}", "official_url": "https://data.worldbank.org/country/pakistan", "raw_urls": urls,
        "definition": "Annual. 'Merchandise' = goods only (WTO-sourced). 'Goods and services' = national-accounts basis incl. services; these will NOT match goods-only figures."}}

# ---------- UN Comtrade preview ----------
CT = "https://comtradeapi.un.org/public/v1/"
def ct_latest_year():
    d = json.loads(fetch(CT + "getDA/C/A/HS?reporterCode=586"))["data"]
    return max(int(x["period"]) for x in d)
def ct_products(flow, y=None, ptn="0"):
    y = y or ct_latest_year(); url = CT + f"preview/C/A/HS?reporterCode=586&period={y}&partnerCode={ptn}&flowCode={flow}&cmdCode=AG2"
    rows = [r for r in json.loads(fetch(url))["data"] if r["partner2Code"] == 0 and r["motCode"] == 0 and r["customsCode"] == "C00"]; hs = ct_hs()
    pn = iso_of(ptn)[1] if str(ptn) != "0" else "World"
    rows.sort(key=lambda r: -r["primaryValue"])
    return {"data": [{"code": r["cmdCode"], "name": hs.get(r["cmdCode"], r["cmdCode"]), "value": r["primaryValue"], **qfields(r)} for r in rows[:12]], "meta": {
        "source": "UN Comtrade (public preview API)", "dataset": f"C/A/HS, reporter 586, flow {flow}, cmdCode AG2 (HS 2-digit), partner {ptn} ({pn})",
        "period": y, "official_url": "https://comtradeplus.un.org/TradeFlow", "raw_urls": [url],
        "definition": f"Annual goods {'exports (FOB)' if flow=='X' else 'imports (CIF)'} as reported by Pakistan to UN Comtrade, US$ (primaryValue)."}}
def ct_partners_top(flow, y=None):
    y = y or ct_latest_year(); url = CT + f"preview/C/A/HS?reporterCode=586&period={y}&flowCode={flow}&cmdCode=TOTAL"
    rows = [r for r in json.loads(fetch(url))["data"] if r["partnerCode"] != 0 and r.get("partner2Code", 0) == 0]
    names = {p["PartnerCode"]: p["text"] for p in ct_partners()}
    rows.sort(key=lambda r: -r["primaryValue"])
    return {"data": [{"partner": names.get(r["partnerCode"], str(r["partnerCode"])), "value": r["primaryValue"]} for r in rows[:10]], "meta": {
        "source": "UN Comtrade (public preview API)", "dataset": f"C/A/HS, reporter 586, flow {flow}, cmdCode TOTAL, all partners",
        "period": y, "official_url": "https://comtradeplus.un.org/TradeFlow", "raw_urls": [url],
        "definition": f"Annual total goods {'exports' if flow=='X' else 'imports'} by partner, as reported by Pakistan. Preview capped at 500 rows."}}

# ---------- WITS TRAINS tariffs ----------
def wits_tariffs(want=None):
    av = fetch("https://wits.worldbank.org/API/V1/wits/datasource/trn/dataavailability/country/586/year/all").decode()
    years = sorted(int(y) for y in re.findall(r"<wits:year>(\d{4})</wits:year>", av))
    top = int(want) if want else time.localtime().tm_year - 1
    cands = list(range(top, 1994, -1))[:8]
    for y in cands:
        url = f"https://wits.worldbank.org/API/V1/SDMX/V21/datasource/TRN/reporter/586/partner/000/product/all/year/{y}/datatype/reported"
        try: x = fetch(url, timeout=180).decode()
        except Exception: continue
        agg = {}
        for code, attrs in re.findall(r'<Series [^>]*PRODUCTCODE="(\d+)"[^>]*>\s*<Obs ([^>]*)/>', x):
            if 'TARIFFTYPE="MFN"' not in attrs: continue
            m = re.search(r'SUM_OF_RATES="([\d.]+)"', attrs); n = re.search(r'TOTALNOOFLINES="(\d+)"', attrs)
            if m and n: a = agg.setdefault(code[:2], [0.0, 0]); a[0] += float(m.group(1)); a[1] += int(n.group(1))
        if agg: break
    else: raise RuntimeError(f"No WITS TRAINS tariff data for {want} or the 7 earlier years")
    hs = ct_hs(); tot = sum(a[0] for a in agg.values()) / sum(a[1] for a in agg.values())
    rows = sorted(({"code": k, "name": hs.get(k, k), "value": a[0]/a[1]} for k, a in agg.items()), key=lambda r: -r["value"])
    return {"data": {"overall": tot, "top": rows[:15]}, "meta": {"source": "World Bank WITS – UNCTAD TRAINS", "dataset": "TRN, reporter 586, partner 000 (World), reported, MFN",
        "period": str(y) + (f" (no data for {want}; nearest earlier year)" if want and int(want) != y else ""), "official_url": "https://wits.worldbank.org/CountryProfile/en/PAK", "raw_urls": [url],
        "definition": "MFN applied tariff, simple average of national tariff lines (%), aggregated from HS6 to HS2 by this hub (sum of rates / number of lines)."}}

# ---------- Products drill-down (Comtrade preview) ----------
def hs_all():
    def f():
        d = json.loads(fetch("https://comtradeapi.un.org/files/v1/app/reference/HS.json"))
        return {"data": [[r["id"], r["text"], r["parent"]] for r in d["results"] if r["id"] != "TOTAL"], "meta": {}}
    return cached("ref_hs_all", f)["data"]
def hs_meta():
    a = hs_all(); return {c: t for c, t, _ in a}, {}
def ct_years():
    d = json.loads(fetch(CT + "getDA/C/A/HS?reporterCode=586"))["data"]
    return {"data": sorted({int(x["period"]) for x in d}, reverse=True), "meta": {"source": "UN Comtrade data availability", "dataset": "getDA/C/A/HS reporter 586",
            "period": "", "official_url": "https://comtradeplus.un.org", "raw_urls": [CT + "getDA/C/A/HS?reporterCode=586"], "definition": "Annual periods Pakistan has reported."}}
def ctq(params):
    url = CT + "preview/C/A/HS?reporterCode=586&" + urllib.parse.urlencode(params, safe=",")
    d = json.loads(fetch(url))
    if d.get("error"): raise RuntimeError("Comtrade preview: " + d["error"])
    return d["data"], url
def qunits():
    def f():
        d = json.loads(fetch("https://comtradeapi.un.org/files/v1/app/reference/QuantityUnits.json"))
        return {"data": {str(u["qtyCode"]): [u["qtyAbbr"], u["qtyDescription"]] for u in d["results"]}, "meta": {}}
    return cached("ref_qunits", f)["data"]
def qfields(r):
    """Quantity fields straight from Comtrade; 0 with unit -1 (or value>0 and qty 0) is treated as not available."""
    U = qunits(); v = r.get("primaryValue") or 0
    qc = str(r.get("qtyUnitCode", -1)); qty = r.get("qty") or 0
    ok = qc != "-1" and qty > 0
    nw = r.get("netWgt") or 0; ac = str(r.get("altQtyUnitCode", -1)); aq = r.get("altQty") or 0
    return {"qty": qty if ok else None, "qtyUnit": U.get(qc, [None])[0] if ok else None, "qtyUnitDesc": U.get(qc, [None, None])[1] if ok else None,
            "qtyEst": bool(r.get("isQtyEstimated")) if ok else None,
            "netWgt": nw if nw > 0 else None, "netWgtEst": bool(r.get("isNetWgtEstimated")) if nw > 0 else None,
            "altQty": aq if ac != "-1" and aq > 0 else None, "altQtyUnit": U.get(ac, [None])[0] if ac != "-1" and aq > 0 else None,
            "unitValue": v / qty if ok and v else None, "unitValueKg": v / nw if nw > 0 and v else None}
def children(parent):
    a = hs_all()
    if parent == "TOTAL": return [c for c, t, p in a if len(c) == 2]
    return [c for c, t, p in a if p == parent]
def ct_balance(year):
    names = {p["PartnerCode"]: p["text"] for p in ct_partners()}; out = {}; urls = []
    for fl in ("X", "M"):
        rows, u = ctq({"period": year, "flowCode": fl, "cmdCode": "TOTAL"}); urls.append(u)
        for r in rows:
            if r["partner2Code"] or r["motCode"] or r["customsCode"] != "C00": continue
            o = out.setdefault(r["partnerCode"], {"X": None, "M": None}); o[fl] = (o[fl] or 0.0) + r["primaryValue"]
    one = sum(1 for c, v in out.items() if c != 0 and (v["X"] is None or v["M"] is None))
    rows = [{"code": c, "partner": names.get(c, str(c)), "exports": v["X"], "imports": v["M"], "balance": v["X"] - v["M"]} for c, v in out.items() if c != 0 and v["X"] is not None and v["M"] is not None]
    rows.sort(key=lambda r: -r["balance"]); W = out.get(0, {"X": None, "M": None})
    return {"data": {"surpluses": [r for r in rows if r["balance"] > 0][:10], "deficits": sorted([r for r in rows if r["balance"] < 0], key=lambda r: r["balance"])[:10], "world": W}, "meta": {
        "source": "UN Comtrade (public preview API)", "dataset": "C/A/HS reporter 586, cmdCode TOTAL, flows X and M, all partners", "period": year,
        "official_url": "https://comtradeplus.un.org/TradeFlow", "raw_urls": urls,
        "definition": f"Balance = Pakistan-reported exports (FOB) − imports (CIF) by partner. {one} partners with only one flow reported are excluded (no balance computed). Imports by country of origin, exports by destination; CIF/FOB asymmetry and origin/destination attribution make bilateral balances indicative."}}
def partner_list():
    rows = [{"code": p["PartnerCode"], "name": p["text"], "iso3": p.get("PartnerCodeIsoAlpha3")} for p in ct_partners()
            if not p.get("isGroup") and "..." not in p["text"] and p.get("PartnerCodeIsoAlpha3") and not p["PartnerCodeIsoAlpha3"].startswith("_") and p["PartnerCode"] != 0]
    return {"data": sorted(rows, key=lambda r: r["name"]), "meta": {"source": "UN Comtrade partner reference", "dataset": "partnerAreas.json", "period": "",
        "official_url": "https://comtradeplus.un.org", "raw_urls": ["https://comtradeapi.un.org/files/v1/app/reference/partnerAreas.json"], "definition": "Partner list; ISO3 codes used to query IMF IMTS."}}
def prod_level(flow, year, parent, ptn="0"):
    names = {c: t for c, t, _ in hs_all()}; kids = children(parent)
    if not kids: raise RuntimeError("No sub-codes for " + parent)
    cmd = "AG2" if parent == "TOTAL" else ",".join(kids)
    cur, url = ctq({"period": year, "partnerCode": ptn, "flowCode": flow, "cmdCode": cmd})
    prev, purl = ctq({"period": int(year) - 1, "partnerCode": ptn, "flowCode": flow, "cmdCode": cmd})
    tot, turl = ctq({"period": year, "partnerCode": ptn, "flowCode": flow, "cmdCode": "TOTAL"})
    oth, ourl = ctq({"period": year, "partnerCode": ptn, "flowCode": "M" if flow == "X" else "X", "cmdCode": cmd})
    ov = {r["cmdCode"]: r["primaryValue"] for r in oth if r["partner2Code"] == 0 and r["motCode"] == 0 and r["customsCode"] == "C00"}
    pn = iso_of(ptn)[1] if str(ptn) != "0" else "World"
    pv = {r["cmdCode"]: r["primaryValue"] for r in prev if r["partner2Code"] == 0 and r["motCode"] == 0 and r["customsCode"] == "C00"}
    T = sum(r["primaryValue"] for r in tot if r["partner2Code"] == 0 and r["motCode"] == 0 and r["customsCode"] == "C00") or None
    rows = []
    for r in cur:
        if r["partner2Code"] or r["motCode"] or r["customsCode"] != "C00": continue
        c, v = r["cmdCode"], r["primaryValue"]; p = pv.get(c)
        rows.append({"code": c, "name": names.get(c, c), "value": v, "share": v / T * 100 if T else None,
                     "prev": p, "chg": (v - p) / p * 100 if p else None,
                     "other": ov.get(c), "balance": None if ov.get(c) is None else ((v - ov[c]) if flow == "X" else (ov[c] - v)), "hasChildren": len(c) < 6, **qfields(r)})
    rows.sort(key=lambda r: -r["value"])
    lvl = {"TOTAL": "HS2 chapters"}.get(parent, "HS4 headings" if len(parent) == 2 else "HS6 subheadings")
    path = [parent[:n] for n in (2, 4) if len(parent) >= n]
    return {"data": {"rows": rows, "total": T, "parent": parent, "parentName": names.get(parent, "All products"), "pathNames": {c: names.get(c, c) for c in path}}, "meta": {
        "source": "UN Comtrade (public preview API)", "dataset": f"C/A/HS reporter 586 flow {flow}, partner {ptn} ({pn}), cmdCode {'AG2' if parent=='TOTAL' else 'children of ' + parent} ({lvl})",
        "period": f"{year} (change vs {int(year)-1})", "official_url": "https://comtradeplus.un.org/TradeFlow", "raw_urls": [url, purl, turl, ourl],
        "definition": f"Annual goods {'exports FOB' if flow=='X' else 'imports CIF'}, US$, as reported by Pakistan. Share = % of Pakistan's total {'exports' if flow=='X' else 'imports'} with {pn} (cmdCode TOTAL). Balance = exports FOB − imports CIF for the same code and partner; n/a when the other flow is not reported (never assumed 0)."}}
def prod_partners(flow, year, code):
    rows, url = ctq({"period": year, "flowCode": flow, "cmdCode": code})
    rows = [r for r in rows if r["partner2Code"] == 0 and r["motCode"] == 0 and r["customsCode"] == "C00"]
    W = next((r["primaryValue"] for r in rows if r["partnerCode"] == 0), None)
    names = {p["PartnerCode"]: p["text"] for p in ct_partners()}
    rs = sorted((r for r in rows if r["partnerCode"] != 0), key=lambda r: -r["primaryValue"])[:10]
    return {"data": [{"partner": names.get(r["partnerCode"], str(r["partnerCode"])), "value": r["primaryValue"], "share": r["primaryValue"] / W * 100 if W else None, **qfields(r)} for r in rs], "code": code, "codeName": {c: t for c, t, _ in hs_all()}.get(code, code), "meta": {
        "source": "UN Comtrade (public preview API)", "dataset": f"C/A/HS reporter 586 flow {flow} cmdCode {code}, all partners", "period": year,
        "official_url": "https://comtradeplus.un.org/TradeFlow", "raw_urls": [url], "definition": "Top 10 partners for this product; share = % of this product's total to/from World."}}
def prod_trend(flow, code, year, ptn="0"):
    pts, urls = [], []
    for y in range(int(year) - 4, int(year) + 1):
        try:
            rows, url = ctq({"period": y, "partnerCode": ptn, "flowCode": flow, "cmdCode": code}); urls.append(url)
            rr = [r for r in rows if r["partner2Code"] == 0 and r["motCode"] == 0 and r["customsCode"] == "C00"]
            if rr: q = qfields(rr[0]); pts.append([str(y), rr[0]["primaryValue"], q["netWgt"], q["qty"], q["qtyUnit"]])
        except Exception: pass
    return {"data": pts, "meta": {"source": "UN Comtrade (public preview API)", "dataset": f"C/A/HS reporter 586 flow {flow} cmdCode {code}, partner {ptn}, one call per year",
        "period": f"{int(year)-4} – {year}", "official_url": "https://comtradeplus.un.org/TradeFlow", "raw_urls": urls,
        "definition": "Annual value, US$, Pakistan-reported. Note: HS revisions (H5→H6 in 2022) can affect comparability of HS6 codes across years."}}


# ---------- Agriculture: FAOSTAT bulk (keyless) ----------
import zipfile, io, csv
FAO_QCL = "https://bulks-faostat.fao.org/production/Production_Crops_Livestock_E_Asia.zip"
FAO_PP = "https://bulks-faostat.fao.org/production/Prices_E_Asia.zip"
def fao_extract(url, member_suffix, keep):
    z = zipfile.ZipFile(io.BytesIO(fetch(url, timeout=180)))
    name = next(n for n in z.namelist() if n.endswith(member_suffix))
    rd = csv.reader(io.TextIOWrapper(z.open(name), encoding="utf-8", errors="replace")); h = next(rd)
    yc = [(i, c[1:]) for i, c in enumerate(h) if re.fullmatch(r"Y\d{4}", c)]
    out = []
    for x in rd:
        if x[0] != "165": continue
        row = dict(zip(h, x))
        if not keep(row): continue
        out.append((row, {y: float(x[i]) for i, y in yc if x[i] not in ("", None)}))
    return out, name, z.getinfo(name).date_time
def fao_crops():
    rows, name, dt = fao_extract(FAO_QCL, "_E_Asia_NOFLAG.csv", lambda r: r["Element"] in ("Production", "Area harvested", "Yield"))
    items = {}
    for r, ys in rows:
        it = items.setdefault(r["Item"], {"code": r["Item Code"], "cpc": r["Item Code (CPC)"].strip("'"), "series": {}})
        it["series"][r["Element"]] = {"unit": r["Unit"], "elementCode": r["Element Code"], "points": sorted(ys.items())}
    items = {k: v for k, v in items.items() if "Area harvested" in v["series"] and "Production" in v["series"]}
    yrs = [p[0] for v in items.values() for s_ in v["series"].values() for p in s_["points"]]
    return {"data": items, "meta": {"source": "FAOSTAT – Crops and livestock products (QCL)", "dataset": "QCL, area 165 (Pakistan), elements 5312 Area harvested / 5510 Production / 5412 Yield",
        "period": f"{min(yrs)} – {max(yrs)}", "official_url": "https://www.fao.org/faostat/en/#data/QCL", "raw_urls": [FAO_QCL],
        "definition": f"Annual national estimates (official/FAO-imputed). Bulk file {name}, file date {dt[0]}-{dt[1]:02d}-{dt[2]:02d}. The FAOSTAT REST API now requires an auth header, so the hub uses the keyless bulk download."}}
def fao_pp():
    rows, name, dt = fao_extract(FAO_PP, "_E_Asia_NOFLAG.csv", lambda r: r.get("Months") == "Annual value" and r["Element Code"] == "5530")
    data = {r["Item"]: {"unit": r["Unit"], "points": sorted(ys.items())} for r, ys in rows}
    return {"data": data, "meta": {"source": "FAOSTAT – Producer Prices (PP)", "dataset": "PP, area 165, element 5530 Producer Price (LCU/tonne), annual value",
        "period": "annual", "official_url": "https://www.fao.org/faostat/en/#data/PP", "raw_urls": [FAO_PP],
        "definition": f"Farm-gate producer price, Pakistani rupees (LCU) per tonne, annual. Bulk file {name}, file date {dt[0]}-{dt[1]:02d}-{dt[2]:02d}."}}

# ---------- Market prices: FAO GIEWS FPMA (keyless REST) ----------
FPMA = "https://fpma.fao.org/giews/v4/price_module/api/v1/"
def mandi():
    lst = json.loads(fetch(FPMA + "FpmaSerieDomestic/?country_iso3=PAK"))["results"]
    ser = [x for x in lst if x["iso3_country_code"] == "PAK"]
    out, urls = [], [FPMA + "FpmaSerieDomestic/?country_iso3=PAK"]
    for x in ser:
        u = FPMA + f"FpmaSeriePrice/{x['uuid']}/"; urls.append(u)
        dp = [d for d in json.loads(fetch(u))["datapoints"] if d["periodicity"] == "weekly" and d["price_value"] is not None]
        dp.sort(key=lambda d: d["date"])
        if not dp: continue
        last = dp[-1]; prev = dp[-2] if len(dp) > 1 else None; yago = next((d for d in reversed(dp) if d["date"] <= str(int(last["date"][:4]) - 1) + last["date"][4:]), None)
        out.append({"market": x["market_name"], "admin": x["admin_unit"], "commodity": x["commodity_name"], "priceType": x["price_type"], "unit": f"{x['currency']}/{x['measure_unit_label']}",
                    "source": x["source_name"], "date": last["date"], "price": last["price_value"], "usd": last["price_value_dollar"],
                    "wow": (last["price_value"] / prev["price_value"] - 1) * 100 if prev else None, "yoy": (last["price_value"] / yago["price_value"] - 1) * 100 if yago else None,
                    "history": [[d["date"], d["price_value"]] for d in dp if d["date"] >= str(int(last["date"][:4]) - 3)], "uuid": x["uuid"], "raw": u})
    latest = max(o["date"] for o in out)
    return {"data": out, "meta": {"source": "FAO GIEWS FPMA Tool (data: Pakistan Bureau of Statistics)", "dataset": "FpmaSerieDomestic country_iso3=PAK, weekly retail series",
        "period": f"latest week {latest}", "official_url": "https://fpma.fao.org/giews/fpmat4/#/dashboard/tool/domestic", "raw_urls": urls[:3] + ["… one FpmaSeriePrice call per series"],
        "definition": "WEEKLY RETAIL prices (PKR/kg) collected by PBS and republished by FAO GIEWS. These are NOT daily wholesale mandi rates. Series that stopped (e.g. plain wheat, 2021) are shown with their real last date."}}

# ---------- PMEX daily exchange prices (public OHLC report; undocumented JSON) ----------
PMEX_URL = "https://mportal.pmex.com.pk/mt5bonew/Home/GetOHLC"
PMEX_PAGE = "https://mportal.pmex.com.pk/mt5bonew/Home/OHLCReport"
# Field mapping verified against the report page's own JS (OHLCReport, table columns in order):
PMEX_MAP = {"Post_Date": "date", "Trader_Id": "symbol", "acc_type": "open", "Trans_Id": "high", "Amount": "low",
            "Status": "close", "Verified_Date": "volume", "Trader_Name": "settlement", "Trans_Date": "fx"}
def pmex_group(sym):
    if sym.startswith("EWR"): return "Warehouse receipts (EWR)"
    if re.match(r"(ICOTTON|IWHEAT|ICORN|ISOYBEAN)", sym): return "International agri (USD-linked)"
    if re.match(r"(PKWHEAT|WHEAT|MAIZE|LGMRRICE|SUGAR|PALMOLEIN)", sym): return "Local agri"
    return None
def pmex_post(frm, to):
    body = urllib.parse.urlencode({"txtFromDate": frm, "txtEndDate": to}).encode()
    req = urllib.request.Request(PMEX_URL, data=body, headers={"User-Agent": "PakTradeHub/1.0", "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=90) as r: raw = r.read()
    d = json.loads(raw)
    if not isinstance(d, list): raise RuntimeError(f"PMEX returned {str(d)[:60]}")
    return d
def pmex():
    t = time.localtime(); y, m = t.tm_year, t.tm_mon
    # PMEX rejects windows spanning >=3 calendar months, and also fails (HTTP 500, maxJsonLength) on dense windows,
    # so fetch one calendar month per call (4 calls), splitting a month in halves if it still fails.
    mi = y * 12 + m - 1; import calendar
    wins = []
    for k in range(mi - 3, mi + 1):
        yy, mo = k // 12, k % 12 + 1; end = calendar.monthrange(yy, mo)[1]
        wins.append((f"{yy}-{mo:02d}-01", time.strftime("%Y-%m-%d") if k == mi else f"{yy}-{mo:02d}-{end:02d}"))
    raw, done = [], []
    for a_, b_ in wins:
        try: raw += pmex_post(a_, b_); done.append((a_, b_))
        except Exception:
            mid = a_[:8] + "15"
            for a2, b2 in ((a_, mid), (a_[:8] + "16", b_)):
                raw += pmex_post(a2, b2); done.append((a2, b2))
    w1, w2 = done[0], done[-1]; rows = []
    cutoff = time.strftime("%Y-%m-%d", time.localtime(time.time() - 92 * 86400)); frm, to = cutoff, w2[1]
    def num(v):
        try: return float(v)
        except Exception: return None
    for r in raw:
        x = {PMEX_MAP[k]: v for k, v in r.items() if k in PMEX_MAP}
        g = pmex_group(x.get("symbol", ""))
        if not g: continue
        dd, mm, yy = x["date"].split("/"); x["date"] = f"{yy}-{mm}-{dd}"
        for k in ("open", "high", "low", "close", "volume", "settlement", "fx"): x[k] = num(x.get(k))
        x["group"] = g
        if x["date"] >= cutoff: rows.append(x)
    rows.sort(key=lambda r: (r["symbol"], r["date"]))
    last = max(r["date"] for r in rows)
    latest = []
    for sym in sorted({r["symbol"] for r in rows if r["date"] == last}):
        ser = [r for r in rows if r["symbol"] == sym]; cur = ser[-1]; prev = ser[-2] if len(ser) > 1 else None
        ref = lambda r: r["settlement"] or r["close"]
        latest.append({**cur, "prevDate": prev["date"] if prev else None,
                       "chg": (ref(cur) - ref(prev)) if prev and ref(prev) and ref(cur) else None,
                       "chgPct": (ref(cur) / ref(prev) - 1) * 100 if prev and ref(prev) and ref(cur) else None})
    hist = {}
    for r in rows: hist.setdefault(r["symbol"], []).append([r["date"], r["close"], r["settlement"]])
    return {"data": {"latest": latest, "history": hist, "lastDate": last}, "meta": {
        "source": "Pakistan Mercantile Exchange (PMEX) – public OHLC report", "dataset": f"GetOHLC, {len(done)} windows {w1[0]} → {w2[1]} (≤1 month each), trimmed to last 92 days, agri symbols only",
        "period": f"{frm} – {last} (latest trading day {last})", "official_url": PMEX_PAGE, "raw_urls": [PMEX_PAGE], "raw_note": f"POST {PMEX_URL} txtFromDate={w2[0]}&txtEndDate={w2[1]} (one POST per window: " + ", ".join(f"{a}–{b}" for a, b in done) + ")",
        "definition": "Exchange prices of futures/spot contracts, NOT physical mandi rates. PMEX publishes no data licence; used for reference. "
                      "Field mapping (from the report page's own JS): Post_Date→date, Trader_Id→symbol, acc_type→open, Trans_Id→high, Amount→low, Status→close, "
                      "Verified_Date→traded volume, Trader_Name→settlement price, Trans_Date→FX rate. Change = vs the previous trading day's settlement price "
                      "(close if no settlement). Contract units differ per symbol; see the PMEX contract specs."}}

# ---------- PBS SPI weekly ----------
import spi as spimod
def spi_route():
    weeks, latest = spimod.spi(26)
    ok = [w for w in weeks if not w.get("missing")]
    return {"data": {"weeks": weeks, "latest": latest}, "meta": {"source": "Pakistan Bureau of Statistics (PBS): Sensitive Price Indicator, weekly",
        "dataset": "SPI weekly Annex (Appendix-A city prices, Appendix-B fertilizers) + SPI Report (indices, national averages), base 2015-16=100",
        "period": f"{ok[-1]['week']} – {ok[0]['week']} ({len(ok)} weeks found of {len(weeks)} tried)", "official_url": spimod.PAGE,
        "raw_urls": [ok[0]["annex"]["url"], ok[0]["reportUrl"]],
        "definition": "Weekly retail prices of 51 essential items in 50 markets across 17 cities (PBS). Released on Thursdays/Fridays. City figures = MIN/AVG/MAX across markets; national average and % changes are taken from the PBS SPI Report file. An avg of 0 in PBS files (item not available) is shown as n/a."}}

ROUTES = {"imf_monthly": imf_monthly, "imf_partners_x": lambda: imf_partners("XG_FOB_USD"), "imf_partners_m": lambda: imf_partners("MG_CIF_USD"),
          "wdi": wdi, "ct_products_x": lambda: ct_products("X"), "ct_products_m": lambda: ct_products("M"),
          "ct_partners_x": lambda: ct_partners_top("X"), "ct_partners_m": lambda: ct_partners_top("M"), "wits_tariffs": wits_tariffs, "fao_crops": fao_crops, "fao_pp": fao_pp, "mandi": mandi}

class H(SimpleHTTPRequestHandler):
    _src = None
    def do_POST(self):
        # manual forced refresh, localhost only: POST /api/refresh?source=pmex|spi|fpma|faostat
        u = urllib.parse.urlparse(self.path); src = dict(urllib.parse.parse_qsl(u.query)).get("source")
        if u.path != "/api/refresh" or src not in SCHED.SOURCES: return self.send_error(404)
        if self.client_address[0] not in ("127.0.0.1", "::1"): return self.send_error(403)
        return self._json(SCHED.run(src, "manual", "manual"), 200)
    def __init__(self, *a, **k): super().__init__(*a, directory=os.path.join(HERE, "static"), **k)
    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path.startswith("/api/"):
            name = path[5:]; self._src = {"pmex": "pmex", "spi": "spi", "mandi": "fpma", "fao_crops": "faostat", "fao_pp": "faostat"}.get(path[5:])
            if name == "refresh_status": return self._json({s: SCHED.status(s) | {"note": SCHED.note(s)} for s in SCHED.SOURCES}, 200)
            if name == "refresh_log": return self._json(SCHED.log_entries()[-100:], 200)
            q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
            if name == "hs_search":
                t = q.get("q", "").lower().strip()
                res = [{"code": c, "name": n, "parent": p} for c, n, p in hs_all() if t and (c.startswith(t) or t in n.lower())][:30]
                return self._json(res, 200)
            Y = q.get("year", ""); PT = q.get("partner", "0")
            if not re.fullmatch(r"\d{1,4}", PT): return self._json({"error": "bad partner"}, 400)
            dyn = {"imf_partners_x": lambda: (f"imfpx_{Y}", lambda: imf_partners("XG_FOB_USD", Y)), "imf_partners_m": lambda: (f"imfpm_{Y}", lambda: imf_partners("MG_CIF_USD", Y)),
                   "ct_products_x": lambda: (f"ctpx_{Y}_{PT}", lambda: ct_products("X", int(Y), PT)), "ct_products_m": lambda: (f"ctpm_{Y}_{PT}", lambda: ct_products("M", int(Y), PT)),
                   "ct_balance": lambda: (f"ctbal_{Y}", lambda: ct_balance(Y)), "partners": lambda: ("partner_list", partner_list),
                   "imf_monthly": lambda: (f"imfm_{PT}", lambda: imf_monthly(PT)), "imf_annual": lambda: (f"imfa_{PT}", lambda: imf_annual(PT)),
                   "ct_partners_x": lambda: (f"ctqx_{Y}", lambda: ct_partners_top("X", int(Y))), "ct_partners_m": lambda: (f"ctqm_{Y}", lambda: ct_partners_top("M", int(Y))),
                   "wits_tariffs": lambda: (f"wits_{Y}", lambda: wits_tariffs(Y)),
                   "years": lambda: ("years", ct_years),
                   "prod": lambda: (f"prod_{q['flow']}_{q['year']}_{q['parent']}_{PT}", lambda: prod_level(q["flow"], q["year"], q["parent"], PT)),
                   "prod_partners": lambda: (f"pp_{q['flow']}_{q['year']}_{q['code']}", lambda: prod_partners(q["flow"], q["year"], q["code"])),
                   "prod_trend": lambda: (f"pt_{q['flow']}_{q['year']}_{q['code']}_{PT}", lambda: prod_trend(q["flow"], q["code"], q["year"], PT))}
            if name in dyn and (Y or name in ("years", "partners", "imf_monthly", "imf_annual") or name.startswith("prod")):
                try:
                    if not re.fullmatch(r"\d{4}", q.get("year", "2000")) or not re.fullmatch(r"[XM]", q.get("flow", "X")) or not re.fullmatch(r"(TOTAL|\d{2,6})", q.get("parent", q.get("code", "TOTAL"))): raise ValueError("bad params")
                    k, f = dyn[name](); return self._json(cached(k, f), 200)
                except Exception as e: return self._json({"error": str(e)}, 502)
            if name == "spi":
                try: return self._json(cached("spi", spi_route, ttl=24 * 3600), 200)
                except Exception as e: return self._json({"error": str(e)}, 502)
            if name == "pmex":
                try: return self._json(cached("pmex", pmex, ttl=3 * 3600), 200)
                except Exception as e: return self._json({"error": str(e)}, 502)
            if name not in ROUTES: return self.send_error(404)
            try: return self._json(cached(name, ROUTES[name]), 200)
            except Exception as e: return self._json({"error": str(e)}, 502)
        return super().do_GET()
    def _json(self, obj, code):
        if isinstance(obj, dict) and isinstance(obj.get("meta"), dict) and self._src: obj["meta"]["refresh"] = SCHED.note(self._src)
        b = json.dumps(obj).encode(); self.send_response(code); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b)

def warm():
    while True:
        for n, f in ROUTES.items():
            try: cached(n, f)
            except Exception as e: print("warm fail", n, e, flush=True)
        time.sleep(3600)

if __name__ == "__main__":
    import sys
    for st in (sys.stdout, sys.stderr):
        try: st.reconfigure(errors="replace")  # Windows consoles (cp1252) cannot print every character
        except Exception: pass
    SCHED.FNS.update({"pmex": pmex, "spi": spi_route, "mandi": mandi, "fao_crops": fao_crops, "fao_pp": fao_pp}); SCHED.WRITE = write_cache
    threading.Thread(target=warm, daemon=True).start(); threading.Thread(target=SCHED.loop, daemon=True).start()
    ThreadingHTTPServer((os.environ.get("HOST", "0.0.0.0"), int(os.environ.get("PORT", 8080))), H).serve_forever()
