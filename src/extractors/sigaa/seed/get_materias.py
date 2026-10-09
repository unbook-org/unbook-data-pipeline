import os
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import datetime
from datetime import datetime


def limpar_nome_departamento(texto_bruto: str) -> str:
    """
    Trata o texto da opção selecionada no select de unidades.
    Exemplo entrada: "DEPTO ADMINISTRAÇÃO - BRASÍLIA - 11.01.01.02.01"
    Exemplo saída: "DEPTO ADMINISTRAÇÃO"
    """
    if not texto_bruto:
        return ""
    partes = texto_bruto.split(" - ")
    return partes[0].strip()


def salvar_lote_incremental(novos_itens: list, caminho_arquivo: str):
    """
    Salva novos itens no JSON em disco preservando o conteúdo que já existia.
    """
    if not novos_itens:
        return

    dados_existentes = []
    if os.path.exists(caminho_arquivo) and os.path.getsize(caminho_arquivo) > 0:
        try:
            with open(caminho_arquivo, "r", encoding="utf-8") as f:
                dados_existentes = json.load(f)
        except Exception:
            dados_existentes = []

    dados_existentes.extend(novos_itens)

    with open(caminho_arquivo, "w", encoding="utf-8") as f:
        json.dump(dados_existentes, f, ensure_ascii=False, indent=4)

    print(f"  💾 [BACKUP] Lote de {len(novos_itens)} itens salvo no JSON em disco!")


def generate_seed_departamentos():

    hora_inicio = datetime.now().strftime("%H:%M:%S")
    print(f"🚀 Processo iniciado às: {hora_inicio}\n")

    # Prepara caminhos de salvamento do dataset
    pasta_destino = os.path.join("data", "raw", "sigaa")
    os.makedirs(pasta_destino, exist_ok=True)
    caminho_arquivo = os.path.join(pasta_destino, "materias.json")

    # Coleta matérias e códigos já existentes para evitar requisições duplicadas
    codigos_processados = set()
    if os.path.exists(caminho_arquivo) and os.path.getsize(caminho_arquivo) > 0:
        try:
            with open(caminho_arquivo, "r", encoding="utf-8") as file:
                materias_existentes = json.load(file)
                for m in materias_existentes:
                    if "codigo" and "nivel" in m:
                        codigos_processados.add(m["codigo"])
            print(f"ℹ️ {len(codigos_processados)} matérias já existem no JSON e serão ignoradas.")
        except Exception as e:
            print(f"⚠️ Erro ao ler JSON existente: {type(e).__name__}. Criando novo do zero.")

    # Opções do Chrome com estabilidade para raspagem pesada
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--headless")

    driver = webdriver.Chrome(options=options)
    
    wait_geral = WebDriverWait(driver, 10)
    wait_rapido = WebDriverWait(driver, 2)

    # Buffer temporário na memória RAM (salvo no disco a cada 10 itens)
    buffer_lote = []
    
    url = "https://sigaa.unb.br/sigaa/public/componentes/busca_componentes.jsf"

    try:

        driver.get(url)

        # Aguarda os selects do formulário carregarem
        wait_geral.until(EC.presence_of_element_located((By.ID, "form:unidades")))
        wait_geral.until(EC.presence_of_element_located((By.ID, "form:nivel")))

        select_element_1 = driver.find_element(By.ID, "form:nivel")
        select_element_2 = driver.find_element(By.ID, "form:unidades")

        opcoes_1 = Select(select_element_1).options
        opcoes_2 = Select(select_element_2).options

        print(f"Total de opções encontradas: {len(opcoes_1)} níveis | {len(opcoes_2)} departamentos")

        for n in range(len(opcoes_1)):
            for i in range(len(opcoes_2)):
                # Garante que está no portal do SIGAA
                driver.get(url)
                wait_geral.until(EC.presence_of_element_located((By.ID, "form:unidades")))

                # Seleciona o nível e o departamento
                Select(driver.find_element(By.ID, "form:nivel")).select_by_index(n)
                select_unidades = Select(driver.find_element(By.ID, "form:unidades"))
                
                opcao_depto = select_unidades.options[i]
                opcao_nivel = Select(driver.find_element(By.ID, "form:nivel")).options[n]
                
                nome_depto_bruto = opcao_depto.text.strip()
                nivel = opcao_nivel.text.strip()
                depto_nome_limpo = limpar_nome_departamento(nome_depto_bruto)

                if not depto_nome_limpo or "SELECIONE" in depto_nome_limpo.upper():
                    continue

                print(f"\n--- Processando: {depto_nome_limpo} (Nível: {nivel}) ---")
                select_unidades.select_by_index(i)

                # Clica no botão de busca
                driver.find_element(By.ID, "form:btnBuscarComponentes").click()

                try:
                    # Aguarda a tabela de listagem
                    wait_rapido.until(EC.presence_of_element_located((By.ID, "formListagemComponentes")))

                    linhas_tabela = driver.find_elements(
                        By.XPATH, "//form[@id='formListagemComponentes']//table/tbody/tr"
                    )
                    total_linhas = len(linhas_tabela)

                    for index in range(total_linhas):
                        try:
                            wait_geral.until(EC.presence_of_element_located((By.ID, "formListagemComponentes")))
                            tr = driver.find_elements(
                                By.XPATH, "//form[@id='formListagemComponentes']//table/tbody/tr"
                            )[index]

                            codigo_elem = tr.find_elements(By.XPATH, "./td[1]")
                            nome_elem = tr.find_elements(By.XPATH, "./td[2]")
                            link_elem = tr.find_elements(By.XPATH, "./td[5]//a")

                            if not (codigo_elem and nome_elem and link_elem):
                                continue

                            codigo = codigo_elem[0].text.strip().upper()
                            nome = nome_elem[0].text.strip().upper()
                            script_onclick = link_elem[0].get_attribute("onclick")

                            if not script_onclick:
                                continue

                            # ⏩ Checagem: Se a matéria já foi raspada anteriormente, pula o postback JSF
                            if codigo in codigos_processados:
                                print(f"  ⏩ {codigo} já processado. Pulando...")
                                continue

                            # Dispara o evento JSF para abrir a página de detalhes
                            driver.execute_script(script_onclick)
                            wait_geral.until(EC.presence_of_element_located((By.CLASS_NAME, "visualizacao")))

                            # Instancia acumuladores da matéria atual
                            pre_req, co_req, equiva = [], [], []
                            ementa = ""
                            carga_materia = "0"

                            linhas_detalhes = driver.find_elements(
                                By.XPATH, "//table[@class='visualizacao']//tbody//tr"
                            )
                            
                            # Preenche as propriedades lendo a tabela
                            for row in linhas_detalhes:
                                texto_linha = row.text

                                if "Pré-Requisitos:" in texto_linha:
                                    tds = row.find_elements(By.TAG_NAME, "td")
                                    for text in tds:
                                        pre_req.append(text.text)

                                elif "Co-Requisitos:" in texto_linha:
                                    tds = row.find_elements(By.TAG_NAME, "td")
                                    for text in tds:
                                        co_req.append(text.text)

                                elif "Equivalências:" in texto_linha:
                                    tds = row.find_elements(By.TAG_NAME, "td")
                                    for text in tds:
                                        equiva.append(text.text)

                                elif "Ementa:" in texto_linha:
                                    tds = row.find_elements(By.TAG_NAME, "td")
                                    for text in tds:
                                        ementa = text.text

                                elif "Carga Horária Total:" in texto_linha or "Total de Carga Horária" in texto_linha:
                                    tds = row.find_elements(By.TAG_NAME, "td")
                                    for text in tds:
                                        texto_ch = text.text.strip()
                                        carga_materia = "".join(filter(str.isdigit, texto_ch)) or "0"

                            ch_int = int(carga_materia)

                            # Modela o objeto da matéria
                            materia_dados = {
                                "nivel": nivel,
                                "codigo": codigo,
                                "nome": nome,
                                "ementa": ementa,
                                "creditos": ch_int // 15 if ch_int > 0 else 0,
                                "carga_horaria": ch_int,
                                "pre_requisito": pre_req,
                                "co_requisito": co_req,
                                "equivalencia": equiva,
                            }

                            buffer_lote.append(materia_dados)
                            codigos_processados.add(codigo)

                            print(f"  [OK] Processado: {codigo} - {nome} ({ch_int}h)")

                            # 💾 A cada 10 matérias no buffer, grava incrementalmente no JSON
                            if len(buffer_lote) >= 10:
                                salvar_lote_incremental(buffer_lote, caminho_arquivo)
                                buffer_lote.clear()

                            # Retorna para a página de listagem
                            driver.back()

                        except Exception as e:
                            print(f"  ❌ Erro ao extrair item no índice {index}: {type(e).__name__}")
                            # Em caso de falha no item, recarrega o formulário
                            driver.get(url)
                            break

                except Exception as e:
                    print(f"  [AVISO] Sem componentes ou timeout em: {depto_nome_limpo} ({type(e).__name__})")

    finally:
        # Salva qualquer item pendente no buffer antes de fechar o driver
        if buffer_lote:
            salvar_lote_incremental(buffer_lote, caminho_arquivo)
            buffer_lote.clear()

        driver.quit()

        print(f"\n[SUCESSO] Processo finalizado! Registros salvos em: {caminho_arquivo}")


        fim_tempo = time.time()
        hora_fim =datetime.now().strftime("%H:%M:%S")

        print(f"🕒 Hora de Início : {hora_inicio}")
        print(f"🕒 Hora Atual/Fim : {hora_fim}")



if __name__ == "__main__":
    generate_seed_departamentos()