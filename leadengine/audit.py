"""Turn a raw scrape into verified signals and gaps.

Rule of thumb: links are facts, model extraction is a claim. When the two disagree, links win, and every
gap carries the evidence that produced it, so an outreach line can always be traced back to the page.
"""
import re
from dataclasses import dataclass, field

# Third-party schedulers that let a customer pick a real slot without calling.
BOOKING_VENDORS = (
    "flexbook.me", "nexhealth", "zocdoc", "localmed", "lighthouse360", "solutionreach", "patientpop",
    "mindbody", "calendly", "acuity", "vagaro", "glofox", "wellnessliving", "trainerize", "setmore",
    "schedulicity", "square.site", "booksy", "janeapp", "tidycal", "simplepractice",
)
# Pages that collect a request someone must call back about.
REQUEST_PATHS = ("request-an-appointment", "request-appt", "book-an-appointment", "appointment-request",
                 "get-started", "get-assessed", "teen-booking")
PLACEHOLDERS = ("example", "123 main", "anytown", "lorem", "service a")


class InvalidScrape(Exception):
    pass


@dataclass
class Gap:
    key: str
    points: int
    headline: str        # what the owner reads
    evidence: str        # what we saw on the page


@dataclass
class Lead:
    name: str
    niche: str
    url: str
    phone: str | None
    address: str | None
    services: list[str]
    booking: str                     # instant | request_form | none
    booking_evidence: str
    text_option: bool
    prices: list[str]
    hours: str | None
    has_faq: bool
    offer: str | None
    gaps: list[Gap] = field(default_factory=list)
    corrections: list[str] = field(default_factory=list)   # model claims the links contradicted


def _clean(v):
    return None if v in (None, "", "null", "None") else v


def validate(scrape: dict) -> None:
    if scrape.get("status_code") != 200:
        raise InvalidScrape(f"HTTP {scrape.get('status_code')}: page not actually read")
    blob = " ".join(str(v) for v in scrape["extracted"].values()).lower()
    if any(p in blob for p in PLACEHOLDERS):
        raise InvalidScrape("placeholder values in extraction (model invented the business)")


def audit(scrape: dict) -> Lead:
    validate(scrape)
    x = {k: _clean(v) for k, v in scrape["extracted"].items()}
    links = scrape["links"]
    corrections = []

    vendor = next((l for l in links if any(v in l for v in BOOKING_VENDORS)), None)
    request = next((l for l in links if any(p in l for p in REQUEST_PATHS)), None)
    if vendor:
        booking, booking_ev = "instant", vendor
    elif request:
        booking, booking_ev = "request_form", request
    else:
        booking, booking_ev = "none", "no scheduler or booking page linked from the homepage"
    if x.get("online_booking") and booking == "none":
        corrections.append(f"model said online booking from the text {x.get('online_booking_evidence')!r}; "
                           f"no booking link exists")

    sms = next((l for l in links if l.startswith("sms:")), None)
    text_claim = bool(x.get("text_or_chat_option")) and re.search(r"\btext\b", x.get("text_or_chat_evidence") or "", re.I)
    if x.get("text_or_chat_option") and not (sms or text_claim):
        corrections.append(f"model said text/chat from {x.get('text_or_chat_evidence')!r}; that is not texting")
    text_option = bool(sms or text_claim)

    prices = [p for p in (x.get("price_examples") or []) if re.search(r"\$\s?\d", p)]
    if x.get("prices_listed") and not prices:
        corrections.append(f"model said prices listed; no dollar amount in {x.get('price_examples')}")

    has_faq = bool(x.get("faq_on_page")) or any("faq" in l for l in links)

    lead = Lead(
        name=x["business_name"], niche=scrape["niche"], url=scrape["url"],
        phone=x.get("phone") or next((l[4:].replace("%20", "").strip() for l in links if l.startswith("tel:")), None),
        address=x.get("address"), services=x.get("services") or [], booking=booking, booking_evidence=booking_ev,
        text_option=text_option, prices=prices, hours=x.get("hours"), has_faq=has_faq,
        offer=x.get("new_client_offer"), corrections=corrections,
    )
    lead.gaps = find_gaps(lead)
    return lead


def find_gaps(l: Lead) -> list[Gap]:
    noun = "patients" if l.niche == "dental" else "clients"
    gaps = []
    if l.booking == "none":
        gaps.append(Gap("no_booking", 30, f"New {noun} can't book online; there is no scheduler on the site",
                        l.booking_evidence))
    elif l.booking == "request_form":
        gaps.append(Gap("request_form_only", 20,
                        f"Booking is a request form, so every request waits for a call back",
                        l.booking_evidence))
    if not l.text_option:
        gaps.append(Gap("no_text", 15, f"No way to text or chat; {noun} who won't call have no option",
                        "no sms: link or text/chat option on the homepage"))
    if l.hours and re.search(r"\bclosed\b", l.hours, re.I):
        gaps.append(Gap("limited_hours", 15, "Closed days mean calls and questions go unanswered for days",
                        f"hours on site: {l.hours}"))
    if not l.prices:
        gaps.append(Gap("no_prices", 10, f"No prices on the homepage, so price-shoppers have to call to ask",
                        "no dollar amounts on the homepage"))
    if not l.has_faq:
        gaps.append(Gap("no_faq", 10, "No FAQ, so the same questions land on the front desk",
                        "no FAQ section or FAQ page linked"))
    return gaps
