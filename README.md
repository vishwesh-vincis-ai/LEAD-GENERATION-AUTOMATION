# Lead Engine (Project 3)

Input: a niche and a city. Output: ranked leads, each with a personalised audit and a demo bot built from that business's own website.

Status: **not started**. Build order: brain → **lead engine** → voice agent → hybrid agent.

## Pipeline
1. Find businesses: Google Places (niche + city).
2. Audit web presence with Firecrawl: WhatsApp button, booking flow, unanswered reviews, site speed.
3. Score pain × fit.
4. Scrape the site → `POST /ingest` into the Business Brain under a new `business_id` → the demo bot already knows their prices.
5. Draft outreach that cites the real gap found. **A human approves and sends every message.** No automated cold WhatsApp.
6. Classify replies, log to CRM (Supabase).

## Depends on Business Brain
`POST /ingest`, `POST /chat`, `POST /drafts/reply`.

## Keys (.env)
`GOOGLE_PLACES_API_KEY`, `FIRECRAWL_API_KEY`, `NVIDIA_API_KEY`, `BRAIN_URL`
