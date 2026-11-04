"""Registro de operaciones del gestor de archivos.

Configura el módulo ``logging`` para escribir en:
- Un archivo rotativo ``logs/file-manager.log`` con todas las operaciones.
- Consola solo avisos e importantes (los detalles van al log).
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "file-manager.log"

_FORMATO = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


class Logger:
    """Fachada de configuración y acceso al logging de la aplicación."""

    _configurado = False

    @classmethod
    def configurar(cls, nivel: int = logging.INFO) -> None:
        """Configura los handlers de archivo y consola (idempotente)."""
        if cls._configurado:
            return
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        raiz = logging.getLogger("filemanager")
        raiz.setLevel(logging.DEBUG)

        archivo = RotatingFileHandler(
            LOG_FILE, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
        )
        archivo.setLevel(logging.DEBUG)
        archivo.setFormatter(logging.Formatter(_FORMATO))
        raiz.addHandler(archivo)

        consola = logging.StreamHandler()
        consola.setLevel(logging.WARNING)
        consola.setFormatter(logging.Formatter(_FORMATO))
        raiz.addHandler(consola)

        cls._configurado = True

    @classmethod
    def obtener(cls, nombre: str = "app") -> logging.Logger:
        """Devuelve el logger jerárquico ``filemanager.<nombre>``."""
        cls.configurar()
        return logging.getLogger(f"filemanager.{nombre}")

    @classmethod
    def ruta_log(cls) -> Path:
        """Devuelve la ruta del archivo de log principal."""
        return LOG_FILE
