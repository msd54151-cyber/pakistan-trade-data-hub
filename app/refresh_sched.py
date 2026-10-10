"""Refresh scheduler (Asia/Karachi). Forced refreshes bypass the cache for PMEX, PBS SPI, FAO FPMA and FAOSTAT; logs to refresh_log.json."""
import json, os, time, datetime, threading
try:  # tzdata may be missing on Windows: PKT/GST have no DST, so fixed offsets are exact
    from zoneinfo import ZoneInfo
    PKT, GST = ZoneInfo("Asia/Karachi"), ZoneInfo("Asia/Dubai")
except Exception:
    PKT = datetime.timezone(datetime.timedelta(hours=5), "PKT"); GST = datetime.timezone(datetime.timedelta(hours=4), "GST")
HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "refresh_log.json"); STATE = os.path.join(HERE, "cache", "sched_state.json")
_L = threading.Lock()
# source -> cache keys refreshed together
SOURCES = {"pmex": ["pmex"], "spi": ["spi"], "fpma": ["mandi"], "faostat": ["fao_crops", "fao_pp"]}
# (source, job, weekdays Mon=0, HH, MM, is_retry)
JOBS = [("pmex", "daily", (0, 1, 2, 3, 4), 18, 30, False), ("pmex", "retry", (0, 1, 2, 3, 4), 21, 0, True),
        ("spi", "thursday", (3,), 19, 0, False), ("spi", "retry", (4,), 10, 0, True),
        ("fpma", "weekly", (0,), 10, 0, False), ("faostat", "weekly", (0,), 10, 0, False)]
FNS = {}       # cache key -> fetch fn (set by server)
WRITE = None   # fn(key, value) writes cache file

def _atomic(p, obj):
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(obj, f, indent=1)
    os.replace(tmp, p)
def _rd(p, d):
    try:
        with open(p, encoding="utf-8") as f: return json.load(f)
    except Exception: return d
def latest_of(key, v):
    d = v.get("data")
    if key == "pmex": return d["lastDate"]
    if key == "spi": return next((w["week"] for w in d["weeks"] if not w.get("missing")), None)
    if key == "mandi": return max(x["date"] for x in d)
    if key == "fao_pp": return str(max(int(p[0]) for x in d.values() for p in x["points"]))
    if key == "fao_crops":
        import re; return (re.findall(r"\d{4}", str(v["meta"].get("period"))) or [None])[-1]
    return v["meta"].get("period")
def log_entries(): return _rd(LOG, [])

def run(source, job="manual", trigger="manual"):
    now = datetime.datetime.now(PKT); out = {"time_pkt": now.strftime("%Y-%m-%d %H:%M:%S PKT"),
           "time_uae": now.astimezone(GST).strftime("%Y-%m-%d %H:%M:%S GST"), "source": source, "job": job, "trigger": trigger}
    prev = {k: last_latest(k) for k in SOURCES[source]}; lat = {}
    try:
        for k in SOURCES[source]:
            v = FNS[k](); WRITE(k, v); lat[k] = latest_of(k, v)
        out.update(success=True, latest=lat, new_period=any(str(lat[k]) != str(prev[k]) for k in lat))
    except Exception as e:
        out.update(success=False, latest=lat or None, error=str(e)[:300])
    with _L:
        L = log_entries(); L.append(out)
        _atomic(LOG, L[-500:])
    return out

def last_latest(key):
    for e in reversed(log_entries()):
        if e.get("success") and e.get("latest") and key in e["latest"]: return e["latest"][key]
    return None

def _slots(job, frm, days=10):
    s, j, wd, hh, mm, _ = job
    for i in range(days):
        d = (frm + datetime.timedelta(days=i)).date()
        if d.weekday() in wd:
            t = datetime.datetime(d.year, d.month, d.day, hh, mm, tzinfo=PKT)
            if t > frm: yield t
def next_run(source):
    now = datetime.datetime.now(PKT)
    t = min(next(_slots(j, now)) for j in JOBS if j[0] == source and not j[5])
    r = [next(_slots(j, now)) for j in JOBS if j[0] == source and j[5]]
    return t, (min(r) if r else None)
def status(source):
    last = next((e for e in reversed(log_entries()) if e["source"] == source), None)
    nx, rt = next_run(source)
    return {"last": last, "next_pkt": nx.strftime("%a %Y-%m-%d %H:%M PKT"), "next_uae": nx.astimezone(GST).strftime("%a %Y-%m-%d %H:%M GST"),
            "retry_pkt": rt.strftime("%a %H:%M PKT") if rt else None}
def note(source):
    s = status(source); l = s["last"]
    lt = (f"Last refreshed {l['time_pkt']} ({l['time_uae'][11:16]} GST), {'OK' if l['success'] else 'FAILED: ' + l.get('error', '')}, latest {', '.join(str(v) for v in (l.get('latest') or {}).values()) or 'n/a'}"
          if l else "Last refreshed: no scheduled/forced run logged yet")
    return lt + f" · Next scheduled refresh {s['next_pkt']} ({s['next_uae'][-9:]})" + (f", retry {s['retry_pkt']} if no new data" if s["retry_pkt"] else "")

def _need_retry(source, slot):
    """Retry only if the main run of the same cycle did not produce a new period."""
    today = slot.date()
    if source == "pmex":
        return str(last_latest("pmex")) < today.isoformat()
    if source == "spi":
        thu = today - datetime.timedelta(days=(today.weekday() - 3) % 7)
        return str(last_latest("spi")) < thu.isoformat()
    return True

def loop():
    while True:
        try:
            now = datetime.datetime.now(PKT); st = _rd(STATE, {})
            for job in JOBS:
                s, j, wd, hh, mm, retry = job
                t = datetime.datetime(now.year, now.month, now.day, hh, mm, tzinfo=PKT); sid = f"{s}:{j}:{now.date()}"
                # fire once per slot, within 3h of the slot time (catch-up if the server was down briefly)
                if now.weekday() in wd and t <= now < t + datetime.timedelta(hours=3) and sid not in st:
                    st[sid] = now.isoformat()
                    _atomic(STATE, st)
                    if retry and not _need_retry(s, t): continue
                    print("scheduled refresh", s, j, run(s, j, "schedule"), flush=True)
        except Exception as e: print("scheduler error", e, flush=True)
        time.sleep(30)
