# Inicializar el módulo de agentes
from .camilo import Camilo, CamiloAgent
from .valentina import Valentina, ValentinaAgent
from .pipe import Pipe, PipeAgent
from .adriana import Adriana, AdrianaAgent

__all__ = [
    'Camilo', 'Valentina', 'Pipe', 'Adriana',
    'CamiloAgent', 'ValentinaAgent', 'PipeAgent', 'AdrianaAgent'
]
