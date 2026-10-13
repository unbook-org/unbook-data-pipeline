"""
Funções puras HTML -> dict/list das telas públicas de currículos do SIGAA.

Sem rede e sem Playwright: cada função recebe o HTML de uma tela já baixada.
Seletores e padrões exemplificados nas fixtures de tests/fixtures/sigaa_curriculo.py.
"""

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from src.utils.logger import get_logger

logger = get_logger("squad.sigaa.curriculum.parser")

PROGRAM_ID_RE = re.compile(r"[?&]id=(\d+)")
PROGRAM_COUNT_RE = re.compile(r"Cursos\s*\((\d+)\)")
CURRICULUM_HEADER_RE = re.compile(r"Curricular\s+(\S+?),\s*Criado em\s+(\d{4})")
CURRICULA_TOTAL_RE = re.compile(r"^(\d+)\s+Estruturas Curriculares Disponíveis$")
REPORT_TRIGGER_RE = re.compile(r"\{'([^']+)':'\1','id':'(\d+)'\}")
LEVEL_RE = re.compile(r"^(\d+)º Nível$")
# O ".+" guloso preserva os " - " internos do nome (ex.: "CÁLCULO 1 - SEMIPRESENCIAL").
COMPONENT_RE = re.compile(r"^(\S+) - (.+) - (\d+)h$")
HOURS_RE = re.compile(r"^(\d+)\s*h?$")

PROGRAM_LINK_TITLE = "Visualizar Página do Curso"
REPORT_LINK_TITLE = "Relatório da Estrutura Curricular"

SECTION_OPTIONAL = "Optativas"
SECTION_COMPLEMENTARY = "Complementares"
SECTION_GROUPS = "Grupos de Componentes Optativos"

NATURE_MAP = {"Obrigatória": "obrigatoria", "Optativa": "optativa"}
STATUS_MAP = {"Ativa": "ativa", "Inativa": "inativa"}

# Rótulos exatos do cabeçalho (há "Total:" e "Total Mínima:", então nada de startswith).
WORKLOAD_LABELS = {
    "Total Mínima:": "total_hours",
    "Carga Horária Optativa Mínima:": "optional_min_hours",
    "Carga Horária Complementar Mínima:": "complementary_min_hours",
    "Carga Horária Máxima de Componentes Eletivos:": "elective_max_hours",
    "Carga Horária Máxima por Período Letivo:": "max_hours_per_term",
    "Carga Horária Mínima por Período Letivo:": "min_hours_per_term",
}
COMPLETION_LABELS = {"Mínimo:": "min", "Médio:": "avg", "Máximo:": "max"}


def clean_text(text: str) -> str:
    """Colapsa espaços, tabs, quebras de linha e &nbsp; num único espaço."""
    return re.sub(r"\s+", " ", text).strip()


def parse_hours(text: str | None) -> int | None:
    """'3525h' -> 3525, '8 &nbsp;' -> 8; qualquer outra coisa -> None."""
    if text is None:
        return None
    match = HOURS_RE.match(clean_text(text))
    return int(match.group(1)) if match else None


def _cell_text(tag: Tag) -> str:
    return clean_text(tag.get_text(" "))


def parse_program_list(html: str) -> list[dict[str, Any]]:
    """
    Lista de cursos (lista.jsf). Uma entrada por linha tr.linhaPar/tr.linhaImpar.

    A unidade vem da última linha de agrupamento td.subFormulario anterior ao curso.
    Colunas: [0] nome [1] grau [2] turno [3] sede [4] modalidade
             [5] grau (repetido) [6] coordenação [7] lupa (href com o id).
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table.listagem")
    if table is None:
        logger.warning("Tabela de cursos (table.listagem) não encontrada.")
        return []

    programs: list[dict[str, Any]] = []
    current_unit: str | None = None

    for row in table.select("tr"):
        unit_cell = row.select_one("td.subFormulario")
        if unit_cell is not None:
            current_unit = _cell_text(unit_cell)
            continue

        classes = row.get("class") or []
        if "linhaPar" not in classes and "linhaImpar" not in classes:
            continue

        cells = row.find_all("td", recursive=False)
        if len(cells) < 8:
            logger.warning(f"Linha de curso com {len(cells)} colunas (esperado 8): {_cell_text(row)!r}")
            continue

        link = cells[7].find("a", title=PROGRAM_LINK_TITLE)
        match = PROGRAM_ID_RE.search(link.get("href", "")) if link else None
        if match is None:
            logger.warning(f"Curso sem id interno na lupa: {_cell_text(cells[0])!r}")
            continue

        if current_unit is None:
            logger.warning(f"Curso sem unidade (td.subFormulario) anterior: {_cell_text(cells[0])!r}")

        programs.append(
            {
                "sigaa_program_id": match.group(1),
                "name": _cell_text(cells[0]),
                "degree": _cell_text(cells[1]),
                "shift": _cell_text(cells[2]),
                "unit": current_unit,
                "city": _cell_text(cells[3]),
                "modality": _cell_text(cells[4]),
            }
        )

    caption = table.find("caption")
    count_match = PROGRAM_COUNT_RE.search(caption.get_text()) if caption else None
    if count_match and int(count_match.group(1)) != len(programs):
        logger.warning(f"Caption indica {count_match.group(1)} cursos, mas {len(programs)} foram extraídos.")

    return programs


def parse_curricula_list(html: str) -> list[dict[str, Any]]:
    """
    Estruturas curriculares de um curso (curriculo.jsf?id=<curso>).

    Além dos campos do schema (código, ano, status, grupo de turno), devolve o
    necessário para abrir o relatório via POST JSF:
      - sigaa_curriculum_id: valor do parâmetro 'id' do onclick;
      - report_trigger: nome do parâmetro do botão (ex.: 'formCurriculosCurso:j_id_jsp_154341757_33j_id_1').
    """
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("#table_lt tr.campos, #table_lt tr.linha_par, #table_lt tr.linha_impar")

    curricula: list[dict[str, Any]] = []
    shift_group: str | None = None
    declared_total: int | None = None

    for row in rows:
        if "campos" in (row.get("class") or []):
            text = _cell_text(row)
            total_match = CURRICULA_TOTAL_RE.match(text)
            if total_match:
                declared_total = int(total_match.group(1))
            else:
                shift_group = text
            continue

        cells = row.find_all("td", recursive=False)
        if len(cells) < 3:
            logger.warning(f"Linha de estrutura com {len(cells)} colunas (esperado 3): {_cell_text(row)!r}")
            continue

        header_match = CURRICULUM_HEADER_RE.search(_cell_text(cells[0]))
        if header_match is None:
            logger.warning(f"Código/ano da estrutura não reconhecidos: {_cell_text(cells[0])!r}")
            continue
        code = header_match.group(1)

        status_text = _cell_text(cells[1])
        status = STATUS_MAP.get(status_text)
        if status is None:
            logger.warning(f"Status desconhecido na estrutura {code}: {status_text!r}")

        link = cells[2].find("a", title=REPORT_LINK_TITLE)
        trigger_match = REPORT_TRIGGER_RE.search(link.get("onclick", "")) if link else None
        if trigger_match is None:
            logger.warning(f"Estrutura {code} sem link de relatório reconhecível.")
            continue

        curricula.append(
            {
                "curriculum_code": code,
                "created_year": int(header_match.group(2)),
                "status": status,
                "shift_group": shift_group,
                "sigaa_curriculum_id": trigger_match.group(2),
                "report_trigger": trigger_match.group(1),
            }
        )

    if declared_total is not None and declared_total != len(curricula):
        logger.warning(f"Página indica {declared_total} estruturas, mas {len(curricula)} foram extraídas.")

    return curricula


def _parse_report_header(container: Tag) -> dict[str, str | None]:
    """Mapa rótulo (th) -> texto do td seguinte, incluindo a tabela aninhada de prazos."""
    fields: dict[str, str | None] = {}
    for th in container.select("table.formulario th"):
        td = th.find_next_sibling("td")
        fields[_cell_text(th)] = _cell_text(td) if td is not None else None
    return fields


def _parse_component_row(row: Tag) -> dict[str, Any] | None:
    cells = row.find_all("td", recursive=False)
    if not cells:
        return None
    text = _cell_text(cells[0])
    match = COMPONENT_RE.match(text)
    if match is None:
        logger.warning(f"Linha de componente fora do padrão 'CÓDIGO - NOME - CARGAh': {text!r}")
        return None

    nature_raw = None
    if len(cells) > 1:
        italic = cells[1].find("i")
        nature_raw = _cell_text(italic) if italic is not None else None

    return {
        "course_code": match.group(1),
        "course_name": match.group(2),
        "workload_hours": int(match.group(3)),
        "nature_raw": nature_raw,
    }


def _merge_component(components: dict[str, dict[str, Any]], new: dict[str, Any], code: str) -> None:
    """Deduplica por course_code; uma ocorrência obrigatória prevalece sobre uma optativa."""
    key = new["course_code"]
    existing = components.get(key)
    if existing is None:
        components[key] = new
        return
    if existing == new:
        return
    if existing["nature"] == "optativa" and new["nature"] == "obrigatoria":
        logger.warning(f"{code}: {key} aparece como optativa e obrigatória; mantida a obrigatória.")
        components[key] = new
        return
    logger.warning(f"{code}: ocorrências divergentes de {key}; mantida a primeira ({existing}), ignorada ({new}).")


def parse_curriculum_report(html: str) -> dict[str, Any]:
    """
    Relatório da Estrutura Curricular (resposta do POST em curriculo.jsf).

    Devolve curriculum_code, workload, completion_semesters e components
    (deduplicados por course_code). Ano, status e grupo de turno não estão no
    relatório: vêm de parse_curricula_list.

    Seções:
      - "Optativas": nature conforme a célula (Optativa), level = None;
      - "Nº Nível": obrigatória recebe level = N; optativa fica com level = None (level só para obrigatórias);
      - "Complementares": componentes descartados com aviso (sem valor no enum nature);
      - "Grupos de Componentes Optativos": não cria componentes, só confere que
        cada um já veio da seção Optativas.
    """
    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one("form#formulario") or soup

    fields = _parse_report_header(container)
    code = fields.get("Código:") or None
    if code is None:
        logger.warning("Relatório sem 'Código:' no cabeçalho.")
    label = code or "<sem código>"

    workload: dict[str, int | None] = {}
    for header_label, key in WORKLOAD_LABELS.items():
        workload[key] = parse_hours(fields.get(header_label))
        if workload[key] is None:
            logger.warning(f"{label}: campo ausente ou inválido no cabeçalho: {header_label!r}")

    completion: dict[str, int | None] = {}
    for header_label, key in COMPLETION_LABELS.items():
        completion[key] = parse_hours(fields.get(header_label))
        if completion[key] is None:
            logger.warning(f"{label}: prazo ausente ou inválido no cabeçalho: {header_label!r}")

    components: dict[str, dict[str, Any]] = {}
    optional_codes = set()
    section: str | None = None
    level: int | None = None
    dropped_levels = 0

    for row in container.select("tr.tituloRelatorio, tr.componentes"):
        if "tituloRelatorio" in (row.get("class") or []):
            section = _cell_text(row)
            level_match = LEVEL_RE.match(section)
            level = int(level_match.group(1)) if level_match else None
            if level is None and section not in (SECTION_OPTIONAL, SECTION_COMPLEMENTARY, SECTION_GROUPS):
                logger.warning(f"{label}: seção desconhecida ignorada: {section!r}")
            continue

        parsed = _parse_component_row(row)
        if parsed is None:
            continue
        nature_raw = parsed.pop("nature_raw")

        if section == SECTION_GROUPS:
            if parsed["course_code"] not in optional_codes:
                logger.warning(f"{label}: {parsed['course_code']} está num grupo optativo mas não na seção Optativas.")
            continue
        if section == SECTION_COMPLEMENTARY:
            logger.warning(
                f"{label}: componente complementar descartado (sem valor em 'nature'): {parsed['course_code']}"
            )
            continue
        if section != SECTION_OPTIONAL and level is None:
            continue

        nature = NATURE_MAP.get(nature_raw or "")
        if nature is None:
            logger.warning(f"{label}: natureza desconhecida em {parsed['course_code']}: {nature_raw!r}")
            continue

        if nature == "obrigatoria" and level is None:
            logger.warning(f"{label}: obrigatória fora de seção de nível descartada: {parsed['course_code']}")
            continue
        if nature == "optativa":
            optional_codes.add(parsed["course_code"])
            if level is not None:
                dropped_levels += 1

        component = {
            **parsed,
            "nature": nature,
            "level": level if nature == "obrigatoria" else None,
            "prerequisites_raw": None,
        }
        _merge_component(components, component, label)

    if dropped_levels:
        logger.info(f"{label}: {dropped_levels} optativa(s) listadas em seção de nível ficaram com level = null.")
    logger.info(f"{label}: pré-requisitos não visíveis no relatório; prerequisites_raw = null.")

    return {
        "curriculum_code": code,
        "workload": workload,
        "completion_semesters": completion,
        "components": list(components.values()),
    }
