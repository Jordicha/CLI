"""Módulos funcionales del gestor de archivos.

Cada módulo expone una clase con la lógica de una operación
(mover, borrar, organizar, renombrar, buscar, información, crear)
y un método ``menu_interactivo`` para el modo menú.
"""

from modules._resultado import Resultado
from modules.mover import Mover
from modules.borrar import Borrar
from modules.organizar import Organizar
from modules.renombrar import Renombrar
from modules.buscar import Buscar
from modules.informacion import Informacion
from modules.crear import Crear

__all__ = [
    "Resultado",
    "Mover",
    "Borrar",
    "Organizar",
    "Renombrar",
    "Buscar",
    "Informacion",
    "Crear",
]
