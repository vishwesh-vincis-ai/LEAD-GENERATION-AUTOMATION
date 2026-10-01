"""Second look before outreach: re-check every gap against the lead's deeper pages.

The homepage audit is fast but shallow. A gap goes into an email only if the deeper pages don't contradict
it. Pages live in data/sites/<slug>/*.md (verbatim scrape excerpts with a Source line).
"""
import re
from pathlib import Path
from urllib.parse import urlparse

from .audit import Gap, Lead

SITES = Path(__file__).parent.parent / "data" / "sites"
SCHEDULER_PHRASES = ("taken straight to the scheduler", "pick your time", "book your next session", "book online",
                     "schedule online", "self-schedule")
CALL_TO_BOOK = re.compile(r"(please )?call [\d\-\(\) .]{7,} to (begin|book|schedule)[^.]*\.", re.I)
WAIT_FOR_REPLY = re.compile(r"[^.\n]*(will reach out|reach out within|replies within)[^.\n]*\.", re.I)
PRICE = re.compile(r"[^.\n]*\$\s?\d[\d,]*(\.\d\d)?[^.\n]*", re.I)


def slug(url: str) -> str:
    host = urlparse(url).netloc.removeprefix("www.")
    return host.rsplit(".", 1)[0]


def pages(lead: Lead) -> dict[str, str]:
    d = SITES / slug(lead.url)
    return {p.name: p.read_text() for p in sorted(d.glob("*.md"))} if d.exists() else {}


def verify(lead: Lead) -> dict:
    """Mutates lead.gaps. Returns what changed and why, for the audit trail."""
    docs = pages(lead)
    if not docs:
        return {"verified": False, "dropped": [], "confirmed": []}
    text = "\n".join(docs.values())
    dropped, confirmed, keep = [], [], []

    for g in lead.gaps:
        if g.key == "no_prices" and (m := _price_line(text)):
            dropped.append({"gap": g.key, "because": m})
            continue
        if g.key in ("no_booking", "request_form_only"):
            hit = next((p for p in SCHEDULER_PHRASES if p in text.lower()), None)
            if hit:
                dropped.append({"gap": g.key, "because": _sentence(text, hit)})
                continue
            if m := CALL_TO_BOOK.search(text) or (g.key == "request_form_only" and WAIT_FOR_REPLY.search(text)):
                g.evidence = m.group(0).strip()
                confirmed.append({"gap": g.key, "because": g.evidence})
        if g.key == "no_text" and re.search(r"\b(call/text|text us|text \d)", text, re.I):
            dropped.append({"gap": g.key, "because": _sentence(text, "text")})
            continue
        if g.key == "no_faq" and re.search(r"frequently asked questions|\bfaq\b", text, re.I):
            dropped.append({"gap": g.key, "because": "FAQ page found"})
            continue
        keep.append(g)
    lead.gaps = keep
    return {"verified": True, "pages": list(docs), "dropped": dropped, "confirmed": confirmed}


def _price_line(text: str) -> str | None:
    for m in PRICE.finditer(text):
        line = m.group(0).strip()
        if "cancellation fee" not in line.lower():   # a fee is not a price list
            return line
    return None


def _sentence(text: str, needle: str) -> str:
    i = text.lower().find(needle.lower())
    if i < 0:
        return needle
    start = max(text.rfind("\n", 0, i), text.rfind(". ", 0, i)) + 1
    end = min([e for e in (text.find("\n", i), text.find(". ", i)) if e > 0] or [len(text)])
    return text[start:end + 1].strip()
