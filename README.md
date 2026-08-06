# UnBook 2.0 - Data Pipeline & Engineering

> Pipeline de Extração, Transformação e Carga (ETL) responsável por minerar, sanitizar e unificar os dados de professores, disciplinas e materiais da Universidade de Brasília (UnB).

---

## 📌 Visão Geral

Este repositório é gerenciado pela **Squad de Engenharia de Dados** do UnBook 2.0. Ele tem como responsabilidade:
1. **Resgatar e Sanitizar** a base de dados legada do UnBook (arquivos `.txt` e SQLite antigos).
2. **Raspar (Web Scraping)** dados atualizados de turmas, docentes e horários diretamente do SIGAA/UnB.
3. **Exportar & Popular** o banco de dados central alimentando a API (`unbook-core-api`).

## 📁 Estrutura do Repositório

```text
unbook-data-pipeline/
├── data/
│   ├── processed/              # [A Fazer] Dados limpos (CSV/JSON/SQLite local)
│   │   └── .gitkeep
│   └── raw/                    # Dados brutos
│       ├── .gitkeep
│       ├── legacy/             # Arquivos .txt do UnBook antigo
│       └── scraped/            # [A Fazer] Downloads puros do SIGAA
├── src/
│   ├── __init__.py
│   ├── extractors/             # Módulos de extração
│   │   ├── __init__.py
│   │   ├── legacy_parser.py    # [A Fazer] Leitor dos .txt antigos
│   │   └── sigaa_scraper.py    # [A Fazer] Web Scraper do SIGAA/UnB
│   ├── loaders/                # Ingestão de dados
│   │   ├── __init__.py
│   │   └── db_loader.py        # [A Fazer] Popula o banco PostgreSQL
│   ├── transformers/           # Limpeza e padronização
│   │   ├── __init__.py
│   │   ├── clean_courses.py    # [A Fazer] Tratamento de disciplinas
│   │   └── clean_professors.py # [A Fazer] Tratamento de nomes de docentes
│   └── utils/                  # Utilitários e helpers
│       ├── __init__.py
│       └── logger.py           # [A Fazer] Logs formatados da CLI
├── tests/                      # Suíte de testes automatizados
│   └── test_extractors.py      # [A Fazer] Testes dos parsers/scrapers
│   └── test_transformers.py    # [A Fazer] Testes da sanitização
├── .venv                       # [Gerar] Pasta venv
├── .editorconfig
├── .env                       # [Gerar] Arquivo .env
├── .env.example
├── .gitignore
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── docker-compose.yml
├── Dockerfile
├── LICENSE
├── main.py
├── README.md
├── requirements.txt
```

## 🛠️ Tech Stack

* **Linguagem:** Python 3.12
* **Scraping & Parsing:** BeautifulSoup4, Selenium / Playwright, Requests
* **Data Wrangling:** Pandas, NumPy
* **Database & ORM:** SQLAlchemy / psycopg2
* **Orquestração:** CLI Interna / Docker

## 🚀 Como Executar Localmente

### Pré-requisitos

* Python 3.12 instalado (ou Docker)
* Virtualenv configurado

### Passo a Passo

1. **Clone o repositório:**
```bash
git clone [https://github.com/unbook-org/unbook-data-pipeline.git](https://github.com/unbook-org/unbook-data-pipeline.git)
cd unbook-data-pipeline

```


2. **Crie e ative o ambiente virtual:**
```bash
python3.12 -m venv venv
source venv/bin/activate

```


3. **Instale as dependências:**
```bash
pip install -r requirements.txt

```


4. **Execute o Pipeline Completo:**
```bash
# Processar dados antigos legados
python main.py --source legacy

# Raspar dados atuais do SIGAA/UnB
python main.py --source sigaa --semester 2026_1

```

UnBook 2.0 - Universidade de Brasília (UnB)