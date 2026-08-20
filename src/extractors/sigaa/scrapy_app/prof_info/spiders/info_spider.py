import json
import scrapy
from typing import List, Dict, Any, Generator
from src.utils.logger import get_logger
from src.utils.paths import SIGAA_SEED_FILE

class InfoSpiderSpider(scrapy.Spider):
    """
    Spider oficial do Scrapy para extração de dados docentes do SIGAA-UnB.
    """
    name = "info_spider_oficial"
    handle_httpstatus_list = [404, 500]

    def __init__(self, *args, **kwargs):
        super(InfoSpiderSpider, self).__init__(*args, **kwargs)
        
        self.custom_logger = get_logger(f"squad.sigaa.{self.name}")
        self.limit = kwargs.get('limit') 

        # Usa o caminho centralizado do utils/paths.py
        self.caminho_arquivo = SIGAA_SEED_FILE
        self.start_urls = []

        try:
            with open(self.caminho_arquivo, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                urls_completas = [
                    item.get("link_mais_info")
                    for item in data
                    if isinstance(item, dict) and item.get("link_mais_info")
                ]
                
                total_disponivel = len(urls_completas)

                if self.limit and isinstance(self.limit, int) and self.limit > 0:
                    self.start_urls = urls_completas[:self.limit]
                    self.custom_logger.info(
                        f"⚠️ MODO DE TESTE: Limitando execução para {len(self.start_urls)} "
                        f"de {total_disponivel} professores disponíveis."
                    )
                else:
                    self.start_urls = urls_completas
                    self.custom_logger.info(f"✅ URLs carregadas: {len(self.start_urls)} (Execução Completa).")

        except Exception as e:
            self.custom_logger.error(f"Erro ao carregar {self.caminho_arquivo.name}: {e}")
            
    # 1. ETAPA PORTAL
    def parse(self, response: scrapy.http.Response) -> Generator[scrapy.Request, None, None]:
        nome = response.css("div#id-docente h3::text").get(default="").strip().upper()
        departamento = response.css("p.departamento::text").get(default="").strip().upper()
        imagem_rel = response.css("div.foto_professor img::attr(src)").get(default="").strip()
        imagem = response.urljoin(imagem_rel) if imagem_rel else ""

        portal: Dict[str, Any] = {
            "nome": nome,
            "link_siape": response.url,
            "imagem": imagem,
            "departamento": departamento,
            "email": response.xpath("//*[@id='contato']//dt[contains(text(), ' Endereço eletrônico ')]/following-sibling::dd[1]").xpath("string(.)").get(default="").strip(),
            "curriculo_lattes": response.xpath("//*[@id='perfil-docente']//dt[contains(text(), ' Currículo Lattes: ')]/following-sibling::dd[1]").xpath("string(.)").get(default="").strip(),
            "sala": response.xpath("//*[@id='contato']//dt[contains(text(), ' Sala ')]/following-sibling::dd[1]").xpath("string(.)").get(default="").strip().upper(),
            "descricao": response.xpath("//*[@id='perfil-docente']//dt[contains(text(), ' Descrição pessoal ')]/following-sibling::dd[1]").xpath("string(.)").get(default="").strip(),
        }

        yield scrapy.Request(
            url=response.url.replace("portal.jsf", "disciplinas.jsf"),
            meta={"dados_perfil": portal},
            callback=self.parse_disciplinas
        )

    # 2. ETAPA DISCIPLINAS
    def parse_disciplinas(self, response: scrapy.http.Response) -> Generator[Dict[str, Any], None, None]:
        portal: Dict[str, Any] = response.meta["dados_perfil"]

        def extrair_lista_disciplinas(seletor_id: str, nivel_academico: str) -> List[Dict[str, str]]:
            lista_disciplinas: List[Dict[str, str]] = []

            if response.status != 200:
                return lista_disciplinas

            blocos = response.css(f"{seletor_id} tbody tr")
            periodo_atual: str = ""

            for tr in blocos:
                td_periodo = tr.css("td.anoPeriodo")
                if td_periodo:
                    periodo_atual = td_periodo.xpath("string(.)").get(default="").strip()
                    continue

                td_spacer = tr.css("td.spacer")
                if td_spacer:
                    periodo_atual = ""
                    continue

                codigo = tr.xpath("./td[1]/text()").get(default="").strip().upper()
                if not codigo:
                    continue

                nome_materia = tr.xpath("./td[2]/a/text()").get(default="").strip()
                if not nome_materia:
                    nome_materia = tr.xpath("./td[2]/text()").get(default="").strip()
                nome_materia = nome_materia.upper()

                link_materia_rel = tr.xpath("./td[2]/a/@href").get(default="").strip()
                link_materia = response.urljoin(link_materia_rel) if link_materia_rel else ""
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

        disciplinas_graduacao = extrair_lista_disciplinas("#turmas-graduacao", "graduacao")
        disciplinas_pos = extrair_lista_disciplinas("#turmas-pos", "pos-graduacao")

        portal["disciplinas"] = disciplinas_graduacao + disciplinas_pos

        self.custom_logger.info(f"Dados completos coletados para: {portal['link_siape']}")
        yield portal