"""Minimal read-only .xlsx reader (standard library only): returns each worksheet as a list of row lists, values only."""
import zipfile, io, re, xml.etree.ElementTree as ET
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "p": "http://schemas.openxmlformats.org/package/2006/relationships"}
def _col(ref):
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group(): n = n * 26 + ord(ch) - 64
    return n - 1
def sheets(b):
    z = zipfile.ZipFile(io.BytesIO(b)); names = z.namelist()
    ss = []
    if "xl/sharedStrings.xml" in names:
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
            ss.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels")).findall("p:Relationship", NS)}
    out = []
    for sh in wb.find("m:sheets", NS).findall("m:sheet", NS):
        t = rels[sh.get("{%s}id" % NS["r"])].lstrip("/"); t = t if t.startswith("xl/") else "xl/" + t
        rows = []
        for row in ET.fromstring(z.read(t)).iter("{%s}row" % NS["m"]):
            ri = int(row.get("r", len(rows) + 1)) - 1
            while len(rows) < ri: rows.append([])
            vals = []
            for i, c in enumerate(row.findall("m:c", NS)):
                ci = _col(c.get("r")) if c.get("r") else len(vals)
                ty = c.get("t"); v = c.find("m:v", NS); x = None
                if ty == "s" and v is not None: x = ss[int(v.text)]
                elif ty == "inlineStr": x = "".join(e.text or "" for e in c.iter("{%s}t" % NS["m"]))
                elif ty == "b" and v is not None: x = v.text == "1"
                elif ty in ("str", "e") and v is not None: x = v.text
                elif v is not None and v.text is not None:
                    f = float(v.text); x = int(f) if f.is_integer() and not re.search(r"[.eE]", v.text) else f
                while len(vals) < ci: vals.append(None)
                vals.append(x)
            rows.append(vals)
        w = max((len(r) for r in rows), default=0)
        out.append([r + [None] * (w - len(r)) for r in rows])
    return out
