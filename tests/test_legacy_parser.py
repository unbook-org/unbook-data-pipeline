import csv
from pathlib import Path

from src.extractors.legacy.parser import parse_reviews, run_legacy_parser
from src.transformers.clean_courses import split_course_code_and_name
from src.transformers.clean_professors import clean_professor_name, is_plausible_professor_name

FIELDNAMES = [
    "Campus que cursou a disciplina?",
    "Disciplina (ou código)",
    "Modalidade",
    "Semestre que cursou? 2024/2, etc",
    "Qual departamento ou curso da disciplina?",
    "Professor (a)",
    "Didática do professor em uma escala de 0 a 10?",
    "Nível de dificuldade da disciplina?",
    "Recomendaria para outro aluno?",
    "Feedback sincero ✨",
    "Como foi? (opcional)",
]


def _write_csv(path: Path, rows: list[dict]) -> Path:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _valid_row(**overrides) -> dict:
    row = {
        "Campus que cursou a disciplina?": "Campus Darcy",
        "Disciplina (ou código)": "CIC0004 - Algoritmos",
        "Modalidade": "🏫 Presencial",
        "Semestre que cursou? 2024/2, etc": "2024.2",
        "Qual departamento ou curso da disciplina?": "CIC",
        "Professor (a)": "dr. maría da silva",
        "Didática do professor em uma escala de 0 a 10?": "8,5",
        "Nível de dificuldade da disciplina?": "🟡 Fácil – Tem desafios, mas nada absurdo.",
        "Recomendaria para outro aluno?": "✅ Sim",
        "Feedback sincero ✨": "Professor explica muito bem e as provas são justas com o conteúdo.",
        "Como foi? (opcional)": "",
    }
    row.update(overrides)
    return row


def test_split_course_code_and_name():
    assert split_course_code_and_name("CIC0004") == ("CIC0004", None)
    assert split_course_code_and_name("CIC 0004 - Algoritmos") == ("CIC0004", "Algoritmos")
    assert split_course_code_and_name("Química geral") == (None, "Química geral")


def test_clean_professor_name_strips_title_and_particles():
    assert clean_professor_name("dr. maría da silva") == "María da Silva"
    assert is_plausible_professor_name("teste") is False
    assert is_plausible_professor_name(".") is False
    assert is_plausible_professor_name("Li") is False


def test_parser_keeps_only_usable_reviews(tmp_path: Path):
    csv_path = _write_csv(
        tmp_path / "avaliacoes.csv",
        [
            _valid_row(),
            _valid_row(
                **{
                    "Disciplina (ou código)": "Teste",
                    "Professor (a)": "Teste",
                    "Feedback sincero ✨": "Foi um teste",
                }
            ),
            _valid_row(**{"Feedback sincero ✨": "."}),
            _valid_row(**{"Feedback sincero ✨": "Bom"}),
            _valid_row(
                **{
                    "Professor (a)": "x" * 200,
                    "Feedback sincero ✨": "Comentário longo o suficiente para passar no filtro de tamanho.",
                }
            ),
        ],
    )

    reviews = parse_reviews(csv_path)

    assert len(reviews) == 1
    review = reviews[0]
    assert review["course_code"] == "CIC0004"
    assert review["course_name"] == "Algoritmos"
    assert review["professor_name"] == "María da Silva"
    assert review["campus"] == "Darcy Ribeiro"
    assert review["semester"] == "2024/2"
    assert review["rating"]["recommended"] is True
    assert review["rating"]["didactics"] == 8.5
    assert review["rating"]["emoji_vibe"] == "🟡"
    assert review["source"] == "legacy"
    assert "explica muito bem" in review["comment"]


def test_parser_maps_outcome_and_recommend_no(tmp_path: Path):
    csv_path = _write_csv(
        tmp_path / "avaliacoes.csv",
        [
            _valid_row(
                **{
                    "Recomendaria para outro aluno?": "❌ Não",
                    "Como foi? (opcional)": "❌ Reprovei",
                    "Semestre que cursou? 2024/2, etc": "1/2025",
                    "Campus que cursou a disciplina?": "Gama",
                }
            )
        ],
    )

    review = parse_reviews(csv_path)[0]
    assert review["rating"]["recommended"] is False
    assert review["semester"] == "2025/1"
    assert review["campus"] == "Gama"
    assert review["outcome"] == "failed"
    assert "Reprovei" not in review["comment"]


def test_run_legacy_parser_writes_json(tmp_path: Path):
    csv_path = _write_csv(tmp_path / "avaliacoes.csv", [_valid_row()])
    output_path = tmp_path / "legacy_reviews.json"

    records = run_legacy_parser(input_path=csv_path, output_path=output_path)

    assert output_path.exists()
    assert len(records) == 1
    assert records[0]["course_code"] == "CIC0004"
