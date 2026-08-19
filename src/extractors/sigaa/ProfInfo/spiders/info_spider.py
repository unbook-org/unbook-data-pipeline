import json
from pathlib import Path
import scrapy
from typing import List, Dict, Any, Generator

class InfoSpiderSpider(scrapy.Spider):
    """
    Spider oficial do Scrapy para extração de dados docentes do SIGAA-UnB.

    Esta spider processa um JSON de entrada contendo links de professores e navega
    assincronamente pelas abas do SIGAA para compilar um perfil unificado.

    Attributes:
        name (str): Nome de registro da spider no Scrapy.
        handle_httpstatus_list (List[int]): Lista de códigos HTTP que não devem
            interromper o fluxo (ex: 404, 500), permitindo que a spider continue
            processando outras abas do mesmo professor.
        caminho_arquivo (str): Caminho absoluto para o arquivo JSON de origem.
        start_urls (List[str]): Lista nativa do Scrapy contendo as URLs iniciais.
        data_raw (List[Dict[str, Any]]): Dados brutos carregados do arquivo JSON.
    """
    name = "info_spider_oficial"
    handle_httpstatus_list = [404, 500]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Raiz do projeto dinâmica
        base_dir = Path(__file__).resolve().parents[5]
        self.caminho_arquivo = (
            base_dir
            / "src"
            / "extractors"
            / "sigaa"
            / "Professores"
            / "Resultado"
            / "resp_selenium.json"
        )
        self.start_urls = []

        try:
            with open(self.caminho_arquivo, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.start_urls = [
                    item.get("link_mais_info")
                    for item in data
                    if isinstance(item, dict) and item.get("link_mais_info")
                ]
                self.logger.info(f"URLs carregadas: {len(self.start_urls)}")
        except Exception as e:
            self.logger.error(f"Erro ao carregar resp_selenium.json: {e}")

    # 1. ETAPA PORTAL
    def parse(self, response: scrapy.http.Response) -> Generator[scrapy.Request, None, None]:
        """
        Processa a página principal (Portal) do docente e extrai dados cadastrais básicos.

        Utiliza seletores CSS e XPath para raspar informações como nome, foto,
        e-mail e departamento. O método cria o dicionário principal e faz o repasse
        (yield) de uma nova requisição para a aba de disciplinas, enviando os dados
        coletados através do atributo `meta`.

        Args:
            response (scrapy.http.Response): Objeto de resposta HTTP contendo o HTML da página.

        Yields:
            scrapy.Request: Requisição para a aba de disciplinas ('disciplinas.jsf'),
            carregando o dicionário `portal` no parâmetro `meta`.
        """

        # Dicionário principal padronizado de acordo com o esquema de saída desejado
        portal: Dict[str, Any] = {
            "nome": response.css("div#id-docente h3::text").get(default="").strip(),
            "link_siape": response.url,
            "imagem": response.css("div.foto_professor img::attr(src)").get(default="").strip(),
            "departamento": response.css("p.departamento::text").get(default="").strip(),
            "email": response.xpath("//*[@id='contato']//dt[contains(text(), ' Endereço eletrônico ')]/following-sibling::dd[1]").xpath("string(.)").get(default="").strip(),
            "curriculo_lattes": response.xpath("//*[@id='perfil-docente']//dt[contains(text(), ' Currículo Lattes: ')]/following-sibling::dd[1]").xpath("string(.)").get(default="").strip(),
            "sala": response.xpath("//*[@id='contato']//dt[contains(text(), ' Sala ')]/following-sibling::dd[1]").xpath("string(.)").get(default="").strip(),
            "descricao": response.xpath("//*[@id='perfil-docente']//dt[contains(text(), ' Descrição pessoal ')]/following-sibling::dd[1]").xpath("string(.)").get(default="").strip(),
        }

        # Repassa o dicionário para a próxima etapa da cascata
        yield scrapy.Request(
            url=response.url.replace("portal.jsf", "disciplinas.jsf"),
            meta={"dados_perfil": portal},
            callback=self.parse_disciplinas
        )

    # 2. ETAPA DISCIPLINAS E YIELD FINAL
    def parse_disciplinas(self, response: scrapy.http.Response) -> Generator[Dict[str, Any], None, None]:
        """
        Processa as tabelas de histórico de turmas e consolida o dicionário final.

        Recupera o dicionário `portal` injetado na requisição anterior. Realiza
        a extração das tabelas de graduação e pós-graduação utilizando variáveis
        de estado para mapear períodos (semestres) que agrupam as disciplinas.

        Args:
            response (scrapy.http.Response): Objeto de resposta HTTP contendo o HTML da aba disciplinas.

        Yields:
            Dict[str, Any]: Dicionário final unificado representando o documento
            completo do docente, pronto para ser exportado pelo pipeline do Scrapy.
        """
        portal: Dict[str, Any] = response.meta["dados_perfil"]

        def extrair_lista_disciplinas(seletor_id: str, nivel_academico: str) -> List[Dict[str, str]]:
            """
            Extrai as disciplinas de uma tabela rastreando dinamicamente o período vigente.

            A função utiliza uma variável de estado (`periodo_atual`) que é atualizada
            sempre que uma tag `<td class="anoPeriodo">` é encontrada e resetada
            ao encontrar `<td class="spacer">`.

            Args:
                seletor_id (str): ID do contêiner da tabela (ex: '#turmas-graduacao').
                nivel_academico (str): Nível a ser injetado nos registros ('graduacao' ou 'pos-graduacao').

            Returns:
                List[Dict[str, str]]: Lista de dicionários, onde cada dicionário
                representa uma disciplina específica devidamente carimbada com seu período.
            """
            lista_disciplinas: List[Dict[str, str]] = []

            if response.status != 200:
                return lista_disciplinas

            blocos = response.css(f"{seletor_id} tbody tr")
            periodo_atual: str = ""

            for tr in blocos:
                # 1. Abertura de Bloco: Atualiza o período quando encontra o cabeçalho
                td_periodo = tr.css("td.anoPeriodo")
                if td_periodo:
                    periodo_atual = td_periodo.xpath("string(.)").get(default="").strip()
                    continue

                # 2. Fechamento de Bloco: Reseta o período ao encontrar o espaçador
                td_spacer = tr.css("td.spacer")
                if td_spacer:
                    periodo_atual = ""
                    continue

                # 3. Linhas de Dados: Extrai informações da disciplina
                codigo = tr.xpath("./td[1]/text()").get(default="").strip()
                if not codigo:
                    continue  # Ignora quebras de linha ou linhas vazias

                nome_materia = tr.xpath("./td[2]/a/text()").get(default="").strip()
                if not nome_materia:
                    nome_materia = tr.xpath("./td[2]/text()").get(default="").strip()

                link_materia = tr.xpath("./td[2]/a/@href").get(default="")
                carga_hor = tr.xpath("./td[3]/text()").get(default="").strip()

                disciplina_item = {
                    "periodo": periodo_atual,
                    "codigo": codigo,
                    "nome": nome_materia,
                    "carga_horaria": carga_hor,
                    "nivel_academico": nivel_academico,
                    "link": link_materia,
                }

                lista_disciplinas.append(disciplina_item)

            return lista_disciplinas

        # Extrai ambas as tabelas
        disciplinas_graduacao = extrair_lista_disciplinas("#turmas-graduacao", "graduacao")
        disciplinas_pos = extrair_lista_disciplinas("#turmas-pos", "pos-graduacao")

        # Concatena as duas listas geradas e as atribui à chave 'disciplinas'
        portal["disciplinas"] = disciplinas_graduacao + disciplinas_pos

        self.logger.info(f"Dados completos coletados para: {portal['link_siape']}")

        # Envia o dicionário final para ser processado pelos Feeds/Pipelines do Scrapy
        yield portal

        # usando o comando -> python -m json.tool resultados_final.json resultados_formatados.json
        #você pode formatar os resultados para facilitar visualização


