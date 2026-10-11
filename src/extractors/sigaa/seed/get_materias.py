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

# 📌 Ancoragem absoluta na raiz do repositório (compatível com script .py e Jupyter Notebook)
try:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
except NameError:
    BASE_DIR = Path.cwd()

PASTA_DESTINO = BASE_DIR / "data" / "raw" / "sigaa"
CAMINHO_ARQUIVO = PASTA_DESTINO / "materias.json"


def limpar_nome_departamento(texto_bruto: str) -> str:
    """
    Higieniza a string da opção de departamento obtida no select.
    Exemplo: "DEPTO ADMINISTRAÇÃO - BRASÍLIA - 11.01" -> "DEPTO ADMINISTRAÇÃO"
    """
    if not texto_bruto:
        return ""
    partes = texto_bruto.split(" - ")
    return partes[0].strip()


def salvar_lote_incremental(novos_itens: list, caminho_arquivo: Path):
    """
    Persiste novos registros no arquivo JSON em lote, preservando dados já existentes.
    """
    if not novos_itens:
        return

    dados_existentes = []
    caminho_arquivo.parent.mkdir(parents=True, exist_ok=True)

    if caminho_arquivo.exists() and caminho_arquivo.stat().st_size > 0:
        try:
            with open(caminho_arquivo, "r", encoding="utf-8") as f:
                dados_existentes = json.load(f)
        except Exception:
            dados_existentes = []

    dados_existentes.extend(novos_itens)

    with open(caminho_arquivo, "w", encoding="utf-8") as f:
        json.dump(dados_existentes, f, ensure_ascii=False, indent=4)

    print(f"  💾 [BACKUP] Lote de {len(novos_itens)} itens salvo no arquivo JSON em disco.")


def generate_seed_departamentos():
    inicio_timestamp = time.time()
    hora_inicio = datetime.now().strftime("%H:%M:%S")

    print(f"==================================================")
    print(f"🚀 Scraping SIGAA Iniciado às: {hora_inicio}")
    print(f"==================================================")

    # Reutiliza uma sessão HTTP para acelerar requisições em lote
    http_session = requests.Session()

    # Leitura prévia para ignorar matérias que já foram raspadas anteriormente
    codigos_processados = set()
    if CAMINHO_ARQUIVO.exists() and CAMINHO_ARQUIVO.stat().st_size > 0:
        try:
            with open(CAMINHO_ARQUIVO, "r", encoding="utf-8") as file:
                materias_existentes = json.load(file)
                for m in materias_existentes:
                    if "codigo" in m and "nivel" in m:
                        codigos_processados.add((m["codigo"], m["nivel"]))
            print(f"ℹ️ {len(codigos_processados)} combinações (código, nível) encontradas no JSON e serão ignoradas.")
        except Exception as e:
            print(f"⚠️ Não foi possível ler o arquivo existente ({type(e).__name__}). Um novo será gerado.")

    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--headless")
    options.add_argument("--blink-settings=imagesEnabled=false")

    driver = webdriver.Chrome(options=options)
    
    wait_geral = WebDriverWait(driver, 0.2)
    wait_rapido = WebDriverWait(driver, 0.1)

    buffer_lote = []
    url_base = "https://sigaa.unb.br/sigaa/public/componentes/busca_componentes.jsf"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

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

                Select(driver.find_element(By.ID, "form:nivel")).select_by_index(n)
                select_unidades = Select(driver.find_element(By.ID, "form:unidades"))
                select_nivel = Select(driver.find_element(By.ID, "form:nivel"))

                nome_depto_bruto = select_unidades.options[i].text.strip()
                nivel = select_nivel.options[n].text.strip()
                depto_nome_limpo = limpar_nome_departamento(nome_depto_bruto)

                if not depto_nome_limpo or "SELECIONE" in depto_nome_limpo.upper():
                    continue

                print(f"📍 Processando: {depto_nome_limpo} | Nível: {nivel}")
                select_unidades.select_by_index(i)

                driver.find_element(By.ID, "form:btnBuscarComponentes").click()

                try:
                    wait_geral.until(EC.presence_of_element_located((By.ID, "formListagemComponentes")))

                    linhas_tabela = driver.find_elements(
                        By.XPATH, "//form[@id='formListagemComponentes']//table/tbody/tr"
                    )
                    total_linhas = len(linhas_tabela)
                    print(total_linhas, "Total Linhas tabela primeira página")

                    for index in range(total_linhas):

                        try:
                            wait_rapido.until(EC.presence_of_element_located((By.ID, "formListagemComponentes")))

                            tr = driver.find_elements(
                                By.XPATH, "//form[@id='formListagemComponentes']//table/tbody/tr"
                            )[index]



                            codigo_elem = tr.find_elements(By.XPATH, "./td[1]")
                            nome_elem = tr.find_elements(By.XPATH, "./td[2]")
                            link_elem = tr.find_elements(By.XPATH, "./td[5]//a")
                            ch_elem = tr.find_elements(By.XPATH, "./td[4]") 

                            if not (codigo_elem and nome_elem and link_elem):
                                continue

                            codigo = codigo_elem[0].text.strip().upper()
                            nome = nome_elem[0].text.strip().upper()
                            ch_int = int(ch_elem[0].text.strip("h"))
                            
                            # Extrai o id do componente com Regex
                            script_onclick = link_elem[0].get_attribute("onclick") or ""
                            match = re.search(r"'id':'(\d+)'", script_onclick)

                            id_componente = match.group(1) if match else None
                           # print(id_componente)
                            if not id_componente:
                                continue

                            # Controle de duplicatas por tupla
                            if (codigo, nivel) in codigos_processados:
                                print(f"  ⏩ {codigo} ({nivel}) já processado. Pulando...")
                                continue

                            slug = f"https://sigaa.unb.br/sigaa/link/public/ensino/visualizarComponente/{id_componente}"

                            # 🚀 Extração direta via HTTP e BS4 inline no loop
                            pre_req, co_req, equiva = [], [], []
                            ementa = ""

                            res_detalhes = http_session.get(slug, headers=headers, timeout=1)
                            if res_detalhes.status_code == 200:
                                #print("Entrou na página")
                                soup = BeautifulSoup(res_detalhes.text, "html.parser")

                                # Captura todas as linhas da tabela de detalhes
                                linhas_detalhes = soup.select("table.visualizacao tr")
                                #print(f"Total de linhas encontradas dentro do componente: {len(linhas_detalhes)}")

                                for row in linhas_detalhes:
                                    texto_linha = row.get_text()

                                    if "Pré-Requisitos:" in texto_linha:
                                        
                                        tds = row.find_all("td")
                                        for i in tds:
                                            pre_req.append(i.get_text().strip("\n"))
                                        # print("Pre-req", pre_req)

                                    elif "Co-Requisitos:" in texto_linha:
                                        tds = row.find_all("td")
                                        for i in tds:
                                            co_req.append(i.get_text().strip("\n"))
                                        # print("co-req", co_req)

                                    elif "Equivalências:" in texto_linha:
                                        
                                        tds = row.find_all("td")
                                        for i in tds:
                                            equiva.append(i.get_text().strip("\n"))
                                        # print("equi", equiva)

                                    elif "Ementa:" in texto_linha or "Ementa/Descrição:" in texto_linha:
                                        # Extrai da própria linha 'row' atual sem depender de índice fixo
                                        tds = row.find_all("td")
                                        # try:
                                        #     for i in tds:
                                        #         # print(i.get_text(), len(tds))
                                        # except Exception:
                                        #     print("tds ementa não tem valor?")
                                        #     ementa = ""
                                        if tds:
                                            ementa = tds[-1].get_text().strip()
                                            #print("Ementa extraída:", ementa)
                                        else:
                                            ementa = "" 



                            materia_dados = {
                                "departamento": depto_nome_limpo,
                                "nivel": nivel,
                                "codigo": codigo,
                                "nome": nome,
                                "slug": slug,
                                "ementa": ementa,
                                "creditos":  ch_int // 15 if ch_int > 0 else 0,
                                "carga_horaria": ch_int,
                                "pre_requisito": pre_req,
                                "co_requisito": co_req,
                                "equivalencia": equiva,
                            }
                            buffer_lote.append(materia_dados)
                            codigos_processados.add((codigo, nivel))

                            hora_loop = datetime.now().strftime("%H:%M:%S")
                            print(f"  [{hora_loop}] [OK] {codigo} - {nome} ({ch_int}h)")
                            

                            # Gravação em lotes de 10
                            if len(buffer_lote) >= 10:
                                salvar_lote_incremental(buffer_lote, CAMINHO_ARQUIVO)
                                buffer_lote.clear()

                        except Exception as e:
                            print(f"  ❌ Falha no índice {index}: {type(e).__name__}")
    
                            break
                            

                except Exception as e:
                    print(f"  [AVISO] Nenhum componente retornado para: {depto_nome_limpo} ({type(e).__name__})")

    finally:
        # Gravação final do buffer pendente
        if buffer_lote:
            salvar_lote_incremental(buffer_lote, CAMINHO_ARQUIVO)
            buffer_lote.clear()

        driver.quit()

        # Métricas Finais de Tempo de Execução
        fim_timestamp = time.time()
        hora_fim = datetime.now().strftime("%H:%M:%S")
        duracao_segundos = fim_timestamp - inicio_timestamp

        minutos, segundos = divmod(duracao_segundos, 60)

        print("\n==================================================")
        print("🎉 [PROCESSO CONCLUÍDO COM SUCESSO]")
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