# Padel Tournament Scraper Assessment

## Executive Summary

Building a unified scraper for Swedish padel tournaments is **Technically Feasible** but has a **High Maintenance Difficulty**. The data is highly fragmented across competing platforms (Rankedin, Matchi, Playtomic) and the national federation.

**Overall Difficulty Score: 8/10**
_(1 = Easy/Static, 10 = Extremely Hard/Anti-bot/Captcha)_

## 1. Fragmentation Analysis

The Swedish padel ecosystem does not have a single source of truth. A complete aggregator must scrape at least 3-4 distinct silos:

| Platform         | Role                                  | Tech Stack Estimation                             | Difficulty     |
| :--------------- | :------------------------------------ | :------------------------------------------------ | :------------- |
| **Rankedin**     | Primary tool for serious tournaments. | Dynamic (React/Vue), likely strict anti-bot.      | **High**       |
| **Svensk Padel** | Official Federation calendar.         | Traditional Web (WordPress similar), Table-based. | **Medium**     |
| **Matchi**       | Club-level booking & activities.      | Dynamic, very high load, strict API security.     | **High**       |
| **Playtomic**    | Club-level booking global.            | Mobile-first, complex web API.                    | **High**       |
| **PadelDirekt**  | News & Discovery.                     | Standard Content Site.                            | **Low/Medium** |

## 2. Seriespel (League Play) Feasibility

**Overview:** League play ("Seriespel") is distinct from tournaments and often managed on specialized platforms.

- **Ligaspel.se**: The most common platform for local leagues.
  - **Difficulty**: **Very High**. Heavy use of login walls for detailed match data. Anti-scraping measures (IP bans) are likely.
- **Backhandsmash**: Another classic platform.
  - **Difficulty**: **High**. Often requires player login to see specific division standings.
- **Rankedin/Matchi Leagues**:
  - **Difficulty**: **High**. Similar to their tournament modules, these are dynamic and protected.

**Conclusion for Leagues**: Scraping "Seriespel" is significantly harder than tournaments because much of the data is behind login walls (for privacy or member-only reasons).

## 3. Other Event Types

Beyond formal tournaments, "Events" in padel often fall into these categories:

| Event Type               | Typical Source                          | Scraping Strategy                                                                               | Difficulty                            |
| :----------------------- | :-------------------------------------- | :---------------------------------------------------------------------------------------------- | :------------------------------------ |
| **Americano / Mexicano** | Matchi / Playtomic "Activities"         | These are listed differently than tournaments. filtered by "Type: Competition".                 | **Medium**                            |
| **Clinics / Courses**    | Swedish Padel Camp, specific Club sites | Highly fragmented. No central aggregator. Requires scraping 10+ individual sites.               | **Very High** (Maintenance nightmare) |
| **Social / Mix-ins**     | Matchi Activities, Facebook Groups      | "Activities" are scrapable. Facebook is effectively impossible to scrape at scale without bans. | **High**                              |

### Key Challenge: Data Normalization

Each source formats dates, locations, and levels (B-class, C-class, etc.) differently.

## 4. Social Media & Image Scraping (Instagram/Facebook)

Users often ask about scraping flyers from Instagram.

| Method                  | Source               | Feasibility       | Verdict                                                                                                |
| :---------------------- | :------------------- | :---------------- | :----------------------------------------------------------------------------------------------------- |
| **Direct Scraping**     | Instagram / Facebook | **Extremely Low** | Meta aggressively blocks scrapers. Requires login, IP rotation, and high maintenance. Not recommended. |
| **OCR (Image Reading)** | Flyer Images         | **Low**           | Requires "Computer Vision" to read text from pixels. Error-prone with creative fonts.                  |

**Recommendation**: Most flyers (like the "NPC Open" example) explicitly say **"Anmälan via Rankedin"**. It is far more efficient to scrape the _source_ (Rankedin) than the advertisement (Instagram).

- **Rankedin**: structured but complex metadata.
- **Svensk Padel**: often unstructured text in table cells.
- **Matchi/Playtomic**: often focused on "activities" rather than formal "tournaments".

**Solution: Fuzzy Matching**
To unify data (e.g., "Padel Crew Helsingborg" vs "Padel Crew Hbg"), use fuzzy logic libraries like `thefuzz` or `rapidfuzz`.

- **Strategy**: Maintain a canonical list of Clubs/Cities. When scraping, match the scraped string to the closest canonical value with a high confidence threshold (>90%).
- **Benefit**: Handles typos, abbreviations, and slight formatting differences automatically.

## 2. Maintenance Overhead

The cost of building the scraper is one-time, but the cost of _maintenance_ is perpetual.

- **Brittle Selectors**: Rankedin and Matchi update their UIs frequently. A CSS selector like `div.tournament-card` may break simply because they renamed a class for styling.
- **Anti-Bot Countermeasures**: If you scrape too aggressively (e.g., once an hour), you _will_ be IP banned. You will need:
  - Rotating Proxies (Monthly cost ~$10-50).
  - Headless Browser infrastructure (Playwright/Selenium).
- **Format Drift**: If Svensk Padel changes their table columns, your parser will start ingesting garbage data until fixed.

**Estimated Maintenance:** 2-4 hours per month to fix broken parsers.

## 3. Conceptual Technical Approach

Do not use simple `requests` or `curl`. You must use a browser automation tool like **Playwright** to handle the dynamic JavaScript rendering of Rankedin and Matchi.

### Proposed Stack

- **Language**: Python 3.10+
- **Core Lib**: `playwright` (for rendering JS and handling navigation).
- **Parsing**: `beautifulsoup4` (faster parsing of the rendered HTML).
- **Scheduler**: GitHub Actions (if low frequency) or a small VPS (DigitalOcean/Hetzner).

### Example Workflow

1. **Launch Browser**: Headless Chromium instance.
2. **Inject Stealth Scripts**: Hide WebDriver flags to avoid immediate detection.
3. **Navigate & Scroll**: Go to Rankedin Calendar -> Scroll to bottom 5 times to load all events.
4. **Extract Raw HTML**: Dump the fully rendered DOM.
5. **Parse & Normalize**: Extract dates/names, convert to ISO 8601 dates.
6. **Upsert to DB**: Save to SQLite/Postgres to avoid duplicates.

## 4. Legal & Ethical Note

_Scraping public data is generally legal, but bypassing authentication or ignoring `robots.txt` can be problematic. Rankedin and Matchi terms of service likely forbid automated collection._

- **Guidance**: Scrape slowly (1 request per 10-20 seconds). Respect `robots.txt`. Do not use the data to build a direct commercial competitor without legal counsel.

## Recommendation

If this is for a personal project or small club utility, proceed with **Playwright**.
If this is for a commercial product, **contact Rankedin/Matchi for an official API partner key**. The scraping route is fragile and significantly risky for a business.
