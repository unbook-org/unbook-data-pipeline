from src.utils.logger import get_logger

logger = get_logger(__name__)

def run_extraction(semester):
    logger.info(f"Iniciando extração do SIGAA para o semestre {semester}...")
    # Aqui a squad vai codar o Playwright/BeautifulSoup no futuro
    dummy_data = [{"course": "CIC0004", "professor": "Bruno Ribas"}]
    logger.info("Extração mockada concluída com sucesso!")
    return dummy_data