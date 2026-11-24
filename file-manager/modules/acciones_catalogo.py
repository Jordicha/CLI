"""Catálogo de acciones: concentración, plantilla y validación previa."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from modules.buscar import Buscar
from utils.config import Config
from utils.errores import AccionNoValida, ConfigError
from utils.interfaz import Interfaz

ARCHIVO_ACCIONES = "acciones.json"

OPERACIONES = (
    "crear",
    "mover",
    "copiar",
    "organizar",
    "renombrar",
    "buscar",
    "tamano",
    "ejecutar",
    "clasificar_ia",
    "renombrar_ia",
)

CRITERIOS_ORGANIZAR = ("extension", "fecha", "creacion", "modificacion", "tamano")
TIPOS_BUSQUEDA = ("archivo", "carpeta", "todo")
MODOS_RENOMBRAR = ("nuevo", "prefijo", "sufijo", "buscar", "numerar")

PLANTILLA: Dict[str, Any] = {
    "preparar-informes": {
        "descripcion": "Crea la estructura de informes y copia los CSV de datos.",
        "pasos": [
            {"crear": ["informes", "informes/datos"]},
            {
                "copiar": {
                    "origenes": ["*.csv"],
                    "destino": "informes/datos",
                    "no_sobrescribir": True,
                }
            },
        ],
    },
    "limpiar-temporales": {
        "descripcion": "Envía a la papelera los .tmp de la carpeta actual.",
        "pasos": [
            {"buscar": {"patron": "*.tmp", "directorio": "."}},
            {
                "mover": {
                    "origenes": ["*.tmp"],
                    "destino": "~/.file-manager-papelera",
                    "crear_destino": True,
                    "no_sobrescribir": True,
                }
            },
        ],
    },
    "ordenar-descargas": {
        "descripcion": "Clasifica ~/Descargas por tipo de archivo.",
        "pasos": [
            {"organizar": {"directorio": "~/Descargas", "por": "extension"}}
        ],
    },
    "responder-copia": {
        "descripcion": "Copia los PDF recientes de la carpeta actual a respaldo/.",
        "pasos": [
            {
                "copiar": {
                    "origenes": ["*.pdf"],
                    "destino": "respaldo",
                    "crear_destino": True,
                    "no_sobrescribir": True,
                }
            }
        ],
    },
    "reporte-tamano": {
        "descripcion": "Avisa si la carpeta actual supera los 500 MB.",
        "pasos": [{"tamano": {"directorio": ".", "alerta_mb": 500}}],
    },
    "clasificar-con-ia": {
        "descripcion": "Clasifica ~/Descargas con IA; sin IA usa la extensión.",
        "pasos": [
            {"clasificar_ia": {"directorio": "~/Descargas", "max": 20}}
        ],
    },
    "renombrar-con-ia": {
        "descripcion": "Propone nombres claros para los PDF de la carpeta actual.",
        "pasos": [
            {"renombrar_ia": {"rutas": ["*.pdf"], "max": 10}}
        ],
    },
}


class CatalogoAcciones:
    """Lee y valida ``acciones.json`` antes de que se ejecute ningún paso."""

    def __init__(
        self, archivo: str | Path | None = None, interfaz: Optional[Interfaz] = None
    ) -> None:
        self._archivo = Path(archivo).expanduser() if archivo else None
        self.interfaz = interfaz or Interfaz()

    @classmethod
    def desde_config(
        cls,
        config: Config,
        interfaz: Optional[Interfaz] = None,
        archivo: str | Path | None = None,
    ) -> "CatalogoAcciones":
        """Fábrica del catálogo a partir de la configuración compartida."""
        origen = archivo if archivo is not None else config.archivo_acciones
        return cls(origen, interfaz)

    @property
    def ruta(self) -> Path:
        """Devuelve la ruta del catálogo (existente o la ubicación por defecto)."""
        if self._archivo is not None:
            return self._archivo
        aqui = Path.cwd() / ARCHIVO_ACCIONES
        if aqui.exists():
            return aqui
        return Path(__file__).resolve().parent.parent / ARCHIVO_ACCIONES

    def cargar(self, obligatoria: bool = True) -> Dict[str, Any]:
        """Lee y valida el catálogo; devuelve ``nombre -> definición``."""
        ruta = self.ruta
        if not ruta.exists():
            if obligatoria:
                self.interfaz.error(
                    f"No existe el catálogo de acciones: {ruta}\n"
                    f"Crea una plantilla con: python main.py acciones --crear"
                )
            return {}
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ConfigError(f"acciones.json no es un JSON válido: {exc}") from exc
        if not isinstance(datos, dict):
            raise ConfigError("acciones.json debe ser un objeto { nombre: accion }.")
        for nombre, accion in datos.items():
            if not isinstance(nombre, str) or not nombre.strip():
                raise ConfigError("Los nombres de accion deben ser textos no vacios.")
            if not isinstance(accion, dict) or "pasos" not in accion:
                raise ConfigError(
                    f"La accion '{nombre}' debe tener la forma "
                    f'{{"descripcion": "...", "pasos": [...]}}.'
                )
            if not isinstance(accion["pasos"], list) or not accion["pasos"]:
                raise ConfigError(
                    f"Accion '{nombre}', campo 'pasos': debe ser una lista no vacia."
                )
            if not isinstance(accion.get("descripcion", ""), str):
                raise ConfigError(
                    f"Accion '{nombre}', campo 'descripcion': debe ser texto."
                )
            for i, paso in enumerate(accion["pasos"], start=1):
                self.validar_paso(nombre, i, paso)
        assert all(
            isinstance(accion, dict) and isinstance(accion["pasos"], list)
            for accion in datos.values()
        )
        return datos

    @staticmethod
    def validar_paso(nombre: str, i: int, paso: Any) -> None:
        """Valida un paso y detalla la acción, el paso y el campo que falla."""
        if not isinstance(paso, dict) or len(paso) != 1:
            raise AccionNoValida(
                f"Accion '{nombre}', paso {i}: cada paso debe ser un objeto "
                f"con UNA operacion ({', '.join(OPERACIONES)})."
            )
        operacion, argumentos = next(iter(paso.items()))
        if operacion not in OPERACIONES:
            raise AccionNoValida(
                f"Accion '{nombre}', paso {i}: operacion desconocida "
                f"'{operacion}'. Validas: {', '.join(OPERACIONES)}."
            )
        assert operacion in OPERACIONES
        if operacion == "ejecutar":
            args: Dict[str, Any] = {"orden": argumentos}
        elif isinstance(argumentos, dict):
            args = argumentos
        else:
            args = {"valor": argumentos}

        def fallar(campo: str, detalle: str) -> None:
            raise AccionNoValida(
                f"Accion '{nombre}', paso {i} ({operacion}): "
                f"campo '{campo}' {detalle}."
            )

        def texto(
            campo: str, obligatorio: bool = True, alias: Optional[str] = None
        ) -> None:
            valor = args.get(campo)
            if valor is None and alias:
                valor = args.get(alias)
            if valor is None:
                if obligatorio:
                    fallar(campo, "es obligatorio")
                return
            if not isinstance(valor, str) or (obligatorio and not valor.strip()):
                fallar(
                    campo,
                    "debe ser texto no vacio" if obligatorio else "debe ser texto",
                )

        def lista(campo: str, alias: Optional[str] = None) -> None:
            valor = args.get(campo)
            if valor is None and alias:
                valor = args.get(alias)
            if valor is None:
                fallar(campo, "es obligatorio")
            if isinstance(valor, str):
                if not valor.strip():
                    fallar(campo, "no puede estar vacio")
                return
            if (
                not isinstance(valor, list)
                or not valor
                or not all(isinstance(v, str) and v.strip() for v in valor)
            ):
                fallar(campo, "debe ser una lista no vacia de textos")

        def booleano(campo: str) -> None:
            if campo in args and not isinstance(args[campo], bool):
                fallar(campo, "debe ser verdadero o falso")

        def numero(campo: str, minimo: float = 0) -> None:
            valor = args.get(campo)
            if valor is None:
                return
            if isinstance(valor, bool) or not isinstance(valor, (int, float)):
                fallar(campo, "debe ser un numero")
            if valor < minimo:
                fallar(campo, f"debe ser >= {minimo}")

        if operacion == "crear":
            lista("rutas", alias="valor")

        elif operacion in ("mover", "copiar"):
            lista("origenes")
            texto("destino")
            booleano("crear_destino")
            booleano("no_sobrescribir")

        elif operacion == "organizar":
            texto("directorio", alias="valor")
            criterio = args.get("por")
            if criterio is not None and criterio not in CRITERIOS_ORGANIZAR:
                fallar(
                    "por",
                    f"debe ser uno de {', '.join(CRITERIOS_ORGANIZAR)}",
                )
            booleano("subcarpetas")

        elif operacion == "renombrar":
            lista("rutas", alias="valor")
            modos = [
                modo for modo in MODOS_RENOMBRAR if args.get(modo) not in (None, False)
            ]
            if not modos:
                fallar(
                    "nuevo/prefijo/sufijo/buscar/numerar", "se requiere al menos uno"
                )
            if "nuevo" in modos:
                texto("nuevo")
            for campo in ("prefijo", "sufijo", "buscar", "reemplazar", "plantilla"):
                if campo in args and not isinstance(args[campo], str):
                    fallar(campo, "debe ser texto")
            for campo in ("numerar", "regex"):
                booleano(campo)

        elif operacion == "buscar":
            for campo in ("patron", "extension", "tamano", "modificado", "directorio"):
                texto(campo, obligatorio=False)
            tipo = args.get("tipo")
            if tipo is not None and tipo not in TIPOS_BUSQUEDA:
                fallar("tipo", f"debe ser uno de {', '.join(TIPOS_BUSQUEDA)}")
            maximo = args.get("max")
            if maximo is not None and (
                isinstance(maximo, bool) or not isinstance(maximo, int) or maximo < 1
            ):
                fallar("max", "debe ser un entero positivo")
            if args.get("tamano"):
                try:
                    Buscar._rango_tamano(args["tamano"])
                except ValueError as exc:
                    fallar("tamano", str(exc))
            if args.get("modificado"):
                try:
                    Buscar._rango_fecha(args["modificado"])
                except (ValueError, AttributeError, TypeError) as exc:
                    fallar("modificado", str(exc))

        elif operacion == "tamano":
            texto("directorio", obligatorio=False)
            numero("alerta_mb")

        elif operacion == "ejecutar":
            texto("orden")
            numero("timeout", minimo=1)

        elif operacion in ("clasificar_ia", "renombrar_ia"):
            if operacion == "clasificar_ia":
                texto("directorio", obligatorio=False)
                texto("patron", obligatorio=False)
            else:
                lista("rutas", alias="valor")
            maximo = args.get("max")
            if maximo is not None and (
                isinstance(maximo, bool)
                or not isinstance(maximo, int)
                or not 1 <= maximo <= 100
            ):
                fallar("max", "debe ser un entero entre 1 y 100")
