import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from src.extractors.sigaa.run import run_sigaa_pipeline
from src.extractors.social.run import run_social_pipeline
from src.utils.logger import get_logger

logger = get_logger("Orchestrator")

def main():
    parser = argparse.ArgumentParser(
        description="UnBook 2.0 - Data Ingestion & Extraction Pipeline",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--source", choices=["sigaa", "social", "all"], default="all")
    parser.add_argument("--limit", type=int, default=None, help="Limite de professores.")
    parser.add_argument("--scrape-facebook", action="store_true", help="Força nova raspagem no Facebook via Playwright")

    args = parser.parse_args()
    
    logger.info("=========================================")
    logger.info(" INICIANDO UNBOOK 2.0 DATA PIPELINE    ")
    logger.info("=========================================")

    # 1. Pipeline SIGAA
    if args.source in ["sigaa", "all"]:
        logger.info("🎓 [SQUAD SIGAA] Inicializando módulo de extração oficial...")
        
        if args.limit:
            logger.warning(f"MODO DE TESTE ATIVADO: A extração será limitada a {args.limit} docentes.")
        
        try:
            logger.info("Acessando rotinas do SIGAA para orquestração das Spiders...")
            out_sigaa = run_sigaa_pipeline(limit=args.limit)
            logger.info(f"✅ SIGAA finalizado com sucesso! Dados unificados em {out_sigaa.name}")
        except Exception as e:
            logger.error(f"❌ Falha crítica no módulo SIGAA: {e}")

    # 2. Pipeline Social (Facebook Feed)
    if args.source in ["social", "all"]:
        logger.info("💬 [SQUAD SOCIAL] Inicializando processamento de relatos...")
        try:
            out_social = run_social_pipeline(scrape=args.scrape_facebook, limit=args.limit)
            logger.info(f"✅ Social processado com sucesso!")
        except Exception as e:
            logger.error(f"❌ Falha no módulo Social: {e}")

    logger.info("🏁 Pipeline global concluído!")

if __name__ == "__main__":
    main()