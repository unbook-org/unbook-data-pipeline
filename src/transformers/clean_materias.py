import os
import json
import re

#pegando o arquivo:
caminho_arq_materias = os.path.join("data","raw","sigaa","materias.json")

caminho_arq_professores = os.path.join("data","processed","sigaa_professores.json") #para pegar os slugs das materias


try:
    with open(caminho_arq_materias, "r", encoding="utf-8") as materias:
        data_materia = json.load(materias)
    with open(caminho_arq_professores, "r", encoding="utf-8") as professores:
        data_professor = json.load(professores)
except Exception as err:
    print(f"Arquivo não existe: {err}")



def clean_jsonfields(data): #     "( ( FGA0146 OU FGA0147 ) E ( FGA0085 ) )" Exemplo
    for componente in data: #componente é a lista de dicionarios de materias
        padrao_ou = r"\(\s*([a-zA-Z]\d{4})\s+OU\s+([a-zA-Z]\d{4})\s*\)"


def lista_codigo_slug(data_professor):
    """
    Extrai matérias com slug dos professores e remove duplicatas.
    """
    lista_materia_slug = []

    for professor in data_professor:
        disciplinas_prof = [
            {"codigo": d.get("codigo"), "slug": d.get("link")}
            for d in professor.get("disciplinas", [])
            if d.get("codigo")
        ]
        lista_materia_slug.extend(disciplinas_prof)

    codigos_vistos = set()
    materias_unicas = []

    for item in lista_materia_slug:
        codigo = item.get("codigo")
        if codigo and codigo not in codigos_vistos:
            codigos_vistos.add(codigo)
            materias_unicas.append(item)

    print(len(materias_unicas))
    return materias_unicas


def limpa_materia(data_materia, data_professor):
    """
    Atribui o 'slug' correto a cada matéria em data_materia com base no mapa de professores.
    """
    codigo_slug = lista_codigo_slug(data_professor)
    
    # 1. Cria um dicionário de busca rápida: {"CIC0004": "/docente/cic0004", ...}

    # 2. Atualiza o campo 'slug' nas matérias
    for materia in data_materia[0:5]: #data materia -> materias.json
        codigo_mat = materia.get("codigo")
        print(codigo_mat, "Codigo Atual")
        #procurar o codigo em professores
        for codigo in codigo_slug:
            if re.match(codigo_mat, codigo.get("codigo")):
                print(f"Encontrou um match -> {codigo.get("slug")}")
                materia["slug"] = codigo.get("slug")

        
        print(f"Processada: {materia.get("codigo")} -> nome {materia.get("nome")} -> slug{materia.get("slug")}")

    return data_materia

limpa_materia(data_materia,data_professor)


# def for componente in data_materia():

# #formato final departamentos 
# {
#     nome: nome-departamentos
#     codigo: nao-definido-ainda    #############################################
#     materias: [                   #dqui para baixo
#         {codigo: codigo-materia
#          nome: 
#          slug:
#          ementa:
#          creditos:
#          carga_horaria:
#          departamento_id: #ignorar é do banco apenas
#          co-requisito: { # ((1 ou 2) e 3)
#              relação: "AND"
#              condicao: [
#                  { relação:"OR"
#                   condicao: [
#                       {materia_id:, codigo:},
#                       {materia_id:, codigo:}
#                   ]
#                  },
#                  {materia_id:, codigo:}
#              ]
#         }
#       ] 
#   }

