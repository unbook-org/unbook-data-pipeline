# UnBook 2.0 - Data Pipeline (`unbook-pipeline`)

> Pipeline de Extração, Transformação e Carga (ETL) responsável por minerar, sanitizar e unificar os dados de professores, disciplinas, ofertas de turmas e relatos da Universidade de Brasília (UnB).

---

## 📌 Visão Geral

Este repositório é gerenciado pelo time de **Engenharia de Dados (`@unbook-org/data-engineers`)** do UnBook 2.0. Ele tem como responsabilidade principal alimentar a base viva da plataforma através de três frentes de trabalho:

1. **`sigaa`**: Web Scraping ativo e contínuo para extração da oferta de turmas, docentes e ementas direto do SIGAA/UnB.
2. **`legacy`**: Resgate, parsing e sanitização da base histórica do UnBook 1.0 (arquivos `.txt` e bases antigas).
3. **`social`**: Mapeamento, extração e categorização de relatos e materiais vindos de grupos comunitários de estudantes (Telegram, etc).

Os dados processados por este pipeline populam o banco central mantido pela **`unbook-api`**, servindo aos módulos de busca (`unbook-search`), guia de cursos (`unbook-catalog`) e simulador de grade (`unbook-planner`).

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
│   ├── processed/                      # [Incluso no .gitignore] Dados limpos (JSON/CSV)
│   │   └── .gitkeep
│   └── raw/                            # [Incluso no .gitignore] Dados brutos não tratados
│       ├── .gitkeep
│       ├── legacy/                     # Arquivos .txt / planilhas do UnBook 1.0
│       ├── scraped/                    # HTMLs e retornos puros do SIGAA
│       └── social/                     # Dumps e conversas categorizadas
├── docs/
│   └── ARCHITECTURE.md                 # Documentação técnica do pipeline
├── src/
│   ├── __init__.py
│   ├── extractors/                     # 🔌 MÓDULOS DE EXTRAÇÃO POR SQUAD
│   │   ├── __init__.py
│   │   ├── legacy/                     # Squad Legacy (@unbook-org/squad-legacy)
│   │   │   ├── __init__.py
│   │   │   └── legacy_parser.py        # Leitor e parser das avaliações antigas
│   │   ├── sigaa/                      # Squad SIGAA (@unbook-org/squad-sigaa)
│   │   │   ├── __init__.py
│   │   │   └── sigaa_scraper.py        # Web Scraper da oferta de turmas UnB
│   │   └── social/                     # Squad Social (@unbook-org/squad-social)
│   │       ├── __init__.py
│   │       └── social_scraper.py       # Extrator de dados/relatos de grupos
│   ├── loaders/                        # 🚚 INGESTÃO DE DADOS
│   │   ├── __init__.py
│   │   └── db_loader.py                # Ingestão dos dados limpos no PostgreSQL
│   ├── transformers/                   # 🧹 LIMPEZA E PADRONIZAÇÃO
│   │   ├── __init__.py
│   │   ├── clean_courses.py            # Tratamento de códigos e nomes de disciplinas
│   │   └── clean_professors.py         # Normalização de nomes de docentes
│   └── utils/                          # 🛠️ UTILITÁRIOS E HELPERS
│       ├── __init__.py
│       └── logger.py                   # Logger formatado da CLI
├── tests/                              # Suíte de testes automatizados
│   ├── test_extractors.py
│   └── test_transformers.py
├── .editorconfig
├── .env.example
├── .gitignore
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── docker-compose.yml
├── Dockerfile
├── LICENSE
├── main.py                             # Orquestrador da CLI do pipeline
└── requirements.txt

```

---

## 🛠️ Tech Stack

* **Linguagem:** Python 3.12+
* **Scraping & Mining:** BeautifulSoup4, Playwright / Scrapy, Requests, Telethon
* **Data Wrangling:** Pandas, NumPy, Pydantic
* **Database & ORM:** SQLAlchemy, psycopg2 (PostgreSQL)
* **Orquestração & Infra:** CLI Interna (`main.py`), Docker, GitHub Actions

---

## 📄 Contrato de Dados (Output Schema)

Para manter a consistência entre todas as frentes de extração, todo extrator em `src/extractors/` **deve** transformar e emitir os dados no formato padronizado abaixo antes de repassar aos *transformers*:

```json
{
  "course_code": "CIC0004",
  "course_name": "ALGORITMOS E PROGRAMAÇÃO DE COMPUTADORES",
  "professor_name": "NOME DO PROFESSOR",
  "campus": "Darcy Ribeiro",
  "semester": "2026/1",
  "rating": {
    "recommended": true,
    "emoji_vibe": "🤯",
    "grade_attained": "MS"
  },
  "comment": "Avaliação sanitizada e sem dados sensíveis.",
  "source": "legacy"
}

```

---

## 🚀 Como Executar Localmente

### Pré-requisitos

* Python 3.12+ instalado
* Git configurado
* Docker / Docker Compose (Opcional, para subir o banco local)

### Passo a Passo

1. **Clone o repositório:**
```bash
git clone [https://github.com/unbook-org/unbook-pipeline.git](https://github.com/unbook-org/unbook-pipeline.git)
cd unbook-pipeline

```


2. **Crie e ative o ambiente virtual:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# ou: venv\Scripts\activate  # Windows

```


3. **Instale as dependências:**
```bash
pip install -r requirements.txt

```


4. **Configure as variáveis de ambiente:**
```bash
cp .env.example .env

```


5. **Execute a CLI do Pipeline:**
```bash
# Executar extração do legado (.txt)
python main.py --source legacy

# Executar raspagem da oferta de turmas do SIGAA/UnB
python main.py --source sigaa --semester 2026_1

# Executar pipeline completo (Extração -> Limpeza -> Carga)
python main.py --full-run

```



---

## 👥 Governança & Contribuição

Este repositório utiliza **`CODEOWNERS`** e proteção de branches no GitHub.

* Nenhuma alteração entra na branch `main` sem passar por **Pull Request (PR)**.
* Alterações na pasta `src/extractors/sigaa/` exigem aprovação da **`@unbook-org/squad-sigaa`**.
* Alterações na pasta `src/extractors/legacy/` exigem aprovação da **`@unbook-org/squad-legacy`**.
* Alterações na pasta `src/extractors/social/` exigem aprovação da **`@unbook-org/squad-social`**.

Consulte o guia completo de contribuição em [`CONTRIBUTING.md`](./CONTRIBUTING.md) antes de abrir a sua branch!

---
