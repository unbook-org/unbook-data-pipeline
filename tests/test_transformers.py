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
