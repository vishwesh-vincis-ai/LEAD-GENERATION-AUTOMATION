"""The cases that would put a false claim in front of a real business owner. Run: pytest -q"""
import json
from pathlib import Path

import pytest

from leadengine.audit import InvalidScrape, audit
from leadengine.outreach import draft
from leadengine.verify import verify

RAW = json.loads((Path(__file__).parent.parent / "data/raw/austin_tx.json").read_text())["scrapes"]
BY_URL = {s["url"]: s for s in RAW}


def scrape(domain: str) -> dict:
    return next(s for u, s in BY_URL.items() if domain in u)


def test_blocked_page_with_invented_business_is_rejected():
    s = scrape("coolcreek")
    assert s["extracted"]["business_name"] == "Example Business Name"   # what the model returned on a 403
    with pytest.raises(InvalidScrape, match="403"):
        audit(s)


def test_placeholder_values_are_rejected_even_on_200():
    s = dict(scrape("coolcreek"), status_code=200)
    with pytest.raises(InvalidScrape, match="placeholder"):
        audit(s)


def test_make_appointment_text_without_a_scheduler_is_not_online_booking():
    lead = audit(scrape("mclane"))
    assert lead.booking == "none"
    assert any("Make appointment" in c for c in lead.corrections)
    assert "no_booking" in {g.key for g in lead.gaps}


def test_scheduler_vendor_link_counts_as_online_booking():
    lead = audit(scrape("atxfamilydental"))
    assert lead.booking == "instant" and "flexbook" in lead.booking_evidence
    assert not {"no_booking", "request_form_only"} & {g.key for g in lead.gaps}


def test_sms_link_counts_as_texting_but_a_short_call_does_not():
    assert audit(scrape("groveatx")).text_option
    motive = audit(scrape("movewithpurpose"))
    assert not motive.text_option and any("short call" in c for c in motive.corrections)


def test_pay_what_you_can_is_not_a_price():
    lead = audit(scrape("outright"))
    assert lead.prices == [] and "no_prices" in {g.key for g in lead.gaps}


def test_deep_pages_drop_gaps_the_homepage_got_wrong():
    lead = audit(scrape("outright"))
    result = verify(lead)
    dropped = {d["gap"] for d in result["dropped"]}
    assert dropped == {"request_form_only", "no_prices"}
    assert "$125.00" in next(d["because"] for d in result["dropped"] if d["gap"] == "no_prices")


def test_deep_pages_confirm_call_to_book_with_a_quote():
    lead = audit(scrape("saustindentist"))
    result = verify(lead)
    assert result["confirmed"][0]["because"].startswith("Please call 512-280-1117")


def test_a_cancellation_fee_is_not_a_price_list():
    lead = audit(scrape("saustindentist"))
    verify(lead)
    assert "no_prices" in {g.key for g in lead.gaps}


def test_outreach_only_states_verified_gaps_and_keeps_opt_out():
    lead = audit(scrape("outright"))
    verify(lead)
    d = draft(lead, demo_ready=False)
    assert "price" not in d["body"].lower() and "book online" not in d["body"].lower()
    assert "no thanks" in d["body"] and "[Your business address]" in d["body"]
