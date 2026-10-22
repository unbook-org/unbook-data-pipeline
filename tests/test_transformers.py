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


def _raw_curricula_checkpoint():
    """Bruto mínimo no formato do checkpoint do scraper (Parte 3), com sujeira proposital."""
    return {
        "source": "https://sigaa.unb.br/sigaa/public/curso/lista.jsf?nivel=G&aba=p-graduacao",
        "updated_at": "2026-10-12T20:22:22-03:00",
        "programs": {
            "414924": {
                "program": {
                    "sigaa_program_id": "414924",
                    "name": "  ENGENHARIA   DE SOFTWARE ",
                    "degree": "Bacharelado",
                    "shift": "DIURNO",
                    "unit": "FCTE - CAMPUS UNB GAMA:\n FACULDADE DE CIÊNCIAS E TECNOLOGIAS EM ENGENHARIA",
                    "city": "BRASÍLIA",
                    "modality": "Presencial",
                },
                "status": "ok",
                "extracted_at": "2026-10-12T19:53:04-03:00",
                "curricula": [
                    {
                        "curriculum_code": " 6360/-2 ",
                        "created_year": "2009",
                        "status": " Inativa",
                        "shift_group": "Matutino \t e Vespertino",
                        "sigaa_curriculum_id": "140",
                        "workload": {
                            "total_hours": "3600h",
                            "optional_min_hours": 540.0,
                            "complementary_min_hours": 0,
                            "elective_max_hours": None,
                            "max_hours_per_term": "480",
                            "min_hours_per_term": " ",
                        },
                        "completion_semesters": {"min": "8", "avg": 10, "max": 16},
                        "components": [
                            {
                                "course_code": "CIC0004",
                                "course_name": "ALGORITMOS E PROGRAMAÇÃO DE COMPUTADORES",
                                "workload_hours": "90h",
                                "nature": "Optativa",
                                "level": None,
                                "prerequisites_raw": None,
                            },
                            {
                                "course_code": " lip0174",
                                "course_name": "LÍNGUA DE SINAIS  BRASILEIRA - BÁSICO",
                                "workload_hours": 60,
                                "nature": "optativa",
                                "level": None,
                                "prerequisites_raw": "  ",
                            },
                            {
                                "course_code": "MAT0025",
                                "course_name": "CÁLCULO 1",
                                "workload_hours": "90",
                                "nature": "OBRIGATÓRIA",
                                "level": "1",
                                "prerequisites_raw": None,
                            },
                        ],
                    }
                ],
            },
        },
    }


def _component(code, nature="optativa", level=None, name="DISCIPLINA", hours=60):
    from src.extractors.sigaa.curriculum.models import Component

    return Component(course_code=code, course_name=name, workload_hours=hours, nature=nature, level=level)


def test_clean_curricula_normalizes_text_labels_and_hours():
    from src.transformers.clean_curricula import clean_curricula

    output, stats = clean_curricula(_raw_curricula_checkpoint())

    program = output.programs[0]
    assert program.name == "ENGENHARIA DE SOFTWARE"
    assert program.unit == "FCTE - CAMPUS UNB GAMA: FACULDADE DE CIÊNCIAS E TECNOLOGIAS EM ENGENHARIA"
    curriculum = program.curricula[0]
    assert curriculum.curriculum_code == "6360/-2"
    assert curriculum.created_year == 2009
    assert curriculum.status == "inativa"
    assert curriculum.shift_group == "Matutino e Vespertino"
    assert curriculum.workload.model_dump() == {
        "total_hours": 3600,
        "optional_min_hours": 540,
        "complementary_min_hours": 0,
        "elective_max_hours": None,
        "max_hours_per_term": 480,
        "min_hours_per_term": None,
    }
    assert curriculum.completion_semesters.model_dump() == {"min": 8, "avg": 10, "max": 16}

    cic, lip, mat = curriculum.components
    assert (cic.workload_hours, cic.nature, cic.level) == (90, "optativa", None)
    assert (lip.course_code, lip.course_name) == ("LIP0174", "LÍNGUA DE SINAIS BRASILEIRA - BÁSICO")
    assert lip.prerequisites_raw is None
    assert (mat.workload_hours, mat.nature, mat.level) == (90, "obrigatoria", 1)

    dumped = output.model_dump(mode="json")
    assert "sigaa_curriculum_id" not in dumped["programs"][0]["curricula"][0]
    assert dumped["extracted_at"] == "2026-10-12T19:53:04-03:00"
    assert (stats.programs, stats.curricula, stats.components) == (1, 1, 3)


def test_normalize_label_and_to_int():
    import pytest

    from src.transformers.clean_curricula import normalize_label, to_int

    assert normalize_label("  Obrigatória ") == "obrigatoria"
    assert normalize_label("INATIVA") == "inativa"
    assert to_int("75h") == 75
    assert to_int(" 30 ") == 30
    assert to_int(45.0) == 45
    assert to_int("") is None
    for chute in ("sessenta", "60,5h", 60.5, True):
        with pytest.raises(ValueError):
            to_int(chute)


def test_dedupe_components_same_structure():
    from src.transformers.clean_curricula import dedupe_components

    components = [
        _component("CIC0004"),
        _component("MAT0025", nature="obrigatoria", level=1),
        _component("CIC0004"),  # repetição exata: some
        _component("FGA0318", hours=45),
        _component("CIC0004", nature="obrigatoria", level=2),  # obrigatória prevalece, na 1ª posição
        _component("FGA0318", hours=60),  # divergente: mantém a primeira
    ]

    unique = dedupe_components(components, "teste")

    assert [c.course_code for c in unique] == ["CIC0004", "MAT0025", "FGA0318"]
    assert (unique[0].nature, unique[0].level) == ("obrigatoria", 2)
    assert unique[2].workload_hours == 45


def test_clean_curricula_dedupes_after_normalization():
    from src.transformers.clean_curricula import clean_curricula

    raw = _raw_curricula_checkpoint()
    components = raw["programs"]["414924"]["curricula"][0]["components"]
    components.append(
        {**components[0], "course_code": " cic0004 ", "course_name": "ALGORITMOS E  PROGRAMAÇÃO DE COMPUTADORES"}
    )

    output, stats = clean_curricula(raw)

    codes = [c.course_code for c in output.programs[0].curricula[0].components]
    assert codes == ["CIC0004", "LIP0174", "MAT0025"]
    assert stats.duplicates_removed == 1


def test_clean_curricula_discards_invalid_records_without_guessing():
    from src.transformers.clean_curricula import clean_curricula

    raw = _raw_curricula_checkpoint()
    curriculum = raw["programs"]["414924"]["curricula"][0]
    curriculum["components"] += [
        {**curriculum["components"][0], "course_code": "XXX0001", "workload_hours": "sessenta"},
        {**curriculum["components"][0], "course_code": "XXX0002", "nature": "Complementar"},
        {**curriculum["components"][0], "course_code": "XXX0003", "nature": "obrigatoria", "level": None},
    ]
    raw["programs"]["414924"]["curricula"].append({**curriculum, "curriculum_code": "6360/1", "status": "Suspensa"})

    output, stats = clean_curricula(raw)

    curricula = output.programs[0].curricula
    assert [c.curriculum_code for c in curricula] == ["6360/-2"]
    assert [c.course_code for c in curricula[0].components] == ["CIC0004", "LIP0174", "MAT0025"]
    assert stats.curricula_invalid == 1
    assert stats.components_invalid == 6  # 3 em cada estrutura (a descartada também conta)


def test_clean_curricula_respects_selection_and_skips_failed():
    from src.transformers.clean_curricula import clean_curricula

    raw = _raw_curricula_checkpoint()
    ok = raw["programs"]["414924"]
    raw["programs"]["414130"] = {"program": {**ok["program"], "sigaa_program_id": "414130"}, "status": "failed"}
    raw["programs"]["99"] = {**ok, "program": {**ok["program"], "sigaa_program_id": "99"}}

    output, stats = clean_curricula(raw)
    assert [p.sigaa_program_id for p in output.programs] == ["99", "414924"]
    assert stats.programs_not_ok == 1

    limited, _ = clean_curricula(raw, program_ids=["414924"])
    assert [p.sigaa_program_id for p in limited.programs] == ["414924"]


def test_coverage_report_counts_codes_and_name_only_records():
    from src.transformers.clean_curricula import coverage_report

    reviews = [
        {"course_code": "CIC0004", "course_name": "APC"},
        {"course_code": "CIC0004", "course_name": "APC"},
        {"course_code": "MAT0025", "course_name": "CÁLCULO 1"},
        {"course_code": "FIS0001", "course_name": None},
        {"course_code": "FIS0001", "course_name": None},
        {"course_code": "ABC1234", "course_name": None},
        {"course_code": None, "course_name": "Cálculo 2"},
    ]

    report = coverage_report(reviews, {"CIC0004", "MAT0025"})

    assert report.records_without_code == 1
    assert (report.distinct_found, report.distinct_codes) == (2, 4)
    assert (report.records_found, report.records_with_code) == (3, 6)
    assert report.missing.most_common() == [("FIS0001", 2), ("ABC1234", 1)]


def test_run_curricula_cleaner_writes_valid_output_and_skips_lfs_pointer(tmp_path):
    import json

    from src.extractors.sigaa.curriculum.models import CurriculaOutput
    from src.transformers.clean_curricula import run_curricula_cleaner

    raw_path = tmp_path / "curriculos_bruto.json"
    raw_path.write_text(json.dumps(_raw_curricula_checkpoint(), ensure_ascii=False), encoding="utf-8")
    legacy_path = tmp_path / "legacy_reviews.json"
    pointer = "version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 1\n"
    legacy_path.write_text(pointer, encoding="utf-8")
    output_path = tmp_path / "sigaa_curriculos.json"

    assert run_curricula_cleaner(raw_path=raw_path, output_path=output_path, legacy_path=legacy_path) == output_path

    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert CurriculaOutput.model_validate(written).programs[0].sigaa_program_id == "414924"
    assert legacy_path.read_text(encoding="utf-8") == pointer
