"""Información de archivos y carpetas.

Muestra nombre, ruta completa, extensión, tamaño, permisos,
fecha de creación (si está disponible) y fecha de modificación.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from utils.interfaz import Interfaz, console
from utils.logger import Logger
from utils.seguridad import Seguridad
from modules.buscar import _tamano_legible

log = Logger.obtener("informacion")


class Informacion:
    """Inspección y presentación de metadatos de archivos."""

    def __init__(self, seguridad: Seguridad, interfaz: Optional[Interfaz] = None) -> None:
        self.seguridad = seguridad
        self.interfaz = interfaz or Interfaz()

    def info(self, rutas: Sequence[str]) -> None:
        """Muestra una ficha de información por cada ruta indicada."""
        for r in rutas:
            try:
                ruta = self.seguridad.validar_existente(r, "la ruta")
                self._ficha(ruta)
                log.info("INFO %s", ruta)
            except (FileNotFoundError, PermissionError) as exc:
                self.interfaz.error(str(exc))

    # ------------------------------------------------------------------ #
    def _ficha(self, ruta: Path) -> None:
        est = ruta.stat()
        es_dir = ruta.is_dir()
        tam = (
            _tamano_legible(self._tamano_carpeta(ruta)) if es_dir
            else _tamano_legible(est.st_size)
        )
        creacion = self._fecha_creacion(ruta, est)
        modificacion = datetime.fromtimestamp(est.st_mtime)
        acceso = datetime.fromtimestamp(est.st_atime)

        filas = [
            ("Nombre", ruta.name or str(ruta)),
            ("Tipo", "Carpeta" if es_dir else "Archivo"),
            ("Ruta completa", str(ruta.resolve())),
            ("Extension", ruta.suffix.lstrip(".") or "(ninguna)"),
            ("Tamaño", tam + (" (contenido)" if es_dir else "")),
            ("Permisos", oct(est.st_mode & 0o777)),
            ("Creado", creacion),
            ("Modificado", modificacion.strftime("%Y-%m-%d %H:%M:%S")),
            ("Ultimo acceso", acceso.strftime("%Y-%m-%d %H:%M:%S")),
        ]
        if es_dir:
            try:
                n_archivos = sum(1 for p in ruta.rglob("*") if p.is_file())
                n_carpetas = sum(1 for p in ruta.rglob("*") if p.is_dir())
                filas.append(("Contenido", f"{n_archivos} archivo(s), {n_carpetas} carpeta(s)"))
            except (PermissionError, OSError):
                filas.append(("Contenido", "(sin permiso)"))

        from rich.panel import Panel

        console.print()
        lineas = "\n".join(
            f"[bold cyan]{campo:<16}[/bold cyan] {valor}" for campo, valor in filas
        )
        console.print(Panel(lineas, title=f"{'[D]' if es_dir else '[F]'} {ruta.name}", expand=False))

    # ------------------------------------------------------------------ #
    @staticmethod
    def _tamano_carpeta(ruta: Path) -> int:
        total = 0
        for p in ruta.rglob("*"):
            try:
                if p.is_file():
                    total += p.stat().st_size
            except OSError:
                continue
        return total

    @staticmethod
    def _fecha_creacion(ruta: Path, est: os.stat_result) -> str:
        """st_ctime es 'cambio de metadatos' en Unix; birthtime si existe."""
        birth = getattr(est, "st_birthtime", None)  # macOS/BSD, algunos FS
        if birth is not None:
            return datetime.fromtimestamp(birth).strftime("%Y-%m-%d %H:%M:%S")
        try:
            import subprocess

            salida = subprocess.run(
                ["stat", "-c", "%w", str(ruta)],
                capture_output=True, text=True, timeout=5,
            )
            valor = salida.stdout.strip()
            if valor and valor != "-" and "unknown" not in valor.lower():
                return valor
        except (OSError, subprocess.SubprocessError):
            pass
        return (
            f"{datetime.fromtimestamp(est.st_ctime).strftime('%Y-%m-%d %H:%M:%S')}"
            " (ctime: cambio de metadatos en Unix)"
        )

    # ------------------------------------------------------------------ #
    def menu_interactivo(self) -> None:
        """Flujo interactivo de información."""
        self.interfaz.encabezado("MOSTRAR INFORMACION")
        rutas = Interfaz.pedir_ruta("Archivo o carpeta").split()
        self.info(rutas)
