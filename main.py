import argparse
import sys
from pathlib import Path

# Fixa a raiz do projeto no PYTHONPATH
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from src.extractors.social.social_parser import run_extraction as parse_social_data
from src.extractors.sigaa.sigaa_scrapper import run_sigaa_pipeline
from src.utils.logger import get_logger

logger = get_logger("UnBook-Main")

def main():
    parser = argparse.ArgumentParser(
        description="UnBook 2.0 - Data Ingestion & Extraction Pipeline",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--source",
        choices=["sigaa", "social", "all"],
        default="all",
        help=(
            "Módulo de dados para executar:\n"
            "  sigaa  : Executa a Spider do SIGAA para raspar docentes e disciplinas\n"
            "  social : Executa o parser do feed social (Facebook DOM dump)\n"
            "  all    : Executa todo o pipeline sequencialmente"
        )
    )

    args = parser.parse_args()
    logger.info("=========================================")
    logger.info("   INICIANDO UNBOOK 2.0 DATA PIPELINE    ")
    logger.info("=========================================")

    # 1. Pipeline SIGAA
    if args.source in ["sigaa", "all"]:
        logger.info("\n🎓 [SQUAD SIGAA] Iniciando extração oficial...")
        try:
            out_sigaa = run_sigaa_pipeline(
                output_rel_path="data/processed/sigaa_professores.json"
            )
            logger.info(f"✅ SIGAA finalizado com sucesso!")
        except Exception as e:
            logger.error(f"❌ Falha no módulo SIGAA: {e}")

    # 2. Pipeline Social (Facebook Feed)
    if args.source in ["social", "all"]:
        logger.info("\n💬 [SQUAD SOCIAL] Processando relatos e feedbacks...")
        try:
            out_social = parse_social_data(
                input_filepath="data/raw/social/facebook_dump_dom.json",
                output_filepath="data/processed/social_parsed.json"
            )
            logger.info(f"✅ Social processado: {len(out_social)} registros.")
        except Exception as e:
            logger.error(f"❌ Falha no módulo Social: {e}")

    logger.info("\n🏁 Pipeline concluído!")

if __name__ == "__main__":
    main()