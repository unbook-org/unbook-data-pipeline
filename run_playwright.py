import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

async def scrape_facebook_by_dom():
    cookies_path = Path("fb_cookies.json")
    if not cookies_path.exists():
        print("❌ ERRO: Arquivo 'fb_cookies.json' não encontrado!")
        return

    with open(cookies_path, "r", encoding="utf-8") as f:
        raw_cookies = json.load(f)

    playwright_cookies = [{"name": c.get("name", ""), "value": c.get("value", ""), "domain": c.get("domain", ""), "path": c.get("path", "/")} for c in raw_cookies]

    print("🚀 Iniciando Playwright (Extração Blindada Anti-Modal)...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False, 
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
        print("🌐 Acessando o grupo do UnBook no Facebook...")
        await page.goto(group_url, timeout=60000)

        try:
            await page.wait_for_selector('div[role="feed"]', timeout=25000)
            print("✅ Feed acessado! Iniciando extração cirúrgica...")
        except Exception as e:
            print(f"❌ Erro: O feed não carregou. Detalhes: {e}")
            await browser.close()
            return

        extracted_posts = {}
        num_scrolls = 500 

        for i in range(1, num_scrolls + 1):
            print(f"   ⬇️ Rolagem {i}/{num_scrolls}...")
            
            # 1. ATAQUE PREVENTIVO: Aperta ESCAPE para garantir que nenhum modal esteja aberto
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(300)

            # 2. Rolagem suave (80% da tela)
            await page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
            await page.wait_for_timeout(2000)

            # 3. EXTRAÇÃO VIA DOM (Sem clicar em nada)
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
                            const meta = c.getAttribute('aria-label') || "";
                            replies.push({
                                meta: meta,
                                raw_text: c.innerText.trim()
                            });
                        });
                        
                        return { author: author, question: mainMsg, replies: replies };
                    }""")

                    # Salva se tiver pergunta clara (não filtramos mais por replies para não perder dados à toa)
                    if len(post_data["question"]) > 5:
                        extracted_posts[pos] = post_data

                except Exception:
                    continue

        await browser.close()

        sorted_keys = sorted([int(k) for k in extracted_posts.keys()])
        final_json = [extracted_posts[str(k)] for k in sorted_keys]

        output_path = Path("data/raw/social/facebook_dump_dom.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(final_json, f, ensure_ascii=False, indent=4)

        print(f"🎉 SUCESSO! {len(final_json)} posts capturados e salvos em: {output_path}")

if __name__ == "__main__":
    asyncio.run(scrape_facebook_by_dom())