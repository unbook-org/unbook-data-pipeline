import time
import json
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

# Importando os caminhos
from utils.paths import SIGAA_SCRAPED_DIR, SIGAA_CLASSES_FILE


def extrair_inteiro(texto):
    """Extrai apenas números de uma string (ex: ' 40 ' -> 40)"""
    match = re.search(r'\d+', texto)
    return int(match.group()) if match else 0


def parse_turmas(html, nome_depto):
    """Extrai as turmas de um HTML da página de listagem do SIGAA, vinculando o docente ao departamento informado."""
    soup = BeautifulSoup(html, "html.parser")
    turmas_div = soup.find("div", {"id": "turmasAbertas"})
    tabelas = turmas_div.find_all("table", class_="listagem") if turmas_div else []

    resultados = []
    current_course_code = ""
    current_course_name = ""

    for table in tabelas:
        for row in table.find_all("tr"):
            row_classes = row.get("class", [])

            # Identifica a linha que contém o nome da disciplina
            if "agrupador" in row_classes:
                titulo_span = row.find("span", class_="tituloDisciplina")
                if titulo_span:
                    texto_titulo = titulo_span.text.strip()
                    # Separa o código do nome (ex: "CIC0004 - ALGORITMOS...")
                    partes = texto_titulo.split(" - ", 1)
                    current_course_code = partes[0].strip() if len(partes) > 0 else ""
                    current_course_name = partes[1].strip() if len(partes) > 1 else texto_titulo
                continue

            # Identifica as linhas que contêm os dados da turma em si
            elif "linhaPar" in row_classes or "linhaImpar" in row_classes:
                cols = row.find_all("td")

                # Verifica se a linha tem o formato esperado e se já temos uma disciplina mãe
                if len(cols) >= 8 and current_course_code:
                    class_code = cols[0].get_text(strip=True)
                    docente = cols[2].get_text(strip=True)

                    # O SIGAA costuma retornar "24M34 (12/08/2026 - 15/12/2026)"
                    schedules_raw = cols[3].get_text(strip=True).split('(')[0].strip()

                    vacancies = extrair_inteiro(cols[5].get_text(strip=True))
                    location = cols[7].get_text(strip=True)

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


def main():
    # Configura o navegador
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    # options.add_argument("--headless") # Descomente para rodar no terminal sem abrir interface

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 15)

    resultados = []

    try:
        url = "https://sigaa.unb.br/sigaa/public/turmas/listar.jsf"
        driver.get(url)

        # 1. Seleciona o Nível "Graduação"
        nivel_select = Select(wait.until(EC.presence_of_element_located((By.ID, "formTurma:inputNivel"))))
        nivel_select.select_by_value("G")  # 'G' é o valor no SIGAA para Graduação
        time.sleep(1)

        # 2. Carrega as opções de departamento
        dept_select_element = driver.find_element(By.ID, "formTurma:inputDepto")
        select_dept = Select(dept_select_element)
        opcoes_dept = select_dept.options

        print(f"Total de opções no filtro (incluindo 'SELECIONE'): {len(opcoes_dept)}")

        # Loop pelos departamentos (começa do 1 para pular a opção vazia "SELECIONE")
        for i in range(1, len(opcoes_dept)):
            driver.get(url)

            # Reseleciona para evitar StaleElementReferenceException do DOM
            nivel_select = Select(wait.until(EC.presence_of_element_located((By.ID, "formTurma:inputNivel"))))
            nivel_select.select_by_value("G")
            time.sleep(1)

            dept_select_element = driver.find_element(By.ID, "formTurma:inputDepto")
            select_dept = Select(dept_select_element)

            opcao_atual = select_dept.options[i]
            nome_depto = opcao_atual.text.strip()

            print(f"\n--- Processando: {nome_depto} ---")
            select_dept.select_by_index(i)

            # Clica no botão Buscar
            botao_buscar = driver.find_element(By.CSS_SELECTOR, "input[value='Buscar']")
            botao_buscar.click()

            try:
                # Espera a tabela de turmas renderizar
                wait.until(EC.presence_of_element_located((By.ID, "turmasAbertas")))
                time.sleep(1.5)  # Respiro para garantir que a tabela carregou no DOM

                resultados.extend(parse_turmas(driver.page_source, nome_depto))

            except Exception:
                print(f"Nenhuma turma encontrada ou tempo esgotado para {nome_depto}.")

    finally:
        driver.quit()

        # Salva os resultados padronizados no diretório orquestrado pelo paths.py
        SIGAA_SCRAPED_DIR.mkdir(parents=True, exist_ok=True)

        with open(SIGAA_CLASSES_FILE, "w", encoding="utf-8") as f:
            json.dump(resultados, f, ensure_ascii=False, indent=4)

        print(f"\n[SUCESSO] Coleta finalizada! {len(resultados)} turmas extraídas em: {SIGAA_CLASSES_FILE}")


if __name__ == "__main__":
    main()
