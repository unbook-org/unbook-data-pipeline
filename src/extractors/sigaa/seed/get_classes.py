import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, UnexpectedAlertPresentException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

try:
    from src.utils.logger import get_logger
    from src.utils.paths import SIGAA_CLASSES_FILE, SIGAA_SCRAPED_DIR
except ImportError:
    BASE_DIR = Path(__file__).resolve().parents[4]
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))
    from src.utils.logger import get_logger
    from src.utils.paths import SIGAA_CLASSES_FILE, SIGAA_SCRAPED_DIR

logger = get_logger("SIGAA-Classes-Scraper")

# Palavras-chave de pós-graduação/especialização que não ofertam disciplinas de graduação
POS_GRAD_KEYWORDS = [
    "PROGRAMA DE PÓS",
    "MESTRADO",
    "DOUTORADO",
    "ESPECIALIZAÇÃO",
    "RESIDÊNCIA MÉDICA",
]


def extrair_inteiro(texto: str) -> int:
    """Extrai apenas dígitos de uma string (ex: ' 40 ' -> 40)."""
    match = re.search(r"\d+", texto)
    return int(match.group()) if match else 0


def limpar_docentes(texto: str) -> str:
    """Remove a carga horária embutida no nome do docente (ex: 'RODRIGO HADDAD (45h)' -> 'RODRIGO HADDAD')."""
    return re.sub(r"\s*\(\d+h\)", "", texto).strip()


def limpar_espacos(texto: str) -> str:
    """Remove quebras de linha e múltiplos espaços consecutivos."""
    return re.sub(r"\s+", " ", texto).strip()


def parse_turmas(html: str, nome_depto: str) -> List[Dict[str, Any]]:
    """
    Extrai as turmas do HTML da página de listagem do SIGAA.
    
    Estrutura típica das colunas no SIGAA:
      [0] Código da Turma (ex: '01')
      [1] Ano-Período (ex: '2026.2')
      [2] Docente com carga horária
      [3] Horário bruto com datas
      [4] Ícone de detalhes (ou vazio)
      [5] Qtde Vagas Ofertadas (número)
      [6] Qtde Vagas Ocupadas (número)
      [7] Local / Sala
    """
    soup = BeautifulSoup(html, "html.parser")
    turmas_div = soup.find("div", {"id": "turmasAbertas"})
    tabelas = turmas_div.find_all("table", class_="listagem") if turmas_div else []

    resultados: List[Dict[str, Any]] = []
    current_course_code = ""
    current_course_name = ""

    for table in tabelas:
        for row in table.find_all("tr"):
            row_classes = row.get("class", [])

            # Linha de cabeçalho da disciplina
            if "agrupador" in row_classes:
                titulo_span = row.find("span", class_="tituloDisciplina")
                if titulo_span:
                    texto_titulo = titulo_span.text.strip()
                    partes = texto_titulo.split(" - ", 1)
                    current_course_code = partes[0].strip() if len(partes) > 0 else ""
                    current_course_name = partes[1].strip() if len(partes) > 1 else texto_titulo
                continue

            # Linhas contendo as turmas da disciplina
            elif "linhaPar" in row_classes or "linhaImpar" in row_classes:
                cols = row.find_all("td")
                if len(cols) >= 6 and current_course_code:
                    class_code = cols[0].get_text(strip=True)
                    docente = limpar_docentes(cols[2].get_text(strip=True))

                    # Remove datas em parênteses do horário: '24M34 (12/08/2026 - 15/12/2026)' -> '24M34'
                    schedules_raw = cols[3].get_text(strip=True).split("(")[0].strip()

                    # Tratamento das colunas de vagas e local
                    if len(cols) >= 8:
                        vacancies = extrair_inteiro(cols[5].get_text(strip=True))
                        location = cols[7].get_text(strip=True)
                    elif len(cols) == 7:
                        if cols[4].get_text(strip=True) == "":
                            vacancies = extrair_inteiro(cols[5].get_text(strip=True))
                            location = cols[6].get_text(strip=True)
                        else:
                            vacancies = extrair_inteiro(cols[4].get_text(strip=True))
                            location = cols[6].get_text(strip=True)
                    else:
                        vacancies = extrair_inteiro(cols[4].get_text(strip=True))
                        location = cols[5].get_text(strip=True)

                    # Se o local foi preenchido com números por desalinhamento, limpa
                    if location.isdigit():
                        location = ""

                    resultados.append({
                        "course_code": current_course_code,
                        "course_name": current_course_name,
                        "class_code": class_code,
                        "schedules_raw": schedules_raw,
                        "location": location,
                        "vacancies": vacancies,
                        "docente": docente,
                        "departamento": nome_depto,
                    })

    return resultados


def dismiss_modals(driver: webdriver.Chrome):
    """Remove modais de cookies e sobreposições do DOM do SIGAA."""
    try:
        driver.execute_script("""
            const modal = document.getElementById('sigaa-cookie-consent');
            if (modal) modal.remove();
            const backdrops = document.querySelectorAll('.modal-backdrop, .ui-widget-overlay');
            backdrops.forEach(b => b.remove());
        """)
    except Exception:
        pass


def init_sigaa_session(driver: webdriver.Chrome, timeout: int = 15) -> bool:
    """Navega pela home do SIGAA e clica no link de turmas para estabelecer sessão JSF válida."""
    try:
        logger.info("Iniciando sessão JSF via home pública do SIGAA...")
        driver.get("https://sigaa.unb.br/sigaa/public/home.jsf")
        time.sleep(1.5)
        dismiss_modals(driver)

        # Clica no link de consulta de turmas
        wait = WebDriverWait(driver, timeout)
        link = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='turmas/listar.jsf']")))
        driver.execute_script("arguments[0].click();", link)
        time.sleep(2)
        dismiss_modals(driver)

        # Garante seleção de Graduação
        nivel_select = Select(wait.until(EC.presence_of_element_located((By.ID, "formTurma:inputNivel"))))
        nivel_select.select_by_value("G")
        time.sleep(0.5)
        return True
    except Exception as exc:
        logger.warning(f"Erro ao inicializar sessão JSF do SIGAA: {exc}")
        return False


def scrape_sigaa_classes(
    output_path: Optional[Path] = None,
    limit_depts: Optional[int] = None,
    headless: bool = True,
    include_pos: bool = False,
    target_depts: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Executa o scraping completo das turmas abertas de todos os departamentos da UnB.
    Salva incrementalmente para garantir tolerância a falhas.
    """
    target_file = Path(output_path) if output_path else SIGAA_CLASSES_FILE
    target_file.parent.mkdir(parents=True, exist_ok=True)

    # Configuração do WebDriver Chrome
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)

    resultados: List[Dict[str, Any]] = []
    processed_dept_names = set()

    try:
        if not init_sigaa_session(driver):
            raise RuntimeError("Não foi possível conectar e iniciar a sessão no SIGAA.")

        dept_select_elem = driver.find_element(By.ID, "formTurma:inputDepto")
        select_dept = Select(dept_select_elem)
        total_options = len(select_dept.options)

        # Mapeia departamentos a consultar
        candidate_indices = []
        for i in range(1, total_options):
            opt_text = select_dept.options[i].text.strip()
            opt_val = select_dept.options[i].get_attribute("value")
            if not opt_val or opt_val == "0":
                continue

            # Filtra pós-graduação caso não solicitado
            is_pos = any(kw in opt_text.upper() for kw in POS_GRAD_KEYWORDS)
            if is_pos and not include_pos:
                continue

            # Filtra por departamentos alvo se fornecido
            if target_depts:
                matched = any(t.upper() in opt_text.upper() for t in target_depts)
                if not matched:
                    continue

            candidate_indices.append((i, opt_val, opt_text))

        if limit_depts:
            candidate_indices = candidate_indices[:limit_depts]

        logger.info(f"Iniciando coleta de turmas para {len(candidate_indices)} departamentos selecionados...")

        for step, (idx, val, raw_name) in enumerate(candidate_indices, 1):
            nome_depto = limpar_espacos(raw_name)
            logger.info(f"[{step}/{len(candidate_indices)}] Consultando: {nome_depto} (id: {val})...")

            # Tenta selecionar e submeter a busca com até 2 tentativas em caso de expiração de sessão
            for attempt in range(2):
                try:
                    dismiss_modals(driver)

                    # Garante graduação selecionada
                    nivel_select = Select(driver.find_element(By.ID, "formTurma:inputNivel"))
                    if nivel_select.first_selected_option.get_attribute("value") != "G":
                        nivel_select.select_by_value("G")

                    dept_select = Select(driver.find_element(By.ID, "formTurma:inputDepto"))
                    dept_select.select_by_value(val)

                    btn = driver.find_element(By.CSS_SELECTOR, "input[value='Buscar']")
                    driver.execute_script("arguments[0].click();", btn)

                    # Espera dinâmica rápida (até 3s) pela renderização da listagem ou término do carregamento
                    time.sleep(2.0)

                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    table = soup.find("table", class_="listagem")

                    if table:
                        dept_turmas = parse_turmas(driver.page_source, nome_depto)
                        resultados.extend(dept_turmas)
                        logger.info(f"  ✓ {len(dept_turmas)} turmas encontradas (Total acumulado: {len(resultados)})")
                    else:
                        logger.info("  - Nenhuma turma de graduação ofertada neste departamento.")

                    processed_dept_names.add(nome_depto)

                    # Salvamento incremental em disco após cada departamento
                    with open(target_file, "w", encoding="utf-8") as f:
                        json.dump(resultados, f, ensure_ascii=False, indent=4)

                    break  # Sucesso, sai do loop de tentativas

                except UnexpectedAlertPresentException as alert_err:
                    logger.warning(f"  Alerta JSF detectado na tentativa {attempt + 1}: {alert_err}. Reiniciando sessão...")
                    init_sigaa_session(driver)
                except Exception as exc:
                    logger.warning(f"  Erro ao processar {nome_depto} na tentativa {attempt + 1}: {exc}")
                    if attempt == 0:
                        init_sigaa_session(driver)
                    else:
                        break

    finally:
        driver.quit()
        # Salva o arquivo final consolidado se houve extração
        if resultados:
            with open(target_file, "w", encoding="utf-8") as f:
                json.dump(resultados, f, ensure_ascii=False, indent=4)
            logger.info(f"🎉 Extração do SIGAA finalizada! Total de {len(resultados)} turmas salvas em {target_file}")
        else:
            logger.info(f"Nenhuma nova turma extraída nesta execução.")

    return resultados


def main():
    parser = argparse.ArgumentParser(description="Extrator de Turmas do SIGAA UnB para todos os Departamentos")
    parser.add_argument("--output", type=str, default=str(SIGAA_CLASSES_FILE), help="Caminho do arquivo JSON de saída")
    parser.add_argument("--limit-depts", type=int, default=None, help="Limite máximo de departamentos a consultar (testes)")
    parser.add_argument("--no-headless", action="store_true", help="Desativa modo headless do Chrome (abre janela visual)")
    parser.add_argument("--include-pos", action="store_true", help="Inclui programas de pós-graduação na busca")
    parser.add_argument("--depts", type=str, default=None, help="Nomes de departamentos específicos separados por vírgula")

    args = parser.parse_args()
    target_depts = [d.strip() for d in args.depts.split(",")] if args.depts else None

    scrape_sigaa_classes(
        output_path=Path(args.output),
        limit_depts=args.limit_depts,
        headless=not args.no_headless,
        include_pos=args.include_pos,
        target_depts=target_depts,
    )


if __name__ == "__main__":
    main()
