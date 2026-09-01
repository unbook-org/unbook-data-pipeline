from pathlib import Path

# Raiz absoluta do projeto
BASE_DIR = Path(__file__).resolve().parents[2]

# Diretórios de Dados
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# Caminhos específicos - SIGAA
SIGAA_RAW_DIR = RAW_DATA_DIR / "sigaa"
SIGAA_SEED_FILE = SIGAA_RAW_DIR / "seed_professores.json"
SIGAA_FINAL_RAW_FILE = SIGAA_RAW_DIR / "sigaa_bruto.json"
SIGAA_PROCESSED_FILE = PROCESSED_DATA_DIR / "sigaa_professores.json"
SIGAA_SCRAPED_DIR = RAW_DATA_DIR / "scraped"
SIGAA_CLASSES_FILE = SIGAA_SCRAPED_DIR / "sigaa_classes.json"

# Caminhos específicos - Social
SOCIAL_RAW_DIR = RAW_DATA_DIR / "social"
SOCIAL_COOKIES_FILE = BASE_DIR / "fb_cookies.json"  # Ou dentro de data/raw/social/
SOCIAL_DUMP_DOM_FILE = SOCIAL_RAW_DIR / "facebook_dump_dom.json"
SOCIAL_PROCESSED_FILE = PROCESSED_DATA_DIR / "social_parsed.json"