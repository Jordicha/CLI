"""Capa IA opcional basada en la API de OpenAI.

Solo se envían nombres de archivo: nunca contenidos ni rutas absolutas.
La clave se lee de ``OPENAI_API_KEY`` (entorno o ``.env``) y no se registra.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from utils.errores import IAError
from utils.logger import Logger

log = Logger.obtener("ia")

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


def configuracion() -> Dict[str, Any]:
    """Devuelve la configuración de IA con valores por defecto seguros."""
    cargar_env()
    try:
        timeout = float(
            os.environ.get("IA_TIMEOUT", TIMEOUT_POR_DEFECTO) or TIMEOUT_POR_DEFECTO
        )
    except (TypeError, ValueError):
        timeout = TIMEOUT_POR_DEFECTO
    return {
        "clave": os.environ.get("OPENAI_API_KEY", "").strip(),
        "modelo": os.environ.get("IA_MODELO", "").strip() or MODELO_POR_DEFECTO,
        "url": os.environ.get("OPENAI_BASE_URL", "").strip() or URL_CHAT,
        "timeout": timeout if timeout > 0 else TIMEOUT_POR_DEFECTO,
    }


def limpiar_json(texto: str) -> str:
    """Elimina cercos de código Markdown de una respuesta JSON."""
    resultado = texto.strip()
    if resultado.startswith("```"):
        resultado = resultado.strip("`").strip()
        if resultado.lower().startswith("json"):
            resultado = resultado[4:].strip()
    return resultado


class IA:
    """Cliente mínimo de OpenAI para tareas pequeñas sobre nombres de archivo."""

    def __init__(self, sin_red: bool = False) -> None:
        self.sin_red = sin_red

    def disponible(self) -> Tuple[bool, str]:
        """Indica si se puede llamar a la API y el motivo en caso contrario."""
        if self.sin_red:
            return False, "modo --sin-ia activo"
        if not configuracion()["clave"]:
            return False, "falta OPENAI_API_KEY en .env"
        return True, ""

    def json(self, sistema: str, usuario: str) -> Dict[str, Any]:
        """Pide a la IA un objeto JSON y lo devuelve ya parseado."""
        disponible, motivo = self.disponible()
        if not disponible:
            raise IAError(motivo)
        conf = configuracion()
        cuerpo = {
            "model": conf["modelo"],
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": sistema},
                {"role": "user", "content": usuario},
            ],
        }
        peticion = urllib.request.Request(
            conf["url"],
            data=json.dumps(cuerpo).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {conf['clave']}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(peticion, timeout=conf["timeout"]) as respuesta:
                contenido = respuesta.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raise IAError(f"la API respondió HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise IAError(f"sin conexión con la API ({type(exc).__name__})") from exc
        try:
            respuesta_json = json.loads(contenido)
            texto = respuesta_json["choices"][0]["message"]["content"]
            datos = json.loads(limpiar_json(texto))
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise IAError("la IA no devolvió un JSON válido") from exc
        if not isinstance(datos, dict):
            raise IAError("la IA no devolvió un objeto JSON")
        log.info("IA respuesta recibida (%d entradas)", len(datos))
        return datos
