# UnBook 2.0 - Data Pipeline (`unbook-pipeline`)

> Pipeline de Extração, Transformação e Carga (ETL) responsável por minerar, sanitizar e unificar os dados de professores, disciplinas, ofertas de turmas e relatos da Universidade de Brasília (UnB).

---

## 📌 Visão Geral

Este repositório é gerenciado pelo time de **Engenharia de Dados (`@unbook-org/data-engineers`)** do UnBook 2.0. Ele tem como responsabilidade principal alimentar a base viva da plataforma através de três frentes de trabalho:

1. **`sigaa`**: Web Scraping assíncrono (Scrapy) para mapeamento completo do corpo docente, ementas e histórico de turmas da UnB a partir do arquivo Seed.
2. **`social`**: Mineração automatizada via DOM (Playwright) e higienização/anonimização (NLP/Regex) de relatos e avaliações comunitárias (Facebook, Telegram).
3. **`legacy`**: Resgate, parsing e sanitização da base histórica do UnBook 1.0.

Os dados processados por este pipeline populam o banco central mantido pela **`unbook-api`**, servindo aos módulos de busca (`unbook-search`), raio-x de docentes com a **Análise UnBook** e simulador de grade (`unbook-planner`).

---

## 📁 Estrutura do Repositório

```text
unbook-pipeline/
├── .github/
│   ├── CODEOWNERS                      # Mapeamento de responsáveis por pasta/squad
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── workflows/
│       └── ci-quality-check.yml        # CI automatizado de testes e linting
├── data/
│   ├── processed/                      # Dados limpos e normalizados
│   │   ├── sigaa_professores.json      # [gitignore]
│   │   ├── social_parsed.json          # [gitignore]
│   │   └── legacy_reviews.json         # Avaliações válidas (matéria, professor, comentário)
│   └── raw/                            # [Incluso no .gitignore / Git LFS] Dados brutos
│       ├── legacy/
│       │   └── avaliacoes_disciplinas.csv  # Dump do formulário (gitignored)
│       ├── sigaa/
│       │   ├── seed_professores.json   # 📦 Arquivo Seed (Rastreado via Git LFS)
│       │   └── sigaa_bruto.json        # Extração bruta pós-Scrapy
│       └── social/
│           └── facebook_dump_dom.json  # Dump DOM capturado pelo Playwright
├── docs/
│   └── ARCHITECTURE.md                 # Documentação técnica do pipeline
├── src/
│   ├── __init__.py
│   ├── extractors/                     # 🔌 MÓDULOS DE EXTRAÇÃO POR SQUAD
│   │   ├── __init__.py
│   │   ├── base.py                     # Contrato base (BaseExtractor)
│   │   ├── legacy/                     # Squad Legacy (@unbook-org/squad-legacy)
│   │   │   ├── parser.py               # Parser do formulário de avaliações
│   │   │   └── run.py
│   │   ├── sigaa/                      # Squad SIGAA (@unbook-org/squad-sigaa)
│   │   │   ├── run.py                  # Orquestrador do crawler SIGAA
│   │   │   ├── scrapy_app/             # Motor Scrapy modular
│   │   │   │   └── prof_info/spiders/info_spider.py
│   │   │   └── seed/                   # Gerador do arquivo de links/seed
│   │   └── social/                     # Squad Social (@unbook-org/squad-social)
│   │       ├── run.py                  # Orquestrador da esteira social
│   │       ├── scraper.py              # Extrator assíncrono Playwright
│   │       └── parser.py               # Anonimização e limpeza de texto
│   ├── loaders/                        # 🚚 INGESTÃO DE DADOS
│   │   └── postgres_loader.py          # Ingestão dos dados processados no PostgreSQL
│   ├── transformers/                   # 🧹 LIMPEZA E ENTITY MATCHING
│   │   ├── clean_courses.py            # Código SIGAA vs. nome da disciplina
│   │   ├── clean_professors.py         # Normalização de nomes de docentes
│   │   └── sigaa_cleaner.py            # Normalização e resolução de entidades
│   └── utils/                          # 🛠️ UTILITÁRIOS GLOBAIS
│       ├── logger.py                   # Logger colorido e padronizado
│       └── paths.py                    # Âncora centralizada de caminhos do projeto
├── tests/
│   ├── test_legacy_parser.py
│   └── test_transformers.py
├── .gitignore
├── fb_cookies.json                     # [SENSÍVEL] Cookies de sessão (ignorado no git)
├── main.py                             # Orquestrador CLI central do pipeline
└── requirements.txt

```

---

## 🛠️ Tech Stack

* **Linguagem:** Python 3.12+
* **Scraping & Automação:** Scrapy, Playwright, Requests
* **Data Wrangling & NLP:** Pydantic, Regex, Pandas
* **Database & Storage:** PostgreSQL, Git LFS (Large File Storage)
* **Logs & CLI:** ANSI Color Logging, Argparse

---

## 🚀 Guia de Instalação e Execução

### 1. Pré-requisitos

* **Python 3.12+** instalado
* **Git** e **Git LFS** instalados no sistema:
* *Ubuntu/Debian:* `sudo apt install git git-lfs && git lfs install`
* *macOS (Homebrew):* `brew install git-lfs && git lfs install`
* *Windows:* Baixe em [git-lfs.com](https://www.google.com/search?q=https://git-lfs.com)



---

### 2. Passo a Passo de Instalação

**1. Clone o repositório e baixe os arquivos LFS:**

```bash
git clone [https://github.com/unbook-org/unbook-pipeline.git](https://github.com/unbook-org/unbook-pipeline.git)
cd unbook-pipeline

# Garante o download do arquivo data/raw/sigaa/seed_professores.json
git lfs pull

```

**2. Crie e ative o ambiente virtual:**

```bash
python -m venv venv
source venv/bin/activate    # Linux/macOS
# venv\Scripts\activate     # Windows

```

**3. Instale as dependências:**

```bash
pip install -r requirements.txt

```

**4. Instale os navegadores do Playwright:**

```bash
playwright install chromium

```

---

### 3. Executando o Pipeline via CLI (`main.py`)

O `main.py` é o ponto de entrada único para todas as extrações.

#### 🎓 Squad SIGAA (Corpo Docente & Turmas)

```bash
# Execução de teste (rápida, limitada aos primeiros 10 professores)
python main.py --source sigaa --limit 10

# Execução completa (todos os docentes da UnB)
python main.py --source sigaa

```

#### 💬 Squad Social (Comunidades & Redes)

> **Nota de Segurança:** Para raspar novos dados do Facebook, garanta que o arquivo `fb_cookies.json` com sua sessão válida esteja presente na raiz (este arquivo é estritamente ignorado pelo Git).

```bash
# Apenas processar e anonimizar o dump local existente (data/raw/social/facebook_dump_dom.json)
python main.py --source social

# Forçar nova raspagem no Facebook via Playwright + Limpeza
python main.py --source social --scrape-facebook

# Nova raspagem com limite de registros para validação
python main.py --source social --scrape-facebook --limit 10

```

#### 📦 Squad Legacy (Formulário de avaliações)

O dump bruto do Google Forms fica em `data/raw/legacy/` (gitignored). O parser extrai só avaliações usáveis no contrato da pipeline (`course_*`, `professor_name`, `comment`, `rating`).

```bash
# Coloque o CSV exportado em:
# data/raw/legacy/avaliacoes_disciplinas.csv

python main.py --source legacy
# Saída: data/processed/legacy_reviews.json
```

#### 🚀 Execução Geral (Pipeline Completo)

```bash
# Executa SIGAA, Social e Legacy sequencialmente
python main.py --source all

```

---

## 👥 Governança & Contribuição

Este repositório utiliza **`CODEOWNERS`** e proteção de branches:

* Nenhuma alteração entra na branch `main` sem passar por **Pull Request (PR)** aprovado.
* Alterações em `src/extractors/sigaa/` exigem aprovação da **`@unbook-org/squad-sigaa`**.
* Alterações em `src/extractors/social/` exigem aprovação da **`@unbook-org/squad-social`**.
* Alterações em `src/extractors/legacy/` exigem aprovação da **`@unbook-org/squad-legacy`**.

Consulte o guia completo em [`CONTRIBUTING.md`](https://www.google.com/search?q=./CONTRIBUTING.md) antes de submeter novos scrapers.
