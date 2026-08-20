import logging
import sys

class ColorFormatter(logging.Formatter):
    """Formatter customizado para adicionar cores ANSI aos logs no terminal."""
    
    # Códigos de cor ANSI 
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    def format(self, record):
        message = record.getMessage()
        
        # Define a cor da mensagem baseada no nível ou no conteúdo
        if record.levelno >= logging.ERROR:
            msg_color = self.RED
            level_color = self.RED
        elif record.levelno == logging.WARNING:
            msg_color = self.YELLOW
            level_color = self.YELLOW
        else:
            level_color = self.BLUE
            # Regras customizadas para pintar a linha dependendo do contexto
            if "✅" in message or "🏁" in message:
                msg_color = self.GREEN
            elif "TESTE" in message:
                msg_color = self.YELLOW
            elif "🚀" in message or "🎓" in message or "💬" in message:
                msg_color = self.CYAN + self.BOLD
            elif "acessando" in message.lower() or "carregando" in message.lower():
                msg_color = self.MAGENTA # Cor específica para ações de "carregamento/leitura"
            else:
                msg_color = self.RESET

        # Monta a string final misturando as cores
        format_str = (
            f"{self.RESET}%(asctime)s {self.RESET}| "
            f"{level_color}%(levelname)-7s{self.RESET} | "
            f"{self.BOLD}%(name)-15s{self.RESET} | "
            f"{msg_color}%(message)s{self.RESET}"
        )
        
        # Data simplificada para deixar o terminal mais limpo (apenas hora)
        formatter = logging.Formatter(fmt=format_str, datefmt="%H:%M:%S")
        return formatter.format(record)


def get_logger(name: str = "UnBook") -> logging.Logger:
    """
    Retorna uma instância configurada do logger padrão do projeto com cores.
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ColorFormatter())
        logger.addHandler(console_handler)
        
    return logger