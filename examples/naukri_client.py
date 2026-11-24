"""Naukri job search and job page reader built on ScrapingBee.

Reads two kinds of public, logged-out naukri.com pages:

  /<keyword>-jobs-in-<city>[-<page>]   search results, 20 cards per page
  /job-listings-<slug>-<job id>        one job page (JSON-LD JobPosting plus page body)

Every request renders the page in a real browser through ScrapingBee and asks
for extract_rules, so JSON comes back instead of HTML. Nothing here logs in,
calls a Naukri backend endpoint or touches the recruiter side of the site.

    pip install requests
    export SCRAPINGBEE_API_KEY=...
    python naukri_client.py search "python developer" --location bangalore --pages 2 --csv jobs.csv
    python naukri_client.py job https://www.naukri.com/job-listings-...-240826007480 --json job.json
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Iterator, Optional

import requests

API = "https://app.scrapingbee.com/api/v1/"
BASE = "https://www.naukri.com"

# Naukri's search page is a Next.js app. Without JavaScript it is a loading
# splash, and with ScrapingBee's default resource blocking the app crashes
# ("Application error: a client-side exception has occurred"). A classic
# proxy with render_js=true and block_resources=false returns the full page
# for 5 credits.
BASE_PARAMS = {
    "render_js": "true",
    "block_resources": "false",
    "country_code": "in",
}

SEARCH_RULES = {
    "h1": "h1[class^='styles_h1-content']",
    "count": {"selector": "span[class^='styles_count-string']", "output": "@title"},
    "jobs": {
        "selector": "div.srp-jobtuple-wrapper",
        "type": "list",
        "output": {
            "id": {"selector": "div.srp-jobtuple-wrapper", "output": "@data-job-id"},
            "title": "a.title",
            "url": {"selector": "a.title", "output": "@href"},
            "company": "a.comp-name",
            "rating": "a.rating span.main-2",
            "reviews": "a.review",
            "experience": "span.expwdth",
            "salary": "span.sal-wrap span[title]",
            "location": "span.locWdth",
            "snippet": "span.job-desc",
            "tags": {"selector": "ul.tags-gt li", "type": "list"},
            "posted": "span.job-post-day",
        },
    },
    "facets": {
        "selector": "div[data-filter-id]",
        "type": "list",
        "output": {
            "id": {"selector": "div[data-filter-id]", "output": "@data-filter-id"},
            "labels": {"selector": "span[class*='filterLabel']", "type": "list", "output": "@title"},
            "counts": {"selector": "span[class^='styles_filterCount']", "type": "list"},
        },
    },
}

JOB_RULES = {
    "title": "h1[class^='styles_jd-header-title']",
    "company": "div[class^='styles_jd-header-comp-name'] > a",
    "rating": "span[class^='styles_amb-rating']",
    "reviews": "span[class^='styles_amb-reviews']",
    "experience": "div[class^='styles_jhc__exp'] span",
    "salary": "div[class^='styles_jhc__salary'] span",
    "work_mode": "div[class^='styles_jhc__wfhmode'] span",
    "locations": {"selector": "span[class^='styles_jhc__location'] a", "type": "list"},
    "stats": {
        "selector": "span[class^='styles_jhc__stat']",
        "type": "list",
        "output": {"label": "label", "value": "span"},
    },
    "details": {
        "selector": "div[class^='styles_other-details'] div[class^='styles_details'], "
        "div[class^='styles_education'] div[class^='styles_details']",
        "type": "list",
        "output": {"label": "label", "value": "span"},
    },
    "skills": {
        "selector": "div[class^='styles_key-skill'] a[class*='styles_chip']",
        "type": "list",
        "output": {"name": "span", "preferred": {"selector": "i.ni-icon-jd-save", "output": "@class"}},
    },
    "salary_insight": "div[class^='styles_sic__typical-range']",
    # output "text" on a <script> came back empty, so ask for the html and strip the tag
    "ld": {"selector": "script[type='application/ld+json']", "type": "list", "output": "html"},
}

# The salary insight card in the right column only mounts once it scrolls into view.
JOB_SCENARIO = {
    "strict": False,
    "instructions": [
        {"wait_for": "h1"},
        {"scroll_y": 900},
        {"wait": 1200},
        {"scroll_y": 900},
        {"wait": 1200},
    ],
}

FACET_NAMES = {
    "wfhType": "work_mode",
    "functionalAreaGid": "department",
    "salaryRange": "salary",
    "business_size": "company_type",
    "glbl_RoleCat": "role_category",
    "stipend": "stipend",
    "internshipDuration": "internship_duration",
    "ugTypeGid": "education",
    "employement": "posted_by",
    "industryTypeGid": "industry",
    "topGroupId": "top_companies",
    "citiesGid": "location",
}


class NaukriError(RuntimeError):
    pass


# ---------------------------------------------------------------- parsing helpers

def _clean(s: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("\u2013", "-").replace("\u2014", "-")).strip()


def _int(s: Optional[str]) -> Optional[int]:
    m = re.search(r"\d[\d,]*", s or "")
    return int(m.group(0).replace(",", "")) if m else None


def _float(s: Optional[str]) -> Optional[float]:
    m = re.search(r"\d+(?:\.\d+)?", s or "")
    return float(m.group(0)) if m else None


def parse_range(s: str) -> tuple[Optional[float], Optional[float]]:
    """'2-5 Yrs' -> (2, 5); '10-20 Lacs PA' -> (10, 20); '6 - 11 years' -> (6, 11)."""
    nums = re.findall(r"\d+(?:\.\d+)?", s or "")
    if not nums:
        return None, None
    lo = float(nums[0])
    hi = float(nums[1]) if len(nums) > 1 else lo
    return lo, hi


def posted_days(s: str) -> Optional[int]:
    """Turn the card's relative date into an age in days (upper bound for '30+')."""
    s = (s or "").lower()
    if not s or s.startswith("starts in"):  # internship cards show a start window instead
        return None
    if "hour" in s or "just now" in s or "today" in s or "few" in s:
        return 0
    n = _int(s) or 1
    if "week" in s:
        return n * 7
    if "month" in s:
        return n * 30
    if "day" in s:
        return n
    return None


def _ld_blocks(raw: list) -> list[dict]:
    out = []
    for html in raw or []:
        body = re.sub(r"^<script[^>]*>|</script>$", "", html.strip(), flags=re.S)
        try:
            data = json.loads(body)
        except ValueError:
            continue
        out.extend(data if isinstance(data, list) else [data])
    return out


# ---------------------------------------------------------------- data classes

@dataclass
class JobCard:
    job_id: str
    title: str
    company: str
    url: str
    rating: Optional[float]
    reviews: Optional[int]
    experience: str
    exp_min: Optional[float]
    exp_max: Optional[float]
    salary: str
    salary_min_lpa: Optional[float]
    salary_max_lpa: Optional[float]
    locations: list[str]
    work_mode: str  # the card folds it into the location: "Hybrid - Pune", "Remote"
    tags: list[str]
    snippet: str
    posted: str
    posted_days: Optional[int]

    @classmethod
    def from_rules(cls, r: dict) -> "JobCard":
        exp = _clean(r.get("experience"))
        sal = _clean(r.get("salary"))
        smin, smax = parse_range(sal) if "lac" in sal.lower() else (None, None)
        emin, emax = parse_range(exp)
        posted = _clean(r.get("posted"))
        locs = [_clean(x) for x in _clean(r.get("location")).split(",") if x.strip()]
        mode = ""
        if locs and locs[0].startswith("Hybrid - "):
            mode, locs[0] = "Hybrid", locs[0][len("Hybrid - "):]
        elif locs == ["Remote"]:
            mode, locs = "Remote", []
        return cls(
            job_id=_clean(r.get("id")),
            title=_clean(r.get("title")),
            company=_clean(r.get("company")),
            url=_clean(r.get("url")),
            rating=_float(r.get("rating")),
            reviews=_int(r.get("reviews")),
            experience=exp,
            exp_min=emin,
            exp_max=emax,
            salary=sal,
            salary_min_lpa=smin,
            salary_max_lpa=smax,
            locations=locs,
            work_mode=mode,
            tags=[_clean(t) for t in r.get("tags") or [] if _clean(t)],
            snippet=_clean(r.get("snippet")),
            posted=posted,
            posted_days=posted_days(posted),
        )


@dataclass
class SearchPage:
    url: str
    page: int
    heading: str
    first: Optional[int]
    last: Optional[int]
    total: Optional[int]
    jobs: list[JobCard]
    facets: dict[str, dict[str, int]] = field(default_factory=dict)
    cards_returned: int = 0
    repeats: int = 0  # cards already seen on an earlier page

    @property
    def partial(self) -> bool:
        """True when the page header promises more cards than came back."""
        if self.first is None or self.last is None:
            return False
        return self.cards_returned < self.last - self.first + 1


@dataclass
class JobDetail:
    job_id: str
    url: str
    title: str
    company: str
    rating: Optional[float]
    reviews: str
    experience: str
    months_of_experience: Optional[int]
    salary: str
    salary_currency: str
    work_mode: str
    locations: list[str]
    posted: str
    date_posted: str
    valid_through: str
    openings: Optional[int]
    applicants: str
    employment_type: str
    industry: str
    role: str
    department: str
    role_category: str
    education_ug: str
    education_pg: str
    skills: list[str]
    preferred_skills: list[str]
    salary_insight: str
    description_html: str = field(repr=False, default="")


# ---------------------------------------------------------------- client

class NaukriClient:
    def __init__(self, api_key: Optional[str] = None, timeout: int = 150, retries: int = 3):
        self.api_key = api_key or os.environ.get("SCRAPINGBEE_API_KEY")
        if not self.api_key:
            raise NaukriError("set SCRAPINGBEE_API_KEY")
        self.timeout = timeout
        self.retries = retries
        self.credits = 0
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {self.api_key}"

    def _get(self, url: str, rules: dict, **extra) -> dict:
        params = {**BASE_PARAMS, "url": url, "extract_rules": json.dumps(rules), **extra}
        for attempt in range(1, self.retries + 1):
            try:
                r = self.session.get(API, params=params, timeout=self.timeout)
            except requests.RequestException as e:
                if attempt == self.retries:
                    raise NaukriError(f"network error on {url}: {e}") from e
                time.sleep(2 * attempt)
                continue
            self.credits += int(r.headers.get("spb-cost", 0) or 0)
            if r.status_code == 500 and attempt < self.retries:
                # ScrapingBee does not bill its own 500s, so a retry is free
                time.sleep(2 * attempt)
                continue
            if r.status_code == 404 or r.headers.get("spb-initial-status-code") == "404":
                return {}
            if r.status_code != 200:
                raise NaukriError(f"HTTP {r.status_code} for {url}: {r.text[:200]}")
            return r.json()
        raise NaukriError(f"gave up on {url}")

    # -- search

    @staticmethod
    def search_url(keyword: str, location: Optional[str] = None, page: int = 1) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", keyword.lower()).strip("-") + "-jobs"
        if location:
            slug += "-in-" + re.sub(r"[^a-z0-9]+", "-", location.lower()).strip("-")
        if page > 1:
            slug += f"-{page}"
        return f"{BASE}/{slug}"

    def search_page(self, keyword: str, location: Optional[str] = None, page: int = 1) -> SearchPage:
        url = self.search_url(keyword, location, page)
        data: dict = {}
        for _ in range(2):
            data = self._get(url, SEARCH_RULES, wait_for="div.srp-jobtuple-wrapper")
            if data.get("jobs"):
                break
            # a 200 with no cards is billed; try once more before giving up
        count = _clean(data.get("count"))  # "1 - 20 of 10552"
        m = re.match(r"(\d+)\s*-\s*(\d+)\s+of\s+([\d,]+)", count)
        facets: dict[str, dict[str, int]] = {}
        for f in data.get("facets") or []:
            name = FACET_NAMES.get(f.get("id"))
            if not name or not f.get("labels") or name in facets:
                continue
            facets[name] = {_clean(k): _int(v) or 0 for k, v in zip(f["labels"], f["counts"])}
        return SearchPage(
            url=url,
            page=page,
            heading=_clean(data.get("h1")),
            first=int(m.group(1)) if m else None,
            last=int(m.group(2)) if m else None,
            total=_int(m.group(3)) if m else None,
            jobs=[JobCard.from_rules(j) for j in data.get("jobs") or []],
            facets=facets,
            cards_returned=len(data.get("jobs") or []),
        )

    def search(self, keyword: str, location: Optional[str] = None, pages: int = 1) -> Iterator[SearchPage]:
        seen: set[str] = set()
        for p in range(1, pages + 1):
            sp = self.search_page(keyword, location, p)
            fresh = [j for j in sp.jobs if j.job_id not in seen]
            seen.update(j.job_id for j in fresh)
            sp.repeats = len(sp.jobs) - len(fresh)
            sp.jobs = fresh
            yield sp
            if not fresh or (sp.total is not None and sp.last is not None and sp.last >= sp.total):
                break

    # -- one job page

    def job(self, url: str) -> Optional[JobDetail]:
        data = self._get(url, JOB_RULES, js_scenario=json.dumps(JOB_SCENARIO))
        if not data or not data.get("title"):
            return None
        ld = next((b for b in _ld_blocks(data.get("ld")) if b.get("@type") == "JobPosting"), {})
        stats = {_clean(s.get("label")).rstrip(":"): _clean(s.get("value")) for s in data.get("stats") or []}
        for k, v in stats.items():  # the span text repeats the label: "Openings: 6"
            stats[k] = re.sub(rf"^{re.escape(k)}:\s*", "", v)
        details = {
            _clean(d.get("label")).rstrip(":"): re.sub(r"\s+,", ",", _clean(d.get("value"))).rstrip(" ,")
            for d in data.get("details") or []
        }
        skills = data.get("skills") or []
        base_salary = ld.get("baseSalary") or {}
        return JobDetail(
            job_id=str((ld.get("identifier") or {}).get("value") or re.sub(r".*-(\d+)/?$", r"\1", url)),
            url=url,
            title=_clean(data.get("title")),
            company=_clean(data.get("company")),
            rating=_float(data.get("rating")),
            reviews=_clean(data.get("reviews")),
            experience=_clean(data.get("experience")),
            months_of_experience=_int((ld.get("experienceRequirements") or {}).get("monthsOfExperience")),
            salary=_clean(data.get("salary")),
            salary_currency=base_salary.get("currency", ""),
            work_mode=_clean(data.get("work_mode")),
            locations=[_clean(x) for x in data.get("locations") or []],
            posted=stats.get("Posted", ""),
            date_posted=ld.get("datePosted", ""),
            valid_through=ld.get("validThrough", ""),
            openings=_int(stats.get("Openings")),
            applicants=stats.get("Applicants", ""),
            employment_type=details.get("Employment Type", ""),
            industry=details.get("Industry Type", ""),
            role=details.get("Role", ""),
            department=details.get("Department", ""),
            role_category=details.get("Role Category", ""),
            education_ug=details.get("UG", ""),
            education_pg=details.get("PG", ""),
            skills=[_clean(s.get("name")) for s in skills],
            preferred_skills=[_clean(s.get("name")) for s in skills if s.get("preferred")],
            salary_insight=_clean(data.get("salary_insight")),
            description_html=ld.get("description", ""),
        )


# ---------------------------------------------------------------- export + CLI

def write_csv(path: str, rows: list) -> None:
    if not rows:
        return
    dicts = [asdict(r) for r in rows]
    for d in dicts:
        d.pop("description_html", None)
        for k, v in d.items():
            if isinstance(v, list):
                d[k] = "; ".join(map(str, v))
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(dicts[0]))
        w.writeheader()
        w.writerows(dicts)


def write_json(path: str, rows: list) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump([asdict(r) for r in rows], fh, ensure_ascii=False, indent=1)


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Naukri search and job pages through ScrapingBee")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search", help="read search result pages")
    s.add_argument("keyword")
    s.add_argument("--location")
    s.add_argument("--pages", type=int, default=1)
    s.add_argument("--csv")
    s.add_argument("--json")
    j = sub.add_parser("job", help="read one or more job pages")
    j.add_argument("urls", nargs="+")
    j.add_argument("--csv")
    j.add_argument("--json")
    a = ap.parse_args(argv)

    client = NaukriClient()
    rows: list = []
    if a.cmd == "search":
        for sp in client.search(a.keyword, a.location, a.pages):
            flag = "  PARTIAL" if sp.partial else ""
            rep = f", {sp.repeats} repeated from an earlier page" if sp.repeats else ""
            print(f"  page {sp.page}: {sp.first}-{sp.last} of {sp.total}, {len(sp.jobs)} new cards{rep}{flag}")
            if sp.page == 1:
                for name in ("work_mode", "salary"):
                    print(f"  {name}: {sp.facets.get(name)}")
            rows.extend(sp.jobs)
        for c in rows[:8]:
            sal = c.salary or "-"
            print(f"{c.job_id}  {c.title[:34]:34}  {c.company[:22]:22}  {c.experience:9}  {sal:15}  {c.posted}")
    else:
        for url in a.urls:
            d = client.job(url)
            if d is None:
                print(json.dumps({"url": url, "found": False}))
                continue
            rows.append(d)
            out = asdict(d)
            out.pop("description_html")
            print(json.dumps(out, ensure_ascii=False))
    print(f"{len(rows)} rows, {client.credits} credits")
    if a.csv:
        write_csv(a.csv, rows)
    if a.json:
        write_json(a.json, rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
