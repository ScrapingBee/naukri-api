"""Compare Indian job markets from public Naukri search pages.

For every role x city pair it reads a few search pages through naukri_client,
then summarises two kinds of evidence side by side:

  - the sidebar filter counts, which describe the whole result set
    (work mode, salary bands, top hiring companies), and
  - the job cards themselves: how many show a salary, the experience they ask
    for, which skills they tag and how fresh they are.

Optionally it opens the first N job pages per market for openings,
applicant counts, preferred skills and the AmbitionBox salary estimate.

    python naukri_market.py --roles "python developer" "data analyst" \
        --cities bangalore pune --pages 2 --details 2 --md market.md --csv market.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Optional

from naukri_client import JobCard, JobDetail, NaukriClient


@dataclass
class Market:
    role: str
    city: str
    totals: list[int] = field(default_factory=list)  # one per page read
    facets: dict[str, dict[str, int]] = field(default_factory=dict)
    cards: list[JobCard] = field(default_factory=list)
    details: list[JobDetail] = field(default_factory=list)
    partial_pages: int = 0

    @property
    def name(self) -> str:
        return f"{self.role} / {self.city}"

    @property
    def total(self) -> Optional[int]:
        return max(self.totals) if self.totals else None

    @property
    def totals_disagree(self) -> bool:
        return len(set(self.totals)) > 1


def _median(xs: list[float]) -> Optional[float]:
    return round(statistics.median(xs), 1) if xs else None


def _share(part: int, whole: int) -> str:
    return f"{100 * part / whole:.0f}%" if whole else "-"


def collect(client: NaukriClient, role: str, city: str, pages: int, details: int) -> Market:
    m = Market(role, city)
    best = -1
    for sp in client.search(role, city, pages):
        if sp.total is not None:
            m.totals.append(sp.total)
        # Some renders report a much smaller total (601 instead of 5279) with
        # matching sidebar counts. Keep the facets of the largest result set.
        if sp.facets and (sp.total or 0) > best:
            best, m.facets = sp.total or 0, sp.facets
        m.partial_pages += sp.partial
        m.cards.extend(sp.jobs)
    for card in m.cards[:details]:
        d = client.job(card.url)
        if d:
            m.details.append(d)
    return m


def summarise(m: Market) -> dict[str, object]:
    cards = m.cards
    paid = [c for c in cards if c.salary_min_lpa is not None]
    mids = [(c.salary_min_lpa + c.salary_max_lpa) / 2 for c in paid]
    fresh = [c for c in cards if c.posted_days is not None and c.posted_days <= 7]
    work = m.facets.get("work_mode", {})
    work_total = sum(work.values())
    tags = Counter(t.lower() for c in cards for t in c.tags)
    out: dict[str, object] = {
        "market": m.name,
        "total_listings": m.total,
        "totals_seen": "/".join(map(str, m.totals)),
        "cards_read": len(cards),
        "salary_shown": _share(len(paid), len(cards)),
        "median_salary_mid_lpa": _median(mids),
        "median_exp_min_yrs": _median([c.exp_min for c in cards if c.exp_min is not None]),
        "median_exp_max_yrs": _median([c.exp_max for c in cards if c.exp_max is not None]),
        "posted_last_7_days": _share(len(fresh), len(cards)),
        "remote": _share(work.get("Remote", 0), work_total),
        "hybrid": _share(work.get("Hybrid", 0), work_total),
        "top_companies": ", ".join(f"{k} ({v})" for k, v in m.facets.get("top_companies", {}).items()),
        "salary_bands": ", ".join(f"{k} ({v})" for k, v in m.facets.get("salary", {}).items()),
        "top_skills": ", ".join(f"{k} {v}" for k, v in tags.most_common(8)),
    }
    if m.details:
        out["openings_sum"] = sum(d.openings or 0 for d in m.details)
        out["applicants"] = ", ".join(d.applicants for d in m.details)
        out["salary_insights"] = ", ".join(d.salary_insight or "-" for d in m.details)
        out["preferred_skills"] = ", ".join(sorted({s for d in m.details for s in d.preferred_skills}))
    return out


def to_markdown(rows: list[dict[str, object]]) -> str:
    keys = [k for k in rows[0] if k != "market"]
    lines = ["| | " + " | ".join(r["market"] for r in rows) + " |",
             "|---" * (len(rows) + 1) + "|"]
    for k in keys:
        lines.append(f"| {k} | " + " | ".join(str(r.get(k, "")) for r in rows) + " |")
    return "\n".join(lines) + "\n"


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Naukri job market comparison")
    ap.add_argument("--roles", nargs="+", required=True)
    ap.add_argument("--cities", nargs="+", required=True)
    ap.add_argument("--pages", type=int, default=2, help="search pages per market, 20 cards each")
    ap.add_argument("--details", type=int, default=0, help="job pages to open per market")
    ap.add_argument("--md", help="write the comparison table as Markdown")
    ap.add_argument("--csv", help="write one row per market")
    ap.add_argument("--cards", help="write every card read as JSON lines")
    a = ap.parse_args(argv)

    client = NaukriClient()
    rows = []
    cards_fh = open(a.cards, "w", encoding="utf-8") if a.cards else None
    for role in a.roles:
        for city in a.cities:
            m = collect(client, role, city, a.pages, a.details)
            row = summarise(m)
            for c in m.cards if cards_fh else []:
                cards_fh.write(json.dumps({"market": m.name, **asdict(c)}, ensure_ascii=False) + "\n")
            rows.append(row)
            warn = "  totals disagree between pages" if m.totals_disagree else ""
            warn += f"  {m.partial_pages} partial page(s)" if m.partial_pages else ""
            print(f"{m.name}: {row['total_listings']} listings, {len(m.cards)} cards, "
                  f"salary shown on {row['salary_shown']}, median mid {row['median_salary_mid_lpa']} LPA{warn}")
            print(f"  skills: {row['top_skills']}")
    if cards_fh:
        cards_fh.close()
    print(f"{len(rows)} markets, {client.credits} credits")
    if not rows:
        return 1
    if a.md:
        with open(a.md, "w", encoding="utf-8") as fh:
            fh.write(to_markdown(rows))
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
            w.writeheader()
            w.writerows(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
