import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from src.utils.logger import get_logger

logger = get_logger("Orchestrator")


def main():
    parser = argparse.ArgumentParser(
        description="UnBook 2.0 - Data Ingestion, Extraction & Loading Pipeline",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--source",
        choices=["sigaa", "social", "legacy", "db", "all"],
        default="all",
        help="Fonte de dados a processar (sigaa, social, legacy, db ou all)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limite de registros processados para testes rápidos.",
    )
    parser.add_argument(
        "--scrape-facebook",
        action="store_true",
        help="Força nova raspagem no Facebook via Playwright",
    )
    parser.add_argument(
        "--scrape-sigaa",
        action="store_true",
        help="Força execução da Spider Scrapy para enriquecer docentes do SIGAA",
    )
    parser.add_argument(
        "--scrape-classes",
        action="store_true",
        help="Força raspagem Selenium de turmas abertas de todos os departamentos no SIGAA",
    )
    parser.add_argument(
        "--limit-depts",
        type=int,
        default=None,
        help="Limite de departamentos a consultar na raspagem de turmas do SIGAA (para testes)",
    )
    parser.add_argument(
        "--skip-scrape",
        action="store_true",
        help="Pula requisições de rede e executa higienização, normalização e carga",
    )
    parser.add_argument(
        "--load-db",
        action="store_true",
        help="Popula os dados processados no banco de dados (PostgreSQL/SQLite)",
    )

    args = parser.parse_args()

    logger.info("=========================================")
    logger.info(" INICIANDO UNBOOK 2.0 DATA PIPELINE    ")
    logger.info("=========================================")

    # 1. Pipeline SIGAA
    if args.source in ["sigaa", "all"]:
        logger.info("🎓 [SQUAD SIGAA] Inicializando módulo de extração oficial...")

        if args.limit:
            logger.warning(f"MODO DE TESTE ATIVADO: A extração será limitada a {args.limit} registros.")

        try:
            from src.extractors.sigaa.run import run_sigaa_pipeline

            # Executa spider se requisitado explicitamente ou se não for skip-scrape
            should_scrape = args.scrape_sigaa and not args.skip_scrape
            should_scrape_classes = args.scrape_classes and not args.skip_scrape
            out_sigaa = run_sigaa_pipeline(
                limit=args.limit,
                scrape=should_scrape,
                scrape_classes=should_scrape_classes,
                limit_depts=args.limit_depts,
            )
            logger.info(f"✅ SIGAA finalizado com sucesso! Dados unificados em {out_sigaa.name}")
        except Exception as e:
            logger.error(f"❌ Falha crítica no módulo SIGAA: {e}")

    # 2. Pipeline Social (Facebook Feed)
    if args.source in ["social", "all"]:
        logger.info("💬 [SQUAD SOCIAL] Inicializando processamento de relatos...")
        try:
            from src.extractors.social.run import run_social_pipeline

            should_scrape = args.scrape_facebook and not args.skip_scrape
            out_social = run_social_pipeline(scrape=should_scrape, limit=args.limit)
            logger.info(f"✅ Social processado com sucesso! {len(out_social)} posts estruturados.")
        except Exception as e:
            logger.error(f"❌ Falha no módulo Social: {e}")

    # 3. Pipeline Legacy (formulário / UnBook 1.0)
    if args.source in ["legacy", "all"]:
        logger.info("📦 [SQUAD LEGACY] Processando avaliações históricas...")
        try:
            from src.extractors.legacy.run import run_legacy_pipeline

            out_legacy = run_legacy_pipeline(limit=args.limit)
            logger.info(f"✅ Legacy finalizado! {len(out_legacy)} avaliações válidas.")
        except Exception as e:
            logger.error(f"❌ Falha no módulo Legacy: {e}")

    # 4. Ingestão no Banco de Dados (PostgreSQL / SQLite)
    if args.source == "db" or args.load_db:
        logger.info("🚚 [LOADER] Ingestão de dados no banco central...")
        try:
            from src.loaders.postgres_loader import run_loader

            stats = run_loader(limit=args.limit)
            logger.info(f"✅ Banco populado com sucesso: {stats}")
        except Exception as e:
            logger.error(f"❌ Falha crítica na carga do banco: {e}")

    logger.info("🏁 Pipeline global concluído!")


if __name__ == "__main__":
    main()
