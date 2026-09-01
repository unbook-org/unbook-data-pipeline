import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from extractors.sigaa.seed.get_classes import (
    extrair_inteiro,
    limpar_docentes,
    limpar_espacos,
    parse_turmas,
)
from extractors.sigaa.scrapy_app.prof_info.items import ProfinfoItem, TurmaItem

# Colunas: [0] turma [1] ano-período [2] docente [3] horário
#          [4] vagas ofertadas [5] vagas ocupadas [6] local
HTML_TURMAS = """
<div id="turmasAbertas">
  <table class="listagem">
    <tr class="agrupador">
      <td><span class="tituloDisciplina">CIC0004 - ALGORITMOS E PROGRAMACAO DE COMPUTADORES</span></td>
    </tr>
    <tr class="linhaPar">
      <td>01</td><td>2026.1</td><td>FULANO DE TAL (45h)</td>
      <td>24M34 (12/08/2026 - 15/12/2026)</td>
      <td> 40 </td><td>35</td><td>BSA - Sala 10</td>
    </tr>
  </table>
</div>
"""


def test_extrair_inteiro():
    assert extrair_inteiro(" 40 ") == 40
    assert extrair_inteiro("sem vagas") == 0


def test_parse_turmas_campos_obrigatorios():
    turmas = parse_turmas(HTML_TURMAS, "Departamento de Ciência da Computação")

    assert len(turmas) == 1
    turma = turmas[0]
    assert turma["course_code"] == "CIC0004"
    assert turma["course_name"] == "ALGORITMOS E PROGRAMACAO DE COMPUTADORES"
    assert turma["class_code"] == "01"
    assert turma["schedules_raw"] == "24M34"
    assert turma["location"] == "BSA - Sala 10"
    assert turma["vacancies"] == 40


def test_parse_turmas_vincula_docente_ao_departamento():
    turmas = parse_turmas(HTML_TURMAS, "Departamento de Ciência da Computação")

    turma = turmas[0]
    assert turma["docente"] == "FULANO DE TAL"
    assert turma["departamento"] == "Departamento de Ciência da Computação"


def test_parse_turmas_sem_tabela_retorna_lista_vazia():
    assert parse_turmas("<html></html>", "Qualquer Departamento") == []


def test_limpar_docentes_remove_carga_horaria():
    assert limpar_docentes("RODRIGO HADDAD (45h)") == "RODRIGO HADDAD"
    assert limpar_docentes("FULANO DE TAL") == "FULANO DE TAL"


def test_limpar_espacos_normaliza_departamento():
    texto = "CAMPUS UNB CEILÂNDIA:\n\tFACULDADE...   - BRASÍLIA"
    assert limpar_espacos(texto) == "CAMPUS UNB CEILÂNDIA: FACULDADE... - BRASÍLIA"


def test_turma_item_possui_campos_obrigatorios():
    campos = TurmaItem.__dataclass_fields__.keys()
    for campo in [
        "course_code", "course_name", "class_code",
        "schedules_raw", "location", "vacancies",
        "docente", "departamento",
    ]:
        assert campo in campos


def test_profinfo_item_vincula_docente_ao_departamento():
    campos = ProfinfoItem.__dataclass_fields__.keys()
    assert "nome" in campos
    assert "departamento" in campos
