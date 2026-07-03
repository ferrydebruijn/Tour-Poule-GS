#!/usr/bin/env python3
"""
Leest formulier-inzendingen in, matcht de renner-namen op de officiele startlijst,
voert de loting uit (5 extra renners per persoon uit de resterende pool) en schrijft
de definitieve poule (vergrendeld) in het poule-state blok van index.html.

Gebruik:
  python3 publiceer_loting.py --submissions submissions.json
  (optioneel: --nloting 5 --seed 42 --dry-run)

submissions.json = JSON-lijst, oudste eerst, bijv.:
[
  {"deelnemer":"Gert-Jan Hermans","renners":["Tiesj Benoot","Cees Bol","Daan Hoole","Lars Craps","Biniam Girmay"]},
  {"deelnemer":"Ferry","renners":["Tadej Pogačar","Mathieu van der Poel","Mads Pedersen","Thymen Arensman","Olav Kooij"]}
]
Bij dubbele naam telt de LAATSTE inzending.
"""
import argparse, json, re, sys, random, difflib

FILE = "index.html"
START = '<script id="poule-state" type="application/json">'
END = '</script>'

def load_html():
    with open(FILE, encoding="utf-8") as f:
        return f.read()

def riders_from_html(html):
    m = re.search(r'const RIDERS\s*=\s*\[(.*?)\]\.map', html, re.S)
    if not m:
        sys.exit("RIDERS-lijst niet gevonden in index.html")
    names = re.findall(r'\["([^"]+)","[^"]+","[^"]+"\]', m.group(1))
    if not names:
        sys.exit("Kon geen renner-namen parsen")
    return names

def extract_state(html):
    i = html.find(START)
    j = html.find(END, i + len(START))
    raw = html[i+len(START):j].strip()
    try:
        data = json.loads(raw)
    except Exception:
        data = {}
    if data.get("__seed__"):
        data = {}
    return data, i+len(START), j

def match_name(name, riders, lower_map):
    n = name.strip()
    if not n: return None, None
    if n in riders: return n, "exact"
    if n.lower() in lower_map: return lower_map[n.lower()], "case"
    cand = difflib.get_close_matches(n, riders, n=1, cutoff=0.72)
    if cand: return cand[0], "fuzzy"
    return n, "GEEN MATCH"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--submissions", required=True)
    p.add_argument("--nloting", type=int, default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()

    html = load_html()
    riders = riders_from_html(html)
    lower_map = {r.lower(): r for r in riders}
    state, s0, s1 = extract_state(html)

    cfg = state.get("config") or {}
    inleg   = cfg.get("inleg", 20)
    nKeuze  = cfg.get("nKeuze", 5)
    nLoting = a.nloting if a.nloting is not None else cfg.get("nLoting", 5)
    etappePct = cfg.get("etappePct", 71.4)

    subs = json.load(open(a.submissions, encoding="utf-8"))
    # dedupe op naam (laatste wint), volgorde = eerste keer gezien
    order, byname = [], {}
    for s in subs:
        nm = (s.get("deelnemer") or "").strip()
        if not nm: continue
        key = nm.lower()
        if key not in byname: order.append(key)
        byname[key] = s  # laatste wint
    deelnemers, keuzes, warnings = [], {}, []
    for key in order:
        s = byname[key]
        nm = (s.get("deelnemer") or "").strip()
        deelnemers.append(nm)
        picks = []
        for rr in (s.get("renners") or [])[:nKeuze]:
            matched, how = match_name(rr, riders, lower_map)
            if how == "GEEN MATCH":
                warnings.append(f"  ! '{rr}' (van {nm}) niet herkend — laten staan, scoort niet automatisch")
            elif how in ("case","fuzzy"):
                warnings.append(f"  ~ '{rr}' -> '{matched}' ({how}) voor {nm}")
            picks.append(matched)
        keuzes[nm] = picks

    # loting: pool = renners die niemand koos
    chosen = set()
    for nm in deelnemers:
        for r in keuzes[nm]:
            if r: chosen.add(r)
    pool = [r for r in riders if r not in chosen]
    rng = random.Random(a.seed)
    rng.shuffle(pool)
    loting = {nm: [] for nm in deelnemers}
    idx = 0
    for k in range(nLoting):
        for nm in deelnemers:
            if idx < len(pool):
                loting[nm].append(pool[idx]); idx += 1

    state.update({
        "config": {"inleg": inleg, "nKeuze": nKeuze, "nLoting": nLoting, "etappePct": etappePct},
        "deelnemers": deelnemers,
        "keuzes": keuzes,
        "loting": loting,
        "aangemeld": deelnemers[:],
        "gelockt": True,
    })
    state.setdefault("uitslagen", {})
    state.setdefault("eind", {"gc":["","","","",""],"punten":["","",""],"berg":["","",""],"rodeLantaarn":[""]})
    state.setdefault("weights", {"rit1":4,"rit2":2,"rit3":1,"rodeLantaarn":1,"geleTrui":4,"groeneTrui":2,"bolletjes":2,"lantaarnGC":1,"besteNL":2})

    print(f"Deelnemers: {len(deelnemers)} | renners/persoon: {nKeuze} gekozen + {nLoting} geloot | pot €{inleg*len(deelnemers)}")
    for nm in deelnemers:
        print(f"  {nm}: gekozen={keuzes[nm]} | geloot={loting[nm]}")
    if warnings:
        print("LET OP — naam-opmerkingen:")
        print("\n".join(warnings))
    if idx < nLoting*len(deelnemers):
        print(f"WAARSCHUWING: pool te klein, {nLoting*len(deelnemers)-idx} lotingsplekken niet gevuld")

    if a.dry_run:
        print("(dry-run: niets weggeschreven)"); return

    new_json = json.dumps(state, ensure_ascii=False, indent=1)
    json.loads(new_json)
    with open(FILE, "w", encoding="utf-8") as f:
        f.write(html[:s0] + "\n" + new_json + "\n" + html[s1:])
    print("index.html geschreven — poule gepubliceerd en vergrendeld.")

if __name__ == "__main__":
    main()
