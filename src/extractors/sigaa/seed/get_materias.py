import os
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select


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


def generate_seed_departamentos():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    # options.add_argument("--headless") # Descomente para rodar em segundo plano

    driver = webdriver.Chrome(options=options)
    
    # Wait geral de 10s para carregamento de páginas
    wait_geral = WebDriverWait(driver, 10)
    # Wait rápido de 2s para identificar rapidamente departamentos sem turmas
    wait_rapido = WebDriverWait(driver, 2)

    # Lista plana de matérias para gerar o JSON final
    lista_materias_final = []
    # Conjunto para rastrear códigos/matérias já adicionadas e evitar duplicatas
    codigos_processados = set()

    try:
        url = "https://sigaa.unb.br/sigaa/public/componentes/busca_componentes.jsf"
        driver.get(url)

        # Aguarda os filtros iniciais carregarem
        wait_geral.until(EC.presence_of_element_located((By.ID, "form:unidades")))
        wait_geral.until(EC.presence_of_element_located((By.ID, "form:nivel")))

        select_element_1 = wait_geral.until(EC.presence_of_element_located((By.ID, "form:nivel")))
        select_element_2 = wait_geral.until(EC.presence_of_element_located((By.ID, "form:unidades")))

        select_1 = Select(select_element_1)
        select_2 = Select(select_element_2)

        opcoes_1 = select_1.options
        opcoes_2 = select_2.options


        print(f"Total de opções encontradas: {len(opcoes_1)} níveis | {len(opcoes_2)} departamentos")

        for n in range(len(opcoes_1)):  # Iteração sobre Níveis de Ensino
            for i in range(len(opcoes_2)):  # Iteração sobre Departamentos len(opcoes_2) para rodar tudo
                # Reseta e recarrega a página de busca a cada combinação
                driver.get(url)
                wait_rapido.until(EC.presence_of_element_located((By.ID, "form:unidades")))

                # Seleciona o nível
                Select(driver.find_element(By.ID, "form:nivel")).select_by_index(n)

                # Seleciona o departamento
                select_unidades = Select(driver.find_element(By.ID, "form:unidades"))
                opcao_depto = select_unidades.options[i]
                
                nome_depto_bruto = opcao_depto.text.strip()
                depto_nome_limpo = limpar_nome_departamento(nome_depto_bruto)

                # Ignora opções vazias ou cabeçalhos
                if not depto_nome_limpo or "SELECIONE" in depto_nome_limpo.upper():
                    continue

                print(f"\n--- Processando: {depto_nome_limpo} (Nível índice: {n}) ---")
                select_unidades.select_by_index(i)

                # Clica em Buscar
                driver.find_element(By.ID, "form:btnBuscarComponentes").click()

                try:
                    # Aguarda a listagem de componentes carregar em até 2s
                    wait_rapido.until(EC.presence_of_element_located((By.ID, "formListagemComponentes")))

                    # Descobre a quantidade de linhas retornadas na tabela
                    linhas_tabela = driver.find_elements(
                        By.XPATH, "//form[@id='formListagemComponentes']//table/tbody/tr"
                    )
                    total_linhas = len(linhas_tabela)

                    # Iteramos pelo ÍNDICE para evitar StaleElementReferenceException
                    for index in range(total_linhas): #total_linhas para rodar tudo
                        try:
                            # Re-localiza a tabela e a linha atual a cada iteração
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

                            # Evita reprocessar uma matéria que já foi coletada em outro nível/departamento
                            if codigo in codigos_processados:
                                continue

                            # Entra na página de detalhes disparando a ação JSF
                            driver.execute_script(script_onclick)

                            # Aguarda a tela de detalhes renderizar
                            wait_geral.until(EC.presence_of_element_located((By.CLASS_NAME, "visualizacao")))

                            # Extração de detalhes (Ementa, Requisitos e Carga Horária)
                            pre_req, co_req, equiva = [], [], []
                            ementa = ""
                            carga_materia = "0"

                            linhas_detalhes = driver.find_elements(
                                By.XPATH, "//table[@class='visualizacao']//tbody//tr"
                            )
                            for row in linhas_detalhes: #cada row começa com /th/
                                texto_linha = row.text
                                #print(texto_linha, "TEXTO LINHA")

                                if "Pré-Requisitos:" in texto_linha:
                                    
                                    tds = row.find_elements(By.TAG_NAME, "td")
                                    for text in tds:
                                        print("PRE REQUISTIS", text.text, tds.index(text))
                                        pre_req.append(text.text)


                                elif "Co-Requisitos:" in texto_linha:
                                    
                                    tds = row.find_elements(By.TAG_NAME, "td")
                                    for text in tds:
                                        print("CO REQ",text.text, tds.index(text))
                                        co_req.append(text.text)

                                elif "Equivalências:" in texto_linha:
                                    
                                    tds = row.find_elements(By.TAG_NAME, "td")
                                    for text in tds:
                                        print("EQIU", text.text, tds.index(text))
                                        equiva.append(text.text)


                                elif "Ementa:" in texto_linha:
                               
                                    tds = row.find_elements(By.TAG_NAME, "td")
                                    for text in tds:
                                        print("EMENTA", text.text, tds.index(text))
                                        ementa = text.text


                                elif "Carga Horária Total:" in texto_linha or "Total de Carga Horária" in texto_linha:
                                    tds = row.find_elements(By.TAG_NAME, "td")
                                    for text in tds:
                                        texto_ch = text.text.strip()
                                        # Filtra apenas os números contidos na string (ex: "60 h." -> "60")
                                        carga_materia = "".join(filter(str.isdigit, texto_ch)) or "0"
                                        print(f"CARGA ENCONTRADA: {carga_materia}")
                                        

                            ch_int = int(carga_materia)

                            # Estrutura exata solicitada
                            materia_dados = {
                                "codigo": codigo,
                                "nome": nome,
                                "ementa": ementa,
                                "creditos": ch_int // 15 if ch_int > 0 else 0,
                                "carga_horaria": ch_int,
                                "pre_requisito": pre_req,
                                "co_requisito": co_req,
                                "equivalencia": equiva,
                            }

                            lista_materias_final.append(materia_dados)
                            codigos_processados.add(codigo)

                            print(f"  [OK] Processado: {codigo} - {nome}")

                            # Retorna para a listagem
                            driver.back()

                        except Exception as err_item:
                            print(f"  ❌ Erro ao processar item índice {index}: {err_item}")
                            driver.back()

                except Exception:
                    print(f"  [AVISO] Nenhum componente encontrado ou timeout para: {depto_nome_limpo}")

    finally:
        driver.quit()

        # Salva o resultado final como uma lista no arquivo materias.json
        pasta_destino = os.path.join("data", "raw", "sigaa")
        os.makedirs(pasta_destino, exist_ok=True)
        caminho_arquivo = os.path.join(pasta_destino, "materias.json")

        with open(caminho_arquivo, "w", encoding="utf-8") as f:
            json.dump(lista_materias_final, f, ensure_ascii=False, indent=4)

        print(f"\n[SUCESSO] Coleta concluída! Total de matérias: {len(lista_materias_final)}")
        print(f"Salvo em: {caminho_arquivo}")


if __name__ == "__main__":
    generate_seed_departamentos()