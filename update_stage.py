#!/usr/bin/env python3
"""
Werkt het ingebedde JSON-blok (id="poule-state") in index.html bij.
Gebruik:
  Etappe-uitslag zetten:
    python3 update_stage.py --stage 3 \
        --rit1 "Tadej Pogačar" --rit2 "..." --rit3 "..." \
        --rodeLantaarn "..." --geleTrui "..." --groeneTrui "..." \
        --bolletjes "..." --lantaarnGC "..." --besteNL "..."
  Eindklassement (na etappe 21) er los bij:
    ... --eind-gc "a;b;c;d;e" --eind-punten "a;b;c" --eind-berg "a;b;c" --eind-lantaarn "x"
  Deelnemers/loting inladen uit een geëxporteerd JSON-bestand (behoudt uitslagen):
    python3 update_stage.py --roster tourpoule_data.json

Alleen meegegeven velden worden gewijzigd; de rest blijft staan.
"""
import argparse, json, re, sys

FILE = "index.html"
START = '<script id="poule-state" type="application/json">'
END = '</script>'
CATS = ["rit1","rit2","rit3","rodeLantaarn","geleTrui","groeneTrui","bolletjes","lantaarnGC","besteNL"]

def load_html():
    with open(FILE, encoding="utf-8") as f:
        return f.read()

def extract_state(html):
    i = html.find(START)
    if i < 0: sys.exit("poule-state blok niet gevonden")
    j = html.find(END, i + len(START))
    if j < 0: sys.exit("einde poule-state blok niet gevonden")
    raw = html[i+len(START):j].strip()
    try:
        data = json.loads(raw)
    except Exception:
        data = {}
    if data.get("__seed__"):
        data = {}
    return data, i+len(START), j

def default_eind():
    return {"gc":["","","","",""],"punten":["","",""],"berg":["","",""],"rodeLantaarn":[""]}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stage", type=int)
    for c in CATS:
        p.add_argument("--"+c, default=None)
    p.add_argument("--eind-gc", default=None)
    p.add_argument("--eind-punten", default=None)
    p.add_argument("--eind-berg", default=None)
    p.add_argument("--eind-lantaarn", default=None)
    p.add_argument("--roster", default=None)
    a = p.parse_args()

    html = load_html()
    state, s0, s1 = extract_state(html)
    state.setdefault("uitslagen", {})
    state.setdefault("eind", default_eind())

    # Roster inladen (behoudt uitslagen/eind die al gezet zijn)
    if a.roster:
        with open(a.roster, encoding="utf-8") as f:
            imp = json.load(f)
        for k in ("deelnemers","keuzes","loting","config","weights","gelockt"):
            if k in imp:
                state[k] = imp[k]
        # neem ook uitslagen/eind uit import als die er zijn en lokaal nog leeg
        print("Roster ingeladen:", len(state.get("deelnemers",[])), "deelnemers")

    # Etappe-uitslag
    if a.stage is not None:
        key = str(a.stage)
        cur = state["uitslagen"].get(key, {})
        for c in CATS:
            v = getattr(a, c)
            if v is not None:
                cur[c] = v.strip()
        state["uitslagen"][key] = cur
        print(f"Etappe {a.stage} bijgewerkt:", {k:v for k,v in cur.items() if v})

    # Eindklassement
    def split(s): return [x.strip() for x in s.split(";")]
    if a.eind_gc is not None:      state["eind"]["gc"] = split(a.eind_gc)
    if a.eind_punten is not None:  state["eind"]["punten"] = split(a.eind_punten)
    if a.eind_berg is not None:    state["eind"]["berg"] = split(a.eind_berg)
    if a.eind_lantaarn is not None:state["eind"]["rodeLantaarn"] = [a.eind_lantaarn.strip()]
    if any(x is not None for x in (a.eind_gc,a.eind_punten,a.eind_berg,a.eind_lantaarn)):
        print("Eindklassement bijgewerkt")

    new_json = json.dumps(state, ensure_ascii=False, indent=1)
    json.loads(new_json)  # validatie
    new_html = html[:s0] + "\n" + new_json + "\n" + html[s1:]
    with open(FILE, "w", encoding="utf-8") as f:
        f.write(new_html)
    print("index.html geschreven. Deelnemers:", len(state.get("deelnemers",[])),
          "| etappes met uitslag:", len(state.get("uitslagen",{})))

if __name__ == "__main__":
    main()
