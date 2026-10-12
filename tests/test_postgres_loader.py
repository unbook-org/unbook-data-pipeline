import pytest
from sqlalchemy import create_engine, select

from src.loaders.postgres_loader import (
    ensure_schema,
    load_avaliacoes,
    load_campi,
    load_departamentos,
    load_materias,
    load_professores,
    load_turmas,
    slugify,
)


@pytest.fixture
def sqlite_db():
    engine = create_engine("sqlite:///:memory:")
    tables = ensure_schema(engine)
    return engine, tables


def test_slugify():
    assert slugify("Maria da Silva") == "maria-da-silva"
    assert slugify("CIC0004 - Algoritmos") == "cic0004-algoritmos"
    assert slugify("") != ""


def test_load_campi(sqlite_db):
    engine, tables = sqlite_db
    with engine.begin() as conn:
        campi_map = load_campi(conn, tables)
        assert "DARCY" in campi_map
        assert "FGA" in campi_map
        assert "FCE" in campi_map
        assert "FAL" in campi_map

        # Chamada repetida deve ser idempotente
        campi_map2 = load_campi(conn, tables)
        assert campi_map2 == campi_map


def test_full_loading_pipeline(sqlite_db):
    engine, tables = sqlite_db

    profs_sample = [
        {
            "nome": "Maria da Silva",
            "siape": "1234567",
            "departamento": "CIC - DEPARTAMENTO DE CIÊNCIA DA COMPUTAÇÃO",
            "email": "maria@unb.br",
            "disciplinas": [
                {
                    "codigo": "CIC0004",
                    "nome": "Algoritmos",
                    "periodo": "2026.1",
                    "carga_horaria": 60,
                }
            ],
        }
    ]

    classes_sample = [
        {
            "course_code": "CIC0004",
            "course_name": "Algoritmos",
            "class_code": "01",
            "schedules_raw": "24M34",
            "location": "PAT AT-01",
            "vacancies": 40,
            "docente": "Maria da Silva",
            "departamento": "CIC - DEPARTAMENTO DE CIÊNCIA DA COMPUTAÇÃO",
        }
    ]

    reviews_sample = [
        {
            "course_code": "CIC0004",
            "course_name": "Algoritmos",
            "professor_name": "Maria da Silva",
            "semester": "2026/1",
            "rating": {
                "didactics": 10.0,
                "difficulty": "Médio",
                "recommended": True,
                "emoji_vibe": "😎",
            },
            "comment": "Excelente professora, explica com clareza e as avaliações são justas.",
            "outcome": "passed",
        }
    ]

    with engine.begin() as conn:
        campi_map = load_campi(conn, tables)
        dept_map = load_departamentos(conn, tables, campi_map, profs_sample, classes_sample, reviews_sample)
        prof_map = load_professores(conn, tables, dept_map, profs_sample)
        mat_map = load_materias(conn, tables, dept_map, profs_sample, classes_sample, reviews_sample)
        turmas_count = load_turmas(conn, tables, mat_map, prof_map, classes_sample)
        reviews_count = load_avaliacoes(conn, tables, mat_map, prof_map, dept_map, reviews_sample)

    assert len(campi_map) == 4
    assert len(dept_map) >= 1
    assert "1234567" in prof_map
    assert "CIC0004" in mat_map
    assert turmas_count == 1
    assert reviews_count == 1

    # Verifica integridade no banco
    with engine.connect() as conn:
        t_prof = tables["professores"]
        t_mat = tables["materias"]
        t_turma = tables["turmas"]
        t_aval = tables["avaliacoes"]

        p_row = conn.execute(select(t_prof.c.nome_completo, t_prof.c.siape)).fetchone()
        assert p_row[0] == "Maria da Silva"
        assert p_row[1] == "1234567"

        m_row = conn.execute(select(t_mat.c.codigo_materia, t_mat.c.creditos)).fetchone()
        assert m_row[0] == "CIC0004"
        assert m_row[1] == 4

        turma_row = conn.execute(select(t_turma.c.vagas_ofertadas, t_turma.c.horario_bruto)).fetchone()
        assert turma_row[0] == 40
        assert turma_row[1] == "24M34"

        aval_row = conn.execute(select(t_aval.c.nota_didatica, t_aval.c.status_aprovacao)).fetchone()
        assert aval_row[0] == 5  # 9.0 / 2 rounded -> 5
        assert aval_row[1] == "passei"
