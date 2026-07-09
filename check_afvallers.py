#!/usr/bin/env python3
"""
Markeert uitgevallen renners en lot automatisch een vervanger voor elke
getroffen deelnemer (renner die nog in koers is en die niemand anders heeft).
Dubbel-veilig: per reeds-gecompenseerde uitvaller wordt maar één keer geloot.

Gebruik (in de repo-map, naast index.html):
  python3 check_afvallers.py --abandons "Arnaud De Lie;Alex Molenaar;Cian Uijtdebroeks;..."
Optioneel: --seed 123 (voor reproduceerbare loting), --dry-run

--abandons = de VOLLEDIGE actuele lijst van renners die de Tour verlaten hebben
(opgave/uitsluiting/DNS/OTL), namen zoals in de media; het script matcht ze op
de officiële startlijst in index.html.
"""
import argparse, json, re, sys, random, difflib

FILE = "index.html"
START = '<script id="poule-state" type="application/json">'
END = '</script>'

def load_html():
    with open(FILE, encoding="utf-8") as f: return f.read()

def riders_from_html(html):
    m = re.search(r'const RIDERS\s*=\s*\[(.*?)\]\.map', html, re.S)
    if not m: sys.exit("RIDERS niet gevonden")
    return re.findall(r'\["([^"]+)","[^"]+","[^"]+"\]', m.group(1))

def match(name, riders, lower):
    n=name.strip()
    if not n: return None
    if n in riders: return n
    if n.lower() in lower: return lower[n.lower()]
    c=difflib.get_close_matches(n, riders, n=1, cutoff=0.82)
    return c[0] if c else None

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--abandons", required=True)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    a=p.parse_args()

    html=load_html()
    riders=riders_from_html(html)
    lower={r.lower():r for r in riders}
    i=html.find(START); j=html.find(END,i+len(START))
    state=json.loads(html[i+len(START):j])

    # abandon-namen matchen
    raw=[x.strip() for x in a.abandons.split(";") if x.strip()]
    ab=[]
    for x in raw:
        mm=match(x,riders,lower)
        if mm: ab.append(mm)
        else: print(f"  ! afvaller '{x}' niet herkend op startlijst — overgeslagen")
    uit=set(state.get("uitgevallen",[])) | set(ab)
    state["uitgevallen"]=sorted(uit)

    # eigenaren (keuze + loting + reeds gelote vervangers)
    owners={}
    for d in state["deelnemers"]:
        for r in state["keuzes"].get(d,[])+state["loting"].get(d,[])+state.get("vervangers",{}).get(d,[]):
            if r: owners.setdefault(r,[]).append(d)

    vervangen=set(state.get("vervangen_voor",[]))   # afvallers waarvoor al vervangen is
    pool=[r for r in riders if r not in owners and r not in uit]
    rng=random.Random(a.seed); rng.shuffle(pool)
    state.setdefault("vervangers",{})

    idx=0; nieuw=[]
    for rider in ab:
        if rider in owners and rider not in vervangen:
            for owner in owners[rider]:      # elke eigenaar krijgt een vervanger
                if idx>=len(pool): print("  ! pool leeg, geen vervanger meer beschikbaar"); break
                pick=pool[idx]; idx+=1
                state["vervangers"].setdefault(owner,[]).append(pick)
                nieuw.append((owner,rider,pick))
            vervangen.add(rider)
    state["vervangen_voor"]=sorted(vervangen)

    if nieuw:
        print("Nieuwe vervangers geloot:")
        for o,r,pk in nieuw: print(f"  {o}: {r} (uit) -> {pk}")
    else:
        print("Geen nieuwe uitvallers met eigenaar; niets te vervangen.")

    if a.dry_run:
        print("(dry-run: niets weggeschreven)"); return
    newjson=json.dumps(state, ensure_ascii=False, indent=1); json.loads(newjson)
    with open(FILE,"w",encoding="utf-8") as f:
        f.write(html[:i+len(START)]+"\n"+newjson+"\n"+html[j:])
    print("index.html bijgewerkt.")

if __name__=="__main__":
    main()
