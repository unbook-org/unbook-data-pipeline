"""
Navegação Playwright (async, Chromium headless) pelas telas públicas de currículos do SIGAA.

Só obtém HTML; todo o parse é feito por src/extractors/sigaa/curriculum/parser.py.
Mapa de navegação em docs/sigaa_curriculos_HANDOFF.md:

  home.jsf -> lista.jsf?nivel=G (GET, já traz todos os cursos)
  -> curriculo.jsf?id=<curso> (GET direto)
  -> clique em "Relatório da Estrutura Curricular" (POST JSF, resposta na mesma URL)
  -> history.back() para o próximo relatório.

Requisitos não funcionais (SPEC): até 2 sessões concorrentes, 1–2 s entre requisições,
User-Agent do UnBook, 3 tentativas por curso com backoff exponencial, reinício da
navegação quando a sessão/ViewState expira e checkpoint incremental retomável.
"""

import asyncio
import json
import os
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from playwright.async_api import (
    Browser,
    BrowserContext,
    Locator,
    Page,
    async_playwright,
)

from src.extractors.sigaa.curriculum.parser import (
    parse_curricula_list,
    parse_curriculum_report,
    parse_program_list,
)
from src.utils.logger import get_logger
from src.utils.paths import SIGAA_CURRICULA_RAW_FILE

logger = get_logger("squad.sigaa.curriculum.scraper")

BASE_URL = "https://sigaa.unb.br/sigaa/public"
HOME_URL = f"{BASE_URL}/home.jsf"
PROGRAM_LIST_URL = f"{BASE_URL}/curso/lista.jsf?nivel=G&aba=p-graduacao"
CURRICULA_URL = f"{BASE_URL}/curso/curriculo.jsf?lc=pt_BR&id={{program_id}}"

USER_AGENT = "UnBook-Pipeline/2.0 (curriculos; +https://github.com/unbook-org/unbook-pipeline)"

MAX_CONCURRENCY = 2
DELAY_RANGE_S = (1.0, 2.0)
MAX_ATTEMPTS = 3
BACKOFF_BASE_S = 2.0
TIMEOUT_MS = 30_000

PROGRAM_LIST_SELECTOR = "table.listagem"
REPORT_HEADER_SELECTOR = "#formulario table.formulario"
REPORT_LINK_SELECTOR = "#table_lt a[title=\"Relatório da Estrutura Curricular\"][onclick*=\"'id':'{curriculum_id}'\"]"

COOKIE_DIALOG_SELECTOR = "#sigaa-cookie-consent[open]"

BRT = timezone(timedelta(hours=-3))


class SessionExpiredError(RuntimeError):
    """Sessão ou ViewState inválido: o SIGAA redireciona em silêncio para home.jsf."""


def now_iso() -> str:
    return datetime.now(BRT).isoformat(timespec="seconds")


def describe_error(error: Exception) -> str:
    """Tipo + primeira linha da mensagem (os erros do Playwright trazem o call log inteiro)."""
    message = str(error).strip().splitlines()
    return f"{type(error).__name__}: {message[0] if message else ''}"


async def _accept_cookies(dialog: Locator) -> None:
    await dialog.get_by_role("button", name="Ciente").click()


# --- Checkpoint ---------------------------------------------------------------

def load_checkpoint(path: Path = SIGAA_CURRICULA_RAW_FILE) -> dict[str, Any]:
    """Lê o bruto existente; sem arquivo, devolve um checkpoint vazio."""
    if not path.exists():
        return {"source": PROGRAM_LIST_URL, "user_agent": USER_AGENT, "updated_at": None, "programs": {}}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_checkpoint(checkpoint: dict[str, Any], path: Path = SIGAA_CURRICULA_RAW_FILE) -> None:
    """Grava de forma atômica (arquivo temporário + rename) para não corromper o bruto num Ctrl+C."""
    checkpoint["updated_at"] = now_iso()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def is_done(checkpoint: dict[str, Any], program_id: str) -> bool:
    return checkpoint["programs"].get(program_id, {}).get("status") == "ok"


def merge_curriculum(entry: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    """Junta a linha da tela de estruturas (ano, status, turno) com o relatório (cargas, componentes)."""
    if report["curriculum_code"] != entry["curriculum_code"]:
        raise ValueError(
            f"Relatório devolveu a estrutura {report['curriculum_code']!r}, esperada {entry['curriculum_code']!r}."
        )
    return {
        "curriculum_code": entry["curriculum_code"],
        "created_year": entry["created_year"],
        "status": entry["status"],
        "shift_group": entry["shift_group"],
        "sigaa_curriculum_id": entry["sigaa_curriculum_id"],
        "workload": report["workload"],
        "completion_semesters": report["completion_semesters"],
        "components": report["components"],
    }


# --- Sessão de navegação --------------------------------------------------------

class CurriculumSession:
    """Um BrowserContext próprio (cookies e ViewState isolados) e uma única aba."""

    def __init__(self, browser: Browser, name: str):
        self.browser = browser
        self.name = name
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self._on_report = False

    @property
    def ready(self) -> bool:
        return self.page is not None

    async def close(self) -> None:
        if self.context is not None:
            try:
                await self.context.close()
            except Exception as e:
                logger.warning(f"[{self.name}] Erro ao fechar contexto: {e}")
        self.context = None
        self.page = None
        self._on_report = False

    async def start(self) -> str:
        """(Re)inicia a navegação a partir da consulta de cursos; devolve o HTML da lista."""
        await self.close()
        self.context = await self.browser.new_context(user_agent=USER_AGENT, locale="pt-BR")
        self.context.set_default_timeout(TIMEOUT_MS)
        self.page = await self.context.new_page()
        # O modal de cookies é fixo no rodapé e intercepta cliques nos links que ficam por baixo.
        # "Ciente" grava o aceite no localStorage, então ele não volta nesta sessão.
        await self.page.add_locator_handler(self.page.locator(COOKIE_DIALOG_SELECTOR), _accept_cookies)

        logger.info(f"[{self.name}] Acessando home e lista de cursos do SIGAA...")
        await self._goto(HOME_URL, allow_home=True)
        html = await self._goto(PROGRAM_LIST_URL)
        if not await self.page.locator(PROGRAM_LIST_SELECTOR).count():
            raise SessionExpiredError("lista de cursos sem table.listagem")
        return html

    async def _pause(self) -> None:
        await asyncio.sleep(random.uniform(*DELAY_RANGE_S))

    def _check_session(self) -> None:
        if self.page.url.split("?")[0].endswith("/home.jsf"):
            raise SessionExpiredError("redirecionado para home.jsf (sessão/ViewState expirado)")

    async def _goto(self, url: str, allow_home: bool = False) -> str:
        await self._pause()
        await self.page.goto(url, wait_until="domcontentloaded")
        if not allow_home:
            self._check_session()
        self._on_report = False
        return await self.page.content()

    async def open_curricula(self, program_id: str) -> str:
        return await self._goto(CURRICULA_URL.format(program_id=program_id))

    async def open_report(self, program_id: str, entry: dict[str, Any]) -> str:
        """Clica no link do relatório (POST JSF) e devolve o HTML da resposta."""
        link = self.page.locator(REPORT_LINK_SELECTOR.format(curriculum_id=entry["sigaa_curriculum_id"]))

        if not await link.count() and self._on_report:
            await self._pause()
            await self.page.go_back(wait_until="domcontentloaded")
            self._check_session()
            self._on_report = False
        if not await link.count():
            await self.open_curricula(program_id)
            if not await link.count():
                raise RuntimeError(f"Link do relatório {entry['curriculum_code']} não encontrado.")

        await self._pause()
        async with self.page.expect_navigation(wait_until="domcontentloaded"):
            await link.first.click()
        self._on_report = True
        self._check_session()
        if not await self.page.locator(REPORT_HEADER_SELECTOR).count():
            raise SessionExpiredError(f"relatório {entry['curriculum_code']} sem cabeçalho (#formulario)")
        return await self.page.content()


async def fetch_program_curricula(
    session: CurriculumSession, program: dict[str, Any], cache: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Todas as estruturas de um curso. `cache` guarda os relatórios já obtidos,
    para que uma nova tentativa do curso não repita POSTs bem-sucedidos.
    """
    program_id = program["sigaa_program_id"]
    entries = parse_curricula_list(await session.open_curricula(program_id))
    if not entries:
        logger.warning(f"Curso {program_id} ({program['name']}) sem estruturas curriculares listadas.")

    curricula = []
    for entry in entries:
        key = entry["sigaa_curriculum_id"]
        if key not in cache:
            report = parse_curriculum_report(await session.open_report(program_id, entry))
            cache[key] = merge_curriculum(entry, report)
        curricula.append(cache[key])
    return curricula


# --- Orquestração do scraping ----------------------------------------------------

@dataclass
class ScrapeSummary:
    selected: int = 0
    reused: int = 0
    ok: int = 0
    curricula: int = 0
    components: int = 0
    elapsed_s: list[float] = field(default_factory=list)
    failures: list[dict[str, Any]] = field(default_factory=list)

    @property
    def avg_elapsed_s(self) -> float | None:
        return sum(self.elapsed_s) / len(self.elapsed_s) if self.elapsed_s else None


def summarize(checkpoint: dict[str, Any], program_ids: list[str] | None = None) -> ScrapeSummary:
    """Resumo do checkpoint (todo ele, ou só dos cursos selecionados neste run)."""
    records = checkpoint["programs"]
    ids = program_ids if program_ids is not None else list(records)
    summary = ScrapeSummary(selected=len(ids))
    for program_id in ids:
        record = records.get(program_id)
        if record is None:
            continue
        if record["status"] == "ok":
            summary.ok += 1
            summary.curricula += len(record["curricula"])
            summary.components += sum(len(c["components"]) for c in record["curricula"])
        else:
            program = record["program"]
            summary.failures.append(
                {
                    "sigaa_program_id": program_id,
                    "name": f"{program['name']} - {program['shift']}",
                    "error": record.get("error"),
                }
            )
    return summary


class CurriculumScraper:
    def __init__(self, checkpoint_path: Path = SIGAA_CURRICULA_RAW_FILE, concurrency: int = MAX_CONCURRENCY):
        self.checkpoint_path = checkpoint_path
        self.concurrency = max(1, min(concurrency, MAX_CONCURRENCY))
        self.checkpoint = load_checkpoint(checkpoint_path)
        self.elapsed_s: list[float] = []

    async def run(self, limit: int | None = None) -> ScrapeSummary:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            sessions = [CurriculumSession(browser, f"s{i + 1}") for i in range(self.concurrency)]
            try:
                programs = await self._load_program_list(sessions[0])
                if limit:
                    programs = programs[:limit]

                pending = [prog for prog in programs if not is_done(self.checkpoint, prog["sigaa_program_id"])]
                reused = len(programs) - len(pending)
                logger.info(
                    f"{len(programs)} curso(s) selecionado(s): {reused} já no checkpoint, {len(pending)} a extrair."
                )

                queue: asyncio.Queue = asyncio.Queue()
                for prog in pending:
                    queue.put_nowait(prog)
                workers = sessions[: min(len(sessions), len(pending))]
                await asyncio.gather(*(self._worker(session, queue) for session in workers))
            finally:
                for session in sessions:
                    await session.close()
                await browser.close()

        summary = summarize(self.checkpoint, [prog["sigaa_program_id"] for prog in programs])
        summary.reused = reused
        summary.elapsed_s = self.elapsed_s
        return summary

    async def _load_program_list(self, session: CurriculumSession) -> list[dict[str, Any]]:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                programs = parse_program_list(await session.start())
                if programs:
                    logger.info(f"Lista de cursos carregada: {len(programs)} cursos.")
                    return programs
                raise RuntimeError("lista de cursos vazia")
            except Exception as e:
                await session.close()
                if attempt == MAX_ATTEMPTS:
                    raise RuntimeError(
                        f"Lista de cursos indisponível após {MAX_ATTEMPTS} tentativas: {describe_error(e)}"
                    ) from e
                await self._backoff("lista de cursos", attempt, e)

    async def _backoff(self, label: str, attempt: int, error: Exception) -> None:
        wait = BACKOFF_BASE_S * 2 ** (attempt - 1) + random.uniform(0, 1)
        logger.warning(
            f"{label}: tentativa {attempt}/{MAX_ATTEMPTS} falhou ({describe_error(error)}). "
            f"Nova tentativa em {wait:.1f}s."
        )
        await asyncio.sleep(wait)

    async def _worker(self, session: CurriculumSession, queue: asyncio.Queue) -> None:
        while True:
            try:
                program = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            await self._scrape_program(session, program)

    async def _scrape_program(self, session: CurriculumSession, program: dict[str, Any]) -> None:
        program_id = program["sigaa_program_id"]
        label = f"Curso {program_id} ({program['name']} - {program['shift']})"
        cache: dict[str, dict[str, Any]] = {}
        started = time.monotonic()

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                if not session.ready:
                    await session.start()
                curricula = await fetch_program_curricula(session, program, cache)
            except Exception as e:
                # Qualquer falha reinicia a navegação do zero (sessão nova) antes da próxima tentativa.
                await session.close()
                if attempt < MAX_ATTEMPTS:
                    await self._backoff(label, attempt, e)
                    continue
                logger.error(f"❌ {label}: falhou após {MAX_ATTEMPTS} tentativas: {describe_error(e)}")
                self.checkpoint["programs"][program_id] = {
                    "program": program,
                    "status": "failed",
                    "error": describe_error(e),
                    "attempts": attempt,
                    "failed_at": now_iso(),
                }
                save_checkpoint(self.checkpoint, self.checkpoint_path)
                return

            elapsed = round(time.monotonic() - started, 1)
            self.elapsed_s.append(elapsed)
            self.checkpoint["programs"][program_id] = {
                "program": program,
                "status": "ok",
                "attempts": attempt,
                "extracted_at": now_iso(),
                "elapsed_s": elapsed,
                "curricula": curricula,
            }
            save_checkpoint(self.checkpoint, self.checkpoint_path)
            n_components = sum(len(c["components"]) for c in curricula)
            logger.info(f"✅ {label}: {len(curricula)} estrutura(s), {n_components} componente(s) em {elapsed}s.")
            return


async def scrape_curricula(
    limit: int | None = None, checkpoint_path: Path = SIGAA_CURRICULA_RAW_FILE
) -> ScrapeSummary:
    """Extrai os currículos dos `limit` primeiros cursos da lista, pulando os já salvos no checkpoint."""
    return await CurriculumScraper(checkpoint_path=checkpoint_path).run(limit=limit)
