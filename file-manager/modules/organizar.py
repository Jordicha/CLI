"""Organización automática de archivos.

Clasifica los archivos de un directorio según:
- Su extensión (imágenes, vídeos, audio, documentos, hojas de cálculo,
  comprimidos, programación, ejecutables u otros).
- Su fecha de creación/modificación (por año-mes).
- Su tamaño (rangos predefinidos).

Crea automáticamente las carpetas de categoría y mueve los archivos.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from modules._resultado import Resultado
from modules.mover import Mover
from utils.interfaz import Interfaz
from utils.logger import Logger
from utils.seguridad import Seguridad

log = Logger.obtener("organizar")

# Mapa de categorías por extensión (en minúsculas, sin punto)
CATEGORIAS: Dict[str, List[str]] = {
    "Imagenes": ["jpg", "jpeg", "png", "gif", "svg", "webp"],
    "Videos": ["mp4", "avi", "mkv", "mov"],
    "Audio": ["mp3", "wav", "flac", "ogg"],
    "Documentos": ["pdf", "docx", "doc", "txt", "odt"],
    "Hojas_de_calculo": ["xlsx", "xls", "csv", "ods"],
    "Comprimidos": ["zip", "rar", "7z", "tar", "gz"],
    "Programacion": ["py", "java", "js", "html", "css", "php", "c", "cpp"],
    "Ejecutables": ["exe", "deb", "rpm", "appimage"],
}
CATEGORIA_OTROS = "Otros"

# Rangos de tamaño para la organización --por tamano
RANGOS_TAMANO: List[Tuple[str, int]] = [
    ("0a_Muy_pequenos_lt_100KB", 100 * 1024),
    ("1a_Pequenos_lt_10MB", 10 * 1024 * 1024),
    ("2a_Medianos_lt_100MB", 100 * 1024 * 1024),
    ("3a_Grandes_lt_1GB", 1024 * 1024 * 1024),
    ("4a_Muy_grandes_ge_1GB", None),
]


def categoria_de(ruta: Path) -> str:
    """Devuelve la categoría de un archivo según su extensión."""
    ext = ruta.suffix.lower().lstrip(".")
    for categoria, extensiones in CATEGORIAS.items():
        if ext in extensiones:
            return categoria
    return CATEGORIA_OTROS


def rango_tamano(tamano: int) -> str:
    """Devuelve el nombre del rango de tamaño correspondiente."""
    for nombre, limite in RANGOS_TAMANO:
        if limite is None or tamano < limite:
            return nombre
    return CATEGORIA_OTROS


def fecha_creacion(ruta: Path) -> float:
    """Fecha de creación si está disponible (Windows/macOS); si no, mtime."""
    try:
        est = ruta.stat()
        creadto = getattr(est, "st_ctime", None)
        # En Unix st_ctime es el cambio de metadatos: usamos st_mtime si existe.
        return est.st_mtime if creadto is None else creadto
    except OSError:
        return 0.0


class Organizar:
    """Organiza automáticamente los archivos de un directorio."""

    def __init__(
        self,
        seguridad: Seguridad,
        interfaz: Optional[Interfaz] = None,
    ) -> None:
        self.seguridad = seguridad
        self.interfaz = interfaz or Interfaz()
        self.mover = Mover(seguridad, interfaz)

    # ------------------------------------------------------------------ #
    def organizar(
        self,
        directorio: str,
        criterio: str = "extension",
        incluir_subcarpetas: bool = False,
    ) -> Resultado:
        """Organiza los archivos de ``directorio`` según ``criterio``.

        Args:
            directorio: Carpeta con los archivos a clasificar.
            criterio: ``extension``, ``fecha``, ``modificacion`` o ``tamano``.
            incluir_subcarpetas: Procesar también archivos dentro de
                subcarpetas (no toca las carpetas de categorías ya creadas).

        Returns:
            Resultado con el recuento de operaciones.
        """
        resultado = Resultado()
        try:
            base = self.seguridad.validar_existente(directorio, "directorio")
            self.seguridad.comprobar_permitido(base)
            self.seguridad.validar_destino(base)
        except (FileNotFoundError, PermissionError) as exc:
            self.interfaz.error(str(exc))
            resultado.errores += 1
            return resultado

        if not base.is_dir():
            self.interfaz.error(f"No es un directorio: {base}")
            resultado.errores += 1
            return resultado

        carpetas_categoria = set(CATEGORIAS) | {CATEGORIA_OTROS}
        if criterio == "tamano":
            carpetas_categoria |= {nombre for nombre, _ in RANGOS_TAMANO}
        elif criterio == "extension":
            pass  # las carpetas de extensión se listan todas arriba
        else:
            # En criterios por fecha se ignoran todas las carpetas AAAA-MM
            carpetas_categoria |= self._carpetas_fecha(base)
        archivos = self._listar_archivos(base, incluir_subcarpetas, carpetas_categoria)
        if not archivos:
            self.interfaz.aviso(f"No hay archivos que organizar en {base}")
            return resultado

        self.interfaz.info(
            f"Organizando {len(archivos)} archivo(s) en {base} "
            f"(criterio: {criterio})"
        )

        plan = self._plan(base, archivos, criterio)
        if self.seguridad.dry_run:
            self.interfaz.simulacion(
                f"Clasificando {len(plan)} archivo(s) segun '{criterio}'"
            )
            for origen, categoria in plan:
                self.interfaz.simulacion(f"  {origen.name} -> {categoria}/")
                resultado.ok()
            return resultado

        for origen, categoria in plan:
            destino = base / categoria
            destino.mkdir(parents=True, exist_ok=True)
            res_parcial = self.mover.mover(
                [str(origen)], str(destino), crear_destino=True, no_sobrescribir=True
            )
            resultado.exito += res_parcial.exito
            resultado.omitidos += res_parcial.omitidos
            resultado.errores += res_parcial.errores

        return resultado

    # ------------------------------------------------------------------ #
    @staticmethod
    def _carpetas_fecha(base: Path) -> set:
        """Nombres de subcarpetas con formato AAAA-MM (destino de fechas)."""
        import re

        patron = re.compile(r"^\d{4}-\d{2}$")
        return {p.name for p in base.iterdir() if p.is_dir() and patron.match(p.name)}

    # ------------------------------------------------------------------ #
    def _listar_archivos(
        self, base: Path, subcarpetas: bool, carpetas_categoria: set
    ) -> List[Path]:
        """Lista los archivos a organizar, ignorando las carpetas de categorías."""
        candidatos = base.rglob("*") if subcarpetas else base.iterdir()
        archivos: List[Path] = []
        for item in sorted(candidatos):
            if not item.is_file():
                continue
            # Ignorar archivos que ya estén dentro de una carpeta de categoría
            try:
                relativa = item.relative_to(base)
            except ValueError:
                continue
            if relativa.parts and relativa.parts[0] in carpetas_categoria:
                continue
            archivos.append(item)
        return archivos

    def _plan(
        self, base: Path, archivos: List[Path], criterio: str
    ) -> List[Tuple[Path, str]]:
        """Calcula la categoría destino de cada archivo según el criterio."""
        plan: List[Tuple[Path, str]] = []
        for archivo in archivos:
            if criterio == "tamano":
                categoria = rango_tamano(archivo.stat().st_size)
            elif criterio in ("fecha", "modificacion", "creacion"):
                marca = (
                    fecha_creacion(archivo)
                    if criterio == "creacion"
                    else archivo.stat().st_mtime
                )
                dt = datetime.fromtimestamp(marca)
                categoria = f"{dt.year:04d}-{dt.month:02d}"
            else:
                categoria = categoria_de(archivo)
            plan.append((archivo, categoria))
        return plan

    # ------------------------------------------------------------------ #
    def menu_interactivo(self) -> None:
        """Flujo interactivo de organización."""
        self.interfaz.encabezado("ORGANIZAR ARCHIVOS AUTOMATICAMENTE")
        ruta = Interfaz.pedir_ruta("Carpeta a organizar")
        criterio = Interfaz.preguntar(
            "Criterio (extension/fecha/modificacion/tamano)", valor_por_defecto="extension"
        )
        subcarpetas = Interfaz.confirmar(
            "¿Incluir subcarpetas?", por_defecto=False
        )
        res = self.organizar(ruta, criterio=criterio, incluir_subcarpetas=subcarpetas)
        self.interfaz.resumen(res.exito, res.omitidos, res.errores)
