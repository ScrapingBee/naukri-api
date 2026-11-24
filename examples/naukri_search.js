// Naukri search page to JSON lines, Node 18+ (global fetch), no dependencies.
//
//   export SCRAPINGBEE_API_KEY=...
//   node naukri_search.js "data analyst" pune 1
//
// Arguments: keyword, optional city, optional page number.

const API = "https://app.scrapingbee.com/api/v1/";

const RULES = {
  count: { selector: "span[class^='styles_count-string']", output: "@title" },
  jobs: {
    selector: "div.srp-jobtuple-wrapper",
    type: "list",
    output: {
      id: { selector: "div.srp-jobtuple-wrapper", output: "@data-job-id" },
      title: "a.title",
      url: { selector: "a.title", output: "@href" },
      company: "a.comp-name",
      experience: "span.expwdth",
      salary: "span.sal-wrap span[title]",
      location: "span.locWdth",
      tags: { selector: "ul.tags-gt li", type: "list" },
      posted: "span.job-post-day",
    },
  },
};

const slug = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

function searchUrl(keyword, city, page) {
  let path = `${slug(keyword)}-jobs`;
  if (city) path += `-in-${slug(city)}`;
  if (page > 1) path += `-${page}`;
  return `https://www.naukri.com/${path}`;
}

async function scrape(url, tries = 3) {
  const params = new URLSearchParams({
    url,
    render_js: "true",
    block_resources: "false", // with blocking on, the Next.js app throws a client-side exception
    country_code: "in",
    wait_for: "div.srp-jobtuple-wrapper",
    extract_rules: JSON.stringify(RULES),
  });
  for (let attempt = 1; attempt <= tries; attempt++) {
    const res = await fetch(`${API}?${params}`, {
      headers: { Authorization: `Bearer ${process.env.SCRAPINGBEE_API_KEY}` },
    });
    const cost = Number(res.headers.get("spb-cost") || 0);
    if (res.status === 500 && attempt < tries) {
      // not billed by ScrapingBee, so retrying costs nothing
      await new Promise((r) => setTimeout(r, 2000 * attempt));
      continue;
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${(await res.text()).slice(0, 200)}`);
    return { data: await res.json(), cost };
  }
  throw new Error(`gave up on ${url}`);
}

async function main() {
  if (!process.env.SCRAPINGBEE_API_KEY) throw new Error("set SCRAPINGBEE_API_KEY");
  const [keyword = "data analyst", city = "", page = "1"] = process.argv.slice(2);
  const url = searchUrl(keyword, city, Number(page));
  const { data, cost } = await scrape(url);
  const jobs = data.jobs || [];
  for (const j of jobs) {
    console.log(JSON.stringify({ ...j, salary: j.salary || null }));
  }
  const withSalary = jobs.filter((j) => j.salary).length;
  console.error(`${url}\n${(data.count || "").trim()}, ${jobs.length} cards, ${withSalary} with a salary, ${cost} credits`);
}

main().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
