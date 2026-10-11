from collections import Counter
from datetime import datetime
import json
import os
from pathlib import Path
import re
import time
import uuid

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import Json

# 1. Configuração e carregamento das credenciais do ambiente
load_dotenv()

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
# LOADERS DO BANCO DE DADOS
################################################################################

def loader_campi_supabase():
    """
    Carrega a lista estática dos campi da UnB para a tabela campi.
    """
    inicio_tempo = time.time()
    hora_inicio = datetime.now().strftime("%H:%M:%S")

    conn = psycopg2.connect(
        host=dbhost, port=dbport, password=dbpass, user=dbuser, dbname=db
    )
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
    Carrega departamentos verificando e calculando a sigla/código mais frequente (moda)
    das matérias vinculadas ao departamento.
    """
    inicio_tempo = time.time()
    hora_inicio = datetime.now().strftime("%H:%M:%S")

    conn = psycopg2.connect(
        host=dbhost, port=dbport, password=dbpass, user=dbuser, dbname=db
    )
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

        # 1. Identifica o campus
        sigla_campus = identificar_sigla_campus(nome_depto)

        # 2. Coleta das siglas dos códigos das matérias do departamento
        materias = departamento.get("materias", [])
        siglas_extraidas = []

        for m in materias:
            codigo_mat = m.get("codigo", "")
            match = re.search(r"[a-zA-Z]+", codigo_mat)
            if match:
                siglas_extraidas.append(match.group(0).upper())

        # 3. Define a sigla do departamento pela moda
        if siglas_extraidas:
            contagem = Counter(siglas_extraidas)
            sigla_materia = contagem.most_common(1)[0][0]
        elif sigla_campus == "FCTE":
            sigla_materia = "FGA"
        else:
            sigla_materia = nome_depto[:10].upper()

        # 4. Gravação no Banco de Dados
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
    Carrega disciplinas verificando conflitos pelo par (codigo_materia, nivel_de_ensino).
    """
    inicio_tempo = time.time()
    hora_inicio = datetime.now().strftime("%H:%M:%S")

    conn = psycopg2.connect(
        host=dbhost, port=dbport, password=dbpass, user=dbuser, dbname=db
    )
    cursor = conn.cursor()

    sql_check = """
        SELECT id FROM materias 
        WHERE codigo_materia = %s AND nivel_de_ensino = %s 
        LIMIT 1;
    """

    sql_update = """
        UPDATE materias
        SET nome = %s,
            slug = %s,
            ementa = %s,
            creditos = %s,
            carga_horaria = %s,
            departamento_id = (SELECT id FROM departamentos WHERE nome = %s LIMIT 1),
            co_requisito = %s,
            equivalencia = %s,
            pre_requisito = %s
        WHERE codigo_materia = %s AND nivel_de_ensino = %s;
    """

    sql_insert = """
        INSERT INTO materias (
            id, codigo_materia, nome, slug, ementa, creditos, carga_horaria, 
            departamento_id, co_requisito, equivalencia, pre_requisito, nivel_de_ensino
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s,
            (SELECT id FROM departamentos WHERE nome = %s LIMIT 1),
            %s, %s, %s, %s
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
        nivel_mat = m.get("nivel", "").strip()

        # Converte dicionários/listas em Json nativo do psycopg2
        co_req = Json(m.get("co_requisito")) if m.get("co_requisito") is not None else None
        equiv = Json(m.get("equivalencia")) if m.get("equivalencia") is not None else None
        pre_req = Json(m.get("pre_requisito")) if m.get("pre_requisito") is not None else None

        try:
            cursor.execute(sql_check, (codigo_mat, nivel_mat))
            existente = cursor.fetchone()

            if existente:
                payload_update = (
                    nome_mat,
                    m.get("slug"),
                    m.get("ementa", ""),
                    m.get("creditos", 0),
                    m.get("carga_horaria", 0),
                    depto_nome,
                    co_req,
                    equiv,
                    pre_req,
                    codigo_mat,
                    nivel_mat,
                )
                cursor.execute(sql_update, payload_update)
                print(f"🔄 [{idx}/{total}] Atualizada: {codigo_mat} - {nome_mat} ({nivel_mat})")
            else:
                payload_insert = (
                    str(uuid.uuid4()),
                    codigo_mat,
                    nome_mat,
                    m.get("slug"),
                    m.get("ementa", ""),
                    m.get("creditos", 0),
                    m.get("carga_horaria", 0),
                    depto_nome,
                    co_req,
                    equiv,
                    pre_req,
                    nivel_mat,
                )
                cursor.execute(sql_insert, payload_insert)
                print(f"✅ [{idx}/{total}] Inserida: {codigo_mat} - {nome_mat} ({nivel_mat})")

            conn.commit()

        except Exception as err:
            erros += 1
            print(f"❌ [{idx}/{total}] Erro na matéria {codigo_mat} ({nivel_mat}): {err}")
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
    """
    inicio_tempo = time.time()
    hora_inicio = datetime.now().strftime("%H:%M:%S")

    conn = psycopg2.connect(
        host=dbhost, port=dbport, password=dbpass, user=dbuser, dbname=db
    )
    cursor = conn.cursor()

    comando_sql = """ 
        INSERT INTO professores (
            id, siape, nome_completo, email_institucional, url_foto, url_lattes, localizacao_gabinete, descricao, departamento_id
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, 
            (SELECT id FROM departamentos WHERE nome = %s LIMIT 1)
        )
        ON CONFLICT (siape) DO UPDATE SET
            nome_completo = EXCLUDED.nome_completo,
            email_institucional = EXCLUDED.email_institucional,
            url_foto = EXCLUDED.url_foto,
            url_lattes = EXCLUDED.url_lattes,
            localizacao_gabinete = EXCLUDED.localizacao_gabinete,
            descricao = EXCLUDED.descricao,
            departamento_id = EXCLUDED.departamento_id;
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

        payload = (
            str(uuid.uuid4()),
            siape_prof,
            nome_prof.upper(),
            i.get("email"),
            i.get("imagem"),
            i.get("curriculo_lattes"),
            i.get("sala"),
            i.get("descricao"),
            i.get("departamento"),
        )

        try:
            cursor.execute(comando_sql, payload)
            conn.commit()
            print(f"✅ [{idx}/{total}] Professor Processado: {nome_prof} (SIAPE: {siape_prof})")

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


################################################################################
# EXECUÇÃO DO PIPELINE DE CARGA
################################################################################

if __name__ == "__main__":
    # 1. Executa a carga de Campi
    loader_campi_supabase()

    # 2. Executa a carga de Departamentos
    caminho_deptos = os.path.join("data", "processed", "departamentos_clean.json")
    if os.path.exists(caminho_deptos):
        with open(caminho_deptos, "r", encoding="utf-8") as f:
            data_departamentos = json.load(f)
        loader_departamentos_supabase(data_departamentos)

    # 3. Executa a carga de Matérias
    caminho_materias = os.path.join("data", "processed", "materias_clean.json")
    if os.path.exists(caminho_materias):
        with open(caminho_materias, "r", encoding="utf-8") as f:
            data_materias = json.load(f)
        loader_materias_supabase(data_materias)

    # 4. Executa a carga de Professores
    caminho_professores = os.path.join("data", "processed", "sigaa_professores.json")
    if os.path.exists(caminho_professores):
        with open(caminho_professores, "r", encoding="utf-8") as f:
            data_professores = json.load(f)
        loader_professores_supabase(data_professores)