"""Draft outreach that cites the real gap. A human reviews, edits and sends every message.

US cold email must identify the sender, give a physical address and honour opt-outs (CAN-SPAM), so the
signature keeps those as placeholders the sender fills in. Nothing here sends anything.
"""
from .audit import Lead


def draft(lead: Lead, demo_ready: bool) -> dict:
    top = sorted(lead.gaps, key=lambda g: -g.points)[:2]
    first = lead.name.split()[0] if lead.niche == "fitness coach" and len(lead.name.split()) == 2 else None
    hello = f"Hi {first}," if first else f"Hi {lead.name} team,"
    noun = "patients" if lead.niche == "dental" else "clients"

    lines = [hello, "", f"I looked at {lead.url.split('//')[1].strip('/')} and noticed two things:"]
    lines += [f"- {g.headline}." for g in top]
    if demo_ready:
        lines += ["", f"I built a small assistant that already knows your site, {_known(lead)}. It answers "
                      f"{noun}' questions with the source, hands anything it can't answer to your team with the "
                      f"person's name and number, and can be connected to your calendar to book directly. "
                      f"Want the 2-minute demo link?"]
    else:
        lines += ["", f"I build assistants that answer {noun}' questions from your own site, book appointments and "
                      f"pass anything else to your team. Happy to set up a free demo on your real info."]
    lines += ["", "[Your name]", "[Your business address]",
              "If this isn't useful, reply \"no thanks\" and I won't follow up."]
    return {
        "to": lead.name,
        "subject": f"{top[0].headline.split(';')[0].split(',')[0]} at {lead.name}" if top else f"Idea for {lead.name}",
        "body": "\n".join(lines),
        "cites": [{"gap": g.key, "evidence": g.evidence} for g in top],
        "status": "draft — needs human approval",
    }


def _known(lead: Lead) -> str:
    """One concrete thing from their own pages, so the claim is checkable."""
    if lead.prices:
        return f"down to details like \"{lead.prices[0]}\""
    if lead.hours:
        return f"down to your hours ({lead.hours.split(',')[0].strip()}, ...)"
    if lead.services:
        return "including " + " and ".join(s.lower() for s in lead.services[:2])
    return "including your services"
