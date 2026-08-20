import sys
import json
from pathlib import Path
from scrapy.crawler import CrawlerProcess
from src.utils.paths import SIGAA_SEED_FILE, SIGAA_FINAL_RAW_FILE
from src.utils.logger import get_logger

# Importação absoluta da spider a partir da raiz para evitar erros do linter
from src.extractors.sigaa.scrapy_app.prof_info.spiders.info_spider import InfoSpiderSpider

# Nome mais curto para alinhar perfeitamente com a formatação colorida do terminal
logger = get_logger("SIGAA-Orch")

def run_sigaa_pipeline(limit=None):
    """Executa a Spider do Scrapy consumindo o Seed gerado."""
    
    # 🎯 O log de carregamento/leitura que aciona a cor MAGENTA que configuramos
    logger.info(f"Acessando {SIGAA_SEED_FILE.name} para extração de matérias e dados dos docentes...")
    logger.info(f"Iniciando Spider Scrapy... Limite: {limit if limit else 'Todos'}")
    
    # Cria os diretórios necessários
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
        }
    }

    process = CrawlerProcess(settings)
    process.crawl(InfoSpiderSpider, limit=limit)
    process.start() 
    
    logger.info(f"✅ Spider finalizada. Dados brutos salvos em: {SIGAA_FINAL_RAW_FILE.name}")
    return SIGAA_FINAL_RAW_FILE

if __name__ == "__main__":
    run_sigaa_pipeline()