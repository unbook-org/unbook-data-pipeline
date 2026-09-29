import sys
import json
from pathlib import Path
from typing import Optional
from scrapy.crawler import CrawlerProcess

from src.extractors.base import BaseExtractor
from src.extractors.sigaa.scrapy_app.prof_info.spiders.info_spider import InfoSpiderSpider
from src.transformers.sigaa_cleaner import run_classes_cleaner, run_sigaa_cleaner
from src.utils.logger import get_logger
from src.utils.paths import SIGAA_CLASSES_FILE, SIGAA_FINAL_RAW_FILE, SIGAA_PROCESSED_FILE, SIGAA_SEED_FILE

logger = get_logger("SIGAA-Orch")


class SigaaExtractor(BaseExtractor):
    """Extrator oficial da Squad SIGAA."""

    def extract(self, limit: Optional[int] = None):
        return run_sigaa_pipeline(limit=limit)


def run_sigaa_pipeline(
    limit: Optional[int] = None,
    scrape: bool = True,
    scrape_classes: bool = False,
    limit_depts: Optional[int] = None,
):
    """
    Executa a extração e transformação dos dados do SIGAA.
    Se scrape=True, executa a Spider do Scrapy para enriquecer o banco bruto.
    Se scrape_classes=True, executa o scraper Selenium para turmas abertas de todos os departamentos.
    Em seguida, executa o módulo de limpeza e unificação com o seed e turmas.
    """
    if scrape_classes:
        logger.info("Iniciando extração automatizada de turmas do SIGAA...")
        try:
            from src.extractors.sigaa.seed.get_classes import scrape_sigaa_classes

            scrape_sigaa_classes(limit_depts=limit_depts)
        except Exception as e:
            logger.error(f"Erro ao extrair turmas do SIGAA: {e}")

    if scrape:
        logger.info(f"Acessando {SIGAA_SEED_FILE.name} para extração de matérias e dados dos docentes...")
        logger.info(f"Iniciando Spider Scrapy... Limite: {limit if limit else 'Todos'}")

        SIGAA_FINAL_RAW_FILE.parent.mkdir(parents=True, exist_ok=True)

        settings = {
            "BOT_NAME": "ProfInfo",
            "ROBOTSTXT_OBEY": False,
            "COOKIES_ENABLED": False,
            "FEED_EXPORT_ENCODING": "utf-8",
            "CONCURRENT_REQUESTS": 32 if not limit or limit > 32 else limit,
            "CONCURRENT_REQUESTS_PER_DOMAIN": 32 if not limit or limit > 32 else limit,
            "DOWNLOAD_DELAY": 0.5,
            "LOG_LEVEL": "WARNING",
            "LOG_STDOUT": False,
            "STATS_DUMP": False,
            "FEEDS": {
                str(SIGAA_FINAL_RAW_FILE): {
                    "format": "json",
                    "encoding": "utf8",
                    "overwrite": True,
                    "indent": 4,
                }
            },
        }

        try:
            process = CrawlerProcess(settings)
            process.crawl(InfoSpiderSpider, limit=limit)
            process.start()
            logger.info(f"✅ Spider finalizada. Dados brutos salvos em: {SIGAA_FINAL_RAW_FILE.name}")
        except Exception as e:
            logger.warning(f"Spider não executada ou já inicializada: {e}")

    # Limpeza e unificação
    logger.info("Executando pipeline de limpeza e normalização do SIGAA...")
    run_sigaa_cleaner()

    if SIGAA_CLASSES_FILE.exists():
        run_classes_cleaner()

    logger.info(f"✅ SIGAA finalizado com sucesso! Dados unificados em {SIGAA_PROCESSED_FILE.name}")
    return SIGAA_PROCESSED_FILE


if __name__ == "__main__":
    run_sigaa_pipeline()