import logging
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from src.extractors.sigaa.curriculum.models import Component, CurriculaOutput
from src.extractors.sigaa.curriculum.parser import (
    parse_curricula_list,
    parse_curriculum_report,
    parse_program_list,
)
from tests.fixtures.sigaa_curriculo import (
    HTML_ESTRUTURAS_CURSO,
    HTML_LISTA_CURSOS,
    HTML_RELATORIO_ATIVO,
    HTML_RELATORIO_INATIVO,
)


def _by_code(report):
    return {c["course_code"]: c for c in report["components"]}


# --- Lista de cursos ---------------------------------------------------------

def test_lista_de_cursos_quantidade():
    programs = parse_program_list(HTML_LISTA_CURSOS)

    assert len(programs) == HTML_LISTA_CURSOS.count('title="Visualizar Página do Curso"') == 4


def test_lista_de_cursos_campos_e_unidade_de_agrupamento():
    programs = parse_program_list(HTML_LISTA_CURSOS)

    assert programs[-1] == {
        "sigaa_program_id": "414924",
        "name": "ENGENHARIA DE SOFTWARE",
        "degree": "Bacharelado",
        "shift": "DIURNO",
        "unit": "FCTE - CAMPUS UNB GAMA: FACULDADE DE CIÊNCIAS E TECNOLOGIAS EM ENGENHARIA",
        "city": "BRASÍLIA",
        "modality": "Presencial",
    }
    assert [p["unit"] for p in programs[:2]] == ["ADM - DEPTO ADMINISTRAÇÃO"] * 2


def test_lista_de_cursos_nome_repetido_tem_ids_distintos():
    adm = [p for p in parse_program_list(HTML_LISTA_CURSOS) if p["name"] == "ADMINISTRAÇÃO"]

    assert [(p["sigaa_program_id"], p["shift"]) for p in adm] == [("414099", "NOTURNO"), ("414112", "DIURNO")]


def test_lista_de_cursos_avisa_divergencia_com_caption(caplog):
    # A fixture mantém o caption original "Cursos (158)" com só 4 linhas.
    with caplog.at_level(logging.WARNING):
        parse_program_list(HTML_LISTA_CURSOS)

    assert "Caption indica 158 cursos, mas 4 foram extraídos." in caplog.text


def test_lista_de_cursos_sem_tabela_retorna_lista_vazia():
    assert parse_program_list("<html></html>") == []


# --- Estruturas curriculares do curso ----------------------------------------

def test_estruturas_do_curso():
    curricula = parse_curricula_list(HTML_ESTRUTURAS_CURSO)

    assert [(c["curriculum_code"], c["created_year"], c["status"]) for c in curricula] == [
        ("6360/2", 2024, "ativa"),
        ("6360/1", 2017, "inativa"),
        ("6360/-2", 2008, "inativa"),
    ]
    assert {c["shift_group"] for c in curricula} == {"Matutino e Vespertino"}


def test_estruturas_do_curso_trazem_dados_para_abrir_relatorio():
    curricula = parse_curricula_list(HTML_ESTRUTURAS_CURSO)

    assert [(c["sigaa_curriculum_id"], c["report_trigger"]) for c in curricula] == [
        ("16220281", "formCurriculosCurso:j_id_jsp_154341757_33"),
        ("411", "formCurriculosCurso:j_id_jsp_154341757_33j_id_1"),
        ("140", "formCurriculosCurso:j_id_jsp_154341757_33j_id_2"),
    ]


def test_estruturas_do_curso_total_confere_sem_aviso(caplog):
    with caplog.at_level(logging.WARNING):
        parse_curricula_list(HTML_ESTRUTURAS_CURSO)

    assert caplog.records == []


# --- Relatório: cabeçalho ----------------------------------------------------

def test_cabecalho_relatorio_ativo():
    report = parse_curriculum_report(HTML_RELATORIO_ATIVO)

    assert report["curriculum_code"] == "6360/2"
    assert report["workload"] == {
        "total_hours": 3525,
        "optional_min_hours": 540,
        "complementary_min_hours": 0,
        "elective_max_hours": 360,
        "max_hours_per_term": 480,
        "min_hours_per_term": 240,
    }
    assert report["completion_semesters"] == {"min": 8, "avg": 10, "max": 16}


def test_cabecalho_relatorio_inativo_com_versao_negativa():
    report = parse_curriculum_report(HTML_RELATORIO_INATIVO)

    assert report["curriculum_code"] == "6360/-2"
    # "Total Mínima:" (3600h), não "Total:" (2130h).
    assert report["workload"]["total_hours"] == 3600
    assert report["workload"]["optional_min_hours"] == 1470
    assert report["completion_semesters"] == {"min": 10, "avg": 10, "max": 16}


def test_relatorio_sem_cabecalho_vira_nulo_e_loga(caplog):
    with caplog.at_level(logging.WARNING):
        report = parse_curriculum_report("<html></html>")

    assert report["curriculum_code"] is None
    assert set(report["workload"].values()) == {None}
    assert set(report["completion_semesters"].values()) == {None}
    assert report["components"] == []
    assert "Total Mínima:" in caplog.text


# --- Relatório: componentes --------------------------------------------------

def test_obrigatorias_com_level_do_nivel():
    components = _by_code(parse_curriculum_report(HTML_RELATORIO_ATIVO))

    obrigatorias = {code: c["level"] for code, c in components.items() if c["nature"] == "obrigatoria"}
    assert obrigatorias == {"CIC0004": 1, "MAT0025": 1, "FGA0318": 10}


def test_optativas_com_level_nulo():
    for html in (HTML_RELATORIO_ATIVO, HTML_RELATORIO_INATIVO):
        optativas = [c for c in parse_curriculum_report(html)["components"] if c["nature"] == "optativa"]
        assert optativas
        assert all(c["level"] is None for c in optativas)


def test_optativa_listada_em_nivel_fica_sem_level_e_sem_duplicar():
    # CIC0004 aparece em Optativas, no 1º Nível (como Optativa) e no grupo CADEIA 2.
    report = parse_curriculum_report(HTML_RELATORIO_INATIVO)
    codes = [c["course_code"] for c in report["components"]]

    assert codes.count("CIC0004") == 1
    assert _by_code(report)["CIC0004"]["nature"] == "optativa"
    assert _by_code(report)["CIC0004"]["level"] is None


def test_grupos_optativos_nao_criam_componentes():
    report = parse_curriculum_report(HTML_RELATORIO_INATIVO)

    assert [c["course_code"] for c in report["components"]] == [
        "CIC0004", "CIC0088", "CIC0007", "MAT0137", "MAT0024",
    ]


def test_nome_de_disciplina_com_hifen():
    ativo = _by_code(parse_curriculum_report(HTML_RELATORIO_ATIVO))
    inativo = _by_code(parse_curriculum_report(HTML_RELATORIO_INATIVO))

    assert ativo["LIP0174"]["course_name"] == "LÍNGUA DE SINAIS BRASILEIRA - BÁSICO"
    assert ativo["LIP0174"]["workload_hours"] == 60
    assert inativo["MAT0137"]["course_name"] == "CÁLCULO 1 - SEMIPRESENCIAL"
    assert inativo["MAT0137"]["workload_hours"] == 90


def test_cargas_fora_de_60h():
    # As fixtures não têm 30h nem 75h; as cargas fora de 60h presentes são 45h e 90h.
    components = _by_code(parse_curriculum_report(HTML_RELATORIO_ATIVO))

    assert components["FGA0318"]["workload_hours"] == 45
    assert components["CIC0004"]["workload_hours"] == 90
    assert components["MAT0025"]["workload_hours"] == 90


def test_prerequisitos_sempre_nulos():
    for html in (HTML_RELATORIO_ATIVO, HTML_RELATORIO_INATIVO):
        assert all(c["prerequisites_raw"] is None for c in parse_curriculum_report(html)["components"])


# --- Modelos Pydantic --------------------------------------------------------

def test_saida_do_parser_valida_contra_os_modelos():
    program = next(p for p in parse_program_list(HTML_LISTA_CURSOS) if p["sigaa_program_id"] == "414924")
    listed = {c["curriculum_code"]: c for c in parse_curricula_list(HTML_ESTRUTURAS_CURSO)}

    curricula = []
    for html in (HTML_RELATORIO_ATIVO, HTML_RELATORIO_INATIVO):
        report = parse_curriculum_report(html)
        entry = listed[report["curriculum_code"]]
        curricula.append(
            {
                **report,
                "created_year": entry["created_year"],
                "status": entry["status"],
                "shift_group": entry["shift_group"],
            }
        )

    output = CurriculaOutput.model_validate(
        {
            "extracted_at": datetime.now(timezone(timedelta(hours=-3))),
            "programs": [{**program, "curricula": curricula}],
        }
    )

    dumped = output.model_dump(mode="json")
    assert dumped["source"] == "https://sigaa.unb.br/sigaa/public/curso/curriculo.jsf"
    assert dumped["extracted_at"].endswith("-03:00")
    assert [c["curriculum_code"] for c in dumped["programs"][0]["curricula"]] == ["6360/2", "6360/-2"]


BASE_COMPONENT = {"course_code": "CIC0004", "course_name": "ALGORITMOS", "workload_hours": 90}


@pytest.mark.parametrize(
    "extra",
    [
        {"nature": "obrigatoria", "level": None},
        {"nature": "optativa", "level": 1},
        {"nature": "complementar", "level": None},
        {"nature": "Obrigatória", "level": 1},
    ],
)
def test_component_rejeita_nature_ou_level_invalidos(extra):
    with pytest.raises(ValidationError):
        Component.model_validate({**BASE_COMPONENT, **extra})


def test_component_aceita_combinacoes_validas():
    assert Component.model_validate({**BASE_COMPONENT, "nature": "obrigatoria", "level": 1}).level == 1
    assert Component.model_validate({**BASE_COMPONENT, "nature": "optativa", "level": None}).level is None


def test_curricula_output_exige_fuso_horario():
    with pytest.raises(ValidationError):
        CurriculaOutput.model_validate({"extracted_at": datetime(2026, 10, 12, 18, 0), "programs": []})
