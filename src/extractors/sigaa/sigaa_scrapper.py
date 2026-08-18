import sys
from pathlib import Path
from scrapy.crawler import CrawlerProcess
from src.extractors.sigaa.ProfInfo.spiders.info_spider import InfoSpiderSpider
from src.utils.logger import get_logger

logger = get_logger(__name__)

def run_sigaa_pipeline(output_rel_path="data/processed/sigaa_professores.json"):
    base_dir = Path(__file__).resolve().parents[3]  # Raiz do projeto
    output_path = base_dir / output_rel_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("🚀 [SIGAA] Disparando Spider de Professores (Modo Turbo)...")

    # =========================================================================
    # ⚙️ PAINEL DE CONTROLE / SETTINGS INJETADO NO CRAWLERPROCESS
    # =========================================================================
    settings = {
        # Identificação e Boas Práticas
        "BOT_NAME": "ProfInfo",
        "ROBOTSTXT_OBEY": False,         # Desliga a checagem extra de robots.txt para acelerar
        "COOKIES_ENABLED": False,        # Páginas públicas do SIGAA não precisam de cookies
        "FEED_EXPORT_ENCODING": "utf-8",

        # 🏎️ Performance e Concorrência Máxima
        "CONCURRENT_REQUESTS": 32,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 32, # Iguala ao global para não afunilar no domínio do SIGAA
        "DOWNLOAD_DELAY": 0.5,               # Delay curto e seguro para requisições em massa
        "AUTOTHROTTLE_ENABLED": False,        # Desliga throttle automático para manter taxa constante
        "DOWNLOAD_TIMEOUT": 10,               # Não prende a fila se o SIGAA engasgar numa página
        "DNSCACHE_ENABLED": True,             # Cache de DNS para evitar requisições de rede repetidas

        # 📊 Logs e Exportação
        "LOG_LEVEL": "INFO",                  # Mude para "WARNING" se quiser silenciar e economizar CPU
        "FEEDS": {
            str(output_path): {
                "format": "json",
                "encoding": "utf8",
                "overwrite": True,
                "indent": 4,
            }
        },
    }

    process = CrawlerProcess(settings=settings)
    process.crawl(InfoSpiderSpider)
    process.start()

    logger.info(f"✅ [SIGAA] Extração concluída! Arquivo final salvo em: {output_path}")
    return output_path