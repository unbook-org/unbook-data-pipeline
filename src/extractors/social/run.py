import asyncio
from src.extractors.social.scraper import scrape_facebook
from src.extractors.social.parser import run_social_parser
from src.utils.paths import SOCIAL_DUMP_DOM_FILE
from src.utils.logger import get_logger

logger = get_logger("Social-Orch")

def run_social_pipeline(scrape: bool = False, scrolls: int = 50, limit: int = None):
    """
    Se scrape=True ou dump não existir, executa Playwright.
    Em seguida, executa o parser para gerar o JSON final limpo.
    """
    if scrape or not SOCIAL_DUMP_DOM_FILE.exists():
        logger.info("Executando extração via Playwright...")
        asyncio.run(scrape_facebook(scrolls=scrolls, headless=True))

    results = run_social_parser()
    if limit and results:
        results = results[:limit]
    return results