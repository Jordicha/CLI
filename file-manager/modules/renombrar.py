"""Renombrar archivos.

Permite renombrar archivos individuales, aplicar patrones con
expresiones regulares, añadir prefijos/sufijos y numerar archivos.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Optional, Sequence

from modules._resultado import Resultado
from utils.interfaz import Interfaz
from utils.logger import Logger
from utils.seguridad import Seguridad

log = Logger.obtener("renombrar")


class Renombrar:
    """Operaciones de renombrado seguras sobre archivos."""

    def __init__(self, seguridad: Seguridad, interfaz: Optional[Interfaz] = None) -> None:
        self.seguridad = seguridad
        self.interfaz = interfaz or Interfaz()

    # ------------------------------------------------------------------ #
    # API pública
    # ------------------------------------------------------------------ #
    def renombrar(self, origen: str, nuevo_nombre: str, forzar: bool = False) -> Resultado:
        """Renombra un archivo individual (``mv nombre viejo nuevo``)."""
        resultado = Resultado()
        try:
            ruta = self.seguridad.validar_existente(origen, "archivo")
            self.seguridad.comprobar_permitido(ruta)
            if "/" in nuevo_nombre or "\\" in nuevo_nombre:
                destino = ruta.parent / nuevo_nombre
                destino.parent.mkdir(parents=True, exist_ok=True)
            else:
                destino = ruta.parent / nuevo_nombre
            self._ejecutar(ruta, destino, forzar, resultado)
        except (FileNotFoundError, PermissionError) as exc:
            self.interfaz.error(str(exc))
            resultado.errores += 1
        return resultado

    def prefijo(
        self, rutas: Sequence[str], prefijo: str, forzar: bool = False
    ) -> Resultado:
        """Añade un prefijo al nombre de varios archivos."""
        return self._por_lote(rutas, lambda p: p.parent / f"{prefijo}{p.name}", forzar)

    def sufijo(
        self, rutas: Sequence[str], sufijo: str, forzar: bool = False
    ) -> Resultado:
        """Añade un sufijo antes de la extensión de varios archivos."""
        def _nuevo(p: Path) -> Path:
            return p.parent / f"{p.stem}{sufijo}{p.suffix}"

        return self._por_lote(rutas, _nuevo, forzar)

    def patron(
        self,
        rutas: Sequence[str],
        buscar: str,
        reemplazar: str,
        regex: bool = False,
        forzar: bool = False,
    ) -> Resultado:
        """Renombra aplicando un patrón (literal o expresión regular)."""
        if regex:
            compilado = re.compile(buscar)

            def _nuevo(p: Path) -> Path:
                nuevo = compilado.sub(reemplazar, p.name)
                return p.parent / nuevo

        else:
            def _nuevo(p: Path) -> Path:
                return p.parent / p.name.replace(buscar, reemplazar)

        return self._por_lote(rutas, _nuevo, forzar)

    def numerar(
        self,
        rutas: Sequence[str],
        plantilla: str = "{i:02d}",
        empezar_en: int = 1,
        forzar: bool = False,
    ) -> Resultado:
        """Numera archivos con una plantilla tipo ``foto_{i:02d}``.

        La plantilla puede contener ``{i}`` (número) y ``{nombre}`` (nombre
        original sin extensión). Si no lleva ``{i}`` se añade al final.
        """
        resultado = Resultado()
        objetivos = [self.seguridad.validar_existente(r, "archivo") for r in rutas]
        plantilla_usar = plantilla if "{i}" in plantilla else plantilla + "_{i}"
        for i, ruta in enumerate(objetivos, start=empezar_en):
            nombre = plantilla_usar.format(i=i, nombre=ruta.stem) + ruta.suffix
            destino = ruta.parent / nombre
            self._ejecutar(ruta, destino, forzar, resultado)
        return resultado

    # ------------------------------------------------------------------ #
    # Internos
    # ------------------------------------------------------------------ #
    def _por_lote(
        self, rutas: Sequence[str], fn: Callable[[Path], Path], forzar: bool
    ) -> Resultado:
        resultado = Resultado()
        for r in rutas:
            try:
                ruta = self.seguridad.validar_existente(r, "archivo")
                self.seguridad.comprobar_permitido(ruta)
                self._ejecutar(ruta, fn(ruta), forzar, resultado)
            except (FileNotFoundError, PermissionError, re.error) as exc:
                self.interfaz.error(str(exc))
                resultado.errores += 1
        return resultado

    def _ejecutar(
        self, origen: Path, destino: Path, forzar: bool, resultado: Resultado
    ) -> None:
        if destino == origen:
            self.interfaz.aviso(f"El nombre no cambia: {origen.name}")
            resultado.omitidos += 1
            return
        if destino.exists() and not self.seguridad.se_puede_sobrescribir(
            destino, forzar=forzar
        ):
            self.interfaz.aviso(f"Cancelado por colisión de nombre: {destino.name}")
            resultado.omitidos += 1
            return
        if self.seguridad.dry_run:
            self.interfaz.simulacion(f"Renombrar: {origen.name} -> {destino.name}")
            log.info("[DRY-RUN] RENOMBRAR %s -> %s", origen, destino)
            resultado.ok()
            return
        try:
            origen.rename(destino)
            self.interfaz.ok(f"Renombrado: {origen.name} -> {destino.name}")
            log.info("RENOMBRADO %s -> %s", origen, destino)
        except OSError as exc:
            self.interfaz.error(f"No se pudo renombrar {origen.name}: {exc}")
            log.exception("Error renombrando %s", origen)
            resultado.errores += 1
            return
        resultado.ok()

    # ------------------------------------------------------------------ #
    def menu_interactivo(self) -> None:
        """Flujo interactivo de renombrado."""
        self.interfaz.encabezado("RENOMBRAR ARCHIVOS")
        modo = Interfaz.preguntar(
            "Modo (individual/prefijo/sufijo/patron/numerar)", valor_por_defecto="individual"
        )
        rutas = Interfaz.pedir_ruta("Archivos (separados por espacios)").split()
        if modo == "individual" and rutas:
            nuevo = Interfaz.pedir_ruta("Nuevo nombre")
            res = self.renombrar(rutas[0], nuevo)
        elif modo == "prefijo":
            texto = Interfaz.pedir_ruta("Prefijo a añadir")
            res = self.prefijo(rutas, texto)
        elif modo == "sufijo":
            texto = Interfaz.pedir_ruta("Sufijo a añadir")
            res = self.sufijo(rutas, texto)
        elif modo == "patron":
            buscar = Interfaz.pedir_ruta("Buscar")
            reemplazar = Interfaz.pedir_ruta("Reemplazar por")
            regex = Interfaz.confirmar("¿Usar expresión regular?", por_defecto=False)
            res = self.patron(rutas, buscar, reemplazar, regex=regex)
        elif modo == "numerar":
            plantilla = Interfaz.preguntar("Plantilla (ej: foto_{i:02d})", valor_por_defecto="{i:02d}")
            res = self.numerar(rutas, plantilla)
        else:
            self.interfaz.error(f"Modo desconocido: {modo}")
            return
        self.interfaz.resumen(res.exito, res.omitidos, res.errores)
