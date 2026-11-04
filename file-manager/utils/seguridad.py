"""Módulo de seguridad del gestor de archivos.

Centraliza todas las comprobaciones de seguridad:
- Confirmación explícita antes de operaciones destructivas.
- Protección contra sobrescritura de archivos.
- Validación de rutas de origen y destino.
- Modo restringido: bloquea operaciones fuera de los directorios permitidos.
- Papelera: eliminación segura moviendo los archivos en lugar de borrarlos.
"""

from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Sequence


class Seguridad:
    """Agrupa las comprobaciones de seguridad usadas por todos los módulos."""

    def __init__(
        self,
        dry_run: bool = False,
        restringido: bool = False,
        rutas_permitidas: Optional[Sequence[str]] = None,
        confirmador: Optional[Callable[[str], bool]] = None,
        papelera_dir: Optional[str] = None,
    ) -> None:
        """Inicializa el gestor de seguridad.

        Args:
            dry_run: Si es True, las operaciones destructivas solo se simulan.
            restringido: Si es True, solo se permiten rutas dentro de
                ``rutas_permitidas``.
            rutas_permitidas: Directorios autorizados en modo restringido.
            confirmador: Función ``pregunta -> bool`` para pedir confirmación.
                Si es ``None``, las confirmaciones destructivas se deniegan.
            papelera_dir: Directorio usado como papelera de eliminación segura.
        """
        self.dry_run = dry_run
        self.restringido = restringido
        self.rutas_permitidas: List[Path] = [
            Path(r).expanduser().resolve() for r in (rutas_permitidas or [])
        ]
        self._confirmador = confirmador
        self.papelera_dir = Path(papelera_dir).expanduser() if papelera_dir else None

    # ------------------------------------------------------------------ #
    # Confirmaciones
    # ------------------------------------------------------------------ #
    def confirmar(self, pregunta: str, forzar: bool = False) -> bool:
        """Pide confirmación explícita para operaciones destructivas.

        En modo ``--dry-run`` no se pregunta: la operación solo se simula.
        Con ``--yes`` (``forzar=True``) se asiente sin preguntar.
        Si no hay función confirmadora disponible, se deniega por seguridad.
        """
        if self.dry_run or forzar:
            return True
        if self._confirmador is None:
            return False
        return bool(self._confirmador(pregunta))

    # ------------------------------------------------------------------ #
    # Validación de rutas
    # ------------------------------------------------------------------ #
    def validar_existente(self, ruta: Path | str, descripcion: str = "ruta") -> Path:
        """Comprueba que la ruta existe y devuelve su Path absoluto.

        Raises:
            FileNotFoundError: si la ruta no existe.
        """
        p = Path(ruta).expanduser()
        if not p.exists():
            raise FileNotFoundError(f"La {descripcion} no existe: {p}")
        return p

    def validar_destino(self, destino: Path | str, crear: bool = False) -> Path:
        """Valida que el destino sea un directorio válido para operaciones.

        Args:
            destino: Ruta del directorio de destino.
            crear: Si es True y no existe, se crea (también en modo simulación
                se informa pero no se crea realmente).

        Raises:
            FileNotFoundError: si no existe y ``crear`` es False.
            NotADirectoryError: si existe pero no es un directorio.
            PermissionError: si está fuera de los directorios permitidos.
        """
        p = Path(destino).expanduser()
        if p.exists():
            if not p.is_dir():
                raise NotADirectoryError(f"El destino no es un directorio: {p}")
        else:
            if not crear:
                raise FileNotFoundError(
                    f"El directorio de destino no existe: {p}\n"
                    f"Crea la carpeta antes de continuar o usa la opción de crearla."
                )
            if not self.dry_run:
                p.mkdir(parents=True, exist_ok=True)
        if not self.dry_run:
            self.comprobar_permitido(p)
        return p

    def comprobar_permitido(self, ruta: Path | str) -> None:
        """Comprueba que la ruta está dentro de los directorios permitidos.

        Raises:
            PermissionError: si el modo restringido está activo y la ruta
                queda fuera de los directorios autorizados.
        """
        if not self.restringido or not self.rutas_permitidas:
            return
        p = Path(ruta).expanduser().resolve()
        for permitida in self.rutas_permitidas:
            try:
                p.relative_to(permitida)
                return
            except ValueError:
                continue
        raise PermissionError(
            f"Operación bloqueada por el modo restringido: {p}\n"
            f"Directorios permitidos: "
            f"{', '.join(str(r) for r in self.rutas_permitidas)}"
        )

    # ------------------------------------------------------------------ #
    # Sobrescritura
    # ------------------------------------------------------------------ #
    def se_puede_sobrescribir(
        self, destino: Path, forzar: bool = False
    ) -> bool:
        """Devuelve True si está permitido sobrescribir ``destino``.

        Si el destino no existe, siempre se puede escribir.
        Si existe, se pide confirmación salvo en dry-run o con ``--yes``.
        """
        if not destino.exists():
            return True
        return self.confirmar(
            f"El destino ya existe: {destino}. ¿Sobrescribir?", forzar=forzar
        )

    def ruta_libre(self, destino: Path) -> Path:
        """Devuelve una variante sin colisiones de ``destino``.

        Si ``archivo.pdf`` existe, propone ``archivo (1).pdf``, ``archivo
        (2).pdf``, etc. Útil para evitar sobrescribir sin preguntar.
        """
        if not destino.exists():
            return destino
        stem, sufijo = destino.stem, destino.suffix
        for i in range(1, 10_000):
            candidato = destino.with_name(f"{stem} ({i}){sufijo}")
            if not candidato.exists():
                return candidato
        raise FileExistsError(f"No se pudo generar un nombre libre para {destino}")

    # ------------------------------------------------------------------ #
    # Eliminación segura (papelera)
    # ------------------------------------------------------------------ #
    def mover_a_papelera(self, ruta: Path) -> Path:
        """Mueve ``ruta`` a la papelera en lugar de borrarla.

        Mantiene la estructura relativa dentro de la papelera para poder
        restaurar los archivos fácilmente.

        Returns:
            La ruta dentro de la papelera.

        Raises:
            RuntimeError: si no se ha configurado directorio de papelera.
        """
        if self.papelera_dir is None:
            raise RuntimeError(
                "No hay papelera configurada. Usa --papelera RUTA para "
                "definirla."
            )
        ruta = Path(ruta).resolve()
        marca = datetime.now().strftime("%Y%m%d-%H%M%S")
        destino = self.papelera_dir / marca / ruta.name
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino = self.ruta_libre(destino)
        if not self.dry_run:
            shutil.move(str(ruta), str(destino))
        return destino

    # ------------------------------------------------------------------ #
    # Utilidades varias
    # ------------------------------------------------------------------ #
    @staticmethod
    def expandir_rutas(rutas: Iterable[str]) -> List[Path]:
        """Expande ``~``, variables de entorno y comodines de una lista de rutas."""
        resultado: List[Path] = []
        for r in rutas:
            r = os.path.expandvars(os.path.expanduser(r))
            if any(c in r for c in "*?["):
                coinc = sorted(Path().glob(r))
                if coinc:
                    resultado.extend(coinc)
                    continue
            resultado.append(Path(r))
        return resultado
