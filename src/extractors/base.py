from abc import ABC, abstractmethod
from typing import Any, Optional

class BaseExtractor(ABC):
    """
    Contrato base para todos os extratores de dados do UnBook 2.0.
    Garante que todas as Squads sigam o mesmo padrão de execução.
    """
    
    @abstractmethod
    def extract(self, limit: Optional[int] = None) -> Any:
        """
        Lógica principal de captura de dados.
        Deve retornar os dados brutos ou o caminho do arquivo gerado.
        """
        pass