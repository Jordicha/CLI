"""Acciones personalizadas definidas en ``acciones.json``.

Permite al usuario definir sus propias operaciones compuestas
(reuniones, limpieza de temporales, respaldos, reportes...) en un
archivo JSON y ejecutarlas desde la CLI:

    python main.py acciones                 # listado
    python main.py acciones --crear         # plantilla de ejemplo
    python main.py acciones limpiar-temporales --dry-run

Formato del archivo (``acciones.json`` en la raíz del proyecto):

    {
      "nombre-accion": {
        "descripcion": "Texto explicativo",
        "pasos": [
          {"crear": ["ruta1", "ruta2"]},
          {"mover": {"origenes": ["*.log"], "destino": "hist/",
                     "crear_destino": true, "no_sobrescribir": true}},
          {"copiar": {"origenes": ["a.txt"], "destino": "backup/"}},
          {"organizar": {"directorio": "descargas", "por": "extension"}},
          {"renombrar": {"rutas": ["a.txt"], "prefijo": "previo_"}},
          {"buscar": {"patron": "factura", "extension": "pdf"}},
          {"tamano": {"directorio": ".", "alerta_mb": 100}},
          {"ejecutar": "echo hola"}
        ]
      }
    }

Todos los pasos pasan por las mismas comprobaciones de seguridad
(dry-run, modo restringido y confirmaciones) que las operaciones sueltas.
"""

from __future__ import annotations

import fnmatch
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from modules._resultado import Resultado
from modules.buscar import Buscar, _tamano_legible
from modules.crear import Crear
from modules.informacion import Informacion
from modules.mover import Mover
from modules.organizar import Organizar
from modules.renombrar import Renombrar
from utils.interfaz import Interfaz
from utils.logger import Logger
from utils.seguridad import Seguridad

log = Logger.obtener("acciones")

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
)

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
}


class Acciones:
    """Catálogo y ejecutor de acciones personalizadas definidas en JSON."""

    def __init__(
        self,
        seguridad: Seguridad,
        archivo: str | Path | None = None,
        interfaz: Optional[Interfaz] = None,
    ) -> None:
        """Inicializa el gestor de acciones.

        Args:
            seguridad: Objeto de seguridad compartido (dry-run, restringido...).
            archivo: Ruta del JSON de acciones. Por defecto se buscan,
                en orden: ``./acciones.json`` y ``acciones.json`` junto a
                ``main.py``.
            interfaz: Interfaz opcional para la salida.
        """
        self.seguridad = seguridad
        self._archivo = Path(archivo).expanduser() if archivo else None
        self.interfaz = interfaz or Interfaz()

    # ------------------------------------------------------------------ #
    # Carga del catálogo
    # ------------------------------------------------------------------ #
    @property
    def ruta_catalogo(self) -> Path:
        """Devuelve la ruta del catálogo (existente o la ubicación por defecto)."""
        if self._archivo is not None:
            return self._archivo
        aqui = Path.cwd() / ARCHIVO_ACCIONES
        if aqui.exists():
            return aqui
        return Path(__file__).resolve().parent.parent / ARCHIVO_ACCIONES

    def cargar(self, obligatoria: bool = True) -> Dict[str, Any]:
        """Lee y valida el catálogo de acciones.

        Args:
            obligatoria: Si es True y el archivo no existe o está vacío,
                se informa y devuelve ``{}`` (no lanza excepción).

        Returns:
            Diccionario ``nombre -> definicion``.

        Raises:
            ValueError: si el JSON es inválido o no respeta el formato.
        """
        ruta = self.ruta_catalogo
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
            raise ValueError(f"acciones.json no es un JSON válido: {exc}") from exc
        if not isinstance(datos, dict):
            raise ValueError("acciones.json debe ser un objeto { nombre: accion }.")
        for nombre, accion in datos.items():
            if not isinstance(accion, dict) or not isinstance(
                accion.get("pasos"), list
            ):
                raise ValueError(
                    f"La accion '{nombre}' debe tener la forma "
                    f'{{"descripcion": "...", "pasos": [...]}}.'
                )
        return datos

    def plantilla(self, forzar: bool = False) -> Resultado:
        """Crea el archivo de acciones con una plantilla de ejemplo.

        Con ``-a`` se escribe en esa ruta; si no, en el directorio actual
        (sin sobrescribir el catálogo del proyecto donde vive main.py).
        """
        resultado = Resultado()
        if self._archivo is not None:
            ruta = self._archivo
        else:
            ruta = Path.cwd() / ARCHIVO_ACCIONES
            catalogo = self.ruta_catalogo
            es_catalogo_proyecto = (
                ruta.exists()
                and catalogo.exists()
                and ruta.resolve() == catalogo.resolve()
            )
            if es_catalogo_proyecto:
                destino_alternativo = Path("~").expanduser() / ARCHIVO_ACCIONES
                self.interfaz.aviso(
                    f"El catalogo del proyecto ya existe: {ruta}\n"
                    f"Indica otra ubicacion con -a RUTA "
                    f"(p. ej. -a {destino_alternativo})"
                )
                resultado.omitidos += 1
                return resultado
        if ruta.exists() and not forzar:
            if not self.seguridad.confirmar(
                f"Ya existe {ruta}. ¿Sobrescribir con la plantilla?"
            ):
                self.interfaz.info("Cancelado: se conserva el catálogo actual.")
                resultado.omitidos += 1
                return resultado
        if self.seguridad.dry_run:
            self.interfaz.simulacion(f"Crear plantilla de acciones en {ruta}")
            resultado.ok()
            return resultado
        ruta.write_text(
            json.dumps(PLANTILLA, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        self.interfaz.ok(f"Plantilla creada: {ruta}")
        self.interfaz.info(
            f"{len(PLANTILLA)} acciones disponibles. Ajusta las rutas a tu caso."
        )
        log.info("PLANTILLA creada en %s", ruta)
        resultado.ok()
        return resultado

    # ------------------------------------------------------------------ #
    # Listado
    # ------------------------------------------------------------------ #
    def listar(self) -> int:
        """Muestra las acciones definidas y devuelve código de salida."""
        try:
            datos = self.cargar()
        except ValueError as exc:
            self.interfaz.error(str(exc))
            return 2
        if not datos:
            return 1
        filas = []
        for nombre, accion in datos.items():
            operaciones = ", ".join(
                sorted(
                    {op for paso in accion["pasos"] if isinstance(paso, dict) for op in paso}
                )
            )
            filas.append(
                (
                    nombre,
                    accion.get("descripcion", ""),
                    str(len(accion["pasos"])),
                    operaciones,
                )
            )
        Interfaz.tabla(
            f"Acciones personalizadas ({self.ruta_catalogo})",
            ["Nombre", "Descripción", "Pasos", "Operaciones"],
            filas,
        )
        return 0

    # ------------------------------------------------------------------ #
    # Ejecución
    # ------------------------------------------------------------------ #
    def ejecutar(self, nombre: str, forzar: bool = False) -> Resultado:
        """Ejecuta todos los pasos de la acción ``nombre``."""
        resultado = Resultado()
        try:
            datos = self.cargar()
        except ValueError as exc:
            self.interfaz.error(str(exc))
            resultado.errores += 1
            return resultado
        accion = datos.get(nombre)
        if accion is None:
            self.interfaz.error(
                f"No existe la accion '{nombre}'. Disponibles: "
                f"{', '.join(datos) if datos else '(ninguna)'}"
            )
            resultado.errores += 1
            return resultado

        descripcion = accion.get("descripcion", "")
        self.interfaz.encabezado(f"ACCION: {nombre}")
        if descripcion:
            self.interfaz.info(descripcion)
        if self.seguridad.dry_run:
            self.interfaz.aviso("MODO SIMULACION: no se modificara nada.")

        for i, paso in enumerate(accion["pasos"], start=1):
            try:
                operacion, argumentos = self._interpretar(paso)
            except ValueError as exc:
                self.interfaz.error(f"Paso {i}: {exc}")
                resultado.errores += 1
                continue
            etiqueta = f"[{i}/{len(accion['pasos'])}] {operacion}"
            self._log_paso(nombre, i, operacion, argumentos)
            try:
                res = self._despachar(operacion, argumentos, forzar)
            except Exception as exc:  # noqa: BLE001 - la acción no debe caerse
                self.interfaz.error(f"{etiqueta}: {exc}")
                log.exception("Accion '%s' paso %d fallo", nombre, i)
                resultado.errores += 1
                continue
            resultado.exito += res.exito
            resultado.omitidos += res.omitidos
            resultado.errores += res.errores
        return resultado

    # ------------------------------------------------------------------ #
    # Internos
    # ------------------------------------------------------------------ #
    @staticmethod
    def _expandir(origenes: Iterable[str]) -> List[str]:
        """Expande comodines (``*.csv``) relative al directorio actual.

        Si un patrón no coincide con nada se conserva tal cual para que el
        módulo correspondiente reporte el error de forma consistente.
        """
        ampliadas: List[str] = []
        for r in origenes:
            if any(c in r for c in "*?["):
                coincidencias = sorted(str(p) for p in Path(".").glob(r))
                if coincidencias:
                    ampliadas.extend(coincidencias)
                    continue
            ampliadas.append(r)
        return ampliadas

    @staticmethod
    def _interpretar(paso: Any) -> Tuple[str, Dict[str, Any]]:
        """Valida un paso y devuelve ``(operacion, argumentos)``."""
        if not isinstance(paso, dict) or len(paso) != 1:
            raise ValueError(
                "Cada paso debe ser un objeto con UNA operacion: "
                + ", ".join(OPERACIONES)
            )
        operacion, argumentos = next(iter(paso.items()))
        if operacion not in OPERACIONES:
            raise ValueError(
                f"Operacion desconocida '{operacion}'. "
                f"Validas: {', '.join(OPERACIONES)}"
            )
        if operacion == "ejecutar":
            argumentos = {"orden": argumentos}
        if not isinstance(argumentos, dict):
            argumentos = {"valor": argumentos}
        return operacion, argumentos

    def _log_paso(self, nombre: str, i: int, operacion: str, args: Dict[str, Any]):
        log.info("ACCION %s paso %d: %s %s", nombre, i, operacion, args)

    def _despachar(
        self, operacion: str, args: Dict[str, Any], forzar: bool
    ) -> Resultado:
        """Ejecuta un paso delegando en el módulo correspondiente."""
        vacio = Resultado()
        seg = self.seguridad

        if operacion == "crear":
            rutas = self._requerir_lista(args, "rutas", vacio)
            return Crear(seg).crear(rutas) if rutas else vacio

        if operacion == "mover":
            origenes = self._requerir_lista(args, "origenes", vacio)
            destino = args.get("destino")
            if not origenes or not destino:
                self.interfaz.error("mover necesita 'origenes' y 'destino'.")
                return vacio
            return Mover(seg).mover(
                origenes,
                destino,
                crear_destino=bool(args.get("crear_destino", False)),
                no_sobrescribir=bool(args.get("no_sobrescribir", True)),
                forzar=forzar,
            )

        if operacion == "copiar":
            return self._copiar(args, forzar)

        if operacion == "organizar":
            directorio = args.get("directorio") or args.get("valor")
            if not directorio:
                self.interfaz.error("organizar necesita 'directorio'.")
                return vacio
            return Organizar(seg).organizar(
                directorio,
                criterio=args.get("por", "extension"),
                incluir_subcarpetas=bool(args.get("subcarpetas", False)),
            )

        if operacion == "renombrar":
            return self._renombrar(args, forzar)

        if operacion == "buscar":
            encontrados = Buscar(seg).buscar(
                patron=args.get("patron") or args.get("valor"),
                extension=args.get("extension"),
                tamano=args.get("tamano"),
                modificado=args.get("modificado"),
                ruta=args.get("directorio", "."),
                tipo=args.get("tipo", "archivo"),
                max_resultados=args.get("max", 200),
            )
            resultado = Resultado()
            if encontrados:
                resultado.ok(f"{len(encontrados)} coincidencia(s)")
            else:
                resultado.omitido("sin coincidencias")
            return resultado

        if operacion == "tamano":
            return self._tamano(args)

        if operacion == "ejecutar":
            return self._ejecutar(args, forzar)

        self.interfaz.error(f"Operacion no implementada: {operacion}")
        return vacio

    # ------------------------------------------------------------------ #
    def _requerir_lista(
        self, args: Dict[str, Any], clave: str, vacio: Resultado
    ) -> Optional[List[str]]:
        """Devuelve ``args[clave]`` como lista, o ``None`` con error mostrado."""
        valor = args.get(clave) or args.get("valor")
        if valor is None:
            self.interfaz.error(f"Falta el parametro '{clave}'.")
            return None
        if isinstance(valor, str):
            valor = [valor]
        if not isinstance(valor, list) or not valor:
            self.interfaz.error(f"'{clave}' debe ser una lista no vacia.")
            return None
        return self._expandir(str(v) for v in valor)

    def _copiar(self, args: Dict[str, Any], forzar: bool) -> Resultado:
        """Copia archivos a un destino respetando seguridad y dry-run."""
        resultado = Resultado()
        origenes = self._requerir_lista(args, "origenes", resultado)
        destino = args.get("destino")
        if origenes is None or not destino:
            self.interfaz.error("copiar necesita 'origenes' y 'destino'.")
            return resultado
        try:
            destino_dir = self.seguridad.validar_destino(
                destino, crear=bool(args.get("crear_destino", False))
            )
        except (FileNotFoundError, NotADirectoryError, PermissionError) as exc:
            self.interfaz.error(str(exc))
            resultado.errores += 1
            return resultado
        no_over = bool(args.get("no_sobrescribir", True))
        for r in Seguridad.expandir_rutas(origenes):
            try:
                origen = self.seguridad.validar_existente(r, "el origen")
                self.seguridad.comprobar_permitido(origen)
                final = destino_dir / origen.name
                if final.exists():
                    if no_over:
                        final = self.seguridad.ruta_libre(final)
                    elif not self.seguridad.se_puede_sobrescribir(
                        final, forzar=forzar
                    ):
                        resultado.omitidos += 1
                        continue
                if self.seguridad.dry_run:
                    tipo = "carpeta" if origen.is_dir() else "archivo"
                    self.interfaz.simulacion(
                        f"Copiar {tipo}: {origen} -> {final}"
                    )
                else:
                    if origen.is_dir():
                        shutil.copytree(origen, final)
                    else:
                        shutil.copy2(origen, final)
                    self.interfaz.ok(f"Copiado: {origen} -> {final}")
                log.info("COPIADO %s -> %s", origen, final)
                resultado.ok()
            except (FileNotFoundError, PermissionError, OSError) as exc:
                self.interfaz.error(f"No se pudo copiar {r}: {exc}")
                resultado.errores += 1
        return resultado

    def _renombrar(self, args: Dict[str, Any], forzar: bool) -> Resultado:
        """Renombra vía nuevo/prefijo/sufijo/patron/numerar."""
        r = Renombrar(self.seguridad)
        rutas = [str(x) for x in (args.get("rutas") or [])]
        if not rutas:
            self.interfaz.error("renombrar necesita 'rutas'.")
            res = Resultado()
            res.errores += 1
            return res
        if args.get("nuevo"):
            if len(rutas) != 1:
                self.interfaz.error("'nuevo' solo sirve con 1 archivo.")
                res = Resultado()
                res.errores += 1
                return res
            return r.renombrar(rutas[0], args["nuevo"], forzar=forzar)
        if args.get("prefijo") is not None:
            return r.prefijo(rutas, args["prefijo"], forzar=forzar)
        if args.get("sufijo") is not None:
            return r.sufijo(rutas, args["sufijo"], forzar=forzar)
        if args.get("buscar") is not None:
            return r.patron(
                rutas,
                args["buscar"],
                args.get("reemplazar", ""),
                regex=bool(args.get("regex", False)),
                forzar=forzar,
            )
        if args.get("numerar"):
            return r.numerar(
                rutas, plantilla=args.get("plantilla", "{i:02d}"), forzar=forzar
            )
        self.interfaz.error(
            "renombrar necesita: nuevo, prefijo, sufijo, buscar o numerar."
        )
        res = Resultado()
        res.errores += 1
        return res

    def _tamano(self, args: Dict[str, Any]) -> Resultado:
        """Suma el tamaño de un directorio y avisa si supera la alerta."""
        resultado = Resultado()
        ruta = Path(args.get("directorio") or args.get("valor") or ".").expanduser()
        if not ruta.exists():
            self.interfaz.error(f"No existe: {ruta}")
            resultado.errores += 1
            return resultado
        total = 0
        archivos = 0
        for item in (ruta.rglob("*") if ruta.is_dir() else [ruta]):
            if item.is_file():
                try:
                    total += item.stat().st_size
                    archivos += 1
                except OSError:
                    continue
        alerta_mb = args.get("alerta_mb")
        texto = f"{ruta}: {archivos} archivo(s), {_tamano_legible(total)}"
        if alerta_mb is not None and total > float(alerta_mb) * 1024 * 1024:
            self.interfaz.aviso(
                f"{texto} - SUPERA el limite de {alerta_mb} MB"
            )
        else:
            self.interfaz.info(texto)
        log.info("TAMANO %s -> %d bytes", ruta, total)
        resultado.ok()
        return resultado

    def _ejecutar(self, args: Dict[str, Any], forzar: bool) -> Resultado:
        """Ejecuta un comando de shell controlado (con confirmación)."""
        resultado = Resultado()
        orden = args.get("orden") or args.get("valor")
        if not isinstance(orden, str) or not orden.strip():
            self.interfaz.error("ejecutar necesita una orden de texto.")
            resultado.errores += 1
            return resultado
        if not self.seguridad.confirmar(
            f"La accion va a ejecutar en la shell:\n  {orden}\n"
            f"¿Permitir ejecución?",
            forzar=forzar,
        ):
            self.interfaz.aviso("Paso 'ejecutar' cancelado por el usuario.")
            resultado.omitidos += 1
            return resultado
        if self.seguridad.dry_run:
            self.interfaz.simulacion(f"Ejecutar: {orden}")
            resultado.ok()
            return resultado
        try:
            proceso = subprocess.run(
                orden,
                shell=True,
                capture_output=True,
                text=True,
                timeout=args.get("timeout", 120),
            )
            salida = (proceso.stdout + proceso.stderr).strip()
            if salida:
                self.interfaz.info(salida[:2000])
            if proceso.returncode == 0:
                self.interfaz.ok(f"Orden ejecutada (codigo 0): {orden}")
                resultado.ok()
            else:
                self.interfaz.error(
                    f"La orden termino con codigo {proceso.returncode}: {orden}"
                )
                resultado.errores += 1
        except subprocess.TimeoutExpired:
            self.interfaz.error(f"Tiempo superado ejecutando: {orden}")
            resultado.errores += 1
        except OSError as exc:
            self.interfaz.error(f"No se pudo ejecutar: {exc}")
            resultado.errores += 1
        return resultado

    # ------------------------------------------------------------------ #
    # Menú interactivo
    # ------------------------------------------------------------------ #
    def menu_interactivo(self) -> None:
        """Flujo interactivo: lista de acciones y selección."""
        self.interfaz.encabezado("ACCIONES PERSONALIZADAS")
        try:
            datos = self.cargar()
        except ValueError as exc:
            self.interfaz.error(str(exc))
            return
        nombres = list(datos)
        if not nombres:
            if Interfaz.confirmar(
                f"¿Crear plantilla de ejemplo en {self.ruta_catalogo}?"
            ):
                self.plantilla()
            return
        for i, nombre in enumerate(nombres, start=1):
            descripcion = datos[nombre].get("descripcion", "")
            self.interfaz.info(f"[{i}] {nombre} - {descripcion}")
        eleccion = Interfaz.preguntar(
            f"Ejecutar accion (1-{len(nombres)}) o 0 para volver",
            valor_por_defecto="0",
        )
        try:
            indice = int(eleccion)
            if 1 <= indice <= len(nombres):
                nombre = nombres[indice - 1]
        except ValueError:
            nombre = eleccion if eleccion in datos else None
        if not nombre:
            self.interfaz.info("Ninguna accion seleccionada.")
            return
        res = self.ejecutar(nombre)
        self.interfaz.resumen(res.exito, res.omitidos, res.errores)
