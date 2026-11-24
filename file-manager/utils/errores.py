"""Excepciones propias del gestor, con mensajes pensados para la CLI."""

from __future__ import annotations


class GestorArchivosError(Exception):
    """Base común para los errores previsibles del gestor."""


class ConfigError(GestorArchivosError):
    """La configuración o un archivo de configuración no es válido."""


class AccionNoValida(ConfigError):
    """Una acción personalizada o uno de sus pasos no es válido."""


class EntradaNoValida(GestorArchivosError, ValueError):
    """Un argumento introducido por el usuario no tiene un formato válido."""


class RutaNoValida(GestorArchivosError, FileNotFoundError):
    """La ruta indicada no existe o no se puede usar."""


class DirectorioNoValido(GestorArchivosError, NotADirectoryError):
    """Se esperaba un directorio pero la ruta apunta a otra cosa."""


class AccesoDenegado(GestorArchivosError, PermissionError):
    """La operación no está permitida por permisos o por el modo restringido."""


class IAError(ConfigError):
    """Fallo de configuración o comunicación con el proveedor de IA."""
