"""Partes puras do scraper de currículos (checkpoint, junção e resumo). Nenhum teste abre o navegador."""

import pytest

from src.extractors.sigaa.curriculum.parser import (
    parse_curricula_list,
    parse_curriculum_report,
)
from src.extractors.sigaa.curriculum.scraper import (
    describe_error,
    is_done,
    load_checkpoint,
    merge_curriculum,
    save_checkpoint,
    summarize,
)
from tests.fixtures.sigaa_curriculo import (
    HTML_ESTRUTURAS_CURSO,
    HTML_RELATORIO_ATIVO,
    HTML_RELATORIO_INATIVO,
)

PROGRAM = {
    "sigaa_program_id": "414924",
    "name": "ENGENHARIA DE SOFTWARE",
    "degree": "Bacharelado",
    "shift": "DIURNO",
    "unit": "FCTE - CAMPUS UNB GAMA: FACULDADE DE CIÊNCIAS E TECNOLOGIAS EM ENGENHARIA",
    "city": "BRASÍLIA",
    "modality": "Presencial",
}


def _entries():
    return {e["curriculum_code"]: e for e in parse_curricula_list(HTML_ESTRUTURAS_CURSO)}


def test_merge_junta_lista_de_estruturas_e_relatorio():
    merged = merge_curriculum(_entries()["6360/2"], parse_curriculum_report(HTML_RELATORIO_ATIVO))

    assert merged["curriculum_code"] == "6360/2"
    assert (merged["created_year"], merged["status"], merged["shift_group"]) == (2024, "ativa", "Matutino e Vespertino")
    assert merged["sigaa_curriculum_id"] == "16220281"
    assert merged["workload"]["total_hours"] == 3525
    assert merged["components"]


def test_merge_rejeita_relatorio_de_outra_estrutura():
    with pytest.raises(ValueError, match="6360/-2"):
        merge_curriculum(_entries()["6360/2"], parse_curriculum_report(HTML_RELATORIO_INATIVO))


def test_checkpoint_inexistente_comeca_vazio(tmp_path):
    checkpoint = load_checkpoint(tmp_path / "curriculos_bruto.json")

    assert checkpoint["programs"] == {}
    assert not is_done(checkpoint, "414924")


def test_checkpoint_ida_e_volta_e_retomada(tmp_path):
    path = tmp_path / "sigaa" / "curriculos_bruto.json"
    checkpoint = load_checkpoint(path)
    curriculum = merge_curriculum(_entries()["6360/2"], parse_curriculum_report(HTML_RELATORIO_ATIVO))
    checkpoint["programs"]["414924"] = {"program": PROGRAM, "status": "ok", "curricula": [curriculum]}
    checkpoint["programs"]["414099"] = {
        "program": {**PROGRAM, "sigaa_program_id": "414099", "name": "ADMINISTRAÇÃO", "shift": "NOTURNO"},
        "status": "failed",
        "error": "TimeoutError: Timeout 30000ms exceeded.",
    }
    save_checkpoint(checkpoint, path)

    reloaded = load_checkpoint(path)
    assert reloaded["updated_at"].endswith("-03:00")
    assert not path.with_suffix(".json.tmp").exists()
    assert is_done(reloaded, "414924")
    assert not is_done(reloaded, "414099")  # falhas são tentadas de novo ao retomar


def test_resumo_conta_ok_falhas_estruturas_e_componentes():
    curriculum = merge_curriculum(_entries()["6360/2"], parse_curriculum_report(HTML_RELATORIO_ATIVO))
    checkpoint = {
        "programs": {
            "414924": {"program": PROGRAM, "status": "ok", "curricula": [curriculum]},
            "414099": {
                "program": {**PROGRAM, "name": "ADMINISTRAÇÃO", "shift": "NOTURNO"},
                "status": "failed",
                "error": "TimeoutError: x",
            },
        }
    }

    summary = summarize(checkpoint)

    assert (summary.selected, summary.ok, summary.curricula) == (2, 1, 1)
    assert summary.components == len(curriculum["components"])
    assert summary.failures == [
        {"sigaa_program_id": "414099", "name": "ADMINISTRAÇÃO - NOTURNO", "error": "TimeoutError: x"}
    ]
    assert summarize(checkpoint, ["414924"]).failures == []


def test_describe_error_usa_so_a_primeira_linha():
    error = TimeoutError("Locator.click: Timeout 30000ms exceeded.\nCall log:\n  - waiting for locator")

    assert describe_error(error) == "TimeoutError: Locator.click: Timeout 30000ms exceeded."
