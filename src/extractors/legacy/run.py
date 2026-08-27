from src.extractors.legacy.parser import run_legacy_parser
from src.utils.logger import get_logger

logger = get_logger("Legacy-Orch")


def run_legacy_pipeline(limit: int | None = None):
    """Lê o CSV bruto do formulário e emite avaliações no contrato da pipeline."""
    logger.info("Executando parser de avaliações históricas...")
    return run_legacy_parser(limit=limit)
