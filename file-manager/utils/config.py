"""Configuración centralizada y fábricas de objetos a partir de ella."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Optional, Tuple

from utils.seguridad import Seguridad

ARCHIVO_ENV = ".env"
MODELO_POR_DEFECTO = "gpt-4o-mini"
URL_CHAT = "https://api.openai.com/v1/chat/completions"
TIMEOUT_POR_DEFECTO = 8.0


def cargar_env(ruta: Optional[Path] = None) -> None:
    """Carga un ``.env`` sencillo sin sobrescribir variables ya definidas."""
    if ruta is None:
        candidatas = (
            Path.cwd() / ARCHIVO_ENV,
            Path(__file__).resolve().parent.parent / ARCHIVO_ENV,
        )
        ruta = next((r for r in candidatas if r.exists()), candidatas[1])
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        texto = linea.strip()
        if not texto or texto.startswith("#") or "=" not in texto:
            continue
        clave, valor = texto.split("=", 1)
        clave, valor = clave.strip(), valor.strip().strip("'\"")
        if clave and clave not in os.environ:
            os.environ[clave] = valor


@dataclass(frozen=True)
class Config:
    """Valores de ejecución compartidos por CLI, motor y proveedor IA."""

    dry_run: bool = False
    restringido: bool = False
    rutas_permitidas: Tuple[str, ...] = ()
    papelera: Optional[str] = None
    sin_ia: bool = False
    clave_ia: str = ""
    modelo_ia: str = MODELO_POR_DEFECTO
    timeout_ia: float = TIMEOUT_POR_DEFECTO
    url_ia: str = URL_CHAT
    archivo_acciones: Optional[str] = None

    @classmethod
    def desde_env(cls, ruta: Optional[Path] = None) -> "Config":
        """Construye la configuración leyendo el entorno y un ``.env``."""
        cargar_env(ruta)
        try:
            timeout = float(
                os.environ.get("IA_TIMEOUT", TIMEOUT_POR_DEFECTO) or TIMEOUT_POR_DEFECTO
            )
        except (TypeError, ValueError):
            timeout = TIMEOUT_POR_DEFECTO
        return cls(
            clave_ia=os.environ.get("OPENAI_API_KEY", "").strip(),
            modelo_ia=os.environ.get("IA_MODELO", "").strip() or MODELO_POR_DEFECTO,
            timeout_ia=timeout if timeout > 0 else TIMEOUT_POR_DEFECTO,
            url_ia=os.environ.get("OPENAI_BASE_URL", "").strip() or URL_CHAT,
        )

    @classmethod
    def desde_args(cls, args: argparse.Namespace) -> "Config":
        """Combina el entorno con las opciones de la línea de comandos."""
        base = cls.desde_env()
        return replace(
            base,
            dry_run=bool(getattr(args, "dry_run", False)),
            restringido=bool(getattr(args, "restringido", False)),
            rutas_permitidas=tuple(getattr(args, "permitido", None) or ()),
            papelera=getattr(args, "papelera", None),
            sin_ia=bool(getattr(args, "sin_ia", False)),
            archivo_acciones=getattr(args, "archivo", None),
        )

    def crear_seguridad(self, confirmador=None) -> Seguridad:
        """Crea la capa de seguridad configurada."""
        return Seguridad.desde_config(self, confirmador)
