import json
import os
import scrapy

class InfoSpiderSpider(scrapy.Spider):
    name = "info_spider_oficial"
    caminho_arquivo = r"F:\UNB\Unbook\Scraper\Professores\Resultado\resp_selenium.json"
    
    def __init__(self, *args, **kwargs):
        super(InfoSpiderSpider, self).__init__(*args, **kwargs)
        
        # Inicia a lista nativa do Scrapy vazia
        self.start_urls = [] 
        
        self.logger.info(f"--- [DIagnóstico] Tentando ler o arquivo em: {self.caminho_arquivo}")
        try:
            with open(self.caminho_arquivo, "r", encoding="utf-8") as file:
                self.data_raw = json.load(file)
                
                if self.data_raw:
                    self.logger.info(f"--- [DIagnóstico] Sucesso! Numero de professores lidos: {len(self.data_raw)}")
                    
                    # 🚨 A PROVA DO CRIME: Vamos imprimir as chaves do primeiro professor do seu JSON!
                    # chaves_reais = list(self.data_raw[0].keys())
                    # self.logger.info(f"🚨 [ALERTA] AS CHAVES QUE EXISTEM NO SEU JSON SÃO: {chaves_reais}")
                    
                    # Gera os links preenchendo a variável oficial do Scrapy
                    self.start_urls = [i.get("link_mais_info") for i in self.data_raw if isinstance(i, dict) and i.get("link_mais_info")]
                    
                    self.logger.info(f"🚨 [ALERTA] TOTAL DE URLs GERADAS PARA O SCRAPY: {len(self.start_urls)}")
                    
        except Exception as e:
            self.logger.error(f"Erro ao ler o arquivo: {e}")

    # 1. ETAPA PORTAL
    # (Como não estamos mais usando start_requests, o Scrapy automaticamente manda a resposta para a def parse)
    def parse(self, response):

        # Monta o dicionário final utilizando a função unificada
        portal = {
            
            "nome": response.css("div#id-docente h3::text").get(default="").strip(),
            "imagem": response.css("div.foto_professor img::attr(src)").get(default="").strip(),
            "email": response.xpath("//*[@id='contato']//dt[contains(text(), ' Endereço eletrônico ')]/following-sibling::dd[1]").xpath("string(.)").get(default="").strip(),
            "departamento": response.css("p.departamento::text").get(default="").strip(),
            "link_siape": response.url,
            "descricao": response.xpath("//*[@id='perfil-docente']//dt[contains(text(), ' Descrição pessoal ')]/following-sibling::dd[1]").xpath("string(.)").get(default="").strip(),
            "curriculo": response.xpath("//*[@id='perfil-docente']//dt[contains(text(), ' Currículo Lattes: ')]/following-sibling::dd[1]").xpath("string(.)").get(default="").strip(),
            "sala": response.xpath("//*[@id='contato']//dt[contains(text(), ' Sala ')]/following-sibling::dd[1]").xpath("string(.)").get(default="").strip(),
        }
        
        # Pula para a próxima aba: Disciplinas
        yield scrapy.Request(
            url=response.url.replace("portal.jsf", "disciplinas.jsf"),
            meta={
                "dados_perfil": portal, 
            },
            callback=self.parse_disciplinas
        )

    # 3. ETAPA DISCIPLINAS E YIELD FINAL
    def parse_disciplinas(self, response):
        
        portal = response.meta["dados_perfil"]
        
        # Função auxiliar para extrair as disciplinas de uma tabela específica
        def extrair_lista_disciplinas(seletor_id): #seletores -> turmas-graduacao, turmas-pos
            lista_disciplinas = []
            # Seleciona todas as linhas da tabela dentro do ID correspondente
            blocos = response.css(f"{seletor_id} tbody tr")
            
            for tr in blocos:
                
                codigo = tr.xpath("./td[1]/text()").get(default="").strip()
                nome_materia = tr.xpath("./td[2]/a/text()").get(default="").strip()
                if not nome_materia:
                    nome_materia = tr.xpath("./td[2]/text()").get(default="").strip()
                link_materia = tr.xpath("./td[2]/a/@href").get(default="")
                carga_hor = tr.xpath("./td[3]/text()").get(default="").strip()
                
                # Cria o dicionário da disciplina atual
                disciplina_item = {
                    "periodo": "", #criar logica para determinar o periodo da disciplina
                    "codigo": codigo,
                    "nome": nome_materia,
                    "link_mat": link_materia,
                    "carga": carga_hor,
                }
                
                # Adiciona à lista
                lista_disciplinas.append(disciplina_item)
            
            return lista_disciplinas
    
        # Coleta graduação e pós-graduação estruturadas corretamente em listas
        nivel_disciplinas = {
            "graduacao": extrair_lista_disciplinas("#turmas-graduacao"),
            "pos-grad": extrair_lista_disciplinas("#turmas-pos")
        }
        
        self.logger.info("DISCIPLINAS COLETADAS")
        
        # Extração simples de atividades
       
        # Consolidação do dicionário final
        portal["disciplinas"] = nivel_disciplinas
        self.logger.info(f"Dados completos coletados para: {portal['link_siape']}")
        yield portal
        
        
#  
#perfil_completo = {
#     nome: 
#     link_siape:
#     imagem:
#     departamento:
#     email:
#     curriculo_lattes: 
#     sala: 
#     descricao:

#     formacao_academica: {
#         graduacao:
#         especializacao:
#         mestrado:
#         doutorado:
#         pos-doutorado:
#     }

#     disciplinas: [
#         {
#             periodo:
#             codigo:
#             nome:
#             carga_horaria:
#             nivel_academico: 
#             link: 
#         }
#     ]


# }