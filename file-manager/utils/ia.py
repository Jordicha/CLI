"""Proveedor IA opcional: cliente OpenAI configurado desde :mod:`utils.config`."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple

from utils.config import Config
from utils.errores import IAError
from utils.logger import Logger

log = Logger.obtener("ia")


class IA:
    """Cliente mínimo de OpenAI para tareas sobre nombres de archivo."""

    def __init__(self, config: Optional[Config] = None) -> None:
        conf = config or Config.desde_env()
        self.sin_red = conf.sin_ia
        self.clave = conf.clave_ia
        self.modelo = conf.modelo_ia
        self.url = conf.url_ia
        self.timeout = conf.timeout_ia

    @classmethod
    def desde_config(cls, config: Optional[Config] = None) -> "IA":
        """Fábrica del proveedor a partir de la configuración compartida."""
        return cls(config)

    @staticmethod
    def limpiar_json(texto: str) -> str:
        """Elimina cercos de código Markdown de una respuesta JSON."""
        resultado = texto.strip()
        if resultado.startswith("```"):
            resultado = resultado.strip("`").strip()
            if resultado.lower().startswith("json"):
                resultado = resultado[4:].strip()
        return resultado

    def disponible(self) -> Tuple[bool, str]:
        """Indica si se puede llamar a la API y el motivo en caso contrario."""
        if self.sin_red:
            return False, "modo --sin-ia activo"
        if not self.clave:
            return False, "falta OPENAI_API_KEY en .env"
        return True, ""

    def json(self, sistema: str, usuario: str) -> Dict[str, Any]:
        """Pide a la IA un objeto JSON y lo devuelve ya parseado."""
        disponible, motivo = self.disponible()
        if not disponible:
            raise IAError(motivo)
        cuerpo = {
            "model": self.modelo,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": sistema},
                {"role": "user", "content": usuario},
            ],
        }
        peticion = urllib.request.Request(
            self.url,
            data=json.dumps(cuerpo).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.clave}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(peticion, timeout=self.timeout) as respuesta:
                contenido = respuesta.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raise IAError(f"la API respondió HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise IAError(f"sin conexión con la API ({type(exc).__name__})") from exc
        try:
            respuesta_json = json.loads(contenido)
            texto = respuesta_json["choices"][0]["message"]["content"]
            datos = json.loads(self.limpiar_json(texto))
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise IAError("la IA no devolvió un JSON válido") from exc
        if not isinstance(datos, dict):
            raise IAError("la IA no devolvió un objeto JSON")
        log.info("IA respuesta recibida (%d entradas)", len(datos))
        return datos
