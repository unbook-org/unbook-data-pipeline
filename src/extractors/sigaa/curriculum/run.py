import asyncio
from pathlib import Path

from src.extractors.base import BaseExtractor
from src.extractors.sigaa.curriculum.scraper import (
    ScrapeSummary,
    load_checkpoint,
    scrape_curricula,
    summarize,
)
from src.utils.logger import get_logger
from src.utils.paths import SIGAA_CURRICULA_RAW_FILE

logger = get_logger("SIGAA-Curr-Orch")


class SigaaCurriculaExtractor(BaseExtractor):
    """Extrator de matrizes curriculares da Squad SIGAA."""

    def extract(self, limit: int | None = None):
        return run_sigaa_curricula_pipeline(limit=limit)


def _log_summary(summary: ScrapeSummary) -> None:
    logger.info("----- Resumo da extração de currículos -----")
    logger.info(f"Cursos selecionados: {summary.selected} (reaproveitados do checkpoint: {summary.reused})")
    logger.info(f"Cursos ok: {summary.ok} | falhas: {len(summary.failures)}")
    logger.info(f"Estruturas: {summary.curricula} | componentes: {summary.components}")
    if summary.avg_elapsed_s is not None:
        logger.info(f"Tempo médio por curso extraído neste run: {summary.avg_elapsed_s:.1f}s")
    for failure in summary.failures:
        logger.error(f"❌ Falha: curso {failure['sigaa_program_id']} ({failure['name']}): {failure['error']}")


def run_sigaa_curricula_pipeline(limit: int | None = None, scrape: bool = True) -> Path:
    """
    Se scrape=True, extrai do SIGAA os currículos dos `limit` primeiros cursos,
    retomando do checkpoint em SIGAA_CURRICULA_RAW_FILE. Sem scrape, só resume o bruto existente.
    A normalização para data/processed/ é a Parte 4 (transformer).
    """
    if scrape:
        logger.info(f"Iniciando extração de matrizes curriculares... Limite: {limit if limit else 'Todos'}")
        summary = asyncio.run(scrape_curricula(limit=limit))
    elif SIGAA_CURRICULA_RAW_FILE.exists():
        logger.info(f"Raspagem pulada. Carregando checkpoint existente: {SIGAA_CURRICULA_RAW_FILE.name}")
        checkpoint = load_checkpoint()
        summary = summarize(checkpoint, list(checkpoint["programs"])[:limit] if limit else None)
    else:
        raise FileNotFoundError(f"Raspagem pulada e bruto inexistente: {SIGAA_CURRICULA_RAW_FILE}")

    _log_summary(summary)
    return SIGAA_CURRICULA_RAW_FILE


if __name__ == "__main__":
    run_sigaa_curricula_pipeline()
