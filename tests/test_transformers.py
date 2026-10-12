from src.transformers.clean_courses import clean_course_name, split_course_code_and_name
from src.transformers.clean_professors import clean_professor_name, is_plausible_professor_name


def test_clean_course_name_collapses_whitespace():
    assert clean_course_name("  Física   1  ") == "Física 1"
    assert clean_course_name("   ") is None


def test_split_handles_lowercase_codes():
    assert split_course_code_and_name("fav0018") == ("FAV0018", None)


def test_professor_multiple_names_keeps_connector():
    assert clean_professor_name("YRIS E DÂMARIS") == "Yris e Dâmaris"


def test_professor_rejects_comment_pasted_in_name_field():
    dumped = (
        "Semestre realizado pelo professor Leonardo lamas, o professor se mostrou "
        "bem empenhado no início com uma boa intenção e dedicação em fazer seus alunos "
        "aprenderem e entender tanto da matéria dele quanto da própria educação física"
    )
    assert is_plausible_professor_name(dumped) is False


def test_sigaa_cleaner_extract_siape():
    from src.transformers.sigaa_cleaner import extract_siape

    assert extract_siape("https://sigaa.unb.br/portal.jsf?siape=2277937") == "2277937"
    assert extract_siape("siape=1234567") == "1234567"
    assert extract_siape("2277937") == "2277937"
    assert extract_siape(None) is None


def test_sigaa_cleaner_clean_department_name():
    from src.transformers.sigaa_cleaner import clean_department_name

    code, name = clean_department_name("FCTS - CAMPUS UNB CEILÂNDIA: FACULDADE DE CIÊNCIAS")
    assert code == "FCTS"
    assert "CAMPUS UNB CEILÂNDIA" in name

    code2, name2 = clean_department_name("Departamento de Ciência da Computação")
    assert code2 == ""
    assert name2 == "Departamento de Ciência da Computação"


def test_sigaa_cleaner_professor_record():
    from src.transformers.sigaa_cleaner import clean_sigaa_professor_record

    raw = {
        "nome": "dr. MARIO DA SILVA",
        "link_siape": "https://sigaa.unb.br/portal.jsf?siape=1234567",
        "imagem": "https://unb.br/foto.jpg",
        "departamento": "CIC - DEPARTAMENTO DE CIÊNCIA DA COMPUTAÇÃO",
        "email": "mario@unb.br",
        "curriculo_lattes": "http://lattes.cnpq.br/123",
        "sala": "NÃO INFORMADO",
        "descricao": "não informada",
        "disciplinas": [
            {
                "codigo": "CIC0004",
                "nome": "ALGORITMOS E PROGRAMAÇÃO",
                "periodo": "2026.1",
                "carga_horaria": "60h",
            },
            # Duplicata que deve ser descartada
            {
                "codigo": "CIC0004",
                "nome": "ALGORITMOS E PROGRAMAÇÃO",
                "periodo": "2026.1",
                "carga_horaria": "60h",
            },
        ],
    }

    cleaned = clean_sigaa_professor_record(raw)
    assert cleaned["nome"] == "Mario da Silva"
    assert cleaned["siape"] == "1234567"
    assert cleaned["sala"] is None
    assert cleaned["descricao"] is None
    assert len(cleaned["disciplinas"]) == 1
    assert cleaned["disciplinas"][0]["carga_horaria"] == 60


def test_sigaa_cleaner_class_record_swapped_columns():
    from src.transformers.sigaa_cleaner import clean_sigaa_class_record

    # Simula o caso com colunas invertidas do scraper
    raw = {
        "course_code": "FCE0006",
        "course_name": "HEMATOLOGIA CLÍNICA",
        "class_code": "01",
        "schedules_raw": "5M5  5T1Quinta-feira 12:00 às 13:50",
        "location": "20",
        "vacancies": 0,
        "docente": "RODRIGO HADDAD (45h)",
        "departamento": "FACULDADE DE CIÊNCIAS",
    }

    cleaned = clean_sigaa_class_record(raw)
    assert cleaned["vacancies"] == 20
    assert cleaned["location"] is None
    assert cleaned["schedules_raw"] == "5M5  5T1"
    assert cleaned["docente"] == "Rodrigo Haddad"

