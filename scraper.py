
import asyncio
import json
import random
import re
from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from thefuzz import fuzz, process
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

OUTPUT_FILE = "frontend-poc/src/tournaments.json"

async def scrape_rankedin():
    events = []
    print("🚀 Starting Rankedin Scraper (Real Data)...")
    
    geolocator = Nominatim(user_agent="padel_scraper_poc")
    location_cache = {}

    def get_coords(city_name):
        if city_name in location_cache: return location_cache[city_name]
        try:
            loc = geolocator.geocode(f"{city_name}, Sweden", timeout=2)
            if loc:
                location_cache[city_name] = (loc.latitude, loc.longitude)
                return (loc.latitude, loc.longitude)
        except:
             pass
        return (None, None)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        page = await browser.new_page()
        
        # 1. Navigation
        print("🌍 Navigating to https://rankedin.com/en/tournament/search...")
        await page.goto("https://rankedin.com/en/tournament/search", timeout=60000)
        
        # Cookie Consent (Try to click 'Accept' or similar)
        try:
            print("🍪 Clicking Cookie Consent...")
            await page.get_by_role("button", name="Accept").click(timeout=3000)
        except:
            pass

        # 2. Broad Search Strategy: National + Local + Time-based
        # We combine:
        # A. Country ("Sweden")
        # B. Months (Jan-Jun)
        # C. Major Cities (Stockholm, Gbg, Malmö)
        # D. User's Local Region (Lidköping, Skara, Skövde)
        queries = [
            "Sweden", 
            "Januari", "Februari", "Mars", "April", "Maj", "Juni",
            "SPT", "Vista", "Svenska Padelligan",
            "Stockholm", "Göteborg", "Malmö", "Helsingborg", "Uppsala", "Västerås", "Örebro", "Linköping",
            "Lidköping", "Skara", "Skövde", "Mariestad", "Vara", "Trollhättan"
        ]
        
        # Foreign Blocklist (Expanded)
        DENMARK_KEYWORDS = [
            "Denmark", "Danmark", "København", "Smash", "Tuborg", "Carlsberg", "Flammen", "State", 
            "Padelhall Skive", "Odense", "Sarajevo", "Karakal", "Riga", "Latvia", "Hills Open", "Finnish",
            "Slovenia", "Ljubljana", "Luxembourg", "Lithuania"
        ]

        for query in queries:
            print(f"🔎 Performing broad search for: '{query}'...")
            
            try:
                # FIX: Handle multiple search inputs (mobile/desktop duplicates)
                search_box = page.get_by_placeholder("Search").first
                await search_box.click()
                await search_box.fill(query)
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(2500) # Slightly faster wait
                
                # Scroll a bit
                await page.mouse.wheel(0, 4000)
                await page.wait_for_timeout(1000)

                # Check results
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                links = soup.select('a[href*="/tournament/"]')
                
                for link in links:
                    href = link.get('href')
                    if any(x in href.lower() for x in ["search", "create", "login", "manage"]): continue
                    
                    full_url = f"https://rankedin.com{href}" if href.startswith("/") else href
                    title = link.get_text(strip=True)
                    
                    # Fallback title
                    if len(title) < 5:
                        parent = link.find_parent('div')
                        if parent: 
                            title = parent.get_text(" ", strip=True)

                    # Deduplication
                    if any(e['url'] == full_url for e in events): continue
                    
                    # Context for checks
                    card_div = link.find_parent('div')
                    card_text = card_div.get_text(" ", strip=True) if card_div else ""
                    text_blob = (title + " " + card_text).lower()

                    # FILTER: Danish/Foreign Check
                    if any(dk.lower() in text_blob for dk in DENMARK_KEYWORDS):
                        print(f"   🇩🇰 Skipping likely Danish event: {title[:30]}...")
                        continue

                    # FILTER Logic V3 (Strict 2026):
                    
                    # 1. Explicate Year Exclusion
                    # If it explicitly says a past year, kill it.
                    if any(y in text_blob for y in ["2020", "2021", "2022", "2023", "2024", "2025"]):
                         # UNLESS it explicitly mentions 2026 (e.g. "Winter 2025/2026")
                         if "2026" not in text_blob:
                             print(f"   🚫 Skipping past year event: {title[:30]}...")
                             continue

                    # 2. Month-based filtering
                    # We only want Q1/Q2 2026. 
                    # If it says "Dec", "Nov", "Oct" and NOT "2026", it's likely late 2025.
                    bad_months = ["dec", "nov", "oct", "sep", "aug"]
                    if any(m in text_blob for m in bad_months):
                        if "2026" not in text_blob:
                             print(f"   🚫 Skipping late 2025 event: {title[:30]}...")
                             continue

                    # 3. Inclusion Logic
                    # Must contain "2026" OR a valid 2026 month (Jan-Jul)
                    valid_years = ["2026"]
                    valid_months = ["jan", "feb", "mar", "apr", "may", "maj", "jun", "jul"] 
                    
                    has_year = any(y in text_blob for y in valid_years)
                    has_month = any(m in text_blob for m in valid_months)
                    
                    if not (has_year or has_month):
                         # If strictly no date cues found, we skip.
                         # The previous "Open" fallback was letting 2025 events through.
                         print(f"   ⚠️ Skipping uncertain date: {title[:30]}...")
                         continue

                    # Date Parsing Logic
                    # Look for patterns like "17 Jan", "23-25 Jan", "09 Jan 2026" in card_text
                    # Simple month mapping
                    months_sv = {
                        "jan": "01", "feb": "02", "mar": "03", "apr": "04", "maj": "05", "jun": "06",
                        "jul": "07", "aug": "08", "sep": "09", "okt": "10", "nov": "11", "dec": "12",
                        "januari": "01", "februari": "02", "mars": "03", "april": "04", "juni": "06", "juli": "07"
                    }

                    parsed_date = "2026-??-??" # Default to unknown but 2026
                    
                    # Regex strategies (in order of preference)
                    
                    # 1. "DD Month" (e.g. "17 Jan" or "17-19 Jan")
                    # Added \b to ensure we don't match "2026" as "20"
                    date_match_text = re.search(r"\b(\d{1,2})(?:-\d{1,2})?\s+([a-zA-Zäåö]+)", text_blob, re.IGNORECASE)
                    
                    # 2. "DD/MM" (e.g. "17/1" or "17/01")
                    date_match_slash = re.search(r"\b(\d{1,2})/(\d{1,2})", text_blob)

                    if date_match_slash:
                         day = date_match_slash.group(1).zfill(2)
                         month_num = date_match_slash.group(2).zfill(2)
                         # Validate month
                         if 1 <= int(month_num) <= 12:
                             parsed_date = f"2026-{month_num}-{day}"

                    elif date_match_text:
                        day = date_match_text.group(1).zfill(2)
                        month_str = date_match_text.group(2).lower()[:3] 
                        
                        month_num = months_sv.get(month_str)
                        if not month_num:
                             months_en = {"jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05"}
                             month_num = months_en.get(month_str)
                        
                        if month_num:
                            parsed_date = f"2026-{month_num}-{day}"
                    
                    # 3. Fallback: Just finding a month name
                    if parsed_date == "2026-??-??":
                         for m_name, m_num in months_sv.items():
                             if f" {m_name}" in text_blob or f"{m_name} " in text_blob:
                                 parsed_date = f"2026-{m_num}-??"
                                 break # Exit after finding the first month

                    # Initialize city to None first
                    city = None

                    # Expanded list of Swedish cities/towns for extraction
                    common_cities = [
                        "Stockholm", "Göteborg", "Malmö", "Helsingborg", "Uppsala", "Västerås", "Örebro", 
                        "Linköping", "Lidköping", "Skara", "Skövde", "Mariestad", "Vara", "Trollhättan",
                        "Borås", "Eskilstuna", "Gävle", "Södertälje", "Norrköping", "Jönköping", "Växjö",
                        "Halmstad", "Karlstad", "Lund", "Umeå", "Luleå", "Sundsvall", "Kalmar", "Falkenberg",
                        "Varberg", "Uddevalla", "Skellefteå", "Karlskrona", "Kristianstad", "Visby",
                        "Landskrona", "Trelleborg", "Motala", "Östersund", "Ängelholm", "Lidingö",
                        "Alingsås", "Lerum", "Enköping", "Vänersborg", "Huddinge", "Nacka", "Sollentuna"
                    ]
                    
                    # 1. Check Title (High confidence)
                    for c in common_cities:
                        if c.lower() in title.lower():
                            city = c
                            break
                    
                    # 2. Check Text Blob (which contains club/location text)
                    if not city:
                         for c in common_cities:
                            if c.lower() in text_blob.lower():
                                city = c
                                break
                    
                    # 3. Fallback
                    if not city:
                        city = "Sverige"

                    lat, lon = get_coords(city)
                    # If geocoding failed, ensure lat/lon are None, None
                    if lat is None or lon is None:
                        lat, lon = None, None
                    
                    events.append({
                        "id": abs(hash(full_url)),
                        "title": title[:60] + "..." if len(title) > 60 else title,
                        "club": "Rankedin Verified",
                        "city": city, 
                        "lat": lat,
                        "lon": lon,
                        "date": parsed_date,
                        "level": "Open",
                        "type": "Turnering",
                        "source": "Rankedin",
                        "url": full_url
                    })
                    
            except Exception as e:
                print(f"   ⚠️ Search '{query}' failed: {e}") 


        # Remove duplicate dictionaries
        seen = set()
        unique_events = []
        for e in events:
            if e['url'] not in seen:
                unique_events.append(e)
                seen.add(e['url'])
        
        return unique_events

        # ... (Old code commented out or removed by flow) ...


        # Scroll to load more items (Simulation)
        for i in range(3):
            print(f"📜 Scrolling page {i+1}...")
            await page.mouse.wheel(0, 3000)
            await page.wait_for_timeout(2000)
            
        # Screenshot for debugging
        await page.screenshot(path="rankedin_debug.png")
        print("📸 Screenshot saved to rankedin_debug.png")
        
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Selectors update: Look for generic links but filter aggressively
        # We also look for specific card classes if generic links fail
        tournament_links = soup.select('a[href*="/tournament/"]')
        if len(tournament_links) < 5:
             # Try looking for div containers that might have onclick or internal structure
             print("⚠️ Few links found, checking card containers...")
             cards = soup.select('div[class*="tournament"], div[class*="card"]')
             print(f"   Found {len(cards)} card containers.")

        print(f"🔍 Found {len(tournament_links)} raw links.")

        seen_ids = set()

        for link in tournament_links:
            try:
                href = link.get('href', '')
                if not href: continue
                
                # FILTER: Exclude "create", "search", "login"
                if any(x in href.lower() for x in ["/create", "/edit", "/manage", "login"]):
                    print(f"  Start Refusing {href} (admin link)")
                    continue
                
                # FILTER: Exclude titles that look like buttons
                title = link.get_text(strip=True)
                # Fallback to parent title
                if len(title) < 5:
                    parent = link.find_parent('div')
                    if parent:
                        title_el = parent.select_one('h3, h4, .title, strong')
                        if title_el:
                            title = title_el.get_text(strip=True)

                if any(x in title.lower() for x in ["create", "search", "my tournaments", "home"]):
                    print(f"  Refusing {href} ('{title}')")
                    continue

                # Heuristics for Swedish events
                # If we scraped a global list, we must filter.
                # If we can't find location, we might just include it and let the user filter.
                # But let's try to look for Sweden/Sverige or known cities.
                # Since we are just grabbing links often, we might miss the location text if it's separate.
                # For this "POC Scraper", we will assume if we found it on a "Sweden" search (if filtering worked) it's valid.
                # Or we check typical city names.
                
                is_swedish = False
                city = "Sweden"
                common_cities = ["Stockholm", "Göteborg", "Malmö", "Helsingborg", "Uppsala", "Västerås", "Norrköping", "Örebro", "Linköping"]
                
                # We need to look at the surrounding text of the link to find city/date
                card_text = link.find_parent('div').get_text(" ", strip=True) if link.find_parent('div') else ""
                
                for c in common_cities:
                    if c in card_text or "Sweden" in card_text or "Sverige" in card_text:
                        is_swedish = True
                        city = c if c in card_text else "Sweden"
                        break
                
                # If we can't confirm Swedish, we stick it in anyway for the demo, 
                # PROD would need stricter filtering.
                
                # Date Parsing - Extremely simplified for POC
                date = "2026-05-01" # Placeholder for future
                
                events.append({
                    "id": abs(hash(full_url)),
                    "title": title,
                    "club": "Rankedin Club",
                    "city": city,
                    "date": date,
                    "level": "Öppen", # Placeholder
                    "type": "Turnering",
                    "source": "Rankedin",
                    "url": full_url
                })
                
                if len(events) >= 10: # Limit for POC
                    break

            except Exception as e:
                continue

        await browser.close()
    
    return events



async def scrape_matchi_tv():
    events = []
    print("🚀 Starting Matchi TV Scraper...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # User provided verified source
        url = "https://matchi.tv/events?c=-1&t=0&il=false"
        print(f"🌍 Navigating to {url}...")
        
        try:
            await page.goto(url, timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Extract events
            # Structure from user text suggests valid text content.
            # We look for event cards.
            # Selectors are guesses based on standard UI, but we can be generic.
            
            # Generic item selector
            items = page.locator("a[href^='/event/'], div[class*='event-card'], div[class*='EventCard']")
            count = await items.count()
            print(f"🔍 Found {count} potential events on Matchi TV.")
            
            if count == 0:
                 # Fallback: Try looking for any links with dates
                 items = page.locator("a")
            
            # Known Swedish Clubs/Cities filter (simple version)
            swedish_keywords = ["Vislanda", "Ekerö", "Halmstad", "Sweden", "Sverige", "Stockholm", "Göteborg", "Malmö"]

            captured = 0
            for i in range(count):
                if captured > 10: break
                item = items.nth(i)
                text = await item.inner_text()
                href = await item.get_attribute("href")
                
                # Filter: Must be 2026
                if "2026" not in text: continue

                # Filter: Must be Swedish (heuristic)
                is_swedish = any(k in text for k in swedish_keywords)
                # Matchi TV lists international, so we skip obvious Danish/Canadian ones
                if "Denmark" in text or "Nisku" in text or "Silkeborg" in text or "Skive" in text:
                    continue
                
                if not is_swedish:
                    # If we can't be sure, skip for safety to keep data clean
                    continue
                    
                full_url = f"https://matchi.tv{href}" if href and href.startswith("/") else href
                
                # Parse title
                lines = text.split("\n")
                title = lines[0]
                for line in lines:
                    if len(line) > 5 and not line[0].isdigit():
                        title = line
                        break
                
                # Club guessing
                club = "Matchi Facility"
                for line in lines:
                    if "Padel" in line or "Center" in line or "Club" in line:
                        club = line

                events.append({
                    "id": abs(hash(full_url)),
                    "title": title,
                    "club": club,
                    "city": "Sweden", 
                    "date": "2026-01-??", # Hard to parse exact date from blob without fuzzy date parser
                    "level": "Open",
                    "type": "Turnering",
                    "source": "Matchi TV",
                    "url": full_url
                })
                captured += 1
                print(f"   ✅ Added Matchi Event: {title}")

        except Exception as e:
            print(f"⚠️ Matchi TV scrape error: {e}")

        await browser.close()
    return events

async def scrape_duckduckgo_regional():
    events = []
    print("🚀 Starting DuckDuckGo Regional Scraper (Lidköping + 50km)...")
    
    # Focused list on Lidköping region
    cities = ["Lidköping", "Skara", "Skövde", "Mariestad", "Vara", "Vänersborg", "Trollhättan"]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        for city in cities:
            query = f'site:matchi.se "padel" "turnering" "{city}" 2026'
            print(f"🦆 Searching DDG for: {query}...")
            
            try:
                await page.goto(f"https://duckduckgo.com/?q={query}&kl=se-sv", timeout=30000)
                await page.wait_for_timeout(2000)
                
                # Extract results
                results = page.locator("article h2 a")
                count = await results.count()
                
                for i in range(min(count, 3)): # Top 3 per city
                    link = results.nth(i)
                    title = await link.inner_text()
                    href = await link.get_attribute("href")
                    
                    if "2026" in title or "2026" in (await page.content()): # content check weak here, improved below
                         # Basic sanity check
                         if not href: continue
                         
                         events.append({
                            "id": abs(hash(href)),
                            "title": f"🔍 {title}", # Prefix to show it's a search result
                            "club": "Okänd (Google Resultat)",
                            "city": city, 
                            "lat": None,
                            "lon": None,
                            "date": "2026-??-??", # Hard to parse from Google snippet
                            "level": "Unknown",
                            "type": "Webbträff",
                            "source": "Google/DDG",
                            "url": href
                        })
            except Exception as e:
                print(f"   ⚠️ DDG Error for {city}: {e}")

        await browser.close()
    return events

async def main():
    # Run scraper
    rankedin_events = await scrape_rankedin()
    ddg_events = await scrape_duckduckgo_regional()
    
    all_events = rankedin_events + ddg_events
    
    # Save to JSON
    print(f"💾 Saving {len(all_events)} events to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_events, f, indent=2, ensure_ascii=False)
    print("✅ Done!")



if __name__ == "__main__":
    asyncio.run(main())
