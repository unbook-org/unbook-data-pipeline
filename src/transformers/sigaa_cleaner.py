import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Optional

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.transformers.clean_courses import clean_course_name
from src.transformers.clean_professors import clean_professor_name
from src.utils.logger import get_logger
from src.utils.paths import (
    SIGAA_CLASSES_FILE,
    SIGAA_CLASSES_PROCESSED_FILE,
    SIGAA_FINAL_RAW_FILE,
    SIGAA_PROCESSED_FILE,
    SIGAA_SEED_FILE,
)

logger = get_logger("squad.sigaa.cleaner")

SCHEDULE_REGEX = re.compile(r"([2-7]+[MTN][1-6]+(?:\s+[2-7]+[MTN][1-6]+)*)")
SIAPE_REGEX = re.compile(r"siape=(\d+)", re.IGNORECASE)


def remover_acentos_e_especiais(texto: str) -> str:
    """
    Remove acentuação, caracteres especiais e retorna o texto em maiúsculo.
    Mantém apenas letras (A-Z) e espaços.
    """
    if not texto:
        return ""

    texto_normalizado = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("utf-8")
    texto_limpo = re.sub(r"[^a-zA-Z\s]", "", texto_normalizado)
    return texto_limpo.strip().upper()


def limpar_espacos(texto: str | None) -> str:
    """Remove espaços excessivos, tabulações e quebras de linha."""
    if not texto:
        return ""
    return re.sub(r"\s+", " ", str(texto)).strip()


def extract_siape(link_or_text: str | None) -> str | None:
    """Extrai o número SIAPE a partir de uma URL ou texto."""
    if not link_or_text:
        return None
    match = SIAPE_REGEX.search(str(link_or_text))
    if match:
        return match.group(1)
    digits = re.sub(r"\D", "", str(link_or_text))
    return digits if len(digits) >= 6 else None


def clean_department_name(dept_raw: str | None) -> tuple[str, str]:
    """
    Normaliza a string de departamento e tenta separar código e nome.
    Ex: 'FCTS - CAMPUS UNB CEILÂNDIA: FACULDADE...' -> ('FCTS', 'CAMPUS UNB CEILÂNDIA...')
    """
    cleaned = limpar_espacos(dept_raw)
    if not cleaned:
        return "", ""

    if " - " in cleaned:
        parts = cleaned.split(" - ", 1)
        code = parts[0].strip().upper()
        name = parts[1].strip()
        if len(code) <= 20 and not " " in code:
            return code, name

    return "", cleaned


def clean_sigaa_professor_record(item: dict[str, Any]) -> dict[str, Any]:
    """Higieniza e normaliza um registro de professor do SIGAA."""
    nome_raw = item.get("nome") or item.get("professor") or ""
    nome = clean_professor_name(nome_raw)

    link_siape = item.get("link_siape") or item.get("link_mais_info") or ""
    siape = extract_siape(link_siape) or extract_siape(item.get("siape"))

    imagem = item.get("imagem") or item.get("link_imagem") or ""
    imagem = imagem.strip() if imagem and imagem.startswith("http") else None

    dept_raw = item.get("departamento") or ""
    dept_code, dept_name = clean_department_name(dept_raw)
    departamento = f"{dept_code} - {dept_name}" if dept_code else dept_name

    email = item.get("email") or ""
    email = email.strip() if "@" in email else None

    lattes = item.get("curriculo_lattes") or ""
    lattes = lattes.strip() if lattes.startswith("http") else None

    sala = limpar_espacos(item.get("sala"))
    if not sala or sala.upper() in {"NÃO INFORMADO", "NAO INFORMADO", "NÃO INFORMADA", "NAO INFORMADA"}:
        sala = None

    descricao = limpar_espacos(item.get("descricao"))
    if not descricao or descricao.lower() in {"não informada", "nao informada", "não informado", "nao informado"}:
        descricao = None

    raw_disciplinas = item.get("disciplinas") or []
    cleaned_disciplinas = []
    seen_disc = set()

    for d in raw_disciplinas:
        codigo = clean_course_name(d.get("codigo") or "")
        nome_disc = clean_course_name(d.get("nome") or "")
        periodo = limpar_espacos(d.get("periodo") or "")
        ch_raw = str(d.get("carga_horaria") or "")
        ch_match = re.search(r"\d+", ch_raw)
        ch = int(ch_match.group()) if ch_match else 60

        if not codigo and not nome_disc:
            continue

        disc_key = (codigo, nome_disc, periodo)
        if disc_key in seen_disc:
            continue
        seen_disc.add(disc_key)

        cleaned_disciplinas.append({
            "periodo": periodo,
            "codigo": codigo.upper() if codigo else "",
            "nome": nome_disc,
            "carga_horaria": ch,
            "nivel_academico": d.get("nivel_academico", "graduacao"),
            "link": d.get("link", ""),
        })

    return {
        "nome": nome,
        "siape": siape,
        "link_siape": link_siape,
        "imagem": imagem,
        "departamento": departamento,
        "email": email,
        "curriculo_lattes": lattes,
        "sala": sala,
        "descricao": descricao,
        "disciplinas": cleaned_disciplinas,
    }


def clean_sigaa_class_record(item: dict[str, Any]) -> dict[str, Any]:
    """Higieniza e normaliza um registro de turma do SIGAA."""
    course_code = (item.get("course_code") or "").strip().upper()
    course_name = clean_course_name(item.get("course_name") or "")
    class_code = (item.get("class_code") or "").strip()

    sched_raw = str(item.get("schedules_raw") or "").strip()
    match = SCHEDULE_REGEX.search(sched_raw)
    schedules_raw = match.group(1).strip() if match else sched_raw

    vagas = item.get("vacancies", 0)
    loc_raw = str(item.get("location") or "").strip()

    # Correção do desalinhamento histórico de colunas do parser
    if loc_raw.isdigit() and vagas == 0:
        vagas = int(loc_raw)
        location = None
    elif loc_raw.isdigit():
        location = None
    else:
        location = loc_raw or None

    docente_raw = item.get("docente") or ""
    docente_raw = re.sub(r"\s*\(\d+h\)", "", docente_raw).strip()
    if "A DEFINIR" in docente_raw.upper() or not docente_raw:
        docente = None
    else:
        docente = clean_professor_name(docente_raw)

    departamento = limpar_espacos(item.get("departamento") or "")

    return {
        "course_code": course_code,
        "course_name": course_name,
        "class_code": class_code,
        "schedules_raw": schedules_raw,
        "location": location,
        "vacancies": int(vagas),
        "docente": docente,
        "departamento": departamento,
    }


def _load_json_resilient(file_path: Path) -> list[dict[str, Any]]:
    """Carrega arquivo JSON com auto-reparo para dumps interrompidos."""
    if not file_path.exists():
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        logger.warning(f"JSON malformado em {file_path.name}. Tentando auto-reparo...")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().rstrip()
            if content.endswith(","):
                content = content[:-1]
            if not content.endswith("]"):
                content += "\n]"
            data = json.loads(content)
            if isinstance(data, list):
                logger.info(f"Auto-reparo bem-sucedido! {len(data)} itens recuperados.")
                return data
        except Exception as err:
            logger.error(f"Falha ao reparar {file_path.name}: {err}")
    return []


def run_sigaa_cleaner(
    input_raw_path: Optional[Path] = None,
    seed_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
) -> list[dict[str, Any]]:
    """
    Unifica e normaliza os dados de docentes do SIGAA.
    Mescla o dump detalhado com o catálogo completo de seed.
    """
    raw_file = input_raw_path or SIGAA_FINAL_RAW_FILE
    seed_file = seed_path or SIGAA_SEED_FILE
    out_file = output_path or SIGAA_PROCESSED_FILE

    professores_map: dict[str, dict[str, Any]] = {}

    # 1. Carrega dados completos do seed (todos os 2900+ docentes da UnB)
    if seed_file.exists():
        seeds = _load_json_resilient(seed_file)
        logger.info(f"Carregando catálogo seed: {len(seeds)} docentes encontrados.")
        for item in seeds:
            cleaned = clean_sigaa_professor_record(item)
            key = cleaned["siape"] or cleaned["nome"].lower()
            if key:
                professores_map[key] = cleaned

    # 2. Mescla com os dados detalhados raspados (com disciplinas, lattes, e-mail)
    if raw_file.exists():
        bruto = _load_json_resilient(raw_file)
        logger.info(f"Mesclando com extração detalhada: {len(bruto)} docentes.")
        for item in bruto:
            cleaned = clean_sigaa_professor_record(item)
            key = cleaned["siape"] or cleaned["nome"].lower()
            if key and key in professores_map:
                existing = professores_map[key]
                # Atualiza com campos mais completos
                for field in ["disciplinas", "email", "curriculo_lattes", "sala", "descricao", "imagem"]:
                    if cleaned.get(field):
                        existing[field] = cleaned[field]
            elif key:
                professores_map[key] = cleaned

    resultados = sorted(professores_map.values(), key=lambda p: p["nome"])

    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=4)

    logger.info(f"✅ {len(resultados)} docentes unificados e salvos em: {out_file.name}")
    return resultados


def run_classes_cleaner(
    input_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
) -> list[dict[str, Any]]:
    """Higieniza os dados de turmas extraídas do SIGAA."""
    in_file = input_path or SIGAA_CLASSES_FILE
    out_file = output_path or SIGAA_CLASSES_PROCESSED_FILE

    if not in_file.exists():
        logger.warning(f"Arquivo de turmas não encontrado: {in_file}")
        return []

    raw_classes = _load_json_resilient(in_file)
    logger.info(f"Higienizando {len(raw_classes)} turmas...")

    cleaned_classes = [clean_sigaa_class_record(c) for c in raw_classes if c.get("course_code")]

    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(cleaned_classes, f, ensure_ascii=False, indent=4)

    logger.info(f"✅ {len(cleaned_classes)} turmas higienizadas e salvas em: {out_file.name}")
    return cleaned_classes


def limpar_dados():
    """Função legada mantida para retrocompatibilidade."""
    return run_sigaa_cleaner()


if __name__ == "__main__":
    run_sigaa_cleaner()
    run_classes_cleaner()
