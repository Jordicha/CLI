"""Borrar archivos y carpetas.

Elimina archivos o carpetas completas con confirmación explícita,
con opción de eliminación segura a través de una papelera.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional, Sequence

from modules._resultado import Resultado
from utils.interfaz import Interfaz
from utils.logger import Logger
from utils.seguridad import Seguridad

log = Logger.obtener("borrar")


class Borrar:
    """Gestiona operaciones de borrado seguro."""

    def __init__(self, seguridad: Seguridad, interfaz: Optional[Interfaz] = None) -> None:
        self.seguridad = seguridad
        self.interfaz = interfaz or Interfaz()

    def borrar(
        self,
        rutas: Sequence[str],
        papelera: bool = False,
        recursivo: bool = False,
        forzar: bool = False,
    ) -> Resultado:
        """Borra ``rutas`` de forma segura.

        Args:
            rutas: Archivos o carpetas a borrar.
            papelera: Mover a la papelera en vez de borrar permanentemente.
            recursivo: Permitir borrar carpetas con contenido (``-r``).
            forzar: Omitir confirmaciones (``--yes``).

        Returns:
            Resultado con el recuento de operaciones.
        """
        resultado = Resultado()
        objetivos = Seguridad.expandir_rutas(rutas)
        if not objetivos:
            self.interfaz.aviso("No se han indicado rutas válidas que borrar.")
            return resultado

        lista = "\n".join(f"  - {p}" for p in objetivos)
        accion = "Enviar a la papelera" if papelera else "BORRAR PERMANENTEMENTE"
        self.interfaz.aviso(f"Vas a {accion} los siguientes elementos:\n{lista}")

        if not self.seguridad.confirmar(
            "¿Confirmas la operación?", forzar=forzar
        ):
            self.interfaz.info("Operación cancelada. No se ha borrado nada.")
            resultado.omitidos = len(objetivos)
            return resultado

        if papelera and self.seguridad.papelera_dir is None:
            destino = Interfaz.pedir_ruta("Carpeta que hará de papelera")
            self.seguridad.papelera_dir = Path(destino).expanduser()

        for objetivo in objetivos:
            self._borrar_uno(objetivo, papelera, recursivo, forzar, resultado)

        return resultado

    # ------------------------------------------------------------------ #
    def _borrar_uno(
        self,
        ruta: Path,
        papelera: bool,
        recursivo: bool,
        forzar: bool,
        resultado: Resultado,
    ) -> None:
        try:
            ruta = self.seguridad.validar_existente(ruta, "la ruta")
            self.seguridad.comprobar_permitido(ruta)

            if ruta.is_dir() and not papelera and any(ruta.iterdir()):
                if not recursivo:
                    self.interfaz.aviso(
                        f"{ruta} es una carpeta con contenido. "
                        f"Usa -r/--recursivo para borrarla."
                    )
                    resultado.omitidos += 1
                    return
                if not self.seguridad.confirmar(
                    f"¿Borrar la carpeta COMPLETA {ruta} y todo su contenido?",
                    forzar=forzar,
                ):
                    self.interfaz.aviso(f"Cancelado: {ruta}")
                    resultado.omitidos += 1
                    return

            if papelera:
                if self.seguridad.dry_run:
                    self.interfaz.simulacion(f"Enviar a papelera: {ruta}")
                    log.info("[DRY-RUN] PAPELERA %s", ruta)
                    resultado.ok()
                    return
                destino = self.seguridad.mover_a_papelera(ruta)
                accion = f"Enviado a papelera: {destino}"
            else:
                if self.seguridad.dry_run:
                    self.interfaz.simulacion(f"Borrar: {ruta}")
                    log.info("[DRY-RUN] BORRAR %s", ruta)
                    resultado.ok()
                    return
                if ruta.is_dir():
                    shutil.rmtree(ruta)
                else:
                    ruta.unlink()
                accion = "Borrado"

            self.interfaz.ok(f"{accion}: {ruta}")
            log.info("%s %s", "PAPELERA" if papelera else "BORRADO", ruta)
            resultado.ok()
        except PermissionError as exc:
            self.interfaz.error(str(exc))
            resultado.errores += 1
        except Exception as exc:  # noqa: BLE001 - robustez de CLI
            self.interfaz.error(f"Error al borrar {ruta}: {exc}")
            log.exception("Error borrando %s", ruta)
            resultado.errores += 1

    # ------------------------------------------------------------------ #
    def menu_interactivo(self) -> None:
        """Flujo interactivo de borrado."""
        self.interfaz.encabezado("BORRAR ARCHIVOS")
        rutas = Interfaz.pedir_ruta("Archivos/carpetas a borrar (separados por espacios)")
        papelera = Interfaz.confirmar(
            "¿Eliminación segura (mover a la papelera)?", por_defecto=True
        )
        recursivo = Interfaz.confirmar(
            "¿Permitir borrar carpetas con contenido (-r)?", por_defecto=False
        )
        res = self.borrar(rutas.split(), papelera=papelera, recursivo=recursivo)
        self.interfaz.resumen(res.exito, res.omitidos, res.errores)
