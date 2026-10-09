import os
import json

#pegando o arquivo:

caminho_arq_departamentos = os.path.join("data","raw","sigaa","departamentos.json")
caminho_arq_materias = os.path.join("data","raw","sigaa","materias.json")


try:
    with open(caminho_arq_departamentos, "r", encoding="utf-8") as departamentos:
        data_departamento = json.load(departamentos)

    with open(caminho_arq_materias, "r", encoding="utf-8") as materias:
        data_materia = json.load(materias)

except Exception as err:
    print(f"Arquivo não existe: {err}")

# #formato final departamentos 
# {
#     nome: nome-departamentos
#     codigo: nao-definido-ainda
#     materias: [
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