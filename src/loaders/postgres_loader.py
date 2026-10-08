import os
from supabase import create_client, Client
import psycopg2
from dotenv import load_dotenv
import json
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
    dados = json.load(file)

def loader_professores_supabase(dados): 

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

            for key, value in i.items():
                if isinstance(value, str):
                    if len(value) >= 200:
                        print(f"Campo '{key}': tamanho {len(value)} caracteres")

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

def loader_departamentos_supabase():
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
        INSERT INTO departamentos (
        id, sigla, nome
        ) VALUES (%s, %s, %s)
        """ #comando para executar 



#  departamento = {
#       intituto de fisica : [fisica1, fisica2, fisica3]
#       departamento de matematica : [calculo1, calculo2]
#   }

