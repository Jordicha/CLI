"""Módulo de resultado estándar devuelto por todas las operaciones."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Resultado:
    """Agrupa el resultado de una operación (mover, borrar, renombrar...).

    Attributes:
        exito: Número de operaciones realizadas (o simuladas) con éxito.
        omitidos: Operaciones evitadas (usuario rechazó, colisiones...).
        errores: Operaciones que fallaron.
        mensajes: Detalle de cada operación, para mostrar o registrar.
    """

    exito: int = 0
    omitidos: int = 0
    errores: int = 0
    mensajes: List[str] = field(default_factory=list)

    def ok(self, mensaje: str = "") -> None:
        self.exito += 1
        if mensaje:
            self.mensajes.append(mensaje)

    def omitido(self, mensaje: str = "") -> None:
        self.omitidos += 1
        if mensaje:
            self.mensajes.append(mensaje)

    def error(self, mensaje: str = "") -> None:
        self.errores += 1
        if mensaje:
            self.mensajes.append(mensaje)
