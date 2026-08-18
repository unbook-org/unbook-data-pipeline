import json
import re
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger(__name__)

def clean_reply_text(raw_text, reply_author):
    """
    Limpa o texto do comentário, removendo o nome do autor duplicado,
    o layout do Facebook ('·', tempos) e o botão 'Responder'.
    """
    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    
    junk_patterns = [
        r"^" + re.escape(reply_author) + r"$",  # Nome do autor no topo
        r"^\d+\s*(sem|d|h|m|a|min|hrs)$",       # Datas (ex: 3 d, 22 h)
        r"^Ver(?:\s+(?:mais|\d+))?\s+respostas?$",
        r"^Responder$",
        r"^·$"
    ]
    
    clean_lines = [l for l in lines if not any(re.match(p, l, re.IGNORECASE) for p in junk_patterns)]
    return " ".join(clean_lines)

def process_dom_json(raw_data):
    structured_posts = []

    for item in raw_data:
        # Se não tiver respostas, ignoramos (já que o objetivo do UnBook são os feedbacks)
        if not item.get("replies"):
            continue

        clean_replies = []
        for reply in item.get("replies", []):
            meta = reply.get("meta", "")
            raw_text = reply.get("raw_text", "")

            # Extrai autor e tempo da string "Comentário de [Nome] há [Tempo]" usando Regex
            match = re.search(r"(?:Comentário|Resposta) de (.+?) há (.+)", meta)
            
            if match:
                reply_author = match.group(1).strip()
                reply_time = match.group(2).strip()
            else:
                reply_author = "Anônimo"
                reply_time = ""

            # Limpa o texto da resposta
            final_text = clean_reply_text(raw_text, reply_author)

            if len(final_text) > 5:
                clean_replies.append({
                    "author": reply_author,
                    "time_ago": reply_time,
                    "content": final_text
                })

        if clean_replies:
            structured_posts.append({
                "source": "facebook_dom",
                "post_author": item.get("author", "Anônimo"),
                "question": item.get("question", ""),
                "replies": clean_replies
            })

    return structured_posts

def run_extraction(
    input_filepath="data/raw/social/facebook_dump_dom.json", 
    output_filepath="data/processed/social_parsed.json"
):
    logger.info("Iniciando limpeza e estruturação dos dados do DOM do Facebook...")

    input_path = Path(input_filepath)
    output_path = Path(output_filepath)

    if not input_path.exists():
        logger.error(f"❌ Arquivo não encontrado: {input_path}")
        return []

    with open(input_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    valid_data = process_dom_json(raw_data)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(valid_data, f, ensure_ascii=False, indent=4)

    logger.info(f"✅ SUCESSO! {len(valid_data)} avaliações estruturadas e prontas para o banco salvas em: {output_filepath}")
    return valid_data