import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
from src.utils.paths import SOCIAL_COOKIES_FILE, SOCIAL_DUMP_DOM_FILE
from src.utils.logger import get_logger

logger = get_logger("squad.social.scraper")

async def scrape_facebook(scrolls: int = 50, headless: bool = True):
    if not SOCIAL_COOKIES_FILE.exists():
        logger.error(f"❌ Arquivo de cookies não encontrado em: {SOCIAL_COOKIES_FILE}")
        return None

    with open(SOCIAL_COOKIES_FILE, "r", encoding="utf-8") as f:
        raw_cookies = json.load(f)

    playwright_cookies = [
        {
            "name": c.get("name", ""),
            "value": c.get("value", ""),
            "domain": c.get("domain", ""),
            "path": c.get("path", "/")
        }
        for c in raw_cookies
    ]

    logger.info(f"Iniciando Playwright ({scrolls} rolagens)...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
            locale="pt-BR"
        )
        await context.add_cookies(playwright_cookies)
        page = await context.new_page()
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")

        group_url = "https://www.facebook.com/groups/724026074439014"
        logger.info("Acessando grupo do UnBook no Facebook...")
        await page.goto(group_url, timeout=60000)

        try:
            await page.wait_for_selector('div[role="feed"]', timeout=25000)
            logger.info("Feed carregado com sucesso.")
        except Exception as e:
            logger.error(f"Feed não encontrado: {e}")
            await browser.close()
            return None

        extracted_posts = {}

        for i in range(1, scrolls + 1):
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(250)
            await page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
            await page.wait_for_timeout(1500)

            posts_on_screen = await page.locator('div[aria-posinset]').all()
            for post in posts_on_screen:
                try:
                    pos = await post.get_attribute('aria-posinset')
                    if not pos or pos in extracted_posts:
                        continue

                    post_data = await post.evaluate("""(node) => {
                        const authorNode = node.querySelector('h2, h3, strong, [data-ad-rendering-role="profile_name"]');
                        const author = authorNode ? authorNode.innerText.split('\\n')[0].trim() : "Anônimo";

                        let mainMsg = "";
                        const msgNode = node.querySelector('[data-ad-rendering-role="story_message"]');
                        if (msgNode) {
                            mainMsg = msgNode.innerText.trim();
                        } else {
                            const textNodes = Array.from(node.querySelectorAll('div[dir="auto"]'));
                            for(let t of textNodes) {
                                if(t.innerText.length > 15 && !t.innerText.includes('Ver mais') && !t.innerText.includes(author)) { 
                                    mainMsg = t.innerText.trim(); 
                                    break; 
                                }
                            }
                        }
                        
                        const commentNodes = node.querySelectorAll('div[role="article"][aria-label*="mentário"], div[role="article"][aria-label*="esposta"]');
                        let replies = [];
                        commentNodes.forEach(c => {
                            replies.push({
                                meta: c.getAttribute('aria-label') || "",
                                raw_text: c.innerText.trim()
                            });
                        });
                        
                        return { author: author, question: mainMsg, replies: replies };
                    }""")

                    if len(post_data["question"]) > 5:
                        extracted_posts[pos] = post_data
                except Exception:
                    continue

        await browser.close()

        sorted_keys = sorted([int(k) for k in extracted_posts.keys()])
        final_json = [extracted_posts[str(k)] for k in sorted_keys]

        SOCIAL_DUMP_DOM_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SOCIAL_DUMP_DOM_FILE, "w", encoding="utf-8") as f:
            json.dump(final_json, f, ensure_ascii=False, indent=4)

        logger.info(f"✅ {len(final_json)} posts brutos salvos em: {SOCIAL_DUMP_DOM_FILE.name}")
        return SOCIAL_DUMP_DOM_FILE