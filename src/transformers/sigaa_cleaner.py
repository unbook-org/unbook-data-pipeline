import json
import re
import unicodedata
from pathlib import Path

def remover_acentos_e_especiais(texto: str) -> str:
    """
    Remove acentuação, caracteres especiais e retorna o texto em maiúsculo.
    Mantém apenas letras (A-Z) e espaços.
    """
    if not texto:
        return ""

    # Normaliza a string para separar os caracteres de seus acentos
    texto_normalizado = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')

    # Remove qualquer caractere que não seja letra ou espaço
    texto_limpo = re.sub(r'[^a-zA-Z\s]', '', texto_normalizado)

    # Retorna sem espaços extras e em caixa alta
    return texto_limpo.strip().upper()

def limpar_dados():
    # __file__ é o script atual em src/transformers/limpeza_docentes.py
    # .parent é a pasta src/transformers/
    # .parents[1] é a pasta src/ (nível onde extractors e transformers se encontram)
    dir_src = Path(__file__).resolve().parents[1]

    # Agora descemos para extractors a partir da pasta src
    caminho_entrada = dir_src / "extractors" / "sigaa" / "ProfInfo" / "resultados_formatados.json"

    # Podemos salvar o resultado limpo na própria pasta transformers ou junto com o original
    # Aqui, estou salvando na pasta transformers para manter a organização
    caminho_saida = dir_src / "transformers" / "resultados_limpos.json"

    try:
        with open(caminho_entrada, 'r', encoding='utf-8') as f:
            dados = json.load(f)

        print(f"Processando {len(dados)} registros...")

        dados = dados[:10]

        print(f"Processando {len(dados)} registros...")

        for docente in dados:
            # 1. Tratar o nome do docente
            if "nome" in docente:
                docente["nome"] = remover_acentos_e_especiais(docente["nome"])

            # 2. Remover a chave de formação acadêmica, caso exista
            docente.pop("formacao_academica", None)

        # Salva o arquivo já formatado (indent=4 equivale a usar o json.tool)
        with open(caminho_saida, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=4)

        print(f"Limpeza concluída! Arquivo salvo em:\n{caminho_saida}")

    except FileNotFoundError:
        print(f"Erro: Arquivo não encontrado no caminho:\n{caminho_entrada}")
    except Exception as e:
        print(f"Ocorreu um erro durante a limpeza: {e}")

if __name__ == "__main__":
    limpar_dados()
