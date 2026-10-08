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
    # options.add_argument("--headless")

    driver = webdriver.Chrome(options=options)
    
    # 1. Wait padrão para o carregamento inicial da página (10s)
    wait_geral = WebDriverWait(driver, 10)
    
    # 2. Wait CURTO (2s) especificamente para verificar se a tabela existe/retornou erro
    wait_rapido = WebDriverWait(driver, 2)
    
    departamentos_dict = {}

    try:
        url = "https://sigaa.unb.br/sigaa/public/componentes/busca_componentes.jsf"
        driver.get(url)

        # Aguarda os selects iniciais carregarem
        wait_geral.until(EC.presence_of_element_located((By.ID, "form:unidades")))
        wait_geral.until(EC.presence_of_element_located((By.ID, "form:nivel")))

        select_nivel_elem = driver.find_element(By.ID, "form:nivel")
        select_unidades_elem = driver.find_element(By.ID, "form:unidades")

        opcoes_nivel = Select(select_nivel_elem).options
        opcoes_unidades = Select(select_unidades_elem).options

        print(f"Total encontrado: {len(opcoes_nivel)} níveis | {len(opcoes_unidades)} departamentos")

        for n in range(len(opcoes_nivel)):
            for i in range(len(opcoes_unidades)):
                driver.get(url)
                
                # Aguarda apenas o elemento do formulário reaparecer
                wait_geral.until(EC.presence_of_element_located((By.ID, "form:unidades")))

                # Seleciona Nível
                Select(driver.find_element(By.ID, "form:nivel")).select_by_index(n)

                # Seleciona Departamento
                select_unidades = Select(driver.find_element(By.ID, "form:unidades"))
                opcao_departamento_elem = select_unidades.options[i]
                
                texto_departamento_bruto = opcao_departamento_elem.text.strip()
                depto_nome_limpo = limpar_nome_departamento(texto_departamento_bruto)

                if not depto_nome_limpo or "SELECIONE" in depto_nome_limpo.upper():
                    continue

                print(f"\n--- Mapeando Seed: {depto_nome_limpo} ---")
                select_unidades.select_by_index(i)

                # Clica no botão de busca
                driver.find_element(By.ID, "form:btnBuscarComponentes").click()

                try:
                    # ⚡ USO DO WAIT CURTO: Aguarda no MÁXIMO 2 segundos para ver se a listagem aparece
                    wait_rapido.until(EC.presence_of_element_located((By.ID, "formListagemComponentes")))

                    linhas_tabela = driver.find_elements(
                        By.XPATH, "//form[@id='formListagemComponentes']//table/tbody/tr"
                    )

                    if depto_nome_limpo not in departamentos_dict:
                        departamentos_dict[depto_nome_limpo] = {
                            "nome": depto_nome_limpo,
                            "materias": []
                        }

                    for tr in linhas_tabela:
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

                        materia_seed = {
                            "codigo": codigo,
                            "nome": nome,
                            "scriptonclick": script_onclick
                        }

                        if materia_seed not in departamentos_dict[depto_nome_limpo]["materias"]:
                            departamentos_dict[depto_nome_limpo]["materias"].append(materia_seed)

                    print(f"  [OK] Coletadas {len(departamentos_dict[depto_nome_limpo]['materias'])} matéria(s)")

                except Exception:
                    # Caso não encontre a listagem em até 2s, pula imediatamente para o próximo sem travamentos
                    print(f"  [AVISO] Sem componentes ou timeout rápido (2s) para: {depto_nome_limpo}")

    finally:
        driver.quit()

        resultado_final = list(departamentos_dict.values())
        
        pasta_destino = os.path.join("data", "raw", "sigaa")
        os.makedirs(pasta_destino, exist_ok=True)
        caminho_arquivo = os.path.join(pasta_destino, "departamentos.json")

        with open(caminho_arquivo, "w", encoding="utf-8") as f:
            json.dump(resultado_final, f, ensure_ascii=False, indent=4)

        print(f"\n[SUCESSO] Semente gerada com sucesso! Salvo em: {caminho_arquivo}")


if __name__ == "__main__":
    generate_seed_departamentos()