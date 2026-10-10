import json
import os
import re

caminho_arq_materias = os.path.join("data", "raw", "sigaa", "materias.json")

try:
    with open(caminho_arq_materias, "r", encoding="utf-8") as materias:
        data_materia = json.load(materias)
except Exception as err:
    print(f"Arquivo não existe: {err}")
    data_materia = []


def limpa_req(data_materia):
    data_materia_clean = []

    for materia in data_materia:
        # Tratamento seguro para pegar o primeiro item de pré/co-requisitos/equivalência
        pre = materia.get("pre_requisito", [])
        co = materia.get("co_requisito", [])
        eq = materia.get("equivalencia", [])

        materia["pre_requisito"] = pre[0].strip() if pre and pre[0] else ""
        materia["co_requisito"] = co[0].strip() if co and co[0] else ""
        materia["equivalencia"] = eq[0].strip() if eq and eq[0] else ""

        data_materia_clean.append(materia)

    return data_materia_clean


# --- Lógica do Parser para Árvore de Condições (JSONField) ---


def tokenizar(expressao: str) -> list[str]:
    """Divide a expressão em tokens (parênteses, operadores e códigos)."""
    expressao_formatada = expressao.replace("(", " ( ").replace(")", " ) ")
    tokens = expressao_formatada.split()
    return [t for t in tokens if t.strip()]


def parse_expressao(tokens: list[str]):
    """Parser para converter tokens em estrutura lógica de dicionários aninhados."""
    if not tokens:
        return None

    pilha_nos = []
    pilha_ops = []

    precedencia = {"OU": 1, "OR": 1, "E": 2, "AND": 2}

    def aplicar_operador():
        if not pilha_ops or len(pilha_nos) < 2:
            return
        op = pilha_ops.pop()
        direita = pilha_nos.pop()
        esquerda = pilha_nos.pop()

        relacao = "OR" if op.upper() in ["OU", "OR"] else "AND"

        condicoes = []

        if isinstance(esquerda, dict) and esquerda.get("relação") == relacao:
            condicoes.extend(esquerda["condicao"])
        else:
            condicoes.append(esquerda)

        if isinstance(direita, dict) and direita.get("relação") == relacao:
            condicoes.extend(direita["condicao"])
        else:
            condicoes.append(direita)

        pilha_nos.append({"relação": relacao, "condicao": condicoes})

    i = 0
    while i < len(tokens):
        token = tokens[i]

        if token == "(":
            pilha_ops.append(token)
        elif token == ")":
            while pilha_ops and pilha_ops[-1] != "(":
                aplicar_operador()
            if pilha_ops and pilha_ops[-1] == "(":
                pilha_ops.pop()
        elif token.upper() in ["E", "AND", "OU", "OR"]:
            op_atual = token.upper()
            while (
                pilha_ops
                and pilha_ops[-1] != "("
                and precedencia.get(pilha_ops[-1], 0)
                >= precedencia.get(op_atual, 0)
            ):
                aplicar_operador()
            pilha_ops.append(op_atual)
        else:
            pilha_nos.append({"materia_id": None, "codigo": token})
        i += 1

    while pilha_ops:
        aplicar_operador()

    return pilha_nos[0] if pilha_nos else None


def formatar_requisito(expressao_texto: str) -> dict | None:
    """Converte a string de pré-requisitos na estrutura JSON em árvore."""
    if not expressao_texto or not expressao_texto.strip():
        return None

    tokens = tokenizar(expressao_texto)
    operadores = {"E", "AND", "OU", "OR"}

    if len(tokens) == 1 and tokens[0] not in operadores:
        return {"materia_id": None, "codigo": tokens[0]}

    return parse_expressao(tokens)


# --- Aplicação e Formatação dos Campos ---


def formata_jsonfield(data_materia):
    clean_materias = []

    for materia in data_materia:
        # Formata pré-requisitos, co-requisitos e equivalências
        materia["pre_requisito"] = formatar_requisito(
            materia.get("pre_requisito", "")
        )
        materia["co_requisito"] = formatar_requisito(
            materia.get("co_requisito", "")
        )
        materia["equivalencia"] = formatar_requisito(
            materia.get("equivalencia", "")
        )

        clean_materias.append(materia)

        # Imprime para verificação
        print(
            f"Matéria: {materia.get('codigo')} | Pré-requisito: {json.dumps(materia['pre_requisito'], ensure_ascii=False)}"
        )

    return clean_materias


# Execução do pipeline
materias_processadas = formata_jsonfield(limpa_req(data_materia))

caminho_final = os.path.join("data", "processed", "materias_clean.json")
with open(caminho_final, "w", encoding="utf-8") as final:
    json.dump(materias_processadas, final, ensure_ascii=False, indent=4)