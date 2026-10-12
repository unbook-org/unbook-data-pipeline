import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

# 📌 Ancoragem absoluta na raiz do repositório
try:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
except NameError:
    BASE_DIR = Path.cwd()

PASTA_DESTINO = BASE_DIR / "data" / "processed" 
CAMINHO_ARQUIVO = PASTA_DESTINO / "departamentos_clean.json"


def limpar_nome_departamento(texto_bruto: str) -> str:
    """
    Higieniza a string da opção de departamento obtida no select.
    Exemplo: "DEPTO ADMINISTRAÇÃO - BRASÍLIA - 11.01" -> "DEPTO ADMINISTRAÇÃO"
    """
    if not texto_bruto:
        return ""
    partes = texto_bruto.split(" - ")
    return partes[0].strip()


def generate_seed_departamentos():
    inicio_timestamp = time.time()
    hora_inicio = datetime.now().strftime("%H:%M:%S")

    print("==================================================")
    print(f"🚀 Mapeamento de Departamentos Iniciado às: {hora_inicio}")
    print("==================================================")

    # Dicionário agrupado por nome do departamento
    departamentos_dict = {}

    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--headless")
    options.add_argument("--blink-settings=imagesEnabled=false")

    driver = webdriver.Chrome(options=options)

    # Wait geral para carregamento de páginas e wait rápido para timeouts de listagem vazia
    wait_geral = WebDriverWait(driver, 10)
    wait_rapido = WebDriverWait(driver, 2)

    url_base = "https://sigaa.unb.br/sigaa/public/componentes/busca_componentes.jsf"

    try:
        driver.get(url_base)

        wait_geral.until(EC.presence_of_element_located((By.ID, "form:unidades")))
        wait_geral.until(EC.presence_of_element_located((By.ID, "form:nivel")))

        opcoes_1 = Select(driver.find_element(By.ID, "form:nivel")).options
        opcoes_2 = Select(driver.find_element(By.ID, "form:unidades")).options

        print(f"Mapeamento Inicial: {len(opcoes_1)} níveis | {len(opcoes_2)} departamentos\n")

        for n in range(len(opcoes_1)):
            for i in range(len(opcoes_2)):
                driver.get(url_base)
                wait_geral.until(EC.presence_of_element_located((By.ID, "form:unidades")))

                # Seleciona Nível e Departamento
                Select(driver.find_element(By.ID, "form:nivel")).select_by_index(n)
                select_unidades = Select(driver.find_element(By.ID, "form:unidades"))

                nome_depto_bruto = select_unidades.options[i].text.strip()
                depto_nome_limpo = limpar_nome_departamento(nome_depto_bruto)

                if not depto_nome_limpo or "SELECIONE" in depto_nome_limpo.upper():
                    continue

                select_unidades.select_by_index(i)

                # Submete a busca
                driver.find_element(By.ID, "form:btnBuscarComponentes").click()

                try:
                    # ⚡ Wait rápido de 2s para ignorar rapidamente seleções sem matérias
                    wait_rapido.until(EC.presence_of_element_located((By.ID, "formListagemComponentes")))

                    linhas_tabela = driver.find_elements(
                        By.XPATH, "//form[@id='formListagemComponentes']//table/tbody/tr"
                    )

                    if depto_nome_limpo not in departamentos_dict:
                        departamentos_dict[depto_nome_limpo] = {
                            "nome": depto_nome_limpo,
                            "materias": []
                        }

                    novas_materias = 0
                    for tr in linhas_tabela:
                        codigo_elem = tr.find_elements(By.XPATH, "./td[1]")
                        nome_elem = tr.find_elements(By.XPATH, "./td[2]")

                        if not (codigo_elem and nome_elem):
                            continue

                        codigo = codigo_elem[0].text.strip().upper()
                        nome = nome_elem[0].text.strip().upper()

                        if not codigo or not nome:
                            continue

                        materia_seed = {
                            "codigo": codigo,
                            "nome": nome
                        }

                        # Garante que não haverá matérias duplicadas no mesmo departamento
                        if materia_seed not in departamentos_dict[depto_nome_limpo]["materias"]:
                            departamentos_dict[depto_nome_limpo]["materias"].append(materia_seed)
                            novas_materias += 1

                    hora_loop = datetime.now().strftime("%H:%M:%S")
                    print(f" 📍 [{hora_loop}] {depto_nome_limpo}: +{novas_materias} matéria(s) cadastrada(s)")

                except Exception:
                    # Se não houver listagem em até 2s, avança imediatamente para o próximo
                    pass

    finally:
        driver.quit()

        # Converte o dicionário para a lista final esperada
        resultado_final = list(departamentos_dict.values())

        # Salva o resultado no arquivo JSON
        PASTA_DESTINO.mkdir(parents=True, exist_ok=True)
        with open(CAMINHO_ARQUIVO, "w", encoding="utf-8") as f:
            json.dump(resultado_final, f, ensure_ascii=False, indent=4)

        # Métricas Finais de Tempo de Execução
        fim_timestamp = time.time()
        hora_fim = datetime.now().strftime("%H:%M:%S")
        duracao_segundos = fim_timestamp - inicio_timestamp
        minutos, segundos = divmod(duracao_segundos, 60)

        print("\n==================================================")
        print("🎉 [MAPEAMENTO DE DEPARTAMENTOS CONCLUÍDO]")
        print(f"🕒 Hora de Início : {hora_inicio}")
        print(f"🕒 Hora Atual/Fim : {hora_fim}")
        if minutos > 0:
            print(f"⏱️ Tempo Decorrido: {int(minutos)}m {segundos:.2f}s")
        else:
            print(f"⏱️ Tempo Decorrido: {duracao_segundos:.2f} segundos")
        print(f"📁 Arquivo Salvo em: {CAMINHO_ARQUIVO}")
        print("==================================================")


if __name__ == "__main__":
    generate_seed_departamentos()