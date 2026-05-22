import json
import logging
import re
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from src.utils.config import get_linkedin_email, get_linkedin_password

logger = logging.getLogger(__name__)

LOGIN_URL = "https://www.linkedin.com/checkpoint/lg/sign-in-another-account"


def _scrape_about(page) -> str:
    logger.info("Scraping About section")
    try:
        about_section = page.locator("section:has(h2:has-text('About'))")
        if about_section.count() == 0:
            about_section = page.locator("#about")
        if about_section.count() == 0:
            about_section = page.locator("article:has(h2:has-text('About'))")
        if about_section.count() == 0:
            logger.warning("About section not found on profile")
            return ""

        see_more = about_section.locator("button:has-text('see more')")
        if see_more.count() == 0:
            see_more = about_section.locator("button:has-text('Show more')")
        if see_more.count() == 0:
            see_more = about_section.locator("[aria-label*='see more' i]")
        if see_more.count() > 0:
            logger.info("Clicking 'see more' in About section")
            see_more.first.click()
            page.wait_for_timeout(1000)

        text = about_section.first.inner_text()
        text = re.sub(r'\s+', ' ', text).strip()
        text = text.replace("About", "", 1).strip()
        logger.info("About section extracted (%d chars)", len(text))
        return text
    except Exception as e:
        logger.warning("Failed to scrape About section: %s", e)
        return ""


def _parse_experience_text(full_text: str) -> dict:
    lines = [l.strip() for l in full_text.split("\n") if l.strip()]

    entry = {
        "title": "",
        "company": "",
        "employment_type": "",
        "location": "",
        "mode": "",
        "dates": "",
        "duration": "",
        "description": "",
        "skills": [],
    }

    if not lines:
        return entry

    entry["title"] = lines[0]

    for idx, line in enumerate(lines):
        if line.startswith("Skills:") or line.startswith("skills:"):
            skills_text = line.split(":", 1)[1].strip()
            entry["skills"] = [s.strip() for s in re.split(r"\s*[·•|]\s*", skills_text) if s.strip()]
            lines = lines[:idx]
            break

    rest = lines[1:]

    def try_split_parts(text: str) -> list[str]:
        return [p.strip() for p in re.split(r"\s*[·•]\s*", text) if p.strip()]

    consumed = 0
    if rest:
        parts = try_split_parts(rest[0])
        if any(kw in rest[0] for kw in ["Full-time", "Part-time", "Contract", "Internship", "Self-employed", "Freelance", "Temporary"]):
            entry["company"] = parts[0] if parts else rest[0]
            entry["employment_type"] = next((kw for kw in ["Full-time", "Part-time", "Contract", "Internship", "Self-employed", "Freelance", "Temporary"] if kw in rest[0]), "")
            consumed = 1

    if len(rest) > consumed:
        parts = try_split_parts(rest[consumed])
        if parts:
            date_pattern = r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Present)"
            if any(re.search(date_pattern, p) for p in parts):
                entry["dates"] = parts[0] if len(parts) > 0 else rest[consumed]
                entry["duration"] = parts[1] if len(parts) > 1 else ""
                consumed += 1

    if len(rest) > consumed:
        parts = try_split_parts(rest[consumed])
        if parts and not any(kw in rest[consumed] for kw in ["yr", "year", "Full-time", "Part-time"]):
            loc_candidates = [p for p in parts if not any(kw in p.lower() for kw in ["yr", "year", "mos", "month"])]
            mode_candidates = [p for p in parts if p.lower() in ["remote", "hybrid", "on-site", "on site"]]
            if loc_candidates:
                entry["location"] = loc_candidates[0]
            if mode_candidates:
                entry["mode"] = mode_candidates[0]
            if not mode_candidates:
                for p in parts:
                    if p.lower() in ["remote", "hybrid", "on-site", "on site"]:
                        entry["mode"] = p
                        break
            if not loc_candidates and not mode_candidates:
                entry["location"] = parts[0]
            consumed += 1

    desc_lines = rest[consumed:]
    if desc_lines:
        entry["description"] = "\n\n".join(desc_lines)

    return entry


def _scrape_experience(page, profile_url: str) -> list[dict]:
    exp_url = profile_url.rstrip("/") + "/details/experience/"
    logger.info("Navigating to experience page: %s", exp_url)
    page.goto(exp_url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(4000)

    logger.info("Scraping experience entries")
    experiences = []

    items = page.locator("li.artdeco-list__item")
    if items.count() == 0:
        items = page.locator("[data-view-name='profile-components'] li")
    if items.count() == 0:
        items = page.locator("section:has(h2:has-text('Experience')) li")
    if items.count() == 0:
        items = page.locator("div.pvs-list__outer-container > ul > li")
    if items.count() == 0:
        items = page.locator("ul.pvs-list > li")

    count = items.count()
    logger.info("Found %d experience items", count)

    for i in range(count):
        item = items.nth(i)
        try:
            item.scroll_into_view_if_needed()
            page.wait_for_timeout(300)

            full_text = item.inner_text().strip()
            if not full_text:
                continue

            entry = _parse_experience_text(full_text)
            if not entry["title"]:
                continue

            experiences.append(entry)
            logger.info(
                "  → %s @ %s (%s, %s)",
                entry["title"], entry["company"], entry["dates"], entry["employment_type"],
            )
        except Exception as e:
            logger.warning("Failed to parse experience item %d: %s", i, e)
            continue

    return experiences


def scrape_linkedin_profile(url: str, timeout_ms: int = 60000) -> dict:
    logger.info("BG Verification requested for URL: %s", url)

    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
        logger.info("Normalized URL to: %s", url)

    if not re.match(r'https?://(www\.)?linkedin\.com/in/[\w\-%]+', url, re.IGNORECASE):
        logger.warning("Invalid LinkedIn URL: %s", url)
        return {"status": "error", "message": "Invalid LinkedIn URL"}

    try:
        email = get_linkedin_email()
        password = get_linkedin_password()
        logger.info("LinkedIn credentials loaded successfully")
    except ValueError as e:
        logger.error("LinkedIn credentials not configured: %s", e)
        return {"status": "error", "message": str(e)}

    try:
        with sync_playwright() as p:
            logger.info("Launching Chromium browser (visible mode)")
            browser = p.chromium.launch(
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 720},
            )
            page = context.new_page()
            logger.info("Navigating to LinkedIn login page")
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_timeout(2000)
            logger.info("Login page loaded — URL: %s", page.url)

            username_input = page.locator("#username")
            if not username_input.is_visible(timeout=5000):
                logger.error("Username field not found on login page")
                browser.close()
                return {"status": "error", "message": "LinkedIn login page did not load correctly — #username field not found"}

            logger.info("Filling login credentials")
            username_input.fill(email)
            page.locator("#password").fill(password)
            page.locator("button[type='submit']").click()
            logger.info("Login form submitted — waiting for redirect away from checkpoint")

            page.wait_for_load_state("load", timeout=timeout_ms)
            page.wait_for_timeout(3000)
            logger.info("Post-login URL: %s", page.url)

            if "checkpoint" in page.url.lower():
                body_text = page.inner_text("body")
                if "incorrect" in body_text.lower() or "wrong" in body_text.lower():
                    logger.error("Login failed — incorrect credentials")
                    browser.close()
                    return {"status": "error", "message": "LinkedIn login failed — incorrect email or password"}
                if "security" in body_text.lower() or "verify" in body_text.lower():
                    logger.error("Login blocked — 2FA/security challenge")
                    browser.close()
                    return {"status": "error", "message": "LinkedIn requires additional verification (2FA) — cannot automate"}
                logger.error("Login failed — still on checkpoint page")
                browser.close()
                return {"status": "error", "message": "LinkedIn login failed — still on checkpoint page"}

            logger.info("Login successful — navigating to profile: %s", url)
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_timeout(4000)
            logger.info("Profile page loaded — URL: %s", page.url)

            about_text = _scrape_about(page)

            experiences = _scrape_experience(page, url)

            browser.close()
            logger.info("Browser closed")

            print("\n" + "=" * 80)
            print("  LINKEDIN BG VERIFICATION RESULT")
            print("=" * 80)
            print("\n--- ABOUT ---")
            print(about_text if about_text else "(not found)")
            print("\n--- EXPERIENCE ---")
            if experiences:
                for i, exp in enumerate(experiences, 1):
                    print(f"\n  [{i}] {exp['title']}")
                    print(f"      Company:        {exp['company']}")
                    print(f"      Employment:     {exp['employment_type']}")
                    print(f"      Dates:          {exp['dates']}")
                    print(f"      Duration:       {exp['duration']}")
                    print(f"      Location:       {exp['location']}")
                    print(f"      Mode:           {exp['mode']}")
                    print(f"      Skills:         {', '.join(exp['skills']) if exp['skills'] else '(none)'}")
                    print(f"      Description:    {exp['description'][:300]}{'...' if len(exp['description']) > 300 else ''}")
            else:
                print("  (no experience entries found)")
            print("\n" + "=" * 80 + "\n")

            return {
                "status": "success",
                "message": "",
                "about": about_text,
                "experience": experiences,
            }

    except PlaywrightTimeout:
        logger.error("Timeout while loading LinkedIn page")
        return {"status": "error", "message": "Request timed out while loading the LinkedIn profile", "about": "", "experience": []}
    except Exception as e:
        logger.error("Scraping failed: %s", str(e), exc_info=True)
        return {"status": "error", "message": f"Scraping failed: {str(e)}", "about": "", "experience": []}
