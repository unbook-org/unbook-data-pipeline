flowchart TB
    %% --- FONTES DE DADOS E PIPELINE ---
    subgraph SQUAD_DATA [Squad Engenharia de Dados]
        RAW_TXT[(Arquivos .txt Legados\n2024_02 / 2025_01)]
        SIGAA_WEB[SIGAA / UnB Portal]
        TELEGRAM_SCRAP[Grupos Telegram / Drives]

        REPO_DATA[repo: unbook-data-pipeline\nPython 3.12 / Scrapers / ETL]
    end

    RAW_TXT --> REPO_DATA
    SIGAA_WEB --> REPO_DATA
    TELEGRAM_SCRAP --> REPO_DATA

    %% --- BANCO DE DADOS & BACKEND CENTRAL ---
    subgraph CORE_INFRA [Plataforma Core & Infraestrutura]
        DB[(PostgreSQL Central / Redis Cache)]
        REPO_CORE[repo: unbook-core-api\nBackend API REST / Auth SSO / DB ORM]
    end

    REPO_DATA -- 1. Popula / Ingestão de Dados Sanitizados --> DB
    REPO_CORE <--> DB

    %% --- SHELL FRONTEND ---
    subgraph CORE_FRONT [Portal & Design System]
        REPO_SHELL[repo: unbook-web-shell\nLanding Page / Portal Principal / Single Sign-On]
    end

    REPO_SHELL <--> REPO_CORE

    %% --- PRODUTOS / SQUADS ---
    subgraph PRODUCTS [Produtos & Squads do Ecossistema]
        REPO_BOOGLE[repo: unboogle\nSquad UnBoogle\nBusca de Provas / Resumos]
        REPO_FLIX[repo: unbflix\nSquad UnBFlix\nCuradoria de Videoaulas / Mídia]
        REPO_PLANNER[repo: unbplanner\nSquad UnBPlanner\nSimulador de Grade / Fluxogramas]
    end

    %% COMUNICAÇÃO DOS PRODUTOS COM O CORE
    REPO_SHELL -. Autenticação & SSO .-> REPO_BOOGLE
    REPO_SHELL -. Autenticação & SSO .-> REPO_FLIX
    REPO_SHELL -. Autenticação & SSO .-> REPO_PLANNER

    REPO_BOOGLE <== 2. Consome Dados & Arquivos ==> REPO_CORE
    REPO_FLIX <== 3. Consome Playlists & Ementas ==> REPO_CORE
    REPO_PLANNER <== 4. Consome Matérias & Horários ==> REPO_CORE

    %% UNBOOK TEMPLATE (PADRONIZAÇÃO)
    subgraph GOVERNANCE [Governança & Padrões]
        REPO_TEMPLATE[repo: repository-template\nCI/CD / Rules / Templates]
    end

    REPO_TEMPLATE -. Herdado por .-> REPO_DATA
    REPO_TEMPLATE -. Herdado por .-> REPO_CORE
    REPO_TEMPLATE -. Herdado por .-> REPO_BOOGLE
    REPO_TEMPLATE -. Herdado por .-> REPO_FLIX
    REPO_TEMPLATE -. Herdado por .-> REPO_PLANNER