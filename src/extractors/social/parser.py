import json
import re
from pathlib import Path
from src.utils.paths import SOCIAL_DUMP_DOM_FILE, SOCIAL_PROCESSED_FILE
from src.utils.logger import get_logger

logger = get_logger("squad.social.parser")

def clean_reply_text(raw_text: str, reply_author: str) -> str:
    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    junk_patterns = [
        r"^" + re.escape(reply_author) + r"$",
        r"^\d+\s*(sem|d|h|m|a|min|hrs)$",
        r"^Ver(?:\s+(?:mais|\d+))?\s+respostas?$",
        r"(?:…\s*)?Ver mais(?:\s+Editado)?$",
        r"^Editado$",
        r"^Responder$",
        r"^·$"
    ]
    clean_lines = [l for l in lines if not any(re.match(p, l, re.IGNORECASE) for p in junk_patterns)]
    return " ".join(clean_lines)

def run_social_parser(input_path: Path = SOCIAL_DUMP_DOM_FILE, output_path: Path = SOCIAL_PROCESSED_FILE):
    if not input_path.exists():
        logger.error(f"❌ Arquivo não encontrado: {input_path}")
        return []

    logger.info(f"Acessando {input_path.name} para limpeza e estruturação...")
    with open(input_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    structured_posts = []
    for item in raw_data:
        if not item.get("replies"):
            continue

        clean_replies = []
        for reply in item.get("replies", []):
            meta = reply.get("meta", "")
            raw_text = reply.get("raw_text", "")

            match = re.search(r"(?:Comentário|Resposta) de (.+?) há (.+)", meta)
            reply_author = match.group(1).strip() if match else "Anônimo"
            reply_time = match.group(2).strip() if match else ""

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

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(structured_posts, f, ensure_ascii=False, indent=4)

    logger.info(f"✅ {len(structured_posts)} posts estruturados salvos em: {output_path.name}")
    return structured_posts