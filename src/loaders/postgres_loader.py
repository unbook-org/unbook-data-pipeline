import hashlib
import json
import os
import re
import sys
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    SmallInteger,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    select,
    text,
)
from sqlalchemy.engine import Engine

from src.transformers.clean_courses import clean_course_name, split_course_code_and_name
from src.transformers.clean_professors import clean_professor_name
from src.transformers.sigaa_cleaner import clean_department_name, extract_siape, limpar_espacos
from src.utils.logger import get_logger
from src.utils.paths import (
    BASE_DIR,
    LEGACY_PROCESSED_FILE,
    SIGAA_CLASSES_FILE,
    SIGAA_CLASSES_PROCESSED_FILE,
    SIGAA_PROCESSED_FILE,
)

logger = get_logger("DB-Loader")

# Carrega variáveis de ambiente do .env
load_dotenv(BASE_DIR / ".env")


def slugify(value: str) -> str:
    """Gera um slug URL-friendly limpo e único a partir de um texto."""
    if not value:
        return str(uuid.uuid4())[:8]
    normalized = unicodedata.normalize("NFKD", str(value)).encode("ASCII", "ignore").decode("utf-8").lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return cleaned or str(uuid.uuid4())[:8]


def get_database_engine() -> tuple[Engine, str]:
    """
    Inicializa o engine do banco de dados a partir do .env.
    Tenta PostgreSQL primeiro; se falhar e USE_SQLITE_FALLBACK=True, usa SQLite.
    """
    database_url = os.getenv("DATABASE_URL")
    db_engine_type = os.getenv("DB_ENGINE", "postgresql").lower()
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "unbook")
    db_user = os.getenv("DB_USER", "unbook_user")
    db_password = os.getenv("DB_PASSWORD", "unbook_password_local")
    use_sqlite_fallback = os.getenv("USE_SQLITE_FALLBACK", "True").lower() in {"true", "1", "yes"}
    sqlite_path = Path(os.getenv("SQLITE_PATH", "data/processed/unbook_dev.db"))

    # Tenta conexão PostgreSQL
    if db_engine_type == "postgresql" or database_url:
        target_url = database_url or f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        if target_url.startswith("postgresql://"):
            target_url = target_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        try:
            pg_engine = create_engine(target_url, pool_pre_ping=True)
            with pg_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✅ Conectado ao PostgreSQL com sucesso.")
            return pg_engine, "postgresql"
        except Exception as err:
            logger.warning(f"Falha na conexão PostgreSQL ({err}).")
            # Tenta fallback para banco alternativo 'unbook' se foi configurado 'unbook_db'
            if db_name != "unbook":
                try:
                    alt_url = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/unbook"
                    alt_engine = create_engine(alt_url, pool_pre_ping=True)
                    with alt_engine.connect() as conn:
                        conn.execute(text("SELECT 1"))
                    logger.info(f"✅ Conectado ao PostgreSQL (banco alternativo 'unbook' em {db_host}:{db_port})")
                    return alt_engine, "postgresql"
                except Exception:
                    pass

    # Fallback para SQLite
    if use_sqlite_fallback:
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        sqlite_url = f"sqlite:///{BASE_DIR / sqlite_path}"
        logger.info(f"📁 Usando banco SQLite local: {sqlite_path}")
        sq_engine = create_engine(sqlite_url)
        return sq_engine, "sqlite"

    raise ConnectionError("Não foi possível conectar ao banco PostgreSQL e o fallback SQLite está desabilitado.")


def define_schema(metadata: MetaData) -> dict[str, Table]:
    """Define as tabelas de acordo com o modelo de dados do ecossistema UnBook."""
    campi = Table(
        "campi",
        metadata,
        Column("id", String(36), primary_key=True),
        Column("sigla", String(10), unique=True, nullable=False),
        Column("nome", String(100), nullable=False),
        extend_existing=True,
    )

    departamentos = Table(
        "departamentos",
        metadata,
        Column("id", String(36), primary_key=True),
        Column("campus_id", String(36), ForeignKey("campi.id"), nullable=False),
        Column("codigo", String(20), unique=True, nullable=False),
        Column("nome", String(150), nullable=False),
        extend_existing=True,
    )

    professores = Table(
        "professores",
        metadata,
        Column("id", String(36), primary_key=True),
        Column("departamento_id", String(36), ForeignKey("departamentos.id"), nullable=True),
        Column("siape", String(20), unique=True, nullable=True),
        Column("nome_completo", String(200), nullable=False),
        Column("slug", String(200), unique=True, nullable=False),
        Column("email_institucional", String(254), nullable=True),
        Column("url_foto", String(200), nullable=True),
        Column("titulo_academico", String(50), nullable=True),
        Column("url_lattes", String(200), nullable=True),
        Column("localizacao_gabinete", String(150), nullable=True),
        extend_existing=True,
    )

    materias = Table(
        "materias",
        metadata,
        Column("id", String(36), primary_key=True),
        Column("departamento_id", String(36), ForeignKey("departamentos.id"), nullable=False),
        Column("codigo_materia", String(20), unique=True, nullable=False),
        Column("nome", String(200), nullable=False),
        Column("slug", String(200), unique=True, nullable=False),
        Column("ementa", Text, nullable=True),
        Column("creditos", Integer, default=4, nullable=False),
        Column("carga_horaria", Integer, default=60, nullable=False),
        extend_existing=True,
    )

    turmas = Table(
        "turmas",
        metadata,
        Column("id", String(36), primary_key=True),
        Column("materia_id", String(36), ForeignKey("materias.id"), nullable=False),
        Column("professor_id", String(36), ForeignKey("professores.id"), nullable=True),
        Column("semestre", String(10), nullable=False),
        Column("codigo_turma", String(10), nullable=False),
        Column("horario_bruto", String(100), nullable=False),
        Column("local_sala", String(150), nullable=True),
        Column("vagas_ofertadas", Integer, default=0, nullable=False),
        Column("vagas_ocupadas", Integer, default=0, nullable=False),
        UniqueConstraint("materia_id", "semestre", "codigo_turma", name="turmas_materia_semestre_cod_uniq"),
        extend_existing=True,
    )

    avaliacoes = Table(
        "avaliacoes",
        metadata,
        Column("id", String(36), primary_key=True),
        Column("materia_id", String(36), ForeignKey("materias.id"), nullable=False),
        Column("professor_id", String(36), ForeignKey("professores.id"), nullable=False),
        Column("turma_id", String(36), ForeignKey("turmas.id"), nullable=True),
        Column("hash_anonimo", String(64), nullable=False),
        Column("nota_didatica", SmallInteger, nullable=False),
        Column("nota_dificuldade", SmallInteger, nullable=False),
        Column("mencao_obtida", String(5), nullable=True),
        Column("status_aprovacao", String(15), default="passei", nullable=False),
        Column("emoji_vibe", String(10), default="😎", nullable=False),
        Column("cobra_presenca", Boolean, default=False, nullable=False),
        Column("avaliacao_justa", Boolean, default=True, nullable=False),
        Column("possui_monitoria", Boolean, default=False, nullable=False),
        Column("comentario", Text, nullable=True),
        Column("status_moderacao", String(15), default="publicada", nullable=False),
        Column("criado_em", DateTime(timezone=True), nullable=False),
        UniqueConstraint("hash_anonimo", "materia_id", "professor_id", name="avaliacoes_hash_mat_prof_uniq"),
        extend_existing=True,
    )

    return {
        "campi": campi,
        "departamentos": departamentos,
        "professores": professores,
        "materias": materias,
        "turmas": turmas,
        "avaliacoes": avaliacoes,
    }


def ensure_schema(engine: Engine) -> dict[str, Table]:
    """Garante que as tabelas necessárias existam no banco."""
    metadata = MetaData()
    tables = define_schema(metadata)
    metadata.create_all(engine, checkfirst=True)
    return tables


def load_campi(conn, tables: dict[str, Table]) -> dict[str, str]:
    """Garante a existência dos campi da UnB e retorna mapa sigla -> id."""
    t_campi = tables["campi"]
    campi_data = [
        {"sigla": "DARCY", "nome": "Campus Universitário Darcy Ribeiro"},
        {"sigla": "FGA", "nome": "Faculdade UnB Gama"},
        {"sigla": "FCE", "nome": "Faculdade UnB Ceilândia"},
        {"sigla": "FAL", "nome": "Faculdade UnB Planaltina"},
    ]

    campi_map = {}
    for c in campi_data:
        row = conn.execute(select(t_campi.c.id).where(t_campi.c.sigla == c["sigla"])).fetchone()
        if row:
            campi_map[c["sigla"]] = str(row[0])
        else:
            cid = str(uuid.uuid4())
            conn.execute(t_campi.insert().values(id=cid, sigla=c["sigla"], nome=c["nome"]))
            campi_map[c["sigla"]] = cid

    return campi_map


def resolve_campus_for_department(dept_text: str) -> str:
    """Classifica o campus a partir do nome ou descrição do departamento."""
    text_lower = dept_text.lower()
    if "ceilândia" in text_lower or "ceilandia" in text_lower or "fce" in text_lower or "fcts" in text_lower:
        return "FCE"
    if "gama" in text_lower or "fga" in text_lower:
        return "FGA"
    if "planaltina" in text_lower or "fal" in text_lower or "fup" in text_lower:
        return "FAL"
    return "DARCY"


def load_departamentos(
    conn,
    tables: dict[str, Table],
    campi_map: dict[str, str],
    profs: list[dict[str, Any]],
    classes: list[dict[str, Any]],
    reviews: list[dict[str, Any]],
) -> dict[str, str]:
    """Extrai e insere departamentos únicos, retornando mapa identificador -> id."""
    t_dept = tables["departamentos"]
    raw_dept_strings = set()

    for p in profs:
        d = p.get("departamento")
        if d:
            raw_dept_strings.add(d)

    for c in classes:
        d = c.get("departamento")
        if d:
            raw_dept_strings.add(d)

    for r in reviews:
        d = r.get("department")
        if d:
            raw_dept_strings.add(d)

    # Coleta departamentos já existentes no banco
    dept_map: dict[str, str] = {}
    existing = conn.execute(select(t_dept.c.id, t_dept.c.codigo, t_dept.c.nome)).fetchall()
    for row in existing:
        did, dcode, dname = str(row[0]), str(row[1]), str(row[2])
        dept_map[dcode.upper()] = did
        dept_map[dname.lower()] = did

    used_codes = {str(row[1]).upper() for row in existing}

    for raw in raw_dept_strings:
        code_cand, clean_name = clean_department_name(raw)
        norm_name = clean_name or raw
        if norm_name.lower() in dept_map:
            continue

        campus_sigla = resolve_campus_for_department(raw)
        campus_id = campi_map.get(campus_sigla, campi_map["DARCY"])

        # Determina código único
        if code_cand and code_cand not in used_codes:
            final_code = code_cand
        else:
            # Gera código mnemônico a partir do nome
            letters = re.findall(r"[A-Z0-9]", norm_name)
            base_code = "".join(letters[:6]).upper() if len(letters) >= 3 else slugify(norm_name)[:6].upper()
            if not base_code:
                base_code = "DEP"
            final_code = base_code
            counter = 1
            while final_code in used_codes:
                final_code = f"{base_code[:4]}{counter}"
                counter += 1

        used_codes.add(final_code)
        dept_id = str(uuid.uuid4())
        conn.execute(
            t_dept.insert().values(
                id=dept_id,
                campus_id=campus_id,
                codigo=final_code,
                nome=norm_name[:150],
            )
        )
        dept_map[final_code] = dept_id
        dept_map[norm_name.lower()] = dept_id
        if code_cand:
            dept_map[code_cand.upper()] = dept_id

    # Garante um departamento genérico para matérias/professores sem vínculo
    if "GERAL" not in dept_map:
        geral_id = str(uuid.uuid4())
        conn.execute(
            t_dept.insert().values(
                id=geral_id,
                campus_id=campi_map["DARCY"],
                codigo="GERAL",
                nome="Departamento Geral / Interdisciplinar",
            )
        )
        dept_map["GERAL"] = geral_id
        dept_map["geral"] = geral_id

    return dept_map


def load_professores(
    conn,
    tables: dict[str, Table],
    dept_map: dict[str, str],
    profs: list[dict[str, Any]],
) -> dict[str, str]:
    """Popula a tabela de professores e retorna mapa de busca -> id."""
    t_prof = tables["professores"]
    prof_map: dict[str, str] = {}

    existing = conn.execute(select(t_prof.c.id, t_prof.c.siape, t_prof.c.nome_completo, t_prof.c.slug)).fetchall()
    used_slugs = {str(row[3]) for row in existing}
    for row in existing:
        pid, siape, nome = str(row[0]), row[1], str(row[2])
        if siape:
            prof_map[str(siape)] = pid
        prof_map[nome.lower()] = pid

    default_dept = dept_map.get("GERAL")

    for p in profs:
        nome = clean_professor_name(p.get("nome") or p.get("professor") or "")
        if not nome:
            continue

        siape = p.get("siape") or extract_siape(p.get("link_siape") or p.get("link_mais_info"))
        if siape and str(siape) in prof_map:
            continue
        if nome.lower() in prof_map and not siape:
            continue

        # Resolve departamento
        dept_raw = p.get("departamento") or ""
        code_cand, clean_name = clean_department_name(dept_raw)
        dept_id = (
            dept_map.get(code_cand.upper())
            or dept_map.get((clean_name or dept_raw).lower())
            or default_dept
        )

        # Gera slug único
        base_slug = slugify(nome)[:180]
        final_slug = base_slug
        counter = 1
        while final_slug in used_slugs:
            final_slug = f"{base_slug[:170]}-{counter}"
            counter += 1
        used_slugs.add(final_slug)

        pid = str(uuid.uuid4())
        conn.execute(
            t_prof.insert().values(
                id=pid,
                departamento_id=dept_id,
                siape=str(siape) if siape else None,
                nome_completo=nome[:200],
                slug=final_slug,
                email_institucional=(p.get("email") or None),
                url_foto=(p.get("imagem") or None),
                titulo_academico=None,
                url_lattes=(p.get("curriculo_lattes") or None),
                localizacao_gabinete=(p.get("sala") or None),
            )
        )
        if siape:
            prof_map[str(siape)] = pid
        prof_map[nome.lower()] = pid

    return prof_map


def load_materias(
    conn,
    tables: dict[str, Table],
    dept_map: dict[str, str],
    profs: list[dict[str, Any]],
    classes: list[dict[str, Any]],
    reviews: list[dict[str, Any]],
) -> dict[str, str]:
    """Extrai e insere disciplinas únicas de todas as fontes."""
    t_mat = tables["materias"]
    materia_map: dict[str, str] = {}

    existing = conn.execute(select(t_mat.c.id, t_mat.c.codigo_materia, t_mat.c.nome, t_mat.c.slug)).fetchall()
    used_slugs = {str(row[3]) for row in existing}
    for row in existing:
        mid, code, name = str(row[0]), str(row[1]).upper(), str(row[2])
        materia_map[code] = mid
        materia_map[name.lower()] = mid

    default_dept = dept_map.get("GERAL")

    # Coleta matérias das disciplinas de docentes
    candidates: dict[str, dict[str, Any]] = {}
    for p in profs:
        for d in p.get("disciplinas", []):
            code = (d.get("codigo") or "").strip().upper()
            nome = clean_course_name(d.get("nome"))
            if code and code not in candidates:
                candidates[code] = {
                    "codigo": code,
                    "nome": nome or code,
                    "ch": d.get("carga_horaria", 60),
                    "dept": p.get("departamento"),
                }

    # Coleta matérias das turmas
    for c in classes:
        code = (c.get("course_code") or "").strip().upper()
        nome = clean_course_name(c.get("course_name"))
        if code and code not in candidates:
            candidates[code] = {
                "codigo": code,
                "nome": nome or code,
                "ch": 60,
                "dept": c.get("departamento"),
            }

    # Coleta matérias das avaliações
    for r in reviews:
        code = (r.get("course_code") or "").strip().upper()
        nome = clean_course_name(r.get("course_name"))
        if code and code not in candidates:
            candidates[code] = {
                "codigo": code,
                "nome": nome or code,
                "ch": 60,
                "dept": r.get("department"),
            }
        elif not code and nome and nome.lower() not in materia_map:
            # Matéria sem código, gera um código sintético único
            synth_code = f"LEG{slugify(nome)[:4].upper()}{len(candidates)+1:03d}"
            candidates[synth_code] = {
                "codigo": synth_code,
                "nome": nome,
                "ch": 60,
                "dept": r.get("department"),
            }

    for code, m in candidates.items():
        if code in materia_map:
            continue

        nome = m["nome"] or code
        dept_raw = m.get("dept") or ""
        code_cand, clean_name = clean_department_name(dept_raw)

        # Tenta inferir departamento pelo código da matéria (ex: CIC0004 -> CIC)
        prefix_code = re.match(r"^([A-Z]{3,4})", code)
        inferred_dept_code = prefix_code.group(1) if prefix_code else None

        dept_id = (
            dept_map.get(code_cand.upper())
            or (dept_map.get(inferred_dept_code) if inferred_dept_code else None)
            or dept_map.get((clean_name or dept_raw).lower())
            or default_dept
        )

        base_slug = slugify(f"{code}-{nome}")[:180]
        final_slug = base_slug
        counter = 1
        while final_slug in used_slugs:
            final_slug = f"{base_slug[:170]}-{counter}"
            counter += 1
        used_slugs.add(final_slug)

        ch = int(m.get("ch") or 60)
        cred = max(1, ch // 15)
        mid = str(uuid.uuid4())

        conn.execute(
            t_mat.insert().values(
                id=mid,
                departamento_id=dept_id,
                codigo_materia=code,
                nome=nome[:200],
                slug=final_slug,
                ementa=None,
                creditos=cred,
                carga_horaria=ch,
            )
        )
        materia_map[code] = mid
        materia_map[nome.lower()] = mid

    return materia_map


def load_turmas(
    conn,
    tables: dict[str, Table],
    materia_map: dict[str, str],
    prof_map: dict[str, str],
    classes: list[dict[str, Any]],
) -> int:
    """Popula turmas ofertadas garantindo resolução das chaves estrangeiras."""
    t_turma = tables["turmas"]
    inserted = 0

    existing_rows = conn.execute(select(t_turma.c.materia_id, t_turma.c.semestre, t_turma.c.codigo_turma)).fetchall()
    existing_turmas = {(str(r[0]), str(r[1]), str(r[2])) for r in existing_rows}

    for c in classes:
        course_code = (c.get("course_code") or "").strip().upper()
        materia_id = materia_map.get(course_code)
        if not materia_id:
            continue

        semestre = "2026.1"  # Semestre de vigência das turmas extraídas
        codigo_turma = (c.get("class_code") or "01").strip()[:10]
        key = (materia_id, semestre, codigo_turma)
        if key in existing_turmas:
            continue

        docente = c.get("docente")
        professor_id = prof_map.get(docente.lower()) if docente else None

        sched = c.get("schedules_raw") or "A DEFINIR"
        vagas = int(c.get("vacancies") or 0)
        loc = c.get("location")

        tid = str(uuid.uuid4())
        conn.execute(
            t_turma.insert().values(
                id=tid,
                materia_id=materia_id,
                professor_id=professor_id,
                semestre=semestre,
                codigo_turma=codigo_turma,
                horario_bruto=sched[:100],
                local_sala=loc[:150] if loc else None,
                vagas_ofertadas=vagas,
                vagas_ocupadas=0,
            )
        )
        existing_turmas.add(key)
        inserted += 1

    return inserted


def load_avaliacoes(
    conn,
    tables: dict[str, Table],
    materia_map: dict[str, str],
    prof_map: dict[str, str],
    dept_map: dict[str, str],
    reviews: list[dict[str, Any]],
) -> int:
    """Carrega avaliações históricas e comunitárias associando matéria e docente."""
    t_aval = tables["avaliacoes"]
    t_prof = tables["professores"]
    inserted = 0

    existing_hashes = {str(r[0]) for r in conn.execute(select(t_aval.c.hash_anonimo)).fetchall()}
    default_dept = dept_map.get("GERAL")

    diff_map = {
        "muito fácil": 1, "muito facil": 1, "🟢": 1,
        "fácil": 2, "facil": 2, "🟡": 2,
        "médio": 3, "medio": 3, "regular": 3, "🟠": 3,
        "difícil": 4, "dificil": 4, "🔴": 4,
        "muito difícil": 5, "muito dificil": 5, "🔥": 5, "💀": 5,
    }

    existing_prof_rows = conn.execute(select(t_prof.c.id, t_prof.c.nome_completo, t_prof.c.slug)).fetchall()
    used_prof_slugs = {str(r[2]) for r in existing_prof_rows}
    for row in existing_prof_rows:
        prof_map[str(row[1]).lower()] = str(row[0])

    for r in reviews:
        # 1. Resolve Matéria
        course_code = (r.get("course_code") or "").strip().upper()
        course_name = (r.get("course_name") or "").strip().lower()
        materia_id = materia_map.get(course_code) or materia_map.get(course_name)
        if not materia_id:
            continue

        # 2. Resolve Professor
        prof_name = clean_professor_name(r.get("professor_name") or "")
        if not prof_name:
            continue

        professor_id = prof_map.get(prof_name.lower())
        if not professor_id:
            # Cria professor ausente como stub para preservar a avaliação
            professor_id = str(uuid.uuid4())
            base_slug = slugify(f"stub-{prof_name}")[:180]
            p_slug = base_slug
            counter = 1
            while p_slug in used_prof_slugs:
                p_slug = f"{base_slug[:170]}-{counter}"
                counter += 1
            used_prof_slugs.add(p_slug)

            conn.execute(
                t_prof.insert().values(
                    id=professor_id,
                    departamento_id=default_dept,
                    siape=None,
                    nome_completo=prof_name[:200],
                    slug=p_slug,
                )
            )
            prof_map[prof_name.lower()] = professor_id

        # 3. Gera hash anônimo determinístico
        comment = r.get("comment") or ""
        hash_seed = f"{comment.strip()}_{r.get('semester')}_{materia_id}_{professor_id}"
        hash_anonimo = hashlib.sha256(hash_seed.encode("utf-8")).hexdigest()
        if hash_anonimo in existing_hashes:
            continue

        # 4. Trata notas e indicadores
        rating_obj = r.get("rating") or {}
        didactics_raw = rating_obj.get("didactics")
        if didactics_raw is not None:
            # Converte de 0-10 para escala 1-5
            val = float(didactics_raw)
            nota_didatica = max(1, min(5, round(val / 2.0)))
        else:
            nota_didatica = 3

        diff_str = str(rating_obj.get("difficulty") or "").lower().strip()
        nota_dificuldade = diff_map.get(diff_str, 3)

        outcome_raw = str(r.get("outcome") or "passed").lower()
        status_aprovacao = "passei" if "pass" in outcome_raw else ("reprovei" if "fail" in outcome_raw else "tranquei")

        emoji_vibe = str(rating_obj.get("emoji_vibe") or "😎")[:10]
        cobra_presenca = bool(re.search(r"chamada|presen[çc]a|falta", comment, re.IGNORECASE))
        avaliacao_justa = rating_obj.get("recommended") is not False

        aid = str(uuid.uuid4())
        conn.execute(
            t_aval.insert().values(
                id=aid,
                materia_id=materia_id,
                professor_id=professor_id,
                turma_id=None,
                hash_anonimo=hash_anonimo,
                nota_didatica=nota_didatica,
                nota_dificuldade=nota_dificuldade,
                mencao_obtida=None,
                status_aprovacao=status_aprovacao,
                emoji_vibe=emoji_vibe,
                cobra_presenca=cobra_presenca,
                avaliacao_justa=avaliacao_justa,
                possui_monitoria=False,
                comentario=comment or None,
                status_moderacao="publicada",
                criado_em=datetime.now(timezone.utc),
            )
        )
        existing_hashes.add(hash_anonimo)
        inserted += 1

    return inserted


def run_loader(limit: Optional[int] = None) -> dict[str, int]:
    """
    Orquestra a carga completa dos dados sanitizados no banco de dados.
    Lê os artefatos JSON processados e insere relacionalmente:
    Campi -> Departamentos -> Professores -> Matérias -> Turmas -> Avaliações.
    """
    logger.info("=========================================")
    logger.info(" INICIANDO CARGA NO BANCO DE DADOS       ")
    logger.info("=========================================")

    engine, engine_type = get_database_engine()
    tables = ensure_schema(engine)

    # Carrega dados limpos
    profs_data = []
    if SIGAA_PROCESSED_FILE.exists():
        with open(SIGAA_PROCESSED_FILE, "r", encoding="utf-8") as f:
            profs_data = json.load(f)

    classes_data = []
    turmas_file = SIGAA_CLASSES_PROCESSED_FILE if SIGAA_CLASSES_PROCESSED_FILE.exists() else SIGAA_CLASSES_FILE
    if turmas_file.exists():
        with open(turmas_file, "r", encoding="utf-8") as f:
            classes_data = json.load(f)

    reviews_data = []
    if LEGACY_PROCESSED_FILE.exists():
        with open(LEGACY_PROCESSED_FILE, "r", encoding="utf-8") as f:
            reviews_data = json.load(f)

    if limit:
        profs_data = profs_data[:limit]
        classes_data = classes_data[:limit]
        reviews_data = reviews_data[:limit]

    logger.info(f"Registros disponíveis para carga:")
    logger.info(f" - Docentes SIGAA: {len(profs_data)}")
    logger.info(f" - Turmas: {len(classes_data)}")
    logger.info(f" - Avaliações Legadas: {len(reviews_data)}")

    stats = {}
    with engine.begin() as conn:
        # 1. Campi
        logger.info("1/6 Populando Campi...")
        campi_map = load_campi(conn, tables)
        stats["campi"] = len(campi_map)

        # 2. Departamentos
        logger.info("2/6 Mapeando e populando Departamentos...")
        dept_map = load_departamentos(conn, tables, campi_map, profs_data, classes_data, reviews_data)
        stats["departamentos"] = len(set(dept_map.values()))

        # 3. Professores
        logger.info("3/6 Inserindo Docentes...")
        prof_map = load_professores(conn, tables, dept_map, profs_data)
        stats["professores"] = len(set(prof_map.values()))

        # 4. Matérias
        logger.info("4/6 Inserindo Matérias...")
        materia_map = load_materias(conn, tables, dept_map, profs_data, classes_data, reviews_data)
        stats["materias"] = len(set(materia_map.values()))

        # 5. Turmas
        logger.info("5/6 Vinculando e inserindo Turmas...")
        stats["turmas_inseridas"] = load_turmas(conn, tables, materia_map, prof_map, classes_data)

        # 6. Avaliações
        logger.info("6/6 Anonimizando e inserindo Avaliações...")
        stats["avaliacoes_inseridas"] = load_avaliacoes(conn, tables, materia_map, prof_map, dept_map, reviews_data)

    logger.info("=========================================")
    logger.info(" CARGA FINALIZADA COM SUCESSO!           ")
    logger.info(f" Engine: {engine_type.upper()}")
    logger.info(f" Total Docentes no Catálogo: {stats.get('professores', 0)}")
    logger.info(f" Total Matérias no Catálogo: {stats.get('materias', 0)}")
    logger.info(f" Turmas Inseridas: {stats.get('turmas_inseridas', 0)}")
    logger.info(f" Avaliações Inseridas: {stats.get('avaliacoes_inseridas', 0)}")
    logger.info("=========================================")

    return stats


if __name__ == "__main__":
    run_loader()