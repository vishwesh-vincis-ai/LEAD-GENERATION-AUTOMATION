"""Audit → rank → verify → re-rank → draft outreach. Usage: python -m leadengine.run [data/raw/austin_tx.json]

Only verified leads get an outreach draft. An unverified lead is marked "verify before outreach".
"""
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .audit import InvalidScrape, audit
from .outreach import draft
from .score import fit, pain, rank
from .verify import slug, verify

OUT = Path(__file__).parent.parent / "data"
DEMO_SLOTS = {"dental": 2, "fitness coach": 1}   # best verified leads per niche get a demo bot


def main(raw_path: str) -> dict:
    raw = json.loads(Path(raw_path).read_text())
    leads, rejected = [], []
    for s in raw["scrapes"]:
        try:
            leads.append(audit(s))
        except InvalidScrape as e:
            rejected.append({"url": s["url"], "reason": str(e), "model_output": s["extracted"]["business_name"]})

    first_pass = {l.url: (i + 1, rank(l)) for i, l in enumerate(sorted(leads, key=rank, reverse=True))}
    checks = {l.url: verify(l) for l in leads}
    leads.sort(key=lambda l: (checks[l.url]["verified"], rank(l)), reverse=True)

    taken = {k: 0 for k in DEMO_SLOTS}
    demo = set()
    for lead in leads:
        if checks[lead.url]["verified"] and taken.get(lead.niche, 99) < DEMO_SLOTS.get(lead.niche, 0):
            taken[lead.niche] += 1
            demo.add(lead.url)

    rows = []
    for i, lead in enumerate(leads):
        v = checks[lead.url]
        rows.append({
            "rank": i + 1, "first_pass_rank": first_pass[lead.url][0], "first_pass_score": first_pass[lead.url][1],
            "score": rank(lead), "pain": pain(lead), "fit": fit(lead), "slug": slug(lead.url), **asdict(lead),
            "verification": v, "demo": lead.url in demo,
            "outreach": draft(lead, demo_ready=lead.url in demo) if v["verified"] else None,
        })
    result = {"query": raw["query"], "collected_at": raw["collected_at"], "leads": rows, "rejected": rejected}
    (OUT / "leads.json").write_text(json.dumps(result, indent=2))

    print(f"{'#':>2} {'was':>3}  {'score':>5}  {'pain':>4}  {'fit':>3}  {'niche':<13} name")
    for r in rows:
        v = r["verification"]
        note = (f"verified, {len(v['dropped'])} gap(s) dropped" if v["verified"] else "verify before outreach")
        note += "  → demo bot" if r["demo"] else ""
        print(f"{r['rank']:>2} {r['first_pass_rank']:>3}  {r['score']:>5}  {r['pain']:>4}  {r['fit']:>3}  "
              f"{r['niche']:<13} {r['name']:<28} {note}")
    for r in rejected:
        print(f"REJECTED {r['url']}: {r['reason']}")
    return result


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(OUT / "raw/austin_tx.json"))
