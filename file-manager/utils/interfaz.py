"""Interfaz de usuario en terminal basada en ``rich``.

Proporciona colores, iconos ASCII, tablas, menús y prompts reutilizables
por el resto de módulos, de forma que el resto del código no dependa
directamente de rich.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Sequence

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

console = Console()

# Iconos ASCII (seguros en cualquier terminal)
ICONOS = {
    "ok": "[green][+][/green]",
    "error": "[red][x][/red]",
    "aviso": "[yellow][!][/yellow]",
    "info": "[cyan][i][/cyan]",
    "archivo": "[white][F][/white]",
    "carpeta": "[blue][D][/blue]",
    "mover": "[cyan]>[/cyan]",
    "borrar": "[red]X[/red]",
    "buscar": "[magenta]?[/magenta]",
    "crear": "[green]+[/green]",
}


class Interfaz:
    """Encapsula la entrada/salida con estilo para toda la aplicación."""

    # ------------------------------------------------------------------ #
    # Mensajes
    # ------------------------------------------------------------------ #
    @staticmethod
    def ok(mensaje: str) -> None:
        console.print(f"{ICONOS['ok']} {mensaje}")

    @staticmethod
    def error(mensaje: str) -> None:
        console.print(f"[red]{ICONOS['error']} {mensaje}[/red]")

    @staticmethod
    def aviso(mensaje: str) -> None:
        console.print(f"{ICONOS['aviso']} [yellow]{mensaje}[/yellow]")

    @staticmethod
    def info(mensaje: str) -> None:
        console.print(f"{ICONOS['info']} {mensaje}")

    @staticmethod
    def simulacion(mensaje: str) -> None:
        console.print(f"{ICONOS['info']} [bold cyan][SIMULACION][/bold cyan] {mensaje}")

    @staticmethod
    def resumen(exito: int, omitidos: int = 0, errores: int = 0) -> None:
        """Muestra un resumen de operaciones realizadas."""
        partes = [f"[green]{exito} realizada(s)[/green]"]
        if omitidos:
            partes.append(f"[yellow]{omitidos} omitida(s)[/yellow]")
        if errores:
            partes.append(f"[red]{errores} error(es)[/red]")
        console.print(f"\n[bold]Resumen:[/bold] " + ", ".join(partes))

    # ------------------------------------------------------------------ #
    # Encabezados y tablas
    # ------------------------------------------------------------------ #
    @staticmethod
    def encabezado(titulo: str) -> None:
        console.print(
            Panel(
                f"[bold white]{titulo}[/bold white]",
                style="cyan",
                expand=False,
            )
        )

    @staticmethod
    def banner() -> None:
        """Banner de bienvenida de la aplicación."""
        arte = Text()
        arte.append("  _____ _ _      __ _                             \n", style="bold cyan")
        arte.append(" |  ___(_) | ___ / _| | __ _ _ __ ___  _ __  _ __/\n", style="bold cyan")
        arte.append(" | |_  | | |/ _ \\ |_| |/ _` | '_ ` _ \\| '_ \\| '_ \\\n", style="bold cyan")
        arte.append(" |  _| | | |  __/  _| | (_| | | | | | | |_) | |_) |\n", style="bold cyan")
        arte.append(" |_|   |_|_|\\___|_| |_|\\__,_|_| |_| |_| .__/| .__/\n", style="bold cyan")
        arte.append("                                        |_|   |_|   ", style="bold cyan")
        console.print(arte)
        console.print("[dim]Gestor de archivos por terminal - v1.0[/dim]\n")

    @staticmethod
    def tabla(
        titulo: str,
        columnas: Sequence[str],
        filas: Iterable[Sequence[str]],
        estilos: Optional[Sequence[str]] = None,
    ) -> Table:
        """Crea y muestra una tabla con encabezados y devuelve el objeto."""
        tabla = Table(title=titulo, header_style="bold cyan", title_style="bold")
        for col in columnas:
            tabla.add_column(col, overflow="fold")
        for fila in filas:
            tabla.add_row(*[str(c) for c in fila])
        if filas is not None:
            console.print(tabla)
        return tabla

    # ------------------------------------------------------------------ #
    # Menú interactivo
    # ------------------------------------------------------------------ #
    OPCIONES_MENU = [
        ("1", "[cyan]>[/cyan]      Mover archivos"),
        ("2", "[red]X[/red]      Borrar archivos"),
        ("3", "[green]+[/green]     Organizar archivos automáticamente"),
        ("4", "[magenta]~[/magenta]     Renombrar archivos"),
        ("5", "[magenta]?[/magenta]     Buscar archivos"),
        ("6", "[white]i[/white]     Mostrar información"),
        ("7", "[blue]D[/blue]     Crear carpeta"),
        ("8", "[yellow]q[/yellow]     Salir"),
    ]

    @staticmethod
    def menu() -> str:
        """Muestra el menú principal y devuelve la opción elegida."""
        console.print()
        lineas = "\n".join(f"[bold][{op}][/bold] {texto}" for op, texto in Interfaz.OPCIONES_MENU)
        console.print(Panel(lineas, title="MENU PRINCIPAL", style="white"))
        return Prompt.ask(
            "[bold]Selecciona una opcion[/bold]",
            choices=[op for op, _ in Interfaz.OPCIONES_MENU],
            default="8",
        )

    # ------------------------------------------------------------------ #
    # Prompts
    # ------------------------------------------------------------------ #
    @staticmethod
    def preguntar(texto: str, valor_por_defecto: Optional[str] = None) -> str:
        """Pide un texto por consola."""
        return Prompt.ask(texto, default=valor_por_defecto) if valor_por_defecto else Prompt.ask(texto)

    @staticmethod
    def confirmar(texto: str, por_defecto: bool = False) -> bool:
        """Pide una confirmación sí/no."""
        return Confirm.ask(texto, default=por_defecto)

    @staticmethod
    def pedir_ruta(texto: str = "Ruta") -> str:
        """Pide una ruta y la devuelve limpia (sin comillas)."""
        r = Prompt.ask(f"[bold]{texto}[/bold]").strip().strip("'\"")
        return r
