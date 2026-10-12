import re
import unicodedata

NAME_PARTICLES = {"de", "da", "do", "dos", "das", "e", "del", "di", "von", "van"}
TITLES_RE = re.compile(
    r"^(dr\.?a?|dra\.?|msc\.?|ms\.?|prof\.?a?|phd\.?)\s+",
    re.IGNORECASE,
)
TEST_NAMES = {"teste", "test", "asdf", "xxx", "foo", "bar"}


def clean_professor_name(name: str) -> str:
    text = re.sub(r"\s+", " ", str(name or "")).strip(" .")
    while True:
        updated = TITLES_RE.sub("", text).strip()
        if updated == text:
            break
        text = updated
    return _title_case_pt(text)


def is_plausible_professor_name(name: str) -> bool:
    cleaned = clean_professor_name(name)
    if not cleaned:
        return False
    if cleaned.lower() in TEST_NAMES:
        return False
    if len(cleaned) > 100:
        return False
    letters = re.sub(r"[^A-Za-zÀ-ÿ]", "", cleaned)
    return len(letters) >= 3


def _title_case_pt(name: str) -> str:
    words = name.split()
    titled = []
    for index, word in enumerate(words):
        lower = word.lower()
        if index > 0 and lower in NAME_PARTICLES:
            titled.append(lower)
            continue
        titled.append("-".join(_capitalize_token(part) for part in word.split("-")))
    return " ".join(titled)


def _capitalize_token(token: str) -> str:
    if not token:
        return token
    if token.isupper() and len(token) <= 3:
        return token
    first = unicodedata.normalize("NFC", token[:1]).upper()
    rest = unicodedata.normalize("NFC", token[1:]).lower()
    return first + rest
