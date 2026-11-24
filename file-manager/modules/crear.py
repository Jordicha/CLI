"""Crear carpetas.

Creación de directorios individuales o por lotes, con la misma
protección de rutas que el resto de operaciones.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

from modules._resultado import Resultado
from utils.interfaz import Interfaz
from utils.logger import Logger
from utils.seguridad import Seguridad

log = Logger.obtener("crear")


class Crear:
    """Creación segura de directorios."""

    def __init__(self, seguridad: Seguridad, interfaz: Optional[Interfaz] = None) -> None:
        self.seguridad = seguridad
        self.interfaz = interfaz or Interfaz()

    def crear(self, rutas: Sequence[str]) -> Resultado:
        """Crea las carpetas indicadas (con Padres intermedios tipo ``mkdir -p``)."""
        resultado = Resultado()
        for r in rutas:
            try:
                ruta = Path(r).expanduser()
                self.seguridad.comprobar_permitido(ruta)
                if ruta.exists():
                    tipo = "carpeta" if ruta.is_dir() else "archivo"
                    self.interfaz.aviso(f"Ya existe esa {tipo}: {ruta}")
                    resultado.omitidos += 1
                    continue
                if self.seguridad.dry_run:
                    self.interfaz.simulacion(f"Crear carpeta: {ruta}")
                else:
                    ruta.mkdir(parents=True, exist_ok=True)
                    self.interfaz.ok(f"Carpeta creada: {ruta}")
                log.info("CREADA %s", ruta)
                resultado.ok()
            except PermissionError as exc:
                self.interfaz.error(str(exc))
                resultado.errores += 1
            except OSError as exc:
                self.interfaz.error(f"Error al crear {r}: {exc}")
                resultado.errores += 1
        return resultado

    def menu_interactivo(self) -> None:
        """Flujo interactivo de creación de carpetas."""
        self.interfaz.encabezado("CREAR CARPETA")
        rutas = Interfaz.pedir_ruta("Carpeta(s) a crear (separadas por espacios)").split()
        res = self.crear(rutas)
        self.interfaz.resumen(res.exito, res.omitidos, res.errores)
