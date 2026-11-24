# Naukri API

<p align="center">
  <a href="https://www.scrapingbee.com/">
    <img src="REPLACE_WITH_SCREENSHOT_URL" alt="naukri-api" />
  </a>
</p>

[![checks](https://github.com/ScrapingBee/naukri-api/workflows/checks/badge.svg)](https://github.com/ScrapingBee/naukri-api/actions)
[![license](https://img.shields.io/github/license/ScrapingBee/naukri-api.svg)](LICENSE)

How many Python jobs are open in Pune compared with Bangalore, how many of them print a salary, and which skills do recruiters tag? This repo answers questions like that from naukri.com, India's biggest job board, using only the pages a logged out visitor can open. It is a [Naukri API](https://www.scrapingbee.com/scrapers/naukri-api/) in Python and Node on top of [ScrapingBee](https://www.scrapingbee.com/): a browser renders the page, [`extract_rules`](https://www.scrapingbee.com/documentation/data-extraction/) turn it into JSON, and the scripts turn that JSON into a market comparison.

Every number on this page was measured on 2026-11-24 with `country_code=in`.

```bash
pip install requests
export SCRAPINGBEE_API_KEY=your_key
python examples/naukri_market.py --roles "python developer" "data analyst" \
    --cities bangalore pune --pages 2 --details 1 --md market.md --cards cards.jsonl
```

```
python developer / bangalore: 10551 listings, 36 cards, salary shown on 33%, median mid 12.5 LPA
  skills: python 25, python development 22, development 21, sql 14, aws 9, django 8, api 8, artificial intelligence 6
python developer / pune: 5279 listings, 40 cards, salary shown on 25%, median mid 18.8 LPA
  skills: python 30, development 14, python development 10, sql 9, django 8, postgresql 7, rest 7, software 7
data analyst / bangalore: 8689 listings, 37 cards, salary shown on 49%, median mid 9.0 LPA  totals disagree between pages
  skills: sql 25, data analysis 21, data 19, bi 15, python 15, analysis 11, power bi 11, data visualization 10
data analyst / pune: 3004 listings, 40 cards, salary shown on 22%, median mid 7.5 LPA
  skills: data analysis 27, sql 19, data 15, data analytics 12, python 11, bi 9, data visualization 8, analysis 8
4 markets, 60 credits
```

## Four Indian job markets, side by side

That run wrote this table to `market.md` (trimmed to the rows worth reading). Two search pages per market plus one job page each, 60 credits in total:

| | python developer / bangalore | python developer / pune | data analyst / bangalore | data analyst / pune |
|---|---|---|---|---|
| total_listings | 10551 | 5279 | 8689 | 3004 |
| cards_read | 36 | 40 | 37 | 40 |
| salary_shown | 33% | 25% | 49% | 22% |
| median_salary_mid_lpa | 12.5 | 18.8 | 9.0 | 7.5 |
| median_exp_min_yrs | 4.0 | 4.5 | 2.0 | 4.0 |
| median_exp_max_yrs | 8.0 | 8.0 | 6.0 | 7.0 |
| posted_last_7_days | 100% | 92% | 84% | 58% |
| remote | 1% | 0% | 1% | 1% |
| hybrid | 12% | 13% | 8% | 13% |
| top_companies | Accenture (1341), Infosys (542), Capgemini (150), Qualcomm (105) | Accenture (488), Infosys (207), Bajaj Finance (98), Capgemini (76) | Accenture (875), Infosys (192), EY (172), CGI (82) | Accenture (122), Bajaj Finance (106), Infosys (90), Capgemini (29) |
| salary_bands | 0-3 Lakhs (711), 3-6 Lakhs (3565), 6-10 Lakhs (5979), 10-15 Lakhs (4312) | 0-3 Lakhs (479), 3-6 Lakhs (2118), 6-10 Lakhs (3070), 10-15 Lakhs (1975) | 0-3 Lakhs (958), 3-6 Lakhs (3355), 6-10 Lakhs (4746), 10-15 Lakhs (3356) | 0-3 Lakhs (394), 3-6 Lakhs (1196), 6-10 Lakhs (1493), 10-15 Lakhs (1063) |
| salary_insights | - | ₹6.5L - ₹9.2L/yr | ₹3.1L - ₹3.4L/yr | ₹6.2L - ₹6.8L/yr |

The rows come from two different sources, and they should be read differently.

**Rows built from the sidebar filters** (`total_listings`, `remote`, `hybrid`, `top_companies`, `salary_bands`) describe the whole result set, all 10,551 Bangalore Python jobs, not just the cards we read. They are cheap: one search page carries all of them. Two caveats. The salary bands overlap, because a "5-15 Lacs" job counts in three bands: the four Bangalore Python bands add up to 14,567, more than the 10,551 jobs. And the sidebar shows only the first four values of each filter (the 15-25 Lakhs band and above sits behind a "View More" button), so the bands above 15 lakh are not in this table.

**Rows built from the cards** (`salary_shown`, the salary and experience medians, `posted_last_7_days`, the skill counts) are a sample: the first 40 cards in Naukri's relevance order. The median salary only covers cards that print one, which is a quarter to a half of them. Treat the Pune Python median of 18.8 LPA (lakh per annum) as "10 cards that disclosed a range", not as the city's pay level.

`salary_insights` is the "typically earns between" estimate in the job page's right column. Naukri labels it as powered by AmbitionBox, and it describes the role at that company, not the posting.

## Files

| File | What it does | Credits |
|---|---|---|
| [`examples/naukri_client.py`](examples/naukri_client.py) | `NaukriClient`, dataclasses `JobCard`, `SearchPage`, `JobDetail`, CLI `search` and `job`, CSV and JSON export | 5 per page |
| [`examples/naukri_market.py`](examples/naukri_market.py) | role x city comparison: filters, card statistics, optional job pages, Markdown/CSV/JSON lines out | 5 per page |
| [`examples/naukri_search.js`](examples/naukri_search.js) | Node 18, one search page to JSON lines, no dependencies | 5 |

## What robots.txt allows

The first request in this project was `https://www.naukri.com/robots.txt` (1 credit, no JavaScript). The rules for general user agents start at `User-agent: *` and do not list either path this repo reads:

```
User-agent: *
Disallow:/preview/
Disallow:/photo/
Disallow:/alljobs/job/
Disallow:/recruiters/open-jobs-*
Disallow:/recruiters/closed-jobs-*
...
Sitemap: https://www.naukri.com/sitemap/sitemap.xml
```

Search pages (`/python-developer-jobs-in-bangalore`) and job pages (`/job-listings-...-240826007480`) are not on that list. The file also names a set of AI crawlers (GPTBot, ClaudeBot, ChatGPT-User, PerplexityBot and others) and gives them `Disallow: /`, with a few allowed sections like `/blog/`. If your project is a crawler of that kind, those lines apply to you.

## One flag decides whether the page exists: rendering and cost

Naukri's pages are a Next.js app. The status code was 200 for every request below, so it tells you nothing; what counts is whether job data is in the body.

| `/python-developer-jobs-in-bangalore` | Credits | Size | Job cards |
|---|---|---|---|
| `render_js=false` | 1 | 39 KB | 0, a loading splash with `"jobDetails":[]` in the server state |
| `render_js=true` | 5 | 1.9 KB | 0, "Application error: a client-side exception has occurred" |
| `render_js=true&premium_proxy=true` | 25 | 1.9 KB | 0, same error |
| `render_js=true&block_resources=false` | 5 | 409 KB | 20, plus an `ItemList` JSON-LD |

The job pages behaved the same way: 39 KB with no `JobPosting` without JavaScript, the same client-side error with JavaScript and default settings, and the full 276 KB page once `block_resources=false` was set. ScrapingBee blocks images and CSS by default to save time ([documented here](https://www.scrapingbee.com/documentation/)), and Naukri's app throws when its resources do not load. So a premium proxy is the wrong fix here: the classic proxy with resources allowed costs 5 credits and works. `country_code=in` is available on classic proxies and did not change the price.

```python
BASE_PARAMS = {
    "render_js": "true",
    "block_resources": "false",
    "country_code": "in",
}
```

One of our rendered test requests came back as a ScrapingBee HTTP 500 with `spb-cost: 0`. `_get()` retries those, since they are not billed.

## What a search card looks like

Each result sits in a `div.srp-jobtuple-wrapper` carrying the job id. Trimmed from the rendered page (icon spans removed):

```html
<div class="srp-jobtuple-wrapper" data-job-id="240826031542">
  <h2><a class="title " title="Python developer (Female's Preferred)"
     href="https://www.naukri.com/job-listings-python-developer-female-s-preferred-infosys-hyderabad-pune-bengaluru-2-to-5-years-240826031542">...</a></h2>
  <a class=" comp-name mw-25" title="Infosys" href="https://www.naukri.com/infosys-jobs-careers-11244">Infosys</a>
  <a class="rating" href="..." title="Powered by Ambition Box"><span class="main-2">3.5</span></a>
  <a class=" review ver-line" ...>55199  Reviews</a>
  <span class="exp-wrap">...<span title="2-5 Yrs " class="expwdth">2-5 Yrs</span></span>
  <span class="loc-wrap ver-line">...<span title="Hyderabad, Pune, Bengaluru " class="locWdth">Hyderabad, Pune, Bengaluru</span></span>
  <span class="job-desc ni-job-tuple-icon ni-job-tuple-icon-srp-description">Roles &amp; ResponsibilitiesDesign, develop, and maintain Python-based applications and sof...</span>
  <ul class="tags-gt "><li class="dot-gt tag-li ">Django</li><li class="dot-gt tag-li ">Python</li><li class="dot-gt tag-li ">Flask</li>...</ul>
  <span class="job-post-day ">2 weeks ago</span>
</div>
```

A card that discloses pay has one more block, and the card above does not have it:

```html
<span class="sal-wrap ver-line"><span class="ni-job-tuple-icon ni-job-tuple-icon-srp-rupee sal">
  <span title="10-20 Lacs PA " class="">10-20 Lacs PA</span></span></span>
```

The card class names are plain (`title`, `comp-name`, `expwdth`). The layout around them uses CSS modules with a hash suffix (`styles_count-string__DlPaZ`), which will change on a redeploy, so the client matches those by prefix: `span[class^='styles_count-string']`.

```python
SEARCH_RULES = {
    "h1": "h1[class^='styles_h1-content']",
    "count": {"selector": "span[class^='styles_count-string']", "output": "@title"},   # "1 - 20 of 10552"
    "jobs": {
        "selector": "div.srp-jobtuple-wrapper",
        "type": "list",
        "output": {
            "id": {"selector": "div.srp-jobtuple-wrapper", "output": "@data-job-id"},
            "title": "a.title",
            "url": {"selector": "a.title", "output": "@href"},
            "company": "a.comp-name",
            "experience": "span.expwdth",
            "salary": "span.sal-wrap span[title]",
            "location": "span.locWdth",
            "tags": {"selector": "ul.tags-gt li", "type": "list"},
            "posted": "span.job-post-day",
            # rating, reviews and snippet too, see the file
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
```

`JobCard.from_rules()` turns the strings into numbers: `"2-5 Yrs"` becomes `exp_min=2.0, exp_max=5.0`, `"3.25-7.5 Lacs PA"` becomes `salary_min_lpa=3.25, salary_max_lpa=7.5`, `"6 days ago"` becomes `posted_days=6`. The location string also carries the work mode when there is one (`"Hybrid - Pune, Gurugram, Bengaluru"`, or just `"Remote"`), so the parser splits that into a `work_mode` field. Internship cards print `"Unpaid"` where the salary goes and `"Starts in 1-3 months"` where the date goes; both are kept as text and left out of the numbers.

### The sidebar is the market summary

The left column holds Naukri's filters, and every option carries a count for the full result set. Each filter is a `div` with a `data-filter-id`:

```html
<div class="styles_filterOptns__1vq77" data-filter-id="wfhType">
  <div class="styles_chckBoxCont__t_dRs">
    <input class="styles_inputCheckbox__TrKnD" id="chk-Work from office-wfhType-" type="checkbox">
    <label ...><p class="styles_txtLbl__Pl_48">
      <span class="styles_ellipsis__cvWP1 styles_filterLabel__jRP04" title="Work from office">Work from office</span>
      <span class="styles_filterCount__Xn_PG">(9161)</span></p></label></div>
  ...Hybrid (1315), Remote (75)
</div>
```

The ids we saw on a search page, and the names the client gives them: `wfhType` (work_mode), `functionalAreaGid` (department), `salaryRange` (salary), `business_size` (company_type), `glbl_RoleCat` (role_category), `ugTypeGid` (education), `employement` (posted_by, company or consultant), `industryTypeGid` (industry), `topGroupId` (top_companies), `citiesGid` (location), plus `stipend` and `internshipDuration` for internships. The `experience` and `freshness` filters are a slider and a dropdown with no counts, so they come back empty.

We tried to get the full list behind "View More" by clicking `button#ctcFilter` in a [`js_scenario`](https://www.scrapingbee.com/documentation/js-scenario/). It expanded once in four attempts, so the scripts do not depend on it.

## The search URL is the Naukri jobs API you get

There is no query string to build. The keyword and the city are in the path, and the page number is a suffix, exactly as the pagination links on the page show:

```html
<a href="/python-developer-jobs-in-bangalore" aria-current="page">1</a>
<a href="/python-developer-jobs-in-bangalore-2" aria-label="Go to page 2">2</a>
<a href="/python-developer-jobs-in-bangalore-3" aria-label="Go to page 3">3</a>
```

```python
@staticmethod
def search_url(keyword, location=None, page=1):
    slug = re.sub(r"[^a-z0-9]+", "-", keyword.lower()).strip("-") + "-jobs"
    if location:
        slug += "-in-" + re.sub(r"[^a-z0-9]+", "-", location.lower()).strip("-")
    if page > 1:
        slug += f"-{page}"
    return f"{BASE}/{slug}"
```

Each page holds 20 cards. Three things showed up when reading more than one:

- **Cards repeat across pages.** Page 2 of the Bangalore Python search had 4 cards from page 1. `search()` keeps a set of job ids and reports the repeats instead of counting them twice.
- **The order changes between renders.** Two reads of the same page 1, a few minutes apart, opened with different cards (an Infosys listing from two weeks ago in one, a listing from that day in the other). Sampling "the first 40 cards" is a sample of relevance order at that moment.
- **The total moves.** Most renders of the Bangalore Python search said "of 10551" or "of 10552", but three of seventeen said "of 1224", with sidebar counts shrunk to match. Bangalore data analyst read 8,689 on page 1 and 6,522 on page 2 of the same run. `naukri_market.py` records every total it sees, prints `totals disagree between pages` when they differ, and keeps the sidebar counts from the page with the largest total.

```bash
python examples/naukri_client.py search "python developer" --location bangalore --pages 2 --csv jobs.csv --json jobs.json
```

```
  page 1: 1-20 of 10551, 20 new cards
  work_mode: {'Work from office': 9161, 'Hybrid': 1315, 'Remote': 75}
  salary: {'0-3 Lakhs': 711, '3-6 Lakhs': 3565, '6-10 Lakhs': 5979, '10-15 Lakhs': 4312}
  page 2: 21-40 of 10551, 16 new cards, 4 repeated from an earlier page
231126024218  Gen AI & B Agentic AI / Python Dev  IT Giant (Multi Nation  3-8 Yrs    6-16 Lacs PA     1 day ago
241126021673  Python developer +SRE For LTI Mind  Intellics Global Servi  5-8 Yrs    15-20 Lacs PA    Few hours ago
231126024052  AI Python Developer                 Saisystems Technology   4-6 Yrs    -                1 day ago
221126002613  Job Opportunity | Python Developer  LTM                     4-9 Yrs    -                2 days ago
181126033973  Python Developer at A FinTech Comp  Talentzo Delhi          0-4 Yrs    10-20 Lacs PA    6 days ago
...
36 rows, 10 credits
```

Of those 36 cards, 12 printed a salary and 15 listed more than one city.

## Reading one job page

A job page has a `JobPosting` in JSON-LD and more fields in the body. From job 240826007480 (description shortened):

```json
{"@context": "http://schema.org", "@type": "JobPosting",
 "title": "Python Software Developer",
 "identifier": {"@type": "PropertyValue", "name": "Capgemini", "value": "240826007480"},
 "datePosted": "2026-11-12", "validThrough": "2027-02-10",
 "experienceRequirements": {"@type": "OccupationalExperienceRequirements", "monthsOfExperience": "72"},
 "industry": "IT Services & Consulting",
 "skills": ["API", "Python", "Rest", "Financial Services", "Investment Banking", "Django", "Cloud",
            "Fast API", "Python Development", "Fast", "AWS", "Flask"],
 "employmentType": "Full Time, Permanent",
 "hiringOrganization": {"@type": "Organization", "name": "Capgemini", ...},
 "jobLocation": {"@type": "Place", "address": {"@type": "PostalAddress",
     "addressLocality": ["Hyderabad", "Pune", "Bengaluru"], ...}},
 "baseSalary": {"@type": "MonetaryAmount", "currency": "INR",
     "value": {"@type": "QuantitativeValue", "value": "Not disclosed", "unitText": "P.A."}},
 "description": "<p> </p><p>Job Summary:<br /> We are looking for a Developer skilled in Python ..."}
```

`monthsOfExperience` is the low end of the range only (72 for "6 - 11 years"), and a "0 - 4 years" job had `"1"`. Use the header text for the range. The openings and applicant counts are not in the JSON-LD at all; they sit in the header:

```html
<div class="styles_jhc__jd-stats__KrId0">
  <span class="styles_jhc__stat__PgY67"><label>Posted: </label><span>1 week ago</span></span>
  <span class="styles_jhc__stat__PgY67"><label>Openings: </label><span>6</span></span>
  <span class="styles_jhc__stat__PgY67"><label>Applicants: </label><span>100+</span></span>
</div>
```

The Key Skills block marks some chips with an icon, and the page legend says those are the preferred skills. `JOB_RULES` reads the icon's class, so an empty value means "listed, not preferred":

```python
"skills": {
    "selector": "div[class^='styles_key-skill'] a[class*='styles_chip']",
    "type": "list",
    "output": {"name": "span", "preferred": {"selector": "i.ni-icon-jd-save", "output": "@class"}},
},
# output "text" on a <script> came back empty, so ask for the html and strip the tag
"ld": {"selector": "script[type='application/ld+json']", "type": "list", "output": "html"},
```

The salary estimate card only mounts once it scrolls into view, so `job()` sends a short scenario: wait for the `h1`, scroll 900 px twice with a 1.2 second pause. The first job page we read without it had an empty `salary_insight`.

```bash
python examples/naukri_client.py job \
  https://www.naukri.com/job-listings-python-developer-at-a-fintech-company-talentzo-delhi-bengaluru-0-to-4-years-181126033973 \
  https://www.naukri.com/job-listings-python-developer-example-bengaluru-2-to-5-years-999999999999
```

```
{"job_id": "181126033973", "title": "Python Developer at A FinTech Company", "company": "Talentzo Delhi",
 "experience": "0 - 4 years", "months_of_experience": 1, "salary": "10-20 Lacs P.A.", "salary_currency": "INR",
 "locations": ["Bengaluru"], "posted": "5 days ago", "date_posted": "2026-11-18", "valid_through": "2027-02-16",
 "openings": 2, "applicants": "100+", "employment_type": "Full Time, Permanent", "industry": "FinTech / Payments",
 "role": "Back End Developer", "department": "Engineering - Software & QA", "role_category": "Software Development",
 "education_ug": "Any Graduate", "skills": ["Python", "AWS", "Django"], "preferred_skills": ["Python"],
 "salary_insight": "₹11.9L - ₹13.8L/yr", ...}
{"url": "https://www.naukri.com/job-listings-python-developer-example-bengaluru-2-to-5-years-999999999999", "found": false}
1 rows, 10 credits
```

The second URL is made up. It still cost 5 credits, because Naukri answered with a page; it just had no job header, so `job()` returned `None`. The page prints the salary estimate with an en dash, and `_clean()` swaps it for a hyphen.

## Node

```bash
node examples/naukri_search.js "devops engineer" hyderabad 1 > devops.jsonl
```

```
https://www.naukri.com/devops-engineer-jobs-in-hyderabad
1 - 20 of 907, 20 cards, 4 with a salary, 5 credits
```

```json
{"id":"261026027001","title":"Devops Engineer","url":"https://www.naukri.com/job-listings-devops-engineer-elabs-infotech-hyderabad-6-to-8-years-261026027001","company":"eLabs Infotech","experience":"6-8 Yrs","salary":null,"location":"Hybrid - Hyderabad","tags":["Continuous Integration","Automation","Docker","Cd","Continuous Integration","AWS","Jenkins","Terraform"],"posted":"4 days ago"}
```

Tags can repeat inside one card ("Continuous Integration" twice above). Dedupe before counting if that matters to you.

## Naukri data that stays behind the login

Everything above comes from pages anyone can open without an account. A good part of Naukri does not work that way, and this repo does not touch it:

- **The resume database and candidate profiles.** Searching job seekers is Naukri's recruiter product and needs a paid recruiter login. ScrapingBee's terms prohibit scraping behind login credentials, and personal profiles are not public pages anyway.
- **Applying, saved jobs, recommendations and alerts.** The job page shows "Continue with Google" where the apply button would be. All of that belongs to a signed-in seeker.
- **Exact applicant numbers.** Logged out, the header shows a bucket such as `100+` or `50+`.
- **Salary bands above the first four** in the sidebar, which need the "View More" click described earlier.

What stays public: the search pages with their filter counts, the job pages with JSON-LD, the posting text, skills, openings, the AmbitionBox rating and review count, and the salary estimate.

naukri.com does not document a public job search API that we could find, which is why this repo reads the public pages.

## Other job boards

Same approach, other sites: [Indeed API](https://www.scrapingbee.com/scrapers/indeed-api/), [Glassdoor jobs API](https://www.scrapingbee.com/scrapers/glassdoor-jobs-api/), [Google Jobs scraper API](https://www.scrapingbee.com/scrapers/google-jobs-scraper-api/), [Monster API](https://www.scrapingbee.com/scrapers/monster-api/), [ZipRecruiter API](https://www.scrapingbee.com/scrapers/ziprecruiter-api/) and [Freelancer scraper API](https://www.scrapingbee.com/scrapers/freelancer-scraper-api/). For page actions see the [JavaScript scenario feature](https://www.scrapingbee.com/features/javascript-scenario/), and for selectors the [data extraction feature](https://www.scrapingbee.com/features/data-extraction/).

## Budget

At 5 credits per page, 20 cards per page, a 1,000 page sweep (20,000 cards) costs 5,000 credits. New accounts get 1,000 free credits, enough for about 200 pages. Plans are on the [pricing page](https://www.scrapingbee.com/pricing/). This whole repo, including the tier tests and every run shown, used about 300 credits.

## FAQ

### Does Naukri have a public API?

We did not find a documented, self-serve API for reading Naukri jobs. This Naukri API reads the same search and job pages a visitor sees instead, at 5 credits per page.

### How do I get Naukri data into a CSV or a spreadsheet?

Run `python examples/naukri_client.py search "<role>" --location <city> --pages 3 --csv jobs.csv`. Each row is one card with the job id, title, company, experience range in years, salary in lakh per annum when shown, cities, work mode, tags and post age. For a summary per market, use `naukri_market.py --csv`.

### Is there a Naukri jobs API for salaries?

Only for jobs that print one. In our samples 22% to 50% of cards showed a salary. The sidebar's salary filter gives counts for the whole result set, in overlapping bands, and each job page adds an AmbitionBox estimate for the role at that company.

### Why does the job count change between runs?

The "1 - 20 of N" header returned different totals for the same URL across renders (10,551 most of the time, 1,224 in a few). Read page 1 more than once, or compare totals across pages, before you trust a single count.

### Can I scrape Naukri candidate profiles or the resume database?

No. That data sits behind a recruiter login, and scraping under login credentials breaks ScrapingBee's terms. This repo reads logged out job pages only.

### Which ScrapingBee settings does Naukri need?

`render_js=true`, `block_resources=false` and `country_code=in` on a classic proxy, 5 credits per page. Without JavaScript you get a loading splash; with default resource blocking, the app crashes and returns an error page.

## License

MIT. See [LICENSE](LICENSE).
