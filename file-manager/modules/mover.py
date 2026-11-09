"""Mover archivos y carpetas.

Mueve uno o varios archivos/carpetas a un directorio de destino,
comprobando que el destino existe y sin sobrescribir sin autorización.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Optional, Sequence

from modules._resultado import Resultado
from utils.interfaz import Interfaz
from utils.logger import Logger
from utils.seguridad import Seguridad

log = Logger.obtener("mover")


class Mover:
    """Gestiona operaciones de movimiento de archivos y carpetas."""

    def __init__(self, seguridad: Seguridad, interfaz: Optional[Interfaz] = None) -> None:
        self.seguridad = seguridad
        self.interfaz = interfaz or Interfaz()

    def mover(
        self,
        origenes: Sequence[str],
        destino: str,
        crear_destino: bool = False,
        no_sobrescribir: bool = False,
        forzar: bool = False,
    ) -> Resultado:
        """Mueve ``origenes`` al directorio ``destino``.

        Args:
            origenes: Archivos o carpetas a mover.
            destino: Directorio de destino.
            crear_destino: Crear el destino si no existe.
            no_sobrescribir: Renombrar en lugar de sobrescribir (``archivo (1).ext``).
            forzar: No pedir confirmaciones (``--yes``).

        Returns:
            Resultado con el recuento de operaciones.
        """
        resultado = Resultado()
        try:
            destino_dir = self.seguridad.validar_destino(destino, crear=crear_destino)
        except (FileNotFoundError, NotADirectoryError, PermissionError) as exc:
            self.interfaz.error(str(exc))
            resultado.error()
            return resultado

        rutas = Seguridad.expandir_rutas(origenes)
        if not rutas:
            self.interfaz.aviso("No se han indicado archivos válidos que mover.")
            return resultado

        if self.seguridad.dry_run:
            self.interfaz.simulacion(
                f"Se moverian {len(rutas)} elemento(s) a {destino_dir}"
            )

        for origen in rutas:
            self._mover_uno(origen, destino_dir, no_sobrescribir, forzar, resultado)

        return resultado

    # ------------------------------------------------------------------ #
    def _mover_uno(
        self,
        origen: Path,
        destino_dir: Path,
        no_sobrescribir: bool,
        forzar: bool,
        resultado: Resultado,
    ) -> None:
        try:
            origen = self.seguridad.validar_existente(origen, "el origen")
            self.seguridad.comprobar_permitido(origen)

            destino_final = destino_dir / origen.name
            if destino_final.resolve() == origen.resolve():
                self.interfaz.aviso(f"El origen ya está en el destino: {origen}")
                resultado.omitidos += 1
                return

            if destino_final.exists():
                if self.seguridad.dry_run:
                    if no_sobrescribir:
                        destino_final = self.seguridad.ruta_libre(destino_final)
                elif no_sobrescribir:
                    destino_final = self.seguridad.ruta_libre(destino_final)
                    self.interfaz.aviso(
                        f"Destino ocupado. Se guardará como: {destino_final.name}"
                    )
                elif not self.seguridad.se_puede_sobrescribir(destino_final, forzar=forzar):
                    self.interfaz.aviso(f"Operación cancelada para: {origen.name}")
                    resultado.omitidos += 1
                    return

            tipo = "carpeta" if origen.is_dir() else "archivo"
            if self.seguridad.dry_run:
                self.interfaz.simulacion(f"Mover {tipo}: {origen} -> {destino_final}")
            else:
                shutil.move(str(origen), str(destino_final))
                self.interfaz.ok(f"{tipo.capitalize()} movido: {origen} -> {destino_final}")
            log.info("MOVIDO %s -> %s", origen, destino_final)
            resultado.ok()
        except PermissionError as exc:
            self.interfaz.error(str(exc))
            resultado.error()
        except shutil.Error as exc:  # errores de shutil (mismo directorio...)
            self.interfaz.error(f"Error al mover {origen}: {exc}")
            log.exception("Error moviendo %s", origen)
            resultado.errores += 1
        except Exception as exc:  # noqa: BLE001 - captura por robustez de CLI
            self.interfaz.error(f"Error inesperado con {origen}: {exc}")
            log.exception("Error inesperado moviendo %s", origen)
            resultado.errores += 1

    # ------------------------------------------------------------------ #
    def menu_interactivo(self) -> None:
        """Flujo interactivo de movimiento."""
        self.interfaz.encabezado("MOVER ARCHIVOS")
        origenes = Interfaz.pedir_ruta("Archivos a mover (separados por espacios)")
        destino = Interfaz.pedir_ruta("Carpeta de destino")
        crear = Interfaz.confirmar("¿Crear el destino si no existe?", por_defecto=False)
        sin_over = Interfaz.confirmar(
            "¿Evitar sobrescribir (renombrar si hay colisión)?", por_defecto=True
        )
        res = self.mover(origenes.split(), destino, crear_destino=crear, no_sobrescribir=sin_over)
        self.interfaz.resumen(res.exito, res.omitidos, res.errores)
