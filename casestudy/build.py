"""Build the case-study page from data/leads.json and data/demos.json.

Usage: python -m casestudy.build   ->  casestudy/index.html
Every number on the page is computed from the two JSON files. The only hand-written inputs are GRADES
(each demo turn checked against the lead's own page) and DIAGNOSIS (measured against the running brain).
"""
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
OUT = Path(__file__).parent / "index.html"

# One grade per demo turn, checked by hand against data/sites/<slug>/*.md.
# ok = answered and the answer matches the page; handoff = the page doesn't say, so handing off is right;
# miss = the page answers it and the bot didn't; contact = the prospect leaving name + phone.
GRADES = {
    "mclanefamilydental": [
        ("ok", 'Page: "We Are accepting new patients."'),
        ("ok", 'Page: "Fri. Closed." The first recording missed this; see "Found and fixed" below.'),
        ("ok", 'Page: "Sedation Dentistry" under Featured Services.'),
        ("handoff", "No prices on the page, so the bot hands off and asks for details."),
        ("contact", "Name and phone captured in one turn."),
    ],
    "hillcountryfamilydental": [
        ("ok", 'Page: "$49 Emergency Exam & X-ray".'),
        ("ok", "Quoted from the FAQ entry of the same name."),
        ("ok", "Quoted from the FAQ, including the oral-sedation exception."),
        ("handoff", "Invisalign isn't on the FAQ page."),
        ("contact", "Name and phone captured in one turn."),
    ],
    "austinsimplyfit": [
        ("ok", 'Page: "FREE consultation and assessment".'),
        ("ok", 'Page: "built around focused 30-minute sessions".'),
        ("ok", 'Page: "There are no memberships or long-term contracts."'),
        ("handoff", 'Page says "packages of 5, 10, or 20" but gives no price.'),
        ("contact", "Name and phone captured in one turn."),
    ],
}

# Measured 2026-10-01 against the brain on NVIDIA (llama-nemotron-embed-vl-1b-v2, 1024-d), McLane tenant,
# before the fix. The "before" answer is from the first recording of data/demos.json.
DIAGNOSIS = {
    "before": "I don't have that information right now, so I'll connect you with our team. "
              "Could you share your name and phone number?",
    "after": "No, we are closed on Fridays. [1]",
    "tests": "13 new brain tests (8 abbreviation cases, 1 schedule label, 4 hours questions); 38/38 brain tests pass",
    "evals": "Brain evals 53/54 before and after the fix (3 hours questions added; the one miss is x02, unchanged)",
    "chunk": "Office Schedule",
    "body": "Mon. 8am – 5pm. Tue. 8am – 5pm. Wed. 8am – 5pm. Thu. 8am – 5pm. Fri. Closed. Sat. Closed. Sun. Closed.",
    "threshold": 0.30,
    "probes": [("Are you open on Fridays?", 0.282, 0.102), ("What are your hours?", 0.289, 0.154)],
}

NICHE_LABEL = {"dental": "dental practices", "fitness coach": "fitness coaches"}
VERDICT_LABEL = {"ok": "Correct", "handoff": "Right to hand off", "miss": "Missed", "contact": "Lead captured"}


def h(s) -> str:
    return escape(str(s))


def bot_html(text: str) -> str:
    return "<br>".join(h(line) for line in text.split("\n") if line.strip())


def build() -> str:
    leads_doc = json.loads((DATA / "leads.json").read_text())
    demos = json.loads((DATA / "demos.json").read_text())
    leads = leads_doc["leads"]
    by_slug = {l["slug"]: l for l in leads}

    graded = [(d, t, GRADES[d["slug"]][i]) for d in demos for i, t in enumerate(d["turns"])]
    count = lambda v: sum(1 for *_, g in graded if g[0] == v)
    ok, miss, handoff, contact = count("ok"), count("miss"), count("handoff"), count("contact")
    answerable = ok + miss
    verified = [l for l in leads if l["verification"]["verified"]]
    dropped = sum(len(l["verification"]["dropped"]) for l in leads)
    corrections = sum(len(l.get("corrections") or []) for l in leads)
    moved = [l for l in leads if l["rank"] != l["first_pass_rank"]]
    q = leads_doc["query"]

    # Leads table
    rows = []
    for l in leads:
        v = l["verification"]
        status = ('<span class="pill pill-ok">Verified</span>' if v["verified"]
                  else '<span class="pill pill-wait">Homepage only</span>')
        move = ""
        if l["rank"] != l["first_pass_rank"]:
            arrow = "▼" if l["rank"] > l["first_pass_rank"] else "▲"
            move = f'<span class="move">{arrow} was #{l["first_pass_rank"]}</span>'
        gaps = "".join(f"<li>{h(g['headline'])}</li>" for g in l["gaps"])
        drops = "".join(f'<li class="dropped">Dropped: {h(d["gap"].replace("_", " "))}. '
                        f'Deeper page: “{h(d["because"])}”</li>' for d in v["dropped"])
        demo = '<span class="pill pill-demo">Demo bot</span>' if l["demo"] else ""
        rows.append(f"""
        <tr>
          <td class="num">{l["rank"]}{move}</td>
          <td><strong>{h(l["name"])}</strong><span class="sub">{h(l["niche"])} · {h(l["url"].split("//")[1].strip("/"))}</span></td>
          <td class="num score"><span class="bar" style="--w:{l["score"]:.0f}%"></span>{l["score"]:.0f}</td>
          <td><ul class="gaps">{gaps}{drops}</ul></td>
          <td class="tags">{status}{demo}</td>
        </tr>""")

    # Transcripts
    convos = []
    for d in demos:
        lead = by_slug[d["slug"]]
        turns = []
        for i, t in enumerate(d["turns"]):
            verdict, note = GRADES[d["slug"]][i]
            cites = "".join(f'<span class="cite">{h(c)}</span>' for c in t["citations"])
            turns.append(f"""
            <li class="turn v-{verdict}">
              <p class="u"><span class="who">Prospect</span>{h(t["user"])}</p>
              <p class="b"><span class="who">Bot</span>{bot_html(t["bot"])}</p>
              <p class="meta"><span class="verdict">{VERDICT_LABEL[verdict]}</span>{cites}
                 <span class="state">{h(t["state"])}</span></p>
              <p class="note">{h(note)}</p>
            </li>""")
        n_ok = sum(1 for v, _ in GRADES[d["slug"]] if v in ("ok", "handoff", "contact"))
        convos.append(f"""
        <article class="convo" id="{h(d["slug"])}">
          <header>
            <h3>{h(d["name"])}</h3>
            <p class="sub">Lead #{lead["rank"]} · loaded with {h(", ".join(d["pages"]))} ·
               {n_ok}/{len(d["turns"])} turns right</p>
          </header>
          <ol class="turns">{"".join(turns)}</ol>
        </article>""")

    probes = "".join(
        f"<tr><td>{h(q_)}</td><td class='num'>{s:.3f}</td><td class='num'>{nxt:.3f}</td>"
        f"<td class='num'>{DIAGNOSIS['threshold']:.2f}</td><td><span class='pill pill-miss'>Filtered out before fix</span></td></tr>"
        for q_, s, nxt in DIAGNOSIS["probes"])

    rejected = "".join(
        f"<li><strong>{h(r['url'].split('//')[1].strip('/'))}</strong>: {h(r['reason'])}. "
        f"The model still returned “{h(r['model_output'])}”.</li>" for r in leads_doc["rejected"])

    tpl = (Path(__file__).parent / "template.html").read_text()
    return (tpl
            .replace("{{CITY}}", h(q["city"]))
            .replace("{{NICHES}}", h(" and ".join(NICHE_LABEL.get(n, n) for n in q["niches"])))
            .replace("{{DATE}}", h(leads_doc["collected_at"]))
            .replace("{{N_LEADS}}", str(len(leads)))
            .replace("{{N_VERIFIED}}", str(len(verified)))
            .replace("{{N_DEMOS}}", str(len(demos)))
            .replace("{{N_DROPPED}}", str(dropped))
            .replace("{{N_CORRECTIONS}}", str(corrections))
            .replace("{{N_REJECTED}}", str(len(leads_doc["rejected"])))
            .replace("{{N_TURNS}}", str(len(graded)))
            .replace("{{OK}}", str(ok))
            .replace("{{ANSWERABLE}}", str(answerable))
            .replace("{{MISS}}", str(miss))
            .replace("{{HANDOFF}}", str(handoff))
            .replace("{{CONTACT}}", str(contact))
            .replace("{{MOVED}}", h(", ".join(f'{l["name"]} (#{l["first_pass_rank"]} → #{l["rank"]})' for l in moved)))
            .replace("{{REJECTED}}", rejected)
            .replace("{{LEAD_ROWS}}", "".join(rows))
            .replace("{{CONVOS}}", "".join(convos))
            .replace("{{DIAG_BODY}}", h(DIAGNOSIS["body"]))
            .replace("{{DIAG_PROBES}}", probes)
            .replace("{{DIAG_BEFORE}}", h(DIAGNOSIS["before"]))
            .replace("{{DIAG_AFTER}}", h(DIAGNOSIS["after"]))
            .replace("{{DIAG_TESTS}}", h(DIAGNOSIS["tests"]))
            .replace("{{DIAG_EVALS}}", h(DIAGNOSIS["evals"]))
            .replace("{{THRESHOLD}}", f"{DIAGNOSIS['threshold']:.2f}"))


if __name__ == "__main__":
    OUT.write_text(build())
    print(f"wrote {OUT}")
