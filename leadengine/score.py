"""Pain × fit. Pain = how much the gaps cost them. Fit = how reachable and worth it they are."""
from .audit import Lead


def pain(lead: Lead) -> int:
    return min(100, sum(g.points for g in lead.gaps))


def fit(lead: Lead) -> int:
    score = 40
    score += 20 if len(lead.services) >= 5 else 10 if len(lead.services) >= 3 else 0   # more services, more enquiries
    score += 20 if lead.phone else 0                                                     # reachable
    score += 20 if lead.address else 0                                                   # real local premises
    return min(100, score)


def rank(lead: Lead) -> float:
    return round(0.6 * pain(lead) + 0.4 * fit(lead), 1)
