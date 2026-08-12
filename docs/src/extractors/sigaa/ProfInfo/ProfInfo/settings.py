# ==============================================================================
# 🚀 PROFINFO - SCRAPY SETTINGS & PAINEL DE CONTROLE
# ==============================================================================
# Este arquivo contém as configurações do projeto, documentação de cada variável
# e guias práticos para acelerar o bot e monitorar sua performance.
# ==============================================================================

BOT_NAME = "ProfInfo"
SPIDER_MODULES = ["ProfInfo.spiders"]
NEWSPIDER_MODULE = "ProfInfo.spiders"
ADDONS = {}

# ==============================================================================
# ⚙️ 1. CONFIGURAÇÕES BASE E COMPORTAMENTO
# ==============================================================================

# Identificação do bot (User-Agent). Descomente e altere se o servidor bloquear o bot padrão do Scrapy.
#USER_AGENT = "ProfInfo (+http://www.yourdomain.com)"

# Respeitar as regras do arquivo robots.txt do site alvo.
# ALERTA DE VELOCIDADE: Se definido como True, o Scrapy fará uma requisição extra 
# no início para ler o robots.txt. Para máxima velocidade (e se você tiver permissão), mude para False.
ROBOTSTXT_OBEY = True

# Desativar cookies economiza memória, processamento e largura de banda.
# Como as páginas do SIGAA que estamos raspando são públicas, geralmente não precisam de cookies.
# Descomente a linha abaixo para ganhar um pequeno bônus de performance.
#COOKIES_ENABLED = False

# Codificação padrão do arquivo JSON gerado.
FEED_EXPORT_ENCODING = "utf-8"


# ==============================================================================
# 🏎️ 2. GUIA DE ACELERAÇÃO (VELOCIDADE MÁXIMA)
# ==============================================================================
# Ajuste os valores abaixo como se fossem as marchas do seu scraper.

# CONCURRENT_REQUESTS: Quantas requisições o Scrapy pode fazer ao mesmo tempo (Global).
# Padrão é 16. Você aumentou para 32. Se sua internet for rápida e o PC aguentar, tente 64 ou 128.
CONCURRENT_REQUESTS = 32

# CONCURRENT_REQUESTS_PER_DOMAIN: Como estamos raspando apenas o SIGAA (um único domínio),
# esse é o limitador real. Se estiver 16, ele só fará 16 por vez, mesmo que o Global seja 32.
# DICA: Iguale este valor ao CONCURRENT_REQUESTS (ex: 32) para liberar todo o potencial.
CONCURRENT_REQUESTS_PER_DOMAIN = 16

# DOWNLOAD_DELAY: Tempo de espera (em segundos) entre as requisições para o mesmo site.
# Atualmente em 0.25s (4 requisições por segundo por domínio). 
# Para modo turbo, mude para 0.1 ou até 0 (sem limite, disparando o mais rápido possível).
DOWNLOAD_DELAY = 0.25

# AUTOTHROTTLE_ENABLED: Regulador automático de velocidade. 
# Quando False, o Scrapy ignora a carga do servidor e baixa na velocidade máxima bruta ditada acima.
AUTOTHROTTLE_ENABLED = False

# DOWNLOAD_TIMEOUT: Tempo máximo (em segundos) que o Scrapy espera o site responder.
# O padrão é 180s. Você ajustou para 10s, o que é excelente para não prender a fila de requisições.
DOWNLOAD_TIMEOUT = 10 

# DNSCACHE_ENABLED: Mantém o IP do site na memória. 
# Evita que o Scrapy faça uma nova consulta de DNS a cada link. Essencial para velocidade.
DNSCACHE_ENABLED = True

# REACTOR_THREADPOOL_MAXSIZE: (Adicional) Aumenta o número de "trabalhadores" resolvendo DNS.
# Descomente se for usar CONCURRENT_REQUESTS muito altos (acima de 64).
#REACTOR_THREADPOOL_MAXSIZE = 20


# ==============================================================================
# 📊 3. GUIA DE MÉTRICAS E MONITORAMENTO
# ==============================================================================
# O Scrapy emite métricas automaticamente. O nível de log define o que você vê no terminal.
# Níveis disponíveis: CRITICAL, ERROR, WARNING, INFO, DEBUG.

# LOG_LEVEL: 
# - Use "INFO" (atual) para ver o status geral e o logstats.
# - Use "DEBUG" se o bot travar e você quiser ver cada link sendo baixado.
# - Use "WARNING" para MÁXIMA VELOCIDADE. Isso desliga os prints no terminal (prints gastam CPU),
#   mostrando apenas erros críticos e o relatório final.
LOG_LEVEL = "WARNING"

# 🔎 COMO LER AS MÉTRICAS NO TERMINAL (Quando LOG_LEVEL = "INFO"):
# 1. LOGSTATS (A cada 1 minuto):
#    Você verá linhas como: "Crawled 300 pages (at 300 pages/min), scraped 150 items (at 150 items/min)"
#    Isso é o seu velocímetro em tempo real.
#
# 2. ESTATÍSTICAS FINAIS (Dumping Scrapy stats):
#    Ao terminar, o Scrapy exibe um bloco com informações cruciais:
#    - 'elapsed_time_seconds': Tempo total da raspagem.
#    - 'downloader/request_count': Total de requisições enviadas.
#    - 'httperror/response_ignored_count': Quantas páginas deram erro (ex: 404).
#    - 'item_scraped_count': Quantos professores foram efetivamente salvos no JSON.


# ==============================================================================
# 🎭 4. INTEGRAÇÃO SCRAPY-PLAYWRIGHT (JAVASCRIPT)
# ==============================================================================
# Configurações para a biblioteca Scrapy-Playwright (se houver alguma spider que exija renderizar JS).
# OBS: A spider 'info_spider_oficial' atual não utiliza Playwright, mas a config está pronta caso precise.

PLAYWRIGHT_BROWSER_TYPE = "chromium"

PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,  # Mude para False se quiser visualizar o navegador "fantasma" abrindo na tela.
    #"slow_mo": 4000 # Mude para Visualizar o navegador de forma devagar
}

# PLAYWRIGHT_MAX_PAGES_PER_CONTEXT = 8