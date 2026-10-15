import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import time
import unicodedata
from typing import Any, Dict, List, Optional, Tuple
import uuid

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import Json, execute_batch
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

try:
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
except ImportError:
    BASE_DIR = Path(__file__).resolve().parents[2]
    import sys
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))
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

# 1. Configuração e carregamento das credenciais do ambiente
load_dotenv(BASE_DIR / ".env")

dbhost = os.getenv("DB_HOST")
dbport = os.getenv("DB_PORT")
db = os.getenv("DB_NAME")
dbuser = os.getenv("DB_USER")
dbpass = os.getenv("DB_PASSWORD")

################################################################################
# MAPEAMENTO Factual PARA DEPARTAMENTOS FORA DO CAMPUS DARCY RIBEIRO
################################################################################

DEPARTAMENTOS_FORA_DARCY = {
    # --- Campus UnB Gama (FGA / FCTE) ---
    "CAMPUS UNB GAMA: FACULDADE DE CIÊNCIAS E TECNOLOGIAS EM ENGENHARIA": "FCTE",
    "CAMPUS UNB GAMA: FACULDADE DE CIÊNCIAS E TECNOLOGIAS EM ENGENHARIA - BRASÍLIA": "FCTE",
    "FACULDADE DE CIÊNCIAS E TECNOLOGIAS EM ENGENHARIA": "FCTE",

    # --- Campus UnB Ceilândia (FCE / FCTS) ---
    "CAMPUS UNB CEILÂNDIA: FACULDADE DE CIÊNCIAS E TECNOLOGIAS EM SAÚDE": "FCTS",
    "CAMPUS UNB CEILÂNDIA: FACULDADE DE CIÊNCIAS E TECNOLOGIAS EM SAÚDE - BRASÍLIA": "FCTS",
    "FACULDADE DE CIÊNCIAS E TECNOLOGIAS EM SAÚDE": "FCTS",
    "DEPTO ENFERMAGEM": "FCTS",
    "DEPTO ENFERMAGEM - BRASÍLIA": "FCTS",
    "DEPARTAMENTO DE FARMACIA": "FCTS",
    "DEPTO FARMACIA": "FCTS",
    "DEPTO FISIOTERAPIA": "FCTS",
    "DEPTO FONOAUDIOLOGIA": "FCTS",
    "DEPTO TERAPIA OCUPACIONAL": "FCTS",
    "DEPTO SAUDE COLETIVA": "FCTS",
    "DEPTO SAUDE COLETIVA - BRASÍLIA": "FCTS",

    # --- Campus UnB Planaltina (FUP) ---
    "FACULDADE DE PLANALTINA": "FUP",
    "FACULDADE DE PLANALTINA - BRASÍLIA": "FUP",
}


def slugify(value: str) -> str:
    """Gera um slug URL-friendly limpo e único a partir de um texto."""
    if not value:
        return str(uuid.uuid4())[:8]
    normalized = unicodedata.normalize("NFKD", str(value)).encode("ASCII", "ignore").decode("utf-8").lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return cleaned or str(uuid.uuid4())[:8]


def identificar_sigla_campus(nome_departamento: str) -> str:
    """
    Retorna a sigla do campus ('Darcy', 'FCTE', 'FCTS' ou 'FUP').
    """
    if not nome_departamento:
        return "Darcy"

    nome_limpo = nome_departamento.strip().upper()

    if nome_limpo in DEPARTAMENTOS_FORA_DARCY:
        return DEPARTAMENTOS_FORA_DARCY[nome_limpo]

    if "GAMA" in nome_limpo:
        return "FCTE"
    elif "CEILÂNDIA" in nome_limpo or "CEILANDIA" in nome_limpo:
        return "FCTS"
    elif "PLANALTINA" in nome_limpo:
        return "FUP"

    return "Darcy"


################################################################################
# LOADERS SUPABASE (POSTGRESQL DIRETO VIA PSYCOPG2)
################################################################################

def get_db_connection():
    """
    Retorna uma conexão ativa com o PostgreSQL.
    Prioriza DATABASE_URL (usada em produção/Supabase).
    Se não informada ou se falhar, utiliza os parâmetros DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD.
    """
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        try:
            conn = psycopg2.connect(db_url)
            params = conn.get_dsn_parameters()
            print(f"🌐 Conectado ao banco: {params.get('host')} (DB: {params.get('dbname')})")
            return conn
        except Exception as err:
            logger.warning(f"Aviso: Falha ao conectar via DATABASE_URL ({err}). Tentando parâmetros individuais...")

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
    )
    params = conn.get_dsn_parameters()
    print(f"🌐 Conectado ao banco: {params.get('host')} (DB: {params.get('dbname')})")
    return conn


def loader_campi_supabase():
    """
    Carrega a lista estática dos campi da UnB para a tabela campi.
    """
    inicio_tempo = time.time()
    hora_inicio = datetime.now().strftime("%H:%M:%S")

    conn = get_db_connection()
    cursor = conn.cursor()

    sql_check = "SELECT id FROM campi WHERE sigla = %s LIMIT 1;"
    sql_update = "UPDATE campi SET nome = %s WHERE sigla = %s;"
    sql_insert = "INSERT INTO campi (id, sigla, nome) VALUES (%s, %s, %s);"

    campi_sigla = ["Darcy", "FCTE", "FCTS", "FUP"]
    campi_nome = [
        "Campus Darcy Ribeiro",
        "Faculdade de Ciências e Tecnologia em Engenharia",
        "Faculdade de Ciências e Tecnologia em Saúde",
        "Faculdade UnB Planaltina",
    ]

    total = len(campi_sigla)
    erros = 0

    print("\n==========================================")
    print(f"🚀 [INÍCIO LOADER CAMPI] às {hora_inicio}")
    print(f"📦 Tamanho Inicial Processamento: {total} registros")
    print("==========================================")

    for idx, (sigla, nome) in enumerate(zip(campi_sigla, campi_nome), 1):
        try:
            cursor.execute(sql_check, (sigla,))
            existente = cursor.fetchone()

            if existente:
                cursor.execute(sql_update, (nome, sigla))
                print(f"🔄 [{idx}/{total}] Campus Atualizado: {sigla} - {nome}")
            else:
                cursor.execute(sql_insert, (str(uuid.uuid4()), sigla, nome))
                print(f"✅ [{idx}/{total}] Campus Inserido: {sigla} - {nome}")

            conn.commit()
        except Exception as err:
            erros += 1
            print(f"❌ [{idx}/{total}] Erro ao registrar campus {sigla}: {err}")
            conn.rollback()

    cursor.close()
    conn.close()

    fim_tempo = time.time()
    duracao = fim_tempo - inicio_tempo

    print("\n==========================================")
    print("🎉 [LOADER CAMPI CONCLUÍDO]")
    print(f"⏱️ Duração: {duracao:.2f}s | Erros: {erros}")
    print("==========================================")


def loader_departamentos_supabase(data_departamentos):
    """
    Carrega departamentos calculando a sigla mais frequente das matérias.
    """
    inicio_tempo = time.time()
    hora_inicio = datetime.now().strftime("%H:%M:%S")

    conn = get_db_connection()
    cursor = conn.cursor()

    sql_check = "SELECT id FROM departamentos WHERE nome = %s LIMIT 1;"
    sql_update = """
        UPDATE departamentos 
        SET codigo = %s,
            campus_id = (SELECT id FROM campi WHERE sigla = %s LIMIT 1)
        WHERE nome = %s;
    """
    sql_insert = """
        INSERT INTO departamentos (id, codigo, nome, campus_id)
        VALUES (
            %s, 
            %s, 
            %s, 
            (SELECT id FROM campi WHERE sigla = %s LIMIT 1)
        );
    """

    total = len(data_departamentos)
    erros = 0

    print("\n==========================================")
    print(f"🚀 [INÍCIO LOADER DEPARTAMENTOS] às {hora_inicio}")
    print(f"📦 Tamanho Inicial Processamento: {total} registros")
    print("==========================================")

    for idx, departamento in enumerate(data_departamentos, 1):
        nome_depto = departamento.get("nome", "").strip()
        sigla_campus = identificar_sigla_campus(nome_depto)

        materias = departamento.get("materias", [])
        siglas_extraidas = []

        for m in materias:
            codigo_mat = m.get("codigo", "")
            match = re.search(r"[a-zA-Z]+", codigo_mat)
            if match:
                siglas_extraidas.append(match.group(0).upper())

        if siglas_extraidas:
            contagem = Counter(siglas_extraidas)
            sigla_materia = contagem.most_common(1)[0][0]
        elif sigla_campus == "FCTE":
            sigla_materia = "FGA"
        else:
            sigla_materia = nome_depto[:10].upper()

        try:
            cursor.execute(sql_check, (nome_depto,))
            existente = cursor.fetchone()

            if existente:
                cursor.execute(sql_update, (sigla_materia, sigla_campus, nome_depto))
                print(f"🔄 [{idx}/{total}] Atualizado: {nome_depto} | Código: {sigla_materia} | Campus: {sigla_campus}")
            else:
                payload = (str(uuid.uuid4()), sigla_materia, nome_depto, sigla_campus)
                cursor.execute(sql_insert, payload)
                print(f"✅ [{idx}/{total}] Inserido: {nome_depto} | Código: {sigla_materia} | Campus: {sigla_campus}")

            conn.commit()
        except Exception as err:
            erros += 1
            print(f"❌ [{idx}/{total}] Erro no departamento {nome_depto}: {err}")
            conn.rollback()

    cursor.close()
    conn.close()

    fim_tempo = time.time()
    duracao = fim_tempo - inicio_tempo

    print("\n==========================================")
    print("🎉 [LOADER DEPARTAMENTOS CONCLUÍDO]")
    print(f"⏱️ Duração: {duracao:.2f}s | Erros: {erros}")
    print("==========================================")


def loader_materias_supabase(data_materias):
    """
    Carrega disciplinas verificando conflitos pelo codigo_materia.
    Compatível com o schema real do Supabase:
    (id, departamento_id, codigo_materia, nome, slug, ementa, creditos, carga_horaria).
    """
    inicio_tempo = time.time()
    hora_inicio = datetime.now().strftime("%H:%M:%S")

    conn = get_db_connection()
    cursor = conn.cursor()

    sql_check = "SELECT id FROM materias WHERE codigo_materia = %s LIMIT 1;"
    sql_update = """
        UPDATE materias
        SET nome = %s,
            slug = %s,
            ementa = %s,
            creditos = %s,
            carga_horaria = %s,
            departamento_id = COALESCE((SELECT id FROM departamentos WHERE nome = %s LIMIT 1), departamento_id)
        WHERE codigo_materia = %s;
    """
    sql_insert = """
        INSERT INTO materias (
            id, codigo_materia, nome, slug, ementa, creditos, carga_horaria, departamento_id
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s,
            COALESCE((SELECT id FROM departamentos WHERE nome = %s LIMIT 1), (SELECT id FROM departamentos LIMIT 1))
        );
    """

    total = len(data_materias)
    erros = 0

    print("\n==========================================")
    print(f"🚀 [INÍCIO LOADER MATÉRIAS] às {hora_inicio}")
    print(f"📦 Tamanho Inicial Processamento: {total} registros")
    print("==========================================")

    for idx, m in enumerate(data_materias, 1):
        codigo_mat = m.get("codigo", "").strip()
        nome_mat = m.get("nome", "").strip()
        depto_nome = m.get("departamento", "").strip()
        slug_mat = m.get("slug") or slugify(f"{codigo_mat}-{nome_mat}")

        try:
            cursor.execute(sql_check, (codigo_mat,))
            existente = cursor.fetchone()

            if existente:
                payload_update = (
                    nome_mat,
                    slug_mat,
                    m.get("ementa", ""),
                    int(m.get("creditos") or 0),
                    int(m.get("carga_horaria") or 0),
                    depto_nome,
                    codigo_mat,
                )
                cursor.execute(sql_update, payload_update)
            else:
                payload_insert = (
                    str(uuid.uuid4()),
                    codigo_mat,
                    nome_mat,
                    slug_mat,
                    m.get("ementa", ""),
                    int(m.get("creditos") or 0),
                    int(m.get("carga_horaria") or 0),
                    depto_nome,
                )
                cursor.execute(sql_insert, payload_insert)

            conn.commit()
            if idx % 500 == 0 or idx == total:
                print(f"⏳ Processadas {idx}/{total} matérias...")
        except Exception as err:
            erros += 1
            print(f"❌ [{idx}/{total}] Erro na matéria {codigo_mat}: {err}")
            conn.rollback()

    cursor.close()
    conn.close()

    fim_tempo = time.time()
    duracao = fim_tempo - inicio_tempo

    print("\n==========================================")
    print("🎉 [LOADER MATÉRIAS CONCLUÍDO]")
    print(f"⏱️ Duração: {duracao:.2f}s | Erros: {erros}")
    print("==========================================")


def loader_professores_supabase(data_professores):
    """
    Carrega professores efetuando o upsert via ON CONFLICT (siape).
    Compatível com o schema real do Supabase:
    (id, departamento_id, siape, nome_completo, slug, email_institucional, url_foto, titulo_academico, url_lattes, localizacao_gabinete).
    """
    inicio_tempo = time.time()
    hora_inicio = datetime.now().strftime("%H:%M:%S")

    conn = get_db_connection()
    cursor = conn.cursor()

    comando_sql = """ 
        INSERT INTO professores (
            id, siape, nome_completo, slug, email_institucional, url_foto, url_lattes, localizacao_gabinete, departamento_id
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, 
            (SELECT id FROM departamentos WHERE nome = %s LIMIT 1)
        )
        ON CONFLICT (siape) DO UPDATE SET
            nome_completo = EXCLUDED.nome_completo,
            slug = EXCLUDED.slug,
            email_institucional = EXCLUDED.email_institucional,
            url_foto = EXCLUDED.url_foto,
            url_lattes = EXCLUDED.url_lattes,
            localizacao_gabinete = EXCLUDED.localizacao_gabinete,
            departamento_id = COALESCE(EXCLUDED.departamento_id, professores.departamento_id);
    """

    total = len(data_professores)
    erros = 0

    print("\n==========================================")
    print(f"🚀 [INÍCIO LOADER PROFESSORES] às {hora_inicio}")
    print(f"📦 Tamanho Inicial Processamento: {total} registros")
    print("==========================================")

    for idx, i in enumerate(data_professores, 1):
        nome_prof = i.get("nome", "Desconhecido").strip()
        siape_prof = i.get("siape")
        slug_prof = i.get("slug") or slugify(f"{nome_prof}-{siape_prof or ''}")

        payload = (
            str(uuid.uuid4()),
            siape_prof,
            nome_prof.upper(),
            slug_prof,
            i.get("email"),
            i.get("imagem"),
            i.get("curriculo_lattes"),
            i.get("sala"),
            i.get("departamento"),
        )

        try:
            cursor.execute(comando_sql, payload)
            conn.commit()
            if idx % 500 == 0 or idx == total:
                print(f"⏳ Processados {idx}/{total} professores...")
        except Exception as err:
            erros += 1
            print(f"❌ [{idx}/{total}] Erro ao registrar professor {nome_prof}: {err}")
            conn.rollback()

    cursor.close()
    conn.close()

    fim_tempo = time.time()
    duracao = fim_tempo - inicio_tempo

    print("\n==========================================")
    print("🎉 [LOADER PROFESSORES CONCLUÍDO]")
    print(f"⏱️ Duração: {duracao:.2f}s | Erros: {erros}")
    print("==========================================")


def loader_turmas_supabase(
    data_turmas: Any,
    semestre: str = "2026.2",
    batch_size: int = 200,
) -> int:
    """
    Carrega turmas para o Supabase (PostgreSQL), vinculando com materias e professores.
    Se a matéria não existir na tabela materias, insere um registro básico para manter integridade referencial.
    Atualiza registros existentes usando ON CONFLICT (materia_id, semestre, codigo_turma).
    """
    inicio_tempo = time.time()
    hora_inicio = datetime.now().strftime("%H:%M:%S")

    if isinstance(data_turmas, (str, Path)):
        with open(data_turmas, "r", encoding="utf-8") as f:
            data_turmas = json.load(f)

    if not data_turmas:
        print("⚠️ Nenhuma turma para processar.")
        return 0

    conn = get_db_connection()
    cursor = conn.cursor()

    total = len(data_turmas)
    print("\n==========================================")
    print(f"🚀 [INÍCIO LOADER TURMAS] às {hora_inicio}")
    print(f"📦 Tamanho Inicial Processamento: {total} turmas (Semestre: {semestre})")
    print("==========================================")

    # 1. Carrega caches de apoio para resolução rápida em memória
    cursor.execute("SELECT UPPER(TRIM(codigo_materia)), id FROM materias;")
    materia_map = {row[0]: row[1] for row in cursor.fetchall()}

    cursor.execute("SELECT UPPER(TRIM(nome_completo)), id FROM professores;")
    prof_map = {row[0]: row[1] for row in cursor.fetchall()}

    cursor.execute("SELECT UPPER(TRIM(nome)), id FROM departamentos;")
    depto_map = {row[0]: row[1] for row in cursor.fetchall()}

    default_depto_id = next(iter(depto_map.values()), None)
    if not default_depto_id:
        cursor.execute("SELECT id FROM departamentos LIMIT 1;")
        row = cursor.fetchone()
        default_depto_id = row[0] if row else str(uuid.uuid4())

    # 2. Pré-insere matérias faltantes para garantir integridade referencial (FK)
    materias_a_inserir = {}
    for t in data_turmas:
        c_code = (t.get("course_code") or "").strip().upper()
        if c_code and c_code not in materia_map and c_code not in materias_a_inserir:
            c_name = (t.get("course_name") or c_code).strip()
            depto_nome = (t.get("departamento") or "").strip().upper()
            depto_id = depto_map.get(depto_nome) or default_depto_id
            slug_base = slugify(f"{c_code}-{c_name}")[:180]
            materias_a_inserir[c_code] = (
                str(uuid.uuid4()),
                depto_id,
                c_code,
                c_name[:200],
                slug_base,
                "",
                4,
                60,
            )

    if materias_a_inserir:
        print(f"ℹ️ Encontradas {len(materias_a_inserir)} matérias ainda não cadastradas. Registrando...")
        sql_insert_materia = """
            INSERT INTO materias (id, departamento_id, codigo_materia, nome, slug, ementa, creditos, carga_horaria)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (slug) DO UPDATE SET nome = EXCLUDED.nome
            RETURNING codigo_materia, id;
        """
        for item in materias_a_inserir.values():
            try:
                cursor.execute(sql_insert_materia, item)
                ret = cursor.fetchone()
                if ret:
                    materia_map[ret[0].upper()] = ret[1]
            except Exception:
                pass
        conn.commit()

    # 3. Prepara os payloads das turmas
    sql_upsert_turma = """
        INSERT INTO turmas (
            id, materia_id, professor_id, semestre, codigo_turma,
            horario_bruto, local_sala, vagas_ofertadas, vagas_ocupadas
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (materia_id, semestre, codigo_turma) DO UPDATE SET
            professor_id = EXCLUDED.professor_id,
            horario_bruto = EXCLUDED.horario_bruto,
            local_sala = EXCLUDED.local_sala,
            vagas_ofertadas = EXCLUDED.vagas_ofertadas,
            vagas_ocupadas = EXCLUDED.vagas_ocupadas;
    """

    payloads = []
    skipped = 0
    for t in data_turmas:
        c_code = (t.get("course_code") or "").strip().upper()
        materia_id = materia_map.get(c_code)
        if not materia_id:
            skipped += 1
            continue

        docente = (t.get("docente") or "").strip().upper()
        professor_id = prof_map.get(docente) if docente else None

        cod_turma = (t.get("class_code") or "01").strip()[:10]
        horario = (t.get("schedules_raw") or "A DEFINIR").strip()[:100]
        local = (t.get("location") or "").strip()[:150] or None
        vagas = int(t.get("vacancies") or 0)

        semestre_val = str(t.get("semestre") or t.get("periodo") or semestre).strip()
        payloads.append((
            str(uuid.uuid4()),
            materia_id,
            professor_id,
            semestre_val,
            cod_turma,
            horario,
            local,
            vagas,
            0,
        ))

    # 4. Inserção em lotes (batch) com execute_batch
    erros = 0
    sucesso = 0
    try:
        execute_batch(cursor, sql_upsert_turma, payloads, page_size=batch_size)
        conn.commit()
        sucesso = len(payloads)
        print(f"✅ {sucesso} turmas inseridas/atualizadas com sucesso!")
    except Exception as batch_err:
        conn.rollback()
        print(f"⚠️ Erro no lote ({batch_err}). Tentando individualmente...")
        for p in payloads:
            try:
                cursor.execute(sql_upsert_turma, p)
                conn.commit()
                sucesso += 1
            except Exception as single_err:
                conn.rollback()
                erros += 1

    cursor.close()
    conn.close()

    fim_tempo = time.time()
    duracao = fim_tempo - inicio_tempo

    print("\n==========================================")
    print("🎉 [LOADER TURMAS CONCLUÍDO]")
    print(f"⏱️ Duração: {duracao:.2f}s | Sucesso: {sucesso} | Pulados: {skipped} | Erros: {erros}")
    print("==========================================")
    return sucesso


################################################################################
# CAMADA DE SCHEMA E COMPATIBILIDADE SQLALCHEMY (UTILIZADA EM TESTES E SQLITE)
################################################################################

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
        Column("nivel_de_ensino", String(50), nullable=True),
        Column("pre_requisito", Text, nullable=True),
        Column("co_requisito", Text, nullable=True),
        Column("equivalencia", Text, nullable=True),
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

    return {
        "campi": campi,
        "departamentos": departamentos,
        "professores": professores,
        "materias": materias,
        "turmas": turmas,
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
    reviews: Optional[list[dict[str, Any]]] = None,
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

    for r in (reviews or []):
        d = r.get("department")
        if d:
            raw_dept_strings.add(d)

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

        if code_cand and code_cand not in used_codes:
            final_code = code_cand
        else:
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

        dept_raw = p.get("departamento") or ""
        code_cand, clean_name = clean_department_name(dept_raw)
        dept_id = (
            dept_map.get(code_cand.upper())
            or dept_map.get((clean_name or dept_raw).lower())
            or default_dept
        )

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
    reviews: Optional[list[dict[str, Any]]] = None,
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

    for r in (reviews or []):
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
    semestre: str = "2026.2",
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

        semestre_val = str(c.get("semestre") or c.get("periodo") or semestre).strip()
        codigo_turma = (c.get("class_code") or "01").strip()[:10]
        key = (materia_id, semestre_val, codigo_turma)
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
                semestre=semestre_val,
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


################################################################################
# ORQUESTRADOR GLOBAL DE CARGA (SUPORTE A main.py E CLI)
################################################################################

def run_loader(limit: Optional[int] = None, semestre: str = "2026.2") -> dict[str, int]:
    """
    Orquestra a carga completa dos dados no banco de dados central (Supabase).
    Executa: Campi -> Departamentos -> Matérias -> Professores -> Turmas.
    """
    stats = {}

    print("=========================================")
    print(" 🚚 INICIANDO INGESTÃO NO BANCO CENTRAL  ")
    print("=========================================")

    # 1. Campi
    try:
        loader_campi_supabase()
        stats["campi"] = 4
    except Exception as e:
        logger.error(f"Erro ao carregar Campi: {e}")

    # 2. Departamentos
    caminho_deptos = BASE_DIR / "data" / "processed" / "departamentos_clean.json"
    if caminho_deptos.exists():
        with open(caminho_deptos, "r", encoding="utf-8") as f:
            deptos_data = json.load(f)
        if limit:
            deptos_data = deptos_data[:limit]
        loader_departamentos_supabase(deptos_data)
        stats["departamentos"] = len(deptos_data)

    # 3. Matérias
    caminho_materias = BASE_DIR / "data" / "processed" / "materias_clean.json"
    if not caminho_materias.exists():
        caminho_materias = BASE_DIR / "data" / "raw" / "sigaa" / "materias.json"
    if caminho_materias.exists():
        with open(caminho_materias, "r", encoding="utf-8") as f:
            mat_data = json.load(f)
        if limit:
            mat_data = mat_data[:limit]
        loader_materias_supabase(mat_data)
        stats["materias"] = len(mat_data)

    # 4. Professores
    caminho_profs = BASE_DIR / "data" / "processed" / "sigaa_professores.json"
    if not caminho_profs.exists():
        caminho_profs = BASE_DIR / "data" / "backup" / "sigaa_professores.json"
    if caminho_profs.exists():
        with open(caminho_profs, "r", encoding="utf-8") as f:
            profs_data = json.load(f)
        if limit:
            profs_data = profs_data[:limit]
        loader_professores_supabase(profs_data)
        stats["professores"] = len(profs_data)

    # 5. Turmas
    caminho_turmas = SIGAA_CLASSES_PROCESSED_FILE
    if not caminho_turmas.exists():
        caminho_turmas = SIGAA_CLASSES_FILE
    if not caminho_turmas.exists():
        caminho_turmas = BASE_DIR / "data" / "backup" / "sigaa_turmas.json"
    if not caminho_turmas.exists():
        caminho_turmas = BASE_DIR / "data" / "backup" / "sigaa_classes.json"

    if caminho_turmas.exists():
        with open(caminho_turmas, "r", encoding="utf-8") as f:
            turmas_data = json.load(f)
        if limit:
            turmas_data = turmas_data[:limit]
        turmas_inseridas = loader_turmas_supabase(turmas_data, semestre=semestre)
        stats["turmas"] = turmas_inseridas

    print("=========================================")
    print(" ✅ CARGA CONCLUÍDA NO SUPABASE          ")
    print(f" Resumo: {stats}")
    print("=========================================")
    return stats


def main():
    parser = argparse.ArgumentParser(description="Loader de dados para o Supabase (PostgreSQL)")
    parser.add_argument("--all", action="store_true", help="Executa carga completa de todas as entidades")
    parser.add_argument("--turmas", action="store_true", help="Executa apenas a carga das turmas")
    parser.add_argument("--campi", action="store_true", help="Executa apenas a carga dos campi")
    parser.add_argument("--deptos", action="store_true", help="Executa apenas a carga dos departamentos")
    parser.add_argument("--materias", action="store_true", help="Executa apenas a carga das matérias")
    parser.add_argument("--professores", action="store_true", help="Executa apenas a carga dos professores")
    parser.add_argument("--file", type=str, default=None, help="Caminho específico do arquivo de turmas")
    parser.add_argument("--semestre", type=str, default="2026.2", help="Semestre das turmas (padrão: 2026.2)")
    parser.add_argument("--limit", type=int, default=None, help="Limite de registros para teste rápido")

    args = parser.parse_args()

    # Se a flag específica de turmas ou arquivo foi informada
    if args.turmas or args.file:
        caminho = Path(args.file) if args.file else None
        if not caminho or not caminho.exists():
            for cand in [
                SIGAA_CLASSES_PROCESSED_FILE,
                SIGAA_CLASSES_FILE,
                BASE_DIR / "data" / "backup" / "sigaa_turmas.json",
                BASE_DIR / "data" / "backup" / "sigaa_classes.json",
            ]:
                if cand.exists():
                    caminho = cand
                    break

        if not caminho or not caminho.exists():
            print("❌ Nenhum arquivo de turmas encontrado!")
            return

        print(f"📁 Lendo turmas de: {caminho}")
        with open(caminho, "r", encoding="utf-8") as f:
            data = json.load(f)
        if args.limit:
            data = data[:args.limit]
        loader_turmas_supabase(data, semestre=args.semestre)
        return

    # Execução de partes específicas
    if args.campi:
        loader_campi_supabase()
        return

    if args.deptos:
        caminho_deptos = BASE_DIR / "data" / "processed" / "departamentos_clean.json"
        if caminho_deptos.exists():
            with open(caminho_deptos, "r", encoding="utf-8") as f:
                loader_departamentos_supabase(json.load(f))
        return

    if args.materias:
        caminho_materias = BASE_DIR / "data" / "processed" / "materias_clean.json"
        if not caminho_materias.exists():
            caminho_materias = BASE_DIR / "data" / "raw" / "sigaa" / "materias.json"
        if caminho_materias.exists():
            with open(caminho_materias, "r", encoding="utf-8") as f:
                loader_materias_supabase(json.load(f))
        return

    if args.professores:
        caminho_profs = BASE_DIR / "data" / "processed" / "sigaa_professores.json"
        if not caminho_profs.exists():
            caminho_profs = BASE_DIR / "data" / "backup" / "sigaa_professores.json"
        if caminho_profs.exists():
            with open(caminho_profs, "r", encoding="utf-8") as f:
                loader_professores_supabase(json.load(f))
        return

    # Padrão ou --all: executa pipeline completo
    run_loader(limit=args.limit, semestre=args.semestre)


if __name__ == "__main__":
    main()