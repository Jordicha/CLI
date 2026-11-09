#!/usr/bin/env python3
"""File Manager - gestor de archivos por terminal.

Uso directo desde la terminal (argparse) o con menú interactivo:

    python main.py organizar ~/Descargas
    python main.py mover archivo.pdf ~/Documentos/
    python main.py borrar archivo.pdf --papelera
    python main.py buscar "factura" --extension pdf
    python main.py info archivo.pdf
    python main.py renombrar archivo.pdf nuevo_nombre.pdf
    python main.py organizar ~/Descargas --dry-run
    python main.py            # abre el menú interactivo
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from modules import (  # noqa: E402
    Acciones,
    Borrar,
    Buscar,
    Crear,
    Informacion,
    Mover,
    Organizar,
    Renombrar,
)
from utils.interfaz import Interfaz  # noqa: E402
from utils.logger import Logger  # noqa: E402
from utils.seguridad import Seguridad  # noqa: E402

log = Logger.obtener("main")


# ---------------------------------------------------------------------- #
# Construcción de argumentos
# ---------------------------------------------------------------------- #
def _anadir_comunes(parser: argparse.ArgumentParser) -> None:
    """Añade las opciones de seguridad compartidas por todas las subórdenes."""
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula la operacion sin modificar nada.",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="No pedir confirmaciones (usar con precaucion).",
    )
    parser.add_argument(
        "--restringido",
        action="store_true",
        help="Bloquear operaciones fuera de los directorios permitidos.",
    )
    parser.add_argument(
        "--permitido",
        action="append",
        metavar="RUTA",
        help="Directorio permitido en modo restringido (repetible).",
    )
    parser.add_argument(
        "--papelera",
        metavar="RUTA",
        default=None,
        help="Carpeta usada como papelera de eliminacion segura.",
    )


def crear_parser() -> argparse.ArgumentParser:
    """Construye el parser principal con todas las subórdenes."""
    parser = argparse.ArgumentParser(
        prog="file-manager",
        description="Gestor de archivos por terminal: mover, borrar, "
        "organizar, renombrar, buscar y consultar archivos.",
        epilog="Si no se indica ninguna suborden se abre el menu interactivo.",
    )
    sub = parser.add_subparsers(dest="comando")

    # mover
    p = sub.add_parser("mover", help="Mover archivos o carpetas a un destino.")
    p.add_argument("origenes", nargs="+", help="Archivos/carpetas a mover.")
    p.add_argument("destino", help="Directorio de destino.")
    p.add_argument("-c", "--crear-destino", action="store_true",
                   help="Crear el destino si no existe.")
    p.add_argument("--no-sobrescribir", action="store_true",
                   help="Renombrar (archivo (1).ext) en lugar de sobrescribir.")
    _anadir_comunes(p)

    # borrar
    p = sub.add_parser("borrar", help="Borrar archivos o carpetas.")
    p.add_argument("rutas", nargs="+", help="Archivos/carpetas a borrar.")
    p.add_argument("--permanente", action="store_true",
                   help="Borrado permanente (sin papelera).")
    p.add_argument("-r", "--recursivo", action="store_true",
                   help="Permitir borrar carpetas con contenido.")
    _anadir_comunes(p)

    # organizar
    p = sub.add_parser("organizar", help="Organizar archivos automaticamente.")
    p.add_argument("directorio", help="Carpeta a organizar.")
    p.add_argument("--por", choices=["extension", "fecha", "creacion",
                                      "modificacion", "tamano"],
                   default="extension", help="Criterio de organizacion.")
    p.add_argument("-s", "--subcarpetas", action="store_true",
                   help="Incluir archivos de subcarpetas.")
    _anadir_comunes(p)

    # renombrar
    p = sub.add_parser("renombrar", help="Renombrar archivos.")
    p.add_argument("rutas", nargs="+", help="Archivos a renombrar.")
    p.add_argument("--nuevo", metavar="NOMBRE",
                   help="Nuevo nombre. Con 1 archivo es el renombrado directo "
                   "(equivale a pasar el nombre como 2er argumento).")
    p.add_argument("--prefijo", metavar="TEXTO", help="Anadir prefijo.")
    p.add_argument("--sufijo", metavar="TEXTO", help="Anadir sufijo antes de la extension.")
    p.add_argument("--buscar", metavar="PATRON", help="Buscar patron en el nombre.")
    p.add_argument("--reemplazar", metavar="TEXTO", default="",
                   help="Texto de reemplazo (con --buscar).")
    p.add_argument("--regex", action="store_true", help="Usar expresion regular con --buscar.")
    p.add_argument("--numerar", action="store_true", help="Numerar los archivos.")
    p.add_argument("--plantilla", default="{i:02d}",
                   help="Plantilla para --numerar (usa {i} y {nombre}).")
    _anadir_comunes(p)

    # buscar
    p = sub.add_parser("buscar", help="Buscar archivos y carpetas.")
    p.add_argument("patron", nargs="?", help="Texto o patron (* ?) a buscar.")
    p.add_argument("-e", "--extension", help="Filtrar por extension (pdf, .pdf).")
    p.add_argument("-t", "--tamano", help="Filtrar por tamano (>=10MB, <=1GB, 1MB-500MB).")
    p.add_argument("-m", "--modificado", help="Filtrar por modificacion "
                   "(>2024-01-01, <2024-12-31, ultimo-7dias).")
    p.add_argument("-d", "--directorio", default=".", help="Donde buscar (por defecto .).")
    p.add_argument("--tipo", choices=["archivo", "carpeta", "todo"], default="archivo")
    p.add_argument("-n", "--max", type=int, default=200, help="Maximo de resultados.")
    _anadir_comunes(p)

    # info
    p = sub.add_parser("info", help="Mostrar informacion de archivos.")
    p.add_argument("rutas", nargs="+", help="Archivos/carpetas a inspeccionar.")
    _anadir_comunes(p)

    # crear
    p = sub.add_parser("crear", help="Crear carpetas.")
    p.add_argument("rutas", nargs="+", help="Carpetas a crear.")
    _anadir_comunes(p)

    # acciones
    p = sub.add_parser(
        "acciones",
        help="Gestionar y ejecutar acciones personalizadas (acciones.json).",
    )
    p.add_argument(
        "accion",
        nargs="?",
        help="Nombre de la accion a ejecutar. Sin nombre, lista las disponibles.",
    )
    p.add_argument("-a", "--archivo", metavar="JSON",
                   help="Fichero de acciones (por defecto ./acciones.json).")
    p.add_argument("--crear", action="store_true",
                   help="Crear una plantilla de acciones.json de ejemplo.")
    _anadir_comunes(p)

    return parser


# ---------------------------------------------------------------------- #
# Factoría de seguridad
# ---------------------------------------------------------------------- #
def crear_seguridad(args: argparse.Namespace) -> Seguridad:
    """Construye el objeto Seguridad compartido a partir de los argumentos."""
    return Seguridad(
        dry_run=getattr(args, "dry_run", False),
        restringido=getattr(args, "restringido", False),
        rutas_permitidas=getattr(args, "permitido", None) or [],
        confirmador=lambda pregunta: Interfaz.confirmar(pregunta, por_defecto=False),
        papelera_dir=getattr(args, "papelera", None),
    )


# ---------------------------------------------------------------------- #
# Handlers de subórdenes -> código de salida
# ---------------------------------------------------------------------- #
def _fin(resultado) -> int:
    Interfaz.resumen(resultado.exito, resultado.omitidos, resultado.errores)
    return 1 if resultado.errores else 0


def cmd_mover(args: argparse.Namespace, seg: Seguridad) -> int:
    res = Mover(seg).mover(
        args.origenes,
        args.destino,
        crear_destino=args.crear_destino,
        no_sobrescribir=args.no_sobrescribir,
        forzar=args.yes,
    )
    return _fin(res)


def cmd_borrar(args: argparse.Namespace, seg: Seguridad) -> int:
    if not args.permanente:
        if seg.papelera_dir is None:
            if not sys.stdin.isatty():
                Interfaz.error(
                    "Sin papelera configurada y sin terminal interactiva. "
                    "Usa --papelera RUTA o --permanente."
                )
                return 2
            papelera = Interfaz.pedir_ruta(
                "Carpeta que hará de papelera",
            )
            args.papelera = papelera
        if args.papelera:
            seg.papelera_dir = Path(args.papelera).expanduser()

    res = Borrar(seg).borrar(
        args.rutas,
        papelera=not args.permanente,
        recursivo=args.recursivo,
        forzar=args.yes,
    )
    return _fin(res)


def cmd_organizar(args: argparse.Namespace, seg: Seguridad) -> int:
    res = Organizar(seg).organizar(
        args.directorio, criterio=args.por, incluir_subcarpetas=args.subcarpetas
    )
    return _fin(res)


def cmd_renombrar(args: argparse.Namespace, seg: Seguridad) -> int:
    r = Renombrar(seg)
    rutas = list(args.rutas)
    nuevo = args.nuevo
    # Forma abreviada: `renombrar archivo.pdf nuevo_nombre.pdf`
    if nuevo is None and len(rutas) == 2:
        nuevo = rutas.pop()
    if nuevo:
        if len(rutas) != 1:
            Interfaz.error("Con un nombre nuevo solo se puede renombrar un archivo.")
            return 2
        res = r.renombrar(rutas[0], nuevo, forzar=args.yes)
    elif args.prefijo is not None:
        res = r.prefijo(rutas, args.prefijo, forzar=args.yes)
    elif args.sufijo is not None:
        res = r.sufijo(rutas, args.sufijo, forzar=args.yes)
    elif args.buscar is not None:
        res = r.patron(rutas, args.buscar, args.reemplazar,
                       regex=args.regex, forzar=args.yes)
    elif args.numerar:
        res = r.numerar(rutas, plantilla=args.plantilla, forzar=args.yes)
    else:
        Interfaz.error(
            "Indica una accion: --nuevo, --prefijo, --sufijo, --buscar o --numerar."
        )
        return 2
    return _fin(res)


def cmd_buscar(args: argparse.Namespace, seg: Seguridad) -> int:
    try:
        resultados = Buscar(seg).buscar(
            patron=args.patron,
            extension=args.extension,
            tamano=args.tamano,
            modificado=args.modificado,
            ruta=args.directorio,
            tipo=args.tipo,
            max_resultados=args.max,
        )
    except ValueError as exc:
        Interfaz.error(str(exc))
        return 2
    return 0 if resultados else 1


def cmd_info(args: argparse.Namespace, seg: Seguridad) -> int:
    Informacion(seg).info(args.rutas)
    return 0


def cmd_crear(args: argparse.Namespace, seg: Seguridad) -> int:
    return _fin(Crear(seg).crear(args.rutas))


def cmd_acciones(args: argparse.Namespace, seg: Seguridad) -> int:
    acciones = Acciones(seg, archivo=args.archivo)
    if args.crear:
        res = acciones.plantilla(forzar=args.yes)
        return 1 if res.errores else 0
    if args.accion:
        res = acciones.ejecutar(args.accion, forzar=args.yes)
        return _fin(res)
    return acciones.listar()


HANDLERS = {
    "mover": cmd_mover,
    "borrar": cmd_borrar,
    "organizar": cmd_organizar,
    "renombrar": cmd_renombrar,
    "buscar": cmd_buscar,
    "info": cmd_info,
    "crear": cmd_crear,
    "acciones": cmd_acciones,
}


# ---------------------------------------------------------------------- #
# Menú interactivo
# ---------------------------------------------------------------------- #
def menu_interactivo(seguridad: Seguridad) -> None:
    """Bucle principal del menú interactivo."""
    Interfaz.banner()
    acciones = {
        "1": Mover(seguridad).menu_interactivo,
        "2": Borrar(seguridad).menu_interactivo,
        "3": Organizar(seguridad).menu_interactivo,
        "4": Renombrar(seguridad).menu_interactivo,
        "5": Buscar(seguridad).menu_interactivo,
        "6": Informacion(seguridad).menu_interactivo,
        "7": Crear(seguridad).menu_interactivo,
        "8": Acciones(seguridad).menu_interactivo,
    }
    while True:
        try:
            opcion = Interfaz.menu()
        except (EOFError, KeyboardInterrupt):
            break
        if opcion == "9":
            break
        if seguridad.dry_run:
            Interfaz.aviso("MODO SIMULACION activo: no se modificara nada.")
        try:
            acciones[opcion]()
        except (EOFError, KeyboardInterrupt):
            Interfaz.aviso("Operacion interrumpida.")
        except Exception as exc:  # noqa: BLE001 - el menú no debe caerse
            Interfaz.error(f"Error inesperado: {exc}")
            log.exception("Error en el menu (opcion %s)", opcion)
    Interfaz.info("Hasta pronto.")


# ---------------------------------------------------------------------- #
# Punto de entrada
# ---------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    parser = crear_parser()
    args = parser.parse_args(argv)
    Logger.obtener("main")

    if args.comando is None:
        # Modo interactivo: la seguridad se configura con valores neutros
        # y el usuario decide confirmaciones en cada operación.
        papelera = str(Path.home() / ".file-manager-papelera")
        menu_interactivo(Seguridad(confirmador=lambda p: Interfaz.confirmar(p),
                                   papelera_dir=papelera))
        return 0

    seguridad = crear_seguridad(args)
    handler = HANDLERS[args.comando]
    try:
        return handler(args, seguridad)
    except FileNotFoundError as exc:
        Interfaz.error(str(exc))
        return 2
    except PermissionError as exc:
        Interfaz.error(str(exc))
        return 2
    except KeyboardInterrupt:
        Interfaz.aviso("Interrumpido por el usuario.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
