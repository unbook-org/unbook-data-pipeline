import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

# Configura o navegador (deixe headless=False para você conseguir acompanhar na tela)
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
#options.add_argument("--headless") # Descomente se quiser rodar em segundo plano sem abrir a janela

driver = webdriver.Chrome(options=options)

resultados = []

try:
    # 1. Acessa a página inicial de busca de docentes do SIGAA
    url = "https://sigaa.unb.br/sigaa/public/docente/busca_docentes.jsf?aba=p-academico"
    driver.get(url)

    # 2. Aguarda o select de departamentos carregar na tela
    wait = WebDriverWait(driver, 15)
    select_element = wait.until(EC.presence_of_element_located((By.ID, "form:departamento")))

    # Extrai todas as opções do select
    select = Select(select_element)
    opcoes = select.options

    print(f"Total de opções encontradas: {len(opcoes)}")

    # Limitando aos 5 primeiros para teste (igual você estava fazendo)
    for i in range(len(opcoes)): #len(opcoes)
        # Recarrega o elemento select a cada loop para evitar StaleElementReferenceException
        select_element = driver.find_element(By.ID, "form:departamento")
        select = Select(select_element)

        opcoes_atualizadas = select.options
        opcao_atual = opcoes_atualizadas[i]

        val_departamento = opcao_atual.get_attribute("value")
        nome_opcao = opcao_atual.text.strip()

        print(f"\n--- Processando: {nome_opcao} (Valor: {val_departamento}) ---")

        # Seleciona o departamento pelo índice ou valor
        select.select_by_index(i)

        # Clica no botão de buscar
        botao_buscar = driver.find_element(By.ID, "form:buscar")
        botao_buscar.click()

        # Aguarda os resultados carregarem (espera o span.nome aparecer na tela)
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "span.nome")))
            time.sleep(1) # Pequena pausa de respiro para renderização do DOM

            # Coleta os dados da página de resultados
            nomes_elementos = driver.find_elements(By.CSS_SELECTOR, "span.nome")

            departamento_elemento = driver.find_elements(By.CSS_SELECTOR, "span.departamento")

            links_elementos = driver.find_elements(By.CSS_SELECTOR, "a[title='Clique aqui para acessar a página pública deste docente']")

            imagens_elementos = driver.find_elements(By.CSS_SELECTOR, "td.foto img")

            nome_dep_texto = departamento_elemento[0].text.strip() if departamento_elemento else nome_opcao

            for elem in nomes_elementos: #limitando pra testes

                index = nomes_elementos.index(elem) #posicao da lista

                professor_nome = elem.text.strip()

                link_info = links_elementos[index].get_attribute("href")
                link_imagem = imagens_elementos[index].get_attribute("src")

                if professor_nome:
                    print(f"Professor: {professor_nome}")
                    resultados.append({
                        "professor": professor_nome,
                        "link_imagem": link_imagem,
                        "link_mais_info" : link_info,
                        "departamento": nome_dep_texto,
                    })

        except Exception as e:
            print(f"Nenhum professor encontrado ou tempo esgotado para este departamento: {e}")

        # Retorna para a página de busca para o próximo ciclo do loop
        driver.get(url)
        time.sleep(1)

finally:
    # Fecha o navegador ao terminar
    driver.quit()

    # Salva os resultados em um arquivo JSON
    with open("resp_selenium.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=4)



    print(f"\n[SUCESSO] Coleta finalizada! Dados salvos em resp_selenium.json. Total coletado: {len(resultados)}")




