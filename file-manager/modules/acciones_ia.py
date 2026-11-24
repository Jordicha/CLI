"""Pasos de acciones que usan el proveedor IA y sus alternativas sin red."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from modules._resultado import Resultado
from modules.mover import Mover
from modules.organizar import CATEGORIAS, CATEGORIA_OTROS, Organizar
from modules.renombrar import Renombrar
from utils.config import Config
from utils.errores import IAError
from utils.ia import IA
from utils.interfaz import Interfaz
from utils.seguridad import Seguridad


class PasosIA:
    """Clasificación y renombrado asistidos por IA, con fallback controlado."""

    def __init__(
        self,
        seguridad: Seguridad,
        config: Optional[Config] = None,
        interfaz: Optional[Interfaz] = None,
    ) -> None:
        self.seguridad = seguridad
        self.config = config or Config.desde_env()
        self.interfaz = interfaz or Interfaz()

    @classmethod
    def desde_config(
        cls, config: Config, seguridad: Seguridad, interfaz: Optional[Interfaz] = None
    ) -> "PasosIA":
        """Fábrica de pasos IA a partir de la configuración compartida."""
        return cls(seguridad, config, interfaz)

    @staticmethod
    def _expandir(origenes: Any) -> List[str]:
        ampliadas: List[str] = []
        for r in origenes:
            texto = str(r)
            if any(c in texto for c in "*?["):
                coincidencias = sorted(str(p) for p in Path(".").glob(texto))
                if coincidencias:
                    ampliadas.extend(coincidencias)
                    continue
            ampliadas.append(texto)
        return ampliadas

    @classmethod
    def _requerir_lista(
        cls, args: Dict[str, Any], clave: str, interfaz: Interfaz
    ) -> Optional[List[str]]:
        valor = args.get(clave) or args.get("valor")
        if valor is None:
            interfaz.error(f"Falta el parametro '{clave}'.")
            return None
        if isinstance(valor, str):
            valor = [valor]
        if not isinstance(valor, list) or not valor:
            interfaz.error(f"'{clave}' debe ser una lista no vacia.")
            return None
        return cls._expandir(valor)

    def _aviso_sin_ia(self, motivo: str) -> None:
        self.interfaz.aviso(
            f"IA no disponible ({motivo}). Se continúa sin IA; "
            "define OPENAI_API_KEY en .env para activarla."
        )

    def _mapa_ia(
        self, sistema: str, usuario: str, permitidos: Set[str]
    ) -> Optional[Dict[str, str]]:
        try:
            datos = IA.desde_config(self.config).json(sistema, usuario)
        except IAError as exc:
            self._aviso_sin_ia(str(exc))
            return None
        if not datos:
            self.interfaz.aviso("La IA no devolvió propuestas; se continúa sin IA.")
            return None
        mapa: Dict[str, str] = {}
        for clave, valor in datos.items():
            nombre = Path(str(clave)).name
            if nombre in permitidos and isinstance(valor, str):
                mapa[nombre] = valor
        return mapa

    def clasificar(self, args: Dict[str, Any], forzar: bool) -> Resultado:
        """Clasifica archivos con IA; sin IA usa la clasificación local."""
        resultado = Resultado()
        base = Path(args.get("directorio") or ".").expanduser()
        if not base.is_dir():
            self.interfaz.error(f"No existe el directorio: {base}")
            resultado.errores += 1
            return resultado
        archivos = sorted(
            p for p in base.glob(args.get("patron") or "*") if p.is_file()
        )[: args.get("max", 20)]
        if not archivos:
            self.interfaz.aviso("No hay archivos para clasificar con IA.")
            return resultado
        categorias = list(CATEGORIAS) + [CATEGORIA_OTROS]
        sistema = (
            "Clasificas archivos por su nombre. Responde SOLO con un objeto JSON "
            "que mapee cada nombre recibido a UNA de estas categorías: "
            + ", ".join(categorias)
            + ". No inventes claves, no uses rutas y no expliques la respuesta."
        )
        usuario = json.dumps(
            {"archivos": [p.name for p in archivos]}, ensure_ascii=False
        )
        mapa = self._mapa_ia(sistema, usuario, {p.name for p in archivos})
        if mapa is None:
            self.interfaz.aviso("Clasificación local por extensión (sin IA).")
            return Organizar(self.seguridad).organizar(str(base), criterio="extension")
        if not self.seguridad.confirmar(
            f"La IA propone clasificar {len(mapa)} archivo(s). ¿Aplicar?", forzar=forzar
        ):
            self.interfaz.info("Cancelado: no se han movido archivos.")
            resultado.omitidos += len(mapa)
            return resultado
        for nombre, categoria in mapa.items():
            if categoria not in categorias:
                self.interfaz.aviso(
                    f"Categoría desconocida para {nombre}: {categoria}"
                )
                resultado.omitidos += 1
                continue
            parcial = Mover(self.seguridad).mover(
                [str(base / nombre)],
                str(base / categoria),
                crear_destino=True,
                no_sobrescribir=True,
                forzar=forzar,
            )
            resultado.exito += parcial.exito
            resultado.omitidos += parcial.omitidos
            resultado.errores += parcial.errores
        return resultado

    def renombrar(self, args: Dict[str, Any], forzar: bool) -> Resultado:
        """Propone nombres con IA; sin IA omite el paso y avisa."""
        vacio = Resultado()
        rutas = self._requerir_lista(args, "rutas", self.interfaz)
        if not rutas:
            return vacio
        archivos = [p for p in (Path(r).expanduser() for r in rutas) if p.is_file()]
        archivos = archivos[: args.get("max", 20)]
        if not archivos:
            self.interfaz.aviso("No hay archivos para renombrar con IA.")
            return Resultado()
        por_nombre = {p.name: p for p in archivos}
        resultado = Resultado()
        sistema = (
            "Propones nombres de archivo claros y breves. Responde SOLO con un "
            "objeto JSON que mapee cada nombre recibido a un nuevo nombre. "
            "Conserva la extensión y no uses rutas ni barras."
        )
        usuario = json.dumps({"archivos": list(por_nombre)}, ensure_ascii=False)
        mapa = self._mapa_ia(sistema, usuario, set(por_nombre))
        if mapa is None:
            self.interfaz.aviso(
                f"Sin IA no hay propuestas de nombre; se omiten {len(archivos)} archivo(s)."
            )
            resultado.omitidos += len(archivos)
            return resultado
        validados: Dict[str, str] = {}
        usados: Set[str] = set()
        for original, nuevo in mapa.items():
            if (
                not nuevo
                or Path(nuevo).name != nuevo
                or "/" in nuevo
                or "\\" in nuevo
                or nuevo in (".", "..")
                or Path(nuevo).suffix.lower() != Path(original).suffix.lower()
                or nuevo in usados
            ):
                self.interfaz.aviso(
                    f"Nombre propuesto descartado para {original}: {nuevo}"
                )
                resultado.omitidos += 1
                continue
            validados[original] = nuevo
            usados.add(nuevo)
        if not validados:
            return resultado
        if not self.seguridad.confirmar(
            f"La IA propone renombrar {len(validados)} archivo(s). ¿Aplicar?", forzar=forzar
        ):
            self.interfaz.info("Cancelado: no se han renombrado archivos.")
            resultado.omitidos += len(validados)
            return resultado
        renombrar = Renombrar(self.seguridad)
        for original, nuevo in validados.items():
            parcial = renombrar.renombrar(str(por_nombre[original]), nuevo, forzar=forzar)
            resultado.exito += parcial.exito
            resultado.omitidos += parcial.omitidos
            resultado.errores += parcial.errores
        return resultado
