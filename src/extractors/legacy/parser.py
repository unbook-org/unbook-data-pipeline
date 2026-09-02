import csv
import json
import re
from pathlib import Path
from typing import Any

from src.transformers.clean_courses import clean_course_name, split_course_code_and_name
from src.transformers.clean_professors import clean_professor_name, is_plausible_professor_name
from src.utils.logger import get_logger
from src.utils.paths import LEGACY_PROCESSED_FILE, LEGACY_RAW_DIR

logger = get_logger("squad.legacy.parser")

MIN_COMMENT_LENGTH = 20
SOURCE = "legacy"

JUNK_COMMENTS = {
    ".",
    "..",
    "...",
    "…",
    "tr",
    "ok",
    "n/a",
    "na",
    "nenhum",
    "teste",
    "test",
    "foi um teste",
}

CAMPUS_ALIASES = {
    "darcy": "Darcy Ribeiro",
    "campus darcy": "Darcy Ribeiro",
    "darcy ribeiro": "Darcy Ribeiro",
    "ceilândia": "Ceilândia",
    "ceilandia": "Ceilândia",
    "campus ceilândia": "Ceilândia",
    "campus ceilandia": "Ceilândia",
    "gama": "Gama",
    "campus gama": "Gama",
    "planaltina": "Planaltina",
    "campus planaltina": "Planaltina",
}

COLUMN_NEEDLES = {
    "course": ("disciplina", "código"),
    "professor": ("professor",),
    "comment": ("feedback",),
    "campus": ("campus",),
    "semester": ("semestre",),
    "recommend": ("recomendaria",),
    "didactics": ("didática",),
    "difficulty": ("dificuldade",),
    "department": ("departamento",),
    "modality": ("modalidade",),
    "how_was": ("como foi",),
    "eval_method": ("método de avaliação",),
}

OUTCOME_ALIASES = {
    "passei": "passed",
    "reprovei": "failed",
    "tranquei": "dropped",
}


def find_legacy_csv(raw_dir: Path | None = None) -> Path | None:
    directory = raw_dir or LEGACY_RAW_DIR
    canonical = directory / "avaliacoes_disciplinas.csv"
    if canonical.exists():
        return canonical
    matches = sorted(directory.glob("*.csv"))
    return matches[0] if matches else None


def parse_reviews(input_path: Path) -> list[dict[str, Any]]:
    with open(input_path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"CSV sem cabeçalho: {input_path}")
        columns = _resolve_columns(reader.fieldnames)
        records: list[dict[str, Any]] = []
        skipped = 0
        for row in reader:
            review = _row_to_review(row, columns)
            if review is None:
                skipped += 1
                continue
            records.append(review)
        logger.info(
            f"Parse concluído: {len(records)} avaliações válidas, {skipped} descartadas."
        )
        return records


def run_legacy_parser(
    input_path: Path | None = None,
    output_path: Path | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    csv_path = input_path or find_legacy_csv()
    if csv_path is None:
        logger.error("❌ Nenhum CSV encontrado em data/raw/legacy/")
        return []

    logger.info(f"Acessando {csv_path.name} para extração de avaliações...")
    records = parse_reviews(csv_path)
    if limit:
        records = records[:limit]

    destination = output_path or LEGACY_PROCESSED_FILE
    destination.parent.mkdir(parents=True, exist_ok=True)
    with open(destination, "w", encoding="utf-8") as handle:
        json.dump(records, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    logger.info(f"✅ {len(records)} avaliações válidas salvas em: {destination}")
    return records


def _resolve_columns(fieldnames: list[str]) -> dict[str, str]:
    resolved: dict[str, str] = {}
    used: set[str] = set()
    for key, needles in COLUMN_NEEDLES.items():
        for column in fieldnames:
            if column in used:
                continue
            lowered = column.lower()
            if all(needle in lowered for needle in needles):
                resolved[key] = column
                used.add(column)
                break
    required = ("course", "professor", "comment")
    missing = [name for name in required if name not in resolved]
    if missing:
        raise KeyError(f"Colunas obrigatórias ausentes no CSV: {missing}")
    return resolved


def _cell(row: dict[str, str], columns: dict[str, str], key: str) -> str:
    column = columns.get(key)
    if not column:
        return ""
    return (row.get(column) or "").strip()


def _row_to_review(row: dict[str, str], columns: dict[str, str]) -> dict[str, Any] | None:
    course_code, course_name = split_course_code_and_name(_cell(row, columns, "course"))
    professor_name = clean_professor_name(_cell(row, columns, "professor"))
    comment = _sanitize_comment(_cell(row, columns, "comment"))

    if not course_code and not course_name:
        return None
    if course_name and course_name.lower() in JUNK_COMMENTS | {"teste", "test"}:
        return None
    if not is_plausible_professor_name(professor_name):
        return None
    if not _is_usable_comment(comment):
        return None

    difficulty_raw = _cell(row, columns, "difficulty")
    return {
        "course_code": course_code,
        "course_name": clean_course_name(course_name),
        "professor_name": professor_name,
        "campus": _normalize_campus(_cell(row, columns, "campus")),
        "semester": _normalize_semester(_cell(row, columns, "semester")),
        "rating": {
            "recommended": _parse_recommended(_cell(row, columns, "recommend")),
            "didactics": _parse_didactics(_cell(row, columns, "didactics")),
            "emoji_vibe": _extract_emoji(difficulty_raw),
            "grade_attained": None,
            "difficulty": _strip_label(difficulty_raw),
        },
        "comment": comment,
        "source": SOURCE,
        "department": clean_course_name(_cell(row, columns, "department")),
        "modality": _strip_label(_cell(row, columns, "modality")),
        "evaluation_method": clean_course_name(_cell(row, columns, "eval_method")),
        "outcome": _parse_outcome(_cell(row, columns, "how_was")),
    }


def _sanitize_comment(text: str) -> str:
    cleaned = re.sub(r"[ \t]+", " ", text or "")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "[email]", cleaned)
    cleaned = re.sub(r"\b\d{10,11}\b", "[telefone]", cleaned)
    return cleaned.strip()


def _is_usable_comment(comment: str) -> bool:
    if len(comment) < MIN_COMMENT_LENGTH:
        return False
    compact = re.sub(r"\W+", "", comment, flags=re.UNICODE).lower()
    if compact in JUNK_COMMENTS or comment.lower() in JUNK_COMMENTS:
        return False
    if not re.search(r"[A-Za-zÀ-ÿ]", comment):
        return False
    return True


def _normalize_campus(raw: str) -> str | None:
    key = re.sub(r"\s+", " ", raw).strip().lower()
    if not key:
        return None
    if key in CAMPUS_ALIASES:
        return CAMPUS_ALIASES[key]
    stripped = re.sub(r"^campus\s+", "", key).strip()
    return CAMPUS_ALIASES.get(stripped, raw.strip())


def _normalize_semester(raw: str) -> str | None:
    text = re.sub(r"\s+", " ", raw or "").strip()
    if not text:
        return None

    match = re.search(r"(20\d{2})\s*[/\.\s]\s*0?([12])\b", text)
    if match:
        return f"{match.group(1)}/{match.group(2)}"

    match = re.search(r"\b(\d{2})\s*[/\.]\s*0?([12])\b", text)
    if match:
        return f"20{match.group(1)}/{match.group(2)}"

    match = re.search(r"\b([12])\s*[/\.]\s*(20\d{2})\b", text)
    if match:
        return f"{match.group(2)}/{match.group(1)}"

    return None


def _parse_outcome(raw: str) -> str | None:
    text = raw.lower()
    for token, outcome in OUTCOME_ALIASES.items():
        if token in text:
            return outcome
    return None


def _parse_recommended(raw: str) -> bool | None:
    text = raw.lower()
    if "depende" in text:
        return None
    if "sim" in text:
        return True
    if "não" in text or "nao" in text:
        return False
    return None


def _parse_didactics(raw: str) -> float | None:
    match = re.search(r"(\d+(?:[.,]\d+)?)", raw.replace(" ", ""))
    if not match:
        return None
    value = float(match.group(1).replace(",", "."))
    if 0 <= value <= 10:
        return int(value) if value.is_integer() else value
    return None


def _extract_emoji(raw: str) -> str | None:
    for emoji in ("💀", "🔥", "🟢", "🟡", "🟠", "🔴"):
        if raw.startswith(emoji):
            return emoji
    return None


def _strip_label(raw: str) -> str | None:
    if not raw:
        return None
    text = re.sub(r"^[^\wÀ-ÿ]+", "", raw).strip()
    text = re.split(r"\s*[–-]\s*", text, maxsplit=1)[0].strip()
    return text or None
