# 📚 Guia Completo: Pipeline de Extração e Carga de Turmas do SIGAA (UnB)

> Documentação técnica detalhada sobre como extrair todas as turmas de graduação da UnB no SIGAA, higienizar os dados e carregá-los no banco de dados **Supabase (PostgreSQL)** sem erros.

---

## 🎯 Sumário Executivo

O pipeline de turmas é composto por três etapas desacopladas:
1. **Extração (Extract):** Navegação automatizada (Selenium Headless) por todos os departamentos de graduação no portal público do SIGAA UnB, coletando ofertas, horários, docentes, vagas e salas. Salva incrementalmente em `data/raw/scraped/sigaa_classes.json`.
2. **Transformação (Transform):** Higienização de horários, remoção de carga horária embutida em nomes de docentes, validação de códigos de disciplinas e formatação padrão. Salva em `data/processed/sigaa_turmas.json`.
3. **Carga (Load):** Ingestão relacional em lote (*batch upsert*) via `psycopg2` na tabela `turmas` do **Supabase**, resolvendo chaves estrangeiras (`materia_id`, `professor_id`) e criando registros básicos (*stubs*) para matérias novas se necessário, garantindo que nenhuma turma seja rejeitada por restrição de chave estrangeira.

---

## 🏗️ Fluxo de Dados (Arquitetura)

```mermaid
flowchart TD
    subgraph SIGAA [Portal Público SIGAA UnB]
        WEB[turmas/listar.jsf\nFormulário de Busca Pública]
    end

    subgraph EXTRACT [1. Extração - Selenium]
        SCRIPTER[src/extractors/sigaa/seed/get_classes.py]
        RAW_JSON[(data/raw/scraped/sigaa_classes.json\nSalvamento incremental)]
    end

    subgraph TRANSFORM [2. Transformação - Sanitização]
        CLEANER[src/transformers/sigaa_cleaner.py\nrun_classes_cleaner()]
        PROCESSED_JSON[(data/processed/sigaa_turmas.json\n6500+ turmas limpas)]
    end

    subgraph LOAD [3. Carga - Supabase PostgreSQL]
        LOADER[src/loaders/postgres_loader.py\nloader_turmas_supabase()]
        DB_MAT[(Tabela: materias)]
        DB_PROF[(Tabela: professores)]
        DB_TURMAS[(Tabela: turmas\nON CONFLICT materia_id, semestre, cod)]
    end

    WEB -->|Raspagem Departamento a Departamento| SCRIPTER
    SCRIPTER -->|Dump bruto| RAW_JSON
    RAW_JSON --> CLEANER
    CLEANER -->|JSON Normalizado| PROCESSED_JSON
    PROCESSED_JSON --> LOADER
    LOADER -.->|Verifica/Cria Materia| DB_MAT
    LOADER -.->|Mapeia Professor| DB_PROF
    LOADER -->|Batch Upsert 200/chunk| DB_TURMAS
```

---

## ⚙️ Configuração do Ambiente (`.env`)

Para comunicação com o Supabase, certifique-se de que o arquivo `.env` na raiz do projeto contenha as credenciais do banco:

```env
DB_HOST=aws-0-sa-east-1.pooler.supabase.com   # Host do Pooler ou Direct Connection
DB_PORT=5432                                  # ou 6543 para Transaction Mode
DB_NAME=postgres
DB_USER=postgres.xxxxxxxxxxxxxxxxxxxx
DB_PASSWORD=sua_senha_segura
```

---

## 🚀 Passo a Passo: Como Rodar

### Etapa 1: Extrair as Turmas do SIGAA (Scraping)

O script principal de raspagem é `src/extractors/sigaa/seed/get_classes.py`.

#### Opção A — Extração Completa de Todos os Departamentos da UnB:
```bash
python src/extractors/sigaa/seed/get_classes.py
```
* **Tempo estimado:** ~6 a 8 minutos (são ~69 departamentos de graduação).
* **Tolerância a falhas:** O script grava no arquivo a cada departamento concluído. Se a conexão cair ou for interrompida, os dados raspados até o momento já estão salvos.
* **Destino:** `data/raw/scraped/sigaa_classes.json`.

#### Opção B — Teste Rápido (apenas os primeiros N departamentos):
```bash
# Testa raspando apenas os 2 primeiros departamentos
python src/extractors/sigaa/seed/get_classes.py --limit-depts 2
```

#### Opção C — Raspagem com Interface Gráfica (Abrir o Chrome visualmente para depurar):
```bash
python src/extractors/sigaa/seed/get_classes.py --no-headless
```

#### Opção D — Raspar apenas departamentos específicos:
```bash
python src/extractors/sigaa/seed/get_classes.py --depts "DEPTO CIÊNCIA DA COMPUTAÇÃO, INSTITUTO DE FÍSICA"
```

#### Opção E — Via Orquestrador Central (`main.py`):
```bash
python main.py --source sigaa --scrape-classes
```

---

### Etapa 2: Higienizar e Normalizar os Dados

Após raspar os dados brutos, execute a limpeza para gerar o arquivo final formatado:

```bash
python -c "from src.transformers.sigaa_cleaner import run_classes_cleaner; run_classes_cleaner()"
```

* **Entrada:** `data/raw/scraped/sigaa_classes.json`
* **Saída:** `data/processed/sigaa_turmas.json`

> [!NOTE]
> Se você precisar carregar a base completa imediatamente sem precisar esperar a raspagem web, utilize o backup existente em `data/backup/sigaa_turmas.json` (que já possui mais de 6.550 turmas completas).
> ```bash
> python -c "from pathlib import Path; from src.transformers.sigaa_cleaner import run_classes_cleaner; run_classes_cleaner(Path('data/backup/sigaa_turmas.json'), Path('data/processed/sigaa_turmas.json'))"
> ```

---

### Etapa 3: Carregar no Banco de Dados Supabase (`postgres_loader.py`)

O script `src/loaders/postgres_loader.py` possui funções dedicadas e flags CLI:

#### Carga Exclusiva das Turmas:
```bash
python src/loaders/postgres_loader.py --turmas
```
* Lê automaticamente de `data/processed/sigaa_turmas.json` (ou usa os backups se o arquivo processado não existir).
* Executa inserções e atualizações em lote (*batch* de 200 registros) em ~5 segundos.

#### Carga de um arquivo JSON específico de turmas:
```bash
python src/loaders/postgres_loader.py --file data/backup/sigaa_turmas.json
```

#### Especificando o Semestre de vigência:
```bash
python src/loaders/postgres_loader.py --turmas --semestre "2026.2"
```

#### Carga com limite para validação rápida:
```bash
python src/loaders/postgres_loader.py --turmas --limit 50
```

#### Carga de Todo o Banco (Campi + Deptos + Matérias + Professores + Turmas):
```bash
# Via postgres_loader direto:
python src/loaders/postgres_loader.py --all

# Ou via main.py:
python main.py --source db
```

---

## 🗄️ Detalhes do Schema do Supabase

A tabela `turmas` possui a seguinte estrutura relacional:

| Coluna | Tipo | Nullable | Descrição / Observação |
| :--- | :--- | :--- | :--- |
| `id` | `VARCHAR` | NÃO | Identificador único UUID v4 |
| `materia_id` | `VARCHAR` | NÃO | Chave estrangeira para `materias(id)` |
| `professor_id`| `VARCHAR` | SIM | Chave estrangeira para `professores(id)` (null se docente não alocado) |
| `semestre` | `VARCHAR` | NÃO | Ex: `"2026.1"`, `"2026.2"` |
| `codigo_turma`| `VARCHAR` | NÃO | Ex: `"01"`, `"02"`, `"A"` |
| `horario_bruto`| `VARCHAR`| NÃO | Ex: `"24M34"`, `"35T12"` |
| `local_sala` | `VARCHAR` | SIM | Ex: `"BSA Sala 10"`, `"PJC BT 02"` |
| `vagas_ofertadas`| `INTEGER`| NÃO | Quantidade total de vagas |
| `vagas_ocupadas` | `INTEGER`| NÃO | Quantidade ocupada (default: 0) |

### 🔒 Restrições Importantes
* **Unique Constraint:** `(materia_id, semestre, codigo_turma)`.
* **Comportamento de Upsert:** Se a turma já existir (mesma matéria, semestre e código), o loader atualiza automaticamente o horário, local, vagas e professor sem duplicar linhas.
* **Auto-resolução de Matérias:** Se a turma referencia uma disciplina cujo código ainda não estava cadastrado na tabela `materias`, o `loader_turmas_supabase` cria automaticamente um registro preliminar para aquela disciplina, associando-a ao departamento respectivo para evitar erros de integridade referencial (*Foreign Key Violation*).

---

## ❓ Perguntas Frequentes & Resolução de Problemas

### 1. "Por que meu arquivo `data/backup/sigaa_classes.json` só tinha 552 linhas?"
O SIGAA lista as turmas por departamento. Uma extração completa percorre ~69 departamentos de graduação. O arquivo `data/backup/sigaa_classes.json` continha apenas o primeiro departamento (`CAMPUS UNB CEILÂNDIA`), indicando que a execução anterior foi interrompida no início. Já o arquivo `data/backup/sigaa_turmas.json` é um backup completo com **6.555 turmas** de todos os departamentos.

### 2. "O SIGAA deu erro de sessão ou timeout durante a raspagem."
O SIGAA utiliza sessões JSF com tempo limite. O script `get_classes.py` possui reconexão automática e tenta novamente até duas vezes caso detecte alerta de sessão expirada. Além disso, como os dados são salvos a cada departamento, mesmo que a execução pare, o progresso anterior é mantido.

### 3. "Como testar se as turmas foram realmente para o Supabase?"
Execute uma consulta rápida via Python:
```bash
python -c "
import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM turmas;')
print('Total de turmas no Supabase:', cur.fetchone()[0])
conn.close()
"
```
