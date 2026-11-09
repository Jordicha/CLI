"""Búsqueda de archivos y carpetas.

Permite buscar por nombre (con comodines o texto), por extensión,
por tamaño (``>=10MB``, ``<=1GB``, rangos) y por fecha de modificación
(``>YYYY-MM-DD``, ``<YYYY-MM-DD``).
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

from utils.interfaz import Interfaz
from utils.logger import Logger
from utils.seguridad import Seguridad

log = Logger.obtener("buscar")

_UNIDADES = {"b": 1, "kb": 1024, "mb": 1024**2, "gb": 1024**3, "tb": 1024**4}


def parsear_tamano(texto: str) -> int:
    """Convierte '10MB', '1.5 gb', '500' a bytes.

    Raises:
        ValueError: si el formato no es válido.
    """
    t = texto.strip().lower().replace(" ", "")
    m = re.fullmatch(r"([\d.]+)([kmgt]?b)?", t)
    if not m:
        raise ValueError(f"Tamaño no válido: {texto!r} (usa p. ej. 10MB, 1.5GB)")
    valor = float(m.group(1))
    unidad = (m.group(2) or "b").lower()
    return int(valor * _UNIDADES[unidad])


def parsear_fecha(texto: str) -> datetime:
    """Convierte 'YYYY-MM-DD' en datetime a medianoche.

    Raises:
        ValueError: si el formato no es válido.
    """
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(texto.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f"Fecha no válida: {texto!r} (usa AAAA-MM-DD)")


class Buscar:
    """Motor de búsqueda sobre el sistema de archivos."""

    def __init__(self, seguridad: Seguridad, interfaz: Optional[Interfaz] = None) -> None:
        self.seguridad = seguridad
        self.interfaz = interfaz or Interfaz()

    # ------------------------------------------------------------------ #
    def buscar(
        self,
        patron: Optional[str] = None,
        extension: Optional[str] = None,
        tamano: Optional[str] = None,
        modificado: Optional[str] = None,
        ruta: str = ".",
        tipo: str = "archivo",  # archivo | carpeta | todo
        max_resultados: int = 200,
    ) -> List[Path]:
        """Busca archivos/carpetas que cumplan todos los criterios dados.

        Args:
            patron: Texto o comodín a buscar en el nombre (sin distinción de
                mayúsculas).
            extension: Extensión, con o sin punto (``pdf`` o ``.pdf``).
            tamano: Criterio de tamaño: ``>=10MB``, ``<=1GB``, ``1MB-500MB``.
            modificado: ``>2024-01-01``, ``<2024-12-31`` o ``ultimo-7dias``.
            ruta: Directorio raíz de búsqueda.
            tipo: ``archivo``, ``carpeta`` o ``todo``.
            max_resultados: Límite de resultados mostrados.

        Returns:
            Lista de rutas encontradas.
        """
        try:
            base = self.seguridad.validar_existente(ruta, "el directorio de busqueda")
            self.seguridad.comprobar_permitido(base)
        except (FileNotFoundError, PermissionError) as exc:
            self.interfaz.error(str(exc))
            return []

        min_t, max_t = self._rango_tamano(tamano)
        min_f, max_f = self._rango_fecha(modificado)
        patron_re = self._patron_a_regex(patron) if patron else None
        extension = f".{extension.lower().lstrip('.')}" if extension else None

        resultados: List[Path] = []
        for item in self._recorrer(base):
            if tipo == "archivo" and not item.is_file():
                continue
            if tipo == "carpeta" and not item.is_dir():
                continue
            if patron_re and not patron_re.search(item.name):
                continue
            if extension and item.suffix.lower() != extension:
                continue
            if min_t is not None or max_t is not None:
                if not item.is_file():
                    continue
                try:
                    tam = item.stat().st_size
                except OSError:
                    continue
                if min_t is not None and tam < min_t:
                    continue
                if max_t is not None and tam > max_t:
                    continue
            if min_f is not None or max_f is not None:
                try:
                    mtime = datetime.fromtimestamp(item.stat().st_mtime)
                except OSError:
                    continue
                if min_f is not None and mtime < min_f:
                    continue
                if max_f is not None and mtime > max_f:
                    continue
            resultados.append(item)
            if len(resultados) >= max_resultados:
                self.interfaz.aviso(
                    f"Mostrando solo los primeros {max_resultados} resultados."
                )
                break

        self._mostrar(resultados, base)
        log.info(
            "BUSQUEDA patron=%s ext=%s tam=%s fecha=%s base=%s -> %d",
            patron, extension, tamano, modificado, base, len(resultados),
        )
        return resultados

    # ------------------------------------------------------------------ #
    # Auxiliares de criterios
    # ------------------------------------------------------------------ #
    @staticmethod
    def _patron_a_regex(patron: str) -> "re.Pattern[str]":
        """Convierte el patrón en regex: comodines literales o búsqueda de texto."""
        if any(c in patron for c in "*?["):
            return re.compile(fnmatch_to_regex(patron), re.IGNORECASE)
        return re.compile(re.escape(patron), re.IGNORECASE)

    @staticmethod
    def _rango_tamano(tamano: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
        if not tamano:
            return None, None
        t = tamano.replace(" ", "").lower()
        m = re.fullmatch(
            r">=([\d.]+[kmgt]?b)|<=([\d.]+[kmgt]?b)|>([\d.]+[kmgt]?b)"
            r"|<([\d.]+[kmgt]?b)|([\d.]+[kmgt]?b)-([\d.]+[kmgt]?b)",
            t,
        )
        if not m:
            raise ValueError(
                f"Criterio de tamaño no válido: {tamano!r}. "
                "Ejemplos: >=10MB, <=1GB, 1MB-500MB"
            )
        if m.group(1):
            return parsear_tamano(m.group(1)), None
        if m.group(2):
            return None, parsear_tamano(m.group(2))
        if m.group(3):
            return parsear_tamano(m.group(3)) + 1, None
        if m.group(4):
            return None, parsear_tamano(m.group(4)) - 1
        return parsear_tamano(m.group(5)), parsear_tamano(m.group(6))

    @staticmethod
    def _rango_fecha(fecha: Optional[str]) -> Tuple[Optional[datetime], Optional[datetime]]:
        if not fecha:
            return None, None
        f = fecha.replace(" ", "").lower()
        if f.startswith("ultimo-") or f.startswith("ultim-"):
            dias = int(re.search(r"(\d+)", f).group(1))  # type: ignore[union-attr]
            return datetime.now() - timedelta(days=dias), None
        if f.startswith(">="):
            return parsear_fecha(f[2:]), None
        if f.startswith("<="):
            return None, parsear_fecha(f[2:]) + timedelta(days=1)
        if f.startswith(">"):
            return parsear_fecha(f[1:]) + timedelta(days=1), None
        if f.startswith("<"):
            return None, parsear_fecha(f[1:])
        # Fecha exacta: todo ese día
        d = parsear_fecha(f)
        return d, d + timedelta(days=1)

    # ------------------------------------------------------------------ #
    # Recorrido y presentación
    # ------------------------------------------------------------------ #
    @staticmethod
    def _recorrer(base: Path) -> Iterator[Path]:
        """Itera recursivamente sin seguir enlaces simbólicos (evita bucles)."""
        for raiz, dirs, archivos in _walk(base):
            for d in dirs:
                yield Path(raiz) / d
            for a in archivos:
                yield Path(raiz) / a

    def _mostrar(self, resultados: List[Path], base: Path) -> None:
        if not resultados:
            self.interfaz.aviso("No se encontraron resultados.")
            return
        filas = []
        for item in resultados:
            icono = (
                "[blue][D][/blue]" if item.is_dir() else "[white][F][/white]"
            )
            try:
                tam = _tamano_legible(item.stat().st_size) if item.is_file() else "-"
                mod = datetime.fromtimestamp(item.stat().st_mtime).strftime(
                    "%Y-%m-%d %H:%M"
                )
            except OSError:
                tam, mod = "-", "-"
            filas.append([icono, item.name, str(item.parent), tam, mod])
        self.interfaz.tabla(
            f"Resultados ({len(resultados)} en {base})",
            ["Tipo", "Nombre", "Directorio", "Tamaño", "Modificado"],
            filas,
        )

    # ------------------------------------------------------------------ #
    def menu_interactivo(self) -> None:
        """Flujo interactivo de búsqueda."""
        self.interfaz.encabezado("BUSCAR ARCHIVOS")
        patron = Interfaz.pedir_ruta("Patrón/texto a buscar")
        extension = Interfaz.preguntar("Extension (opcional)", valor_por_defecto="")
        tamano = Interfaz.preguntar("Tamaño (opcional, ej: >=10MB)", valor_por_defecto="")
        modificado = Interfaz.preguntar(
            "Modificado despues de (opcional, YYYY-MM-DD)", valor_por_defecto=""
        )
        ruta = Interfaz.preguntar("Donde buscar", valor_por_defecto=".")
        try:
            self.buscar(
                patron=patron or None,
                extension=extension or None,
                tamano=tamano or None,
                modificado=modificado or None,
                ruta=ruta,
            )
        except ValueError as exc:
            self.interfaz.error(str(exc))


# ---------------------------------------------------------------------- #
# Utilidades de módulo
# ---------------------------------------------------------------------- #
def fnmatch_to_regex(patron: str) -> str:
    """Convierte un patrón con comodines estilo shell a regex."""
    i, n, res = 0, len(patron), ""
    while i < n:
        c = patron[i]
        i += 1
        if c == "*":
            if i < n and patron[i] == "*":
                i += 1
            res += ".*"
        elif c == "?":
            res += "."
        elif c == "[":
            j = i
            if j < n and patron[j] == "!":
                j += 1
            if j < n and patron[j] == "]":
                j += 1
            while j < n and patron[j] != "]":
                j += 1
            if j >= n:
                res += "\\["
            else:
                cls = patron[i:j].replace("\\", "\\\\")
                i = j + 1
                res += f"[{cls}]"
        else:
            res += re.escape(c)
    return f"(?s:{res})\\Z"


def _walk(base: Path):
    """os.walk seguro que no sigue enlaces simbólicos."""
    import os

    yield from os.walk(base, followlinks=False)


def _tamano_legible(bytes_: int) -> str:
    for unidad in ("B", "KB", "MB", "GB", "TB"):
        if bytes_ < 1024 or unidad == "TB":
            return f"{bytes_:.1f} {unidad}" if unidad != "B" else f"{bytes_} B"
        bytes_ /= 1024
    return f"{bytes_:.1f} TB"
