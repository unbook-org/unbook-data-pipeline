"""
Normalização do bruto de matrizes curriculares do SIGAA (data/raw/sigaa/curriculos_bruto.json)
para o schema de src/extractors/sigaa/curriculum/models.py (data/processed/sigaa_curriculos.json).

Só normaliza o que é determinístico (espaços, caixa/acentos de `nature`/`status`, horas como int)
e deduplica componentes. Registro que não passa nos modelos Pydantic é logado e descartado,
nunca corrigido. Ao final, loga a cobertura dos códigos de legacy_reviews.json (somente leitura).
"""

import json
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from src.extractors.sigaa.curriculum.models import Component, CurriculaOutput, Curriculum, Program
from src.utils.logger import get_logger
from src.utils.paths import LEGACY_PROCESSED_FILE, SIGAA_CURRICULA_PROCESSED_FILE, SIGAA_CURRICULA_RAW_FILE

logger = get_logger("squad.sigaa.curriculum.cleaner")

HOURS_RE = re.compile(r"^(\d+)\s*h?$", re.IGNORECASE)
# Campos que só existem no bruto (usados para navegar no SIGAA) e não vão para o schema.
RAW_ONLY_CURRICULUM_KEYS = {"sigaa_curriculum_id"}
LFS_POINTER_PREFIX = "version https://git-lfs"
TOP_MISSING_CODES = 20


@dataclass
class CleanStats:
    programs: int = 0
    programs_not_ok: int = 0
    programs_invalid: int = 0
    curricula: int = 0
    curricula_invalid: int = 0
    components: int = 0
    components_invalid: int = 0
    duplicates_removed: int = 0


@dataclass
class CoverageReport:
    total_records: int = 0
    records_without_code: int = 0
    records_with_code: int = 0
    records_found: int = 0
    distinct_codes: int = 0
    distinct_found: int = 0
    missing: Counter = field(default_factory=Counter)

    @property
    def distinct_pct(self) -> float:
        return 100 * self.distinct_found / self.distinct_codes if self.distinct_codes else 0.0

    @property
    def records_pct(self) -> float:
        return 100 * self.records_found / self.records_with_code if self.records_with_code else 0.0


# --- Normalização de valores ---


def clean_text(value: Any) -> Any:
    """Trim + espaços colapsados; string vazia vira None. Não-str passa intacto (a validação decide)."""
    if not isinstance(value, str):
        return value
    return re.sub(r"\s+", " ", value).strip() or None


def normalize_label(value: Any) -> Any:
    """Minúsculo e sem acento: "Obrigatória " -> "obrigatoria"."""
    text = clean_text(value)
    if not isinstance(text, str):
        return text
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def to_int(value: Any) -> int | None:
    """60, 60.0, "60" ou "60h" -> 60; vazio -> None. Qualquer outra coisa levanta ValueError."""
    if isinstance(value, str):
        value = clean_text(value)
    if value is None:
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        match = HOURS_RE.match(value)
        if match:
            return int(match.group(1))
    raise ValueError(f"valor não inteiro: {value!r}")


def _ints(section: Any) -> Any:
    return {key: to_int(value) for key, value in section.items()} if isinstance(section, dict) else section


def _describe(error: Exception) -> str:
    if isinstance(error, ValidationError):
        return "; ".join(f"{'.'.join(map(str, e['loc'])) or '<raiz>'}: {e['msg']}" for e in error.errors()[:3])
    return str(error)


# --- Registros ---


def clean_component(raw: dict[str, Any]) -> Component:
    """Normaliza e valida um componente. Levanta ValueError (inclui ValidationError) se inválido."""
    data = dict(raw)
    data["course_code"] = clean_text(data.get("course_code"))
    if isinstance(data["course_code"], str):
        data["course_code"] = data["course_code"].upper()
    data["course_name"] = clean_text(data.get("course_name"))
    data["workload_hours"] = to_int(data.get("workload_hours"))
    data["nature"] = normalize_label(data.get("nature"))
    data["level"] = to_int(data.get("level"))
    data["prerequisites_raw"] = clean_text(data.get("prerequisites_raw"))
    return Component.model_validate(data)


def dedupe_components(components: list[Component], label: str) -> list[Component]:
    """
    Deduplica por course_code dentro de uma estrutura, mantendo a posição da primeira ocorrência.
    Mesma regra do parser: obrigatória prevalece sobre optativa; outras divergências mantêm a primeira.
    """
    kept: dict[str, Component] = {}
    for component in components:
        code = component.course_code
        existing = kept.get(code)
        if existing is None:
            kept[code] = component
        elif existing == component:
            continue
        elif existing.nature == "optativa" and component.nature == "obrigatoria":
            logger.warning(f"{label}: {code} aparece como optativa e obrigatória; mantida a obrigatória.")
            kept[code] = component
        else:
            logger.warning(
                f"{label}: ocorrências divergentes de {code}; mantida a primeira "
                f"({existing.model_dump()}), ignorada ({component.model_dump()})."
            )
    return list(kept.values())


def clean_curriculum(raw: dict[str, Any], label: str, stats: CleanStats) -> Curriculum | None:
    label = f"{label} / {clean_text(raw.get('curriculum_code'))}"

    components: list[Component] = []
    for raw_component in raw.get("components") or []:
        try:
            components.append(clean_component(raw_component))
        except ValueError as error:
            stats.components_invalid += 1
            logger.warning(f"{label}: componente descartado {raw_component.get('course_code')!r}: {_describe(error)}")
    unique = dedupe_components(components, label)
    stats.duplicates_removed += len(components) - len(unique)

    try:
        data = {key: value for key, value in raw.items() if key not in RAW_ONLY_CURRICULUM_KEYS}
        data["curriculum_code"] = clean_text(data.get("curriculum_code"))
        data["created_year"] = to_int(data.get("created_year"))
        data["status"] = normalize_label(data.get("status"))
        data["shift_group"] = clean_text(data.get("shift_group"))
        data["workload"] = _ints(data.get("workload"))
        data["completion_semesters"] = _ints(data.get("completion_semesters"))
        data["components"] = unique
        curriculum = Curriculum.model_validate(data)
    except ValueError as error:
        stats.curricula_invalid += 1
        logger.warning(f"{label}: estrutura descartada: {_describe(error)}")
        return None

    stats.curricula += 1
    stats.components += len(unique)
    return curriculum


def clean_program(entry: dict[str, Any], stats: CleanStats) -> Program | None:
    program = {key: clean_text(value) for key, value in (entry.get("program") or {}).items()}
    label = f"curso {program.get('sigaa_program_id')} ({program.get('name')} - {program.get('shift')})"

    curricula = [
        curriculum
        for raw in entry.get("curricula") or []
        if (curriculum := clean_curriculum(raw, label, stats)) is not None
    ]
    try:
        cleaned = Program.model_validate({**program, "curricula": curricula})
    except ValidationError as error:
        stats.programs_invalid += 1
        logger.warning(f"{label}: curso descartado: {_describe(error)}")
        return None

    stats.programs += 1
    return cleaned


def clean_curricula(
    raw: dict[str, Any], program_ids: list[str] | None = None
) -> tuple[CurriculaOutput, CleanStats]:
    """Bruto (checkpoint do scraper) -> CurriculaOutput validado. `program_ids` restringe os cursos (--limit)."""
    stats = CleanStats()
    records = raw.get("programs") or {}
    selected = set(program_ids) if program_ids is not None else set(records)

    programs: list[Program] = []
    extracted_at: list[datetime] = []
    for program_id, entry in records.items():
        if program_id not in selected:
            continue
        if entry.get("status") != "ok":
            stats.programs_not_ok += 1
            logger.warning(f"curso {program_id}: status {entry.get('status')!r} no bruto; ignorado.")
            continue
        program = clean_program(entry, stats)
        if program is None:
            continue
        programs.append(program)
        if entry.get("extracted_at"):
            extracted_at.append(datetime.fromisoformat(entry["extracted_at"]))

    # Ordem estável entre runs (a ordem do checkpoint é a de conclusão dos workers).
    programs.sort(key=lambda p: (len(p.sigaa_program_id), p.sigaa_program_id))
    newest = max(extracted_at) if extracted_at else raw.get("updated_at")
    return CurriculaOutput(extracted_at=newest, programs=programs), stats


# --- Cobertura dos códigos do legacy ---


def load_legacy_reviews(path: Path = LEGACY_PROCESSED_FILE) -> list[dict[str, Any]] | None:
    """Lê legacy_reviews.json (somente leitura). None se ausente, ponteiro do LFS ou formato inesperado."""
    if not path.exists():
        logger.warning(f"Cobertura pulada: {path} não existe.")
        return None
    text = path.read_text(encoding="utf-8")
    if text.startswith(LFS_POINTER_PREFIX):
        logger.warning(f"Cobertura pulada: {path.name} é um ponteiro do Git LFS (rode `git lfs pull`).")
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        logger.warning(f"Cobertura pulada: {path.name} não é um JSON válido ({error}).")
        return None
    if not isinstance(data, list):
        logger.warning(f"Cobertura pulada: {path.name} não é uma lista de avaliações.")
        return None
    return data


def coverage_report(reviews: list[dict[str, Any]], known_codes: set[str]) -> CoverageReport:
    """Quantos course_code do legacy aparecem em alguma matriz. Registros só com course_name ficam à parte."""
    report = CoverageReport(total_records=len(reviews))
    codes: Counter = Counter()
    for review in reviews:
        code = clean_text(review.get("course_code"))
        if not isinstance(code, str):
            report.records_without_code += 1
            continue
        codes[code.upper()] += 1

    report.records_with_code = sum(codes.values())
    report.distinct_codes = len(codes)
    for code, count in codes.items():
        if code in known_codes:
            report.distinct_found += 1
            report.records_found += count
        else:
            report.missing[code] = count
    return report


def log_coverage_report(output: CurriculaOutput, legacy_path: Path = LEGACY_PROCESSED_FILE) -> CoverageReport | None:
    reviews = load_legacy_reviews(legacy_path)
    if reviews is None:
        return None

    known_codes = {c.course_code for p in output.programs for cur in p.curricula for c in cur.components}
    report = coverage_report(reviews, known_codes)

    logger.info(f"----- Cobertura de {legacy_path.name} nas matrizes ({len(output.programs)} curso(s)) -----")
    logger.info(
        f"Avaliações: {report.total_records} | com course_code: {report.records_with_code} | "
        f"sem course_code (só course_name, sem matching): {report.records_without_code}"
    )
    logger.info(
        f"Códigos distintos encontrados: {report.distinct_found}/{report.distinct_codes} "
        f"({report.distinct_pct:.1f}%) | avaliações cobertas: {report.records_found}/{report.records_with_code} "
        f"({report.records_pct:.1f}%)"
    )
    if report.missing:
        logger.info(f"Top {TOP_MISSING_CODES} códigos não encontrados (código: avaliações):")
        for code, count in report.missing.most_common(TOP_MISSING_CODES):
            logger.info(f"  {code}: {count}")
    return report


# --- Orquestração ---


def run_curricula_cleaner(
    program_ids: list[str] | None = None,
    raw_path: Path = SIGAA_CURRICULA_RAW_FILE,
    output_path: Path = SIGAA_CURRICULA_PROCESSED_FILE,
    legacy_path: Path = LEGACY_PROCESSED_FILE,
) -> Path:
    if not raw_path.exists():
        raise FileNotFoundError(f"Bruto de currículos inexistente: {raw_path}")

    logger.info(f"Carregando {raw_path.name} para normalização...")
    with open(raw_path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)

    output, stats = clean_curricula(raw, program_ids)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(output.model_dump(mode="json"), handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    logger.info("----- Resumo da normalização de currículos -----")
    logger.info(
        f"Cursos válidos: {stats.programs} | descartados: {stats.programs_invalid} | "
        f"ignorados (status != ok no bruto): {stats.programs_not_ok}"
    )
    logger.info(f"Estruturas válidas: {stats.curricula} | descartadas: {stats.curricula_invalid}")
    logger.info(
        f"Componentes válidos: {stats.components} | descartados: {stats.components_invalid} | "
        f"duplicados removidos: {stats.duplicates_removed}"
    )
    logger.info(f"✅ Currículos normalizados salvos em: {output_path}")

    log_coverage_report(output, legacy_path)
    return output_path
