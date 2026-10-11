import os
from supabase import create_client, Client
import psycopg2
from dotenv import load_dotenv
import json
import re
import uuid

# 1. Configuração das credenciais
load_dotenv()

dbhost = os.getenv("DB_HOST")
dbport= os.getenv("DB_PORT")
db= os.getenv("DB_NAME")
dbuser= os.getenv("DB_USER")
dbpass= os.getenv("DB_PASSWORD")

######################################################################################################################

caminho_arquivo = os.path.join("data","processed","sigaa_professores.json")
with open(caminho_arquivo, "r", encoding="utf-8") as file:
    data_professor = json.load(file)

def loader_professores_supabase(data_professor): 

    conn = psycopg2.connect( #conectando ao banco de dados
    host=dbhost,
    port=dbport,
    password=dbpass,
    user=dbuser,  # Usuário obrigatório
    dbname=db
    )

    if conn:
        print("connection success")
    cursor = conn.cursor()

    comando_sql = """ 
        INSERT INTO professores (
            id, siape, nome_completo, email_institucional, url_foto, url_lattes, localizacao_gabinete, descricao, departamento_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, SELECT id FROM departamentos WHERE nome = %s )
        ON CONFLICT (siape) DO UPDATE SET
            nome_completo = EXCLUDED.nome_completo,
            email_institucional = EXCLUDED.email_institucional,
            url_foto = EXCLUDED.url_foto,
            url_lattes = EXCLUDED.url_lattes,
            localizacao_gabinete = EXCLUDED.localizacao_gabinete,
            descricao = EXCLUDED.descricao;
        """ #comando para executar o update ou adição
        
    professores_erro=[] #lista para tratamento de erro de professores

    for i in dados: #iterando sobre cada item da lista "dados" (que nesse caso são os professores)
        print(f"! Posição atual: {dados.index(i)} !\n! Nome professor: {i["nome"]}\n !")
        professores = (str(uuid.uuid4()), i["siape"], i["nome"].upper(), i["email"], i["imagem"], i["curriculo_lattes"], i["sala"], i["descricao"], i["departamento"] ) #payload com os dados 
        try:
            cursor.execute(comando_sql, professores) #executa o comando

            conn.commit() #confirma a execucao
        except Exception as err:
            print(f"? Nome professor com erro: {i["nome"]} ?\n? Erro: {err} ?\n? Index com erro: {dados.index(i)} ?")
            conn.rollback()

    print(f"Número de professores com erros gerais: {len(professores_erro)}\nOs professores são: ")
    for i in professores_erro:
        print(f"{professores_erro[i]}")

def loader_campi_supabase():

    conn = psycopg2.connect( #conectando ao banco de dados
    host=dbhost,
    port=dbport,
    password=dbpass,
    user=dbuser,  # Usuário obrigatório
    dbname=db
    )

    if conn:
        print("connection success")
    cursor = conn.cursor()

    comando_sql = """ 
        INSERT INTO campi (
        id, sigla, nome
        ) VALUES (%s, %s, %s)
        """ #comando para executar o update ou adição

    campi_sigla = ["Darcy", "FCTE", "FCTS", "FUP"]
    campi_nome = ["Campus Darcy Ribeiro", "Faculdade de Ciencias e Tecnologia em Engenharia", "Faculdade de Ciencias e Tecnologia em Saude", "Faculdade UnB Planaltina"]
    for i in campi_sigla:
        print(f"Campus selecionado: {i}")
        campi = (str(uuid.uuid4()), i,  campi_nome[campi_sigla.index(i)]) #payload com os dados id, sigla, nome
        try:
            cursor.execute(comando_sql, campi) #executa o comando

            conn.commit() #confirma a execucao
        except Exception as err:
            print(f"Campus com erro: {i}")
            conn.rollback()
    print("! Campi adicionados. !")

caminho_arquivo_departamento = os.path.join("data", "processed", "departamentos_clean.json")
with open(caminho_arquivo_departamento, "r", encoding="utf-8") as f:
    data_departamentos = json.load(f)

from collections import Counter

# Mapeamento prévio dos departamentos fora do Campus Darcy Ribeiro (FGA/FCTE, FCE/FCTS, FAL)
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

    # --- Campus UnB Planaltina (FAL) ---
    "FACULDADE DE PLANALTINA": "FUP",
    "FACULDADE DE PLANALTINA - BRASÍLIA": "FUP",
}


def identificar_sigla_campus(nome_departamento: str) -> str:
    """
    Retorna a sigla do campus ('DARCY', 'FCTE', 'FCTS' ou 'FUP').
    """
    if not nome_departamento:
        return "Darcy"

    nome_limpo = nome_departamento.upper()

    if nome_limpo in DEPARTAMENTOS_FORA_DARCY:
        return DEPARTAMENTOS_FORA_DARCY[nome_limpo]

    if "GAMA" in nome_limpo:
        return "FCTE"
    elif "CEILÂNDIA" in nome_limpo or "CEILANDIA" in nome_limpo:
        return "FCTS"
    elif "PLANALTINA" in nome_limpo:
        return "FUP"
    return "Darcy"


def loader_departamentos_supabase(data_departamentos):
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

    print("\n--- Carregando Departamentos ---")
    for departamento in data_departamentos:
        nome_depto = departamento.get("nome", "").strip()

        # 1. Identifica a sigla do campus
        sigla_campus = identificar_sigla_campus(nome_depto)

        # 2. Coleta das siglas dos códigos das matérias do departamento
        materias = departamento.get("materias", [])
        siglas_extraidas = []

        for m in materias:
            codigo_mat = m.get("codigo", "")
            match = re.search(r"[a-zA-Z]+", codigo_mat)
            if match:
                siglas_extraidas.append(match.group(0).upper())

        # 3. Define a sigla do departamento pela mais frequente (Moda)
        if siglas_extraidas:
            contagem = Counter(siglas_extraidas)
            sigla_materia = contagem.most_common(1)[0][0]
        elif sigla_campus == "FCTE":
            sigla_materia = "FGA"
        else:
            sigla_materia = nome_depto[:10].upper()

        # 4. Verifica se já existe e decide entre UPDATE e INSERT
        try:
            cursor.execute(sql_check, (nome_depto,))
            existente = cursor.fetchone()

            if existente:
                cursor.execute(sql_update, (sigla_materia, sigla_campus, nome_depto))
                print(f"🔄 Departamento atualizado: {nome_depto} (Código: {sigla_materia})")
            else:
                payload = (str(uuid.uuid4()), sigla_materia, nome_depto, sigla_campus)
                cursor.execute(sql_insert, payload)
                print(f"✅ Departamento inserido: {nome_depto} (Código: {sigla_materia})")

            conn.commit()
        except Exception as err:
            print(f"❌ Erro ao registrar departamento {nome_depto}: {err}")
            conn.rollback()

    cursor.close()
    conn.close()
    print("Processamento de departamentos concluído!")

caminho_arquivo = os.path.join("data","processed","sigaa_professores.json")
with open(caminho_arquivo, "r", encoding="utf-8") as file:
    data_materias = json.load(file)

from psycopg2.extras import Json

def loader_materias_supabase(data_materias):
    """
    Insere ou atualiza os registros da tabela materias a partir do JSON de entrada.
    Campos como pre_requisito, co_requisito e equivalencia são convertidos para JSONB.
    """
    conn = psycopg2.connect(
        host=dbhost,
        port=dbport,
        password=dbpass,
        user=dbuser,
        dbname=db
    )

    if conn:
        print("Conexão estabelecida com sucesso!")

    cursor = conn.cursor()

    # Consulta SQL com subconsulta para buscar o id do departamento pelo nome
    # e ON CONFLICT para atualizar os campos caso o código da matéria já exista
    comando_sql = """
    INSERT INTO materias (
        id, 
        codigo_materia, 
        nome, 
        slug, 
        ementa, 
        creditos, 
        carga_horaria, 
        departamento_id, 
        co_requisito, 
        equivalencia, 
        pre_requisito, 
        nivel_de_ensino
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s,
        (SELECT id FROM departamentos WHERE nome = %s LIMIT 1),
        %s, %s, %s, %s
    )
    ON CONFLICT (codigo_materia) DO UPDATE SET
        nome = EXCLUDED.nome,
        slug = EXCLUDED.slug,
        ementa = EXCLUDED.ementa,
        creditos = EXCLUDED.creditos,
        carga_horaria = EXCLUDED.carga_horaria,
        departamento_id = EXCLUDED.departamento_id,
        co_requisito = EXCLUDED.co_requisito,
        equivalencia = EXCLUDED.equivalencia,
        pre_requisito = EXCLUDED.pre_requisito,
        nivel_de_ensino = EXCLUDED.nivel_de_ensino;
    """

    print("\n--- Carregando Matérias ---")
    for index, m in enumerate(data_materias):
        codigo_mat = m.get("codigo", "").strip()
        nome_mat = m.get("nome", "").strip()
        depto_nome = m.get("departamento", "").strip()

        # O psycopg2 exige o wrapper Json() para converter listas/dicionários Python em colunas jsonb
        co_req = Json(m.get("co_requisito")) if m.get("co_requisito") is not None else None
        equiv = Json(m.get("equivalencia")) if m.get("equivalencia") is not None else None
        pre_req = Json(m.get("pre_requisito")) if m.get("pre_requisito") is not None else None

        payload = (
            str(uuid.uuid4()),                  # id
            codigo_mat,                         # codigo_materia
            nome_mat,                           # nome
            m.get("slug"),                      # slug
            m.get("ementa", ""),                # ementa
            m.get("creditos", 0),               # creditos
            m.get("carga_horaria", 0),          # carga_horaria
            depto_nome,                         # departamento (usado no WHERE do SELECT id)
            co_req,                             # co_requisito (jsonb)
            equiv,                              # equivalencia (jsonb)
            pre_req,                            # pre_requisito (jsonb)
            m.get("nivel")                      # nivel_de_ensino
        )

        try:
            cursor.execute(comando_sql, payload)
            conn.commit()
            print(f"✅ Matéria [{index}]: {codigo_mat} - {nome_mat}")
        except Exception as err:
            print(f"❌ Erro na matéria [{index}] {codigo_mat}: {err}")
            conn.rollback()

    cursor.close()
    conn.close()
    print("Processamento de matérias concluído!")

loader_materias_supabase(data_materias)

# SELECT pg_terminate_backend(pid)
# FROM pg_stat_activity
# WHERE state != 'idle'
#   AND pid <> pg_backend_pid()
#   AND (now() - query_start) > interval '1 minute';
