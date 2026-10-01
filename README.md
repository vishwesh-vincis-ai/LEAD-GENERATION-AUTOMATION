# Lead Engine (Project 3)

Input: a niche and a city. Output: ranked leads, each with an evidence-backed audit, an outreach draft that cites
the real gap, and a demo bot preloaded with that business's own website, running on the
[Business Brain](https://github.com/vishwesh-vincis-ai/LANGFLOW-BRAIN).

**First run: Austin, TX · dental practices and fitness coaches · 11 independent businesses.**

## Pipeline
```
search + scrape ──► validate ──► audit ──► rank ──► verify ──► re-rank ──► outreach draft ──► demo bot
 (Firecrawl)       reject 403s   links are   pain×fit   deep pages     verified      cites only         one brain tenant
                   + invented    facts, model           drop false     leads only    verified gaps      per lead
                   businesses    output is a claim      gaps
```

| Step | Code | What it guarantees |
|---|---|---|
| Validate | `leadengine/audit.py` | A page that wasn't actually read (non-200, placeholder values) never becomes a lead |
| Audit | `leadengine/audit.py` | Booking, texting and price signals come from links and dollar amounts; model claims the links contradict are logged as corrections |
| Score | `leadengine/score.py` | Pain (what the gaps cost) × fit (reachable, real premises, breadth of services) |
| Verify | `leadengine/verify.py` | Before outreach, every gap is re-checked against deeper pages; contradicted gaps are dropped, confirmed ones get a quote |
| Outreach | `leadengine/outreach.py` | Draft only. States verified gaps, names one checkable fact from their site, keeps CAN-SPAM sender/address/opt-out placeholders |
| Demo | `leadengine/demo.py` | Each selected lead becomes its own brain tenant with only its own pages |

## What the first run caught
These are the reasons the verify and validate steps exist. Each is a regression test in `tests/test_pipeline.py`.

- **Invented business.** coolcreekfamilydental.com returned HTTP 403. The extraction model still returned
  "Example Business Name, 123 Main St, 20% off first service". Rejected.
- **"Make appointment" isn't booking.** The model read McLane's button as online booking. The link goes to a
  contact page. Corrected; the gap stays.
- **"Short call" isn't texting.** The model credited Motive Training with a text/chat option from the words "short call". Corrected.
- **Homepage-only audits get it wrong.** Outright Fitness looked like "no prices, request form only". Its
  training page lists $125 / $65 drop-ins and sends buyers "straight to the scheduler". Verify dropped both
  gaps and Outright fell from #3 to #5. An email claiming those gaps would have been false.
- **A fee isn't a price list.** South Austin's "$50 cancellation fee" doesn't clear the no-prices gap.

## Results (Austin, TX)
| # | Lead | Niche | Score | Verified gaps | Demo |
|---|---|---|---|---|---|
| 1 | McLane Family Dental | dental | 84 | no scheduler, no texting, closed Fri–Sun, no prices, no FAQ | ✓ |
| 2 | Hill Country Family Dental | dental | 70 | request form only, no texting, closed Fri–Sun | ✓ |
| 3 | South Austin Family Dental | dental | 63 | "Please call 512-280-1117 to begin the process of becoming a new patient", no texting, no prices, no FAQ | |
| 4 | Austin Simply Fit | fitness | 51 | request form ("A member of our team will reach out…"), no texting, no prices | ✓ |
| 5 | Outright Fitness | fitness | 46 | no FAQ (2 false gaps dropped) | |

Leads 6–11 are audited from their homepage only and marked *verify before outreach*. Full output: `data/leads.json`.

## Run
```bash
python -m leadengine.run                 # audit → verify → rank → drafts → data/leads.json
python -m leadengine.demo                # needs the brain API (BRAIN_URL, default http://localhost:8000)
pytest -q tests                          # 10 pipeline tests
python -m casestudy.build                # data/*.json → casestudy/index.html
```
Collection (search and scrape) ran through Firecrawl; raw responses are stored verbatim in
`data/raw/austin_tx.json`, and deeper pages as excerpts in `data/sites/<slug>/`.

## Rules this project keeps
- You approve and send every message. Nothing here sends email, texts or WhatsApp.
- No automated cold WhatsApp: business-initiated WhatsApp needs approved templates and gets numbers banned.
- A gap goes into a draft only if a deeper page doesn't contradict it.

## Next
1. Merge the brain's hours fix (langflow-brain branch `claude/nice-carson-iqf3xo`); until then the demos need that branch running
2. Verify leads 6–11 (one deeper page each)
3. Google Places for discovery and review-response rate (needs `GOOGLE_PLACES_API_KEY`)
4. Reply classification and a CRM table in Supabase
