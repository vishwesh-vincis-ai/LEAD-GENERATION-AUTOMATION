"""Build a demo bot per selected lead on the Business Brain and record a real conversation with it.

Each lead becomes its own tenant in the brain (business_id = site slug), loaded only with that lead's pages.
Usage: python -m leadengine.demo   (needs the brain API running; BRAIN_URL defaults to http://localhost:8000)
"""
import json
import os
from pathlib import Path

import httpx

from .verify import SITES

BRAIN = os.getenv("BRAIN_URL", "http://localhost:8000")
DATA = Path(__file__).parent.parent / "data"

# What a real prospect would ask. The last question per lead is one the site does not answer.
SCRIPTS = {
    "mclanefamilydental": ["Are you accepting new patients?", "Are you open on Fridays?",
                           "Do you offer sedation dentistry?", "How much is a cleaning without insurance?",
                           "Maria Lopez, 512 555 0142"],
    "hillcountryfamilydental": ["How much is an emergency exam?", "Do root canals hurt?",
                                "Can I drive myself home after a root canal?", "Do you offer Invisalign?",
                                "James Carter 512-555-0187"],
    "austinsimplyfit": ["Is the first consultation free?", "How long are the training sessions?",
                        "Do I have to sign a long-term contract?", "How much does a 10-session package cost?",
                        "Priya Shah, 512 555 0119"],
}


def run() -> list[dict]:
    leads = json.loads((DATA / "leads.json").read_text())["leads"]
    out = []
    for lead in (l for l in leads if l["demo"]):
        slug = lead["slug"]
        files = [str(p.resolve()) for p in sorted((SITES / slug).glob("*.md"))]
        ingest = httpx.post(f"{BRAIN}/ingest", json={"business_id": slug, "business_name": lead["name"],
                                                    "sources": files}, timeout=300).json()
        turns = []
        for msg in SCRIPTS[slug]:
            r = httpx.post(f"{BRAIN}/chat", json={"business_id": slug, "session_id": f"demo-{slug}",
                                                  "message": msg}, timeout=120).json()
            turns.append({"user": msg, "bot": r["reply"], "state": r["state"],
                          "citations": [c["section"] for c in r.get("citations", [])]})
        out.append({"slug": slug, "name": lead["name"], "niche": lead["niche"], "pages": [Path(f).name for f in files],
                    "ingest": ingest, "turns": turns})
        print(f"\n== {lead['name']}  ({ingest})")
        for t in turns:
            print(f"  U: {t['user']}\n  B: {t['bot'][:150]!r}  [{t['state']}]")
    (DATA / "demos.json").write_text(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    run()
