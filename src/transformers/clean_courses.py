import re

COURSE_CODE_RE = re.compile(
    r"^\s*([A-Za-z]{3})\s*-?\s*(\d{4})(?:\s*[-–:]\s*(.+))?$",
    re.IGNORECASE,
)


def split_course_code_and_name(raw: str) -> tuple[str | None, str | None]:
    """Separa código SIGAA (ABC1234) e nome da disciplina."""
    text = clean_course_name(raw) or ""
    if not text:
        return None, None

    match = COURSE_CODE_RE.match(text)
    if match:
        code = f"{match.group(1).upper()}{match.group(2)}"
        name = clean_course_name(match.group(3) or "")
        return code, name

    return None, text


def clean_course_name(name: str | None) -> str | None:
    if not name:
        return None
    cleaned = re.sub(r"\s+", " ", str(name)).strip(" \t-–:_")
    return cleaned or None
