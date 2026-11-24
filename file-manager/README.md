# File Manager CLI

Gestor de archivos por terminal, rápido y seguro, escrito en **Python 3**.

Permite mover, borrar, organizar, renombrar, buscar y consultar archivos y
carpetas, tanto desde un **menú interactivo** con colores como mediante
**comandos directos** con `argparse`.

```
===================================
       FILE MANAGER CLI
===================================
[1] Mover archivos
[2] Borrar archivos
[3] Organizar archivos automáticamente
[4] Renombrar archivos
[5] Buscar archivos
[6] Mostrar información
[7] Crear carpeta
[8] Acciones personalizadas
[9] Salir
```

## Características

- **Mover** archivos y carpetas con comprobación de destino y protección
  contra sobrescritura.
- **Borrar** con confirmación explícita y **papelera de eliminación segura**.
- **Organizar automáticamente** por extensión, fecha (creación/modificación)
  o tamaño, creando las carpetas de categoría.
- **Renombrar** en lote: prefijos, sufijos, patrones (texto o regex) y
  numeración automática.
- **Buscar** por nombre, extensión, tamaño y fecha de modificación.
- **Información** detallada: nombre, ruta, extensión, tamaño, permisos y
  fechas de creación/modificación/acceso.
- **Acciones personalizadas**: define tus propias operaciones compuestas
  en `acciones.json` y ejecútalas con un solo comando.
- **Seguridad**: modo simulación (`--dry-run`), modo restringido por
  directorios, confirmaciones obligatorias y registro en log.
- Compatible con **Linux y Windows**.

## Instalación en una orden

Requisitos: Python 3.10 o superior y `pipx` (o `uv`).

```bash
pipx install git+https://github.com/Jordicha/CLI
```

Equivalente con `uv`:

```bash
uv tool install git+https://github.com/Jordicha/CLI
```

Eso instala el comando `file-manager`, disponible en cualquier carpeta.
El historial de versiones está en [CHANGELOG.md](../CHANGELOG.md).

Para desarrollar desde el clon:

```bash
cd file-manager
python3 -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q
```

## Uso

Tras instalar, ejecuta `file-manager` desde cualquier directorio. Dentro del
clon, el equivalente es `python main.py` desde `file-manager/`.

### Menú interactivo

```bash
file-manager
```

### Comandos directos

```bash
file-manager --help
file-manager organizar ~/Descargas
file-manager mover archivo.pdf ~/Documentos/
file-manager borrar archivo.pdf                   # a la papelera (seguro)
file-manager buscar "factura"
file-manager buscar "factura" -e pdf -t ">=1MB" -m "ultimo-30dias"
file-manager info archivo.pdf
file-manager renombrar archivo.pdf nuevo_nombre.pdf
file-manager crear ~/Proyectos/nuevo
file-manager acciones
file-manager acciones ordenar-descargas --dry-run
```

### Subórdenes y ejemplos

#### mover

```bash
file-manager mover *.png ~/Imágenes/            # admite comodines
file-manager mover archivo.pdf ~/Documentos/ --no-sobrescribir
file-manager mover carpeta ~/backup/ -c         # crea el destino si falta
```

#### borrar

Por defecto borra **enviando a la papelera** (`~/.file-manager-papelera`
o la que indiques con `--papelera`):

```bash
file-manager borrar archivo.pdf                       # a la papelera
file-manager borrar archivo.pdf --papelera ~/papelera
file-manager borrar archivo.pdf --permanente          # borrado definitivo
file-manager borrar carpeta --permanente -r           # carpeta con contenido
```

#### organizar

```bash
file-manager organizar ~/Descargas                        # por extensión
file-manager organizar ~/Descargas --por fecha            # AAAA-MM
file-manager organizar ~/Descargas --por tamano           # rangos
file-manager organizar ~/Descargas -s                     # incluye subcarpetas
file-manager organizar ~/Descargas --dry-run              # simulación
```

Categorías por extensión: `Imagenes`, `Videos`, `Audio`, `Documentos`,
`Hojas_de_calculo`, `Comprimidos`, `Programacion`, `Ejecutables` y `Otros`.

#### renombrar

```bash
file-manager renombrar viejo.pdf nuevo.pdf            # individual
file-manager renombrar *.jpg --prefijo "vacaciones_"
file-manager renombrar *.jpg --sufijo "_editado"
file-manager renombrar *.pdf --buscar "borrador" --reemplazar "final"
file-manager renombrar *.txt --buscar '^(\d+)' --reemplazar 'doc_\1' --regex
file-manager renombrar *.jpg --numerar --plantilla "playa_{i:02d}"
```

#### buscar

```bash
file-manager buscar "informe"                 # texto en el nombre
file-manager buscar "*.iso"                   # comodines
file-manager buscar -e pdf -d ~/Documentos    # por extensión
file-manager buscar -t ">=100MB"              # o "<=1GB", "1MB-500MB"
file-manager buscar -m "ultimo-7dias"         # o ">2024-01-01", "<2024-12-31"
file-manager buscar "temp" --tipo carpeta
```

#### info y crear

```bash
file-manager info archivo.pdf ~/Descargas     # archivos y carpetas
file-manager crear ~/Proyectos/2026/informe   # equivalentes a mkdir -p
```

#### acciones (personalizadas)

Incluye `acciones.json` con 7 acciones de ejemplo. Cada acción es una
lista de pasos que reutilizan las operaciones del gestor:

```bash
file-manager acciones                          # listar acciones
file-manager acciones ordenar-descargas        # ejecutar una
file-manager acciones limpiar-temporales --dry-run
file-manager acciones --crear                  # generar plantilla nueva
file-manager acciones mi-accion -a otro.json   # catálogo alternativo
```

Acciones incluidas por defecto:

| Acción              | Qué hace                                              |
| ------------------- | ----------------------------------------------------- |
| `ordenar-descargas` | Clasifica `~/Descargas` por extensión.                |
| `limpiar-temporales`| Busca `*.tmp` y los envía a la papelera.              |
| `informes-mensuales`| Crea `informes/datos` y copia los CSV actuales.       |
| `reporte-tamano`    | Muestra el tamaño total y avisa si supera 500 MB.     |
| `respaldar-csv`     | Crea `backup/datos`, copia los CSV sin sobrescribir y mide el tamaño. |
| `clasificar-con-ia` | Clasifica `~/Descargas` con IA; sin clave/red usa la extensión.      |
| `renombrar-con-ia`  | Propone nombres para los PDF de la carpeta actual; sin IA no toca nada. |

Formato del archivo:

```json
{
  "nombre-accion": {
    "descripcion": "Qué hace",
    "pasos": [
      {"crear": ["informes", "informes/datos"]},
      {"copiar": {"origenes": ["*.csv"], "destino": "informes/datos",
                  "no_sobrescribir": true}},
      {"mover": {"origenes": ["*.tmp"], "destino": "papelera",
                 "crear_destino": true, "no_sobrescribir": true}},
      {"organizar": {"directorio": "~/Descargas", "por": "extension"}},
      {"renombrar": {"rutas": ["a.txt"], "prefijo": "previo_"}},
      {"buscar": {"patron": "factura", "extension": "pdf"}},
      {"tamano": {"directorio": ".", "alerta_mb": 500}},
      {"ejecutar": "echo hola"},
      {"clasificar_ia": {"directorio": "descargas", "max": 20}},
      {"renombrar_ia": {"rutas": ["*.pdf"], "max": 10}}
    ]
  }
}
```

Operaciones disponibles en cada paso: `crear`, `mover`, `copiar`,
`organizar`, `renombrar`, `buscar`, `tamano`, `ejecutar` (esta última
pide confirmación explícita salvo con `--yes`), `clasificar_ia` y
`renombrar_ia`. Los comodines (`*.csv`)
se expanden sobre el directorio actual, también en `renombrar`. Todas las
acciones respetan `--dry-run`, `--restringido` y las confirmaciones; en
una simulación encadenada, los pasos que dependen de carpetas o archivos
creados por pasos anteriores se marcan como simulados en lugar de fallar.

El catálogo se valida por completo antes de ejecutar cualquier paso: si un
campo falta o tiene un tipo incorrecto, el error indica la acción, el paso y
el campo (p. ej. `Accion 'respaldo', paso 2 (mover): campo 'origenes' es obligatorio.`)
y no se toca ningún fichero. Añadir una acción nueva solo requiere editar el
JSON; la decisión de usar configuración externa se explica en el
[ADR 0001](../docs/adr/0001-configuracion-externa.md).

### Capa IA (opcional)

Los pasos `clasificar_ia` y `renombrar_ia` usan OpenAI. Solo envían
**nombres de archivo**: nunca contenidos ni rutas absolutas. La clave se lee
de `OPENAI_API_KEY` en `.env` (o del entorno); `.env` está ignorado por Git
y `.env.example` documenta el resto:

```bash
OPENAI_API_KEY=sk-...
IA_MODELO=gpt-4o-mini
IA_TIMEOUT=8
OPENAI_BASE_URL=https://api.openai.com/v1/chat/completions
```

Si falta la clave, no hay red, la API falla o se usa `--sin-ia`, la CLI lo
explica y sigue: `clasificar_ia` clasifica por extensión y `renombrar_ia`
omite el paso. No hay traceback y las acciones sin IA siguen funcionando.
Antes de mover o renombrar se pide confirmación (salvo `-y`/`--dry-run`).

### Opciones globales de seguridad

| Opción               | Descripción                                             |
| -------------------- | ------------------------------------------------------- |
| `--dry-run`          | Simula la operación sin modificar nada.                 |
| `-y`, `--yes`        | No pedir confirmaciones (usar con precaución).          |
| `--restringido`      | Bloquea operaciones fuera de los directorios permitidos.|
| `--permitido RUTA`   | Directorio autorizado (repetible).                      |
| `--papelera RUTA`    | Carpeta usada como papelera de eliminación segura.      |
| `--sin-ia`           | Desactiva la IA y usa siempre el modo sin red.          |

```bash
file-manager organizar ~/Descargas --dry-run
file-manager borrar ~/temp/* --permanente -y \
    --restringido --permitido ~/temp
```

### Robustez ante errores

Las entradas previsibles (rutas inexistentes, JSON roto, fechas o tamaños mal
formados, destinos que no son directorios, modo restringido, falta de papelera
o fallos de IA) se convierten en excepciones propias de `utils/errores.py`:
`ConfigError`, `AccionNoValida`, `RutaNoValida`, `DirectorioNoValido`,
`AccesoDenegado`, `EntradaNoValida` e `IAError`. La CLI las muestra con
mensajes humanos y devuelve un código de salida distinto de 0, sin traceback.
Los catálogos se validan por completo antes de ejecutar, de modo que un paso
inválido no deja efectos parciales. Las invariantes internas usan `assert`
durante el desarrollo.

La configuración se concentra en `utils/config.py`: `Config.desde_args()` y
`Config.desde_env()` alimentan las fábricas `crear_seguridad()`,
`Acciones.desde_config()`, `CatalogoAcciones.desde_config()`,
`PasosIA.desde_config()` e `IA.desde_config()`. Así la CLI y los módulos
comparten un único objeto de configuración en lugar de leer el entorno cada
uno por su cuenta.

### Pruebas automáticas

```bash
cd file-manager
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q
```

`tests/conftest.py` aísla cada prueba en `tmp_path`: cambia el directorio de
trabajo, define un `HOME` temporal y deja `OPENAI_API_KEY` vacía. Ninguna
prueba toca archivos reales ni llama a la API. `.github/workflows/tests.yml`
ejecuta la misma suite con Python 3.12 en cada `push` y `pull request`.

| Prueba | Aserción clave | Qué demuestra |
| ------ | -------------- | ------------- |
| `test_mover_archivo_existente...` | código `0`, contenido intacto en el destino, origen borrado, mensaje `Archivo movido` | Camino feliz: la operación se hace y se informa. |
| `test_catalogo_json_roto...` | código `2`, mensaje `JSON válido`, sin `Traceback` | Un JSON inválido se convierte en error humano. |
| `test_mover_origen_inexistente...` | código `1`, mensaje `No existe el origen`, destino vacío, sin `Traceback` | Una ruta mala no crea efectos parciales. |
| `test_modo_restringido...` | código `1`, mensaje `bloqueada por el modo restringido`, origen intacto, destino sin copia, sin `Traceback` | La política de seguridad se aplica antes de mover. |

## Seguridad

- Nunca se borra sin **confirmación explícita** (salvo `--yes` + borrado
  explícito del usuario).
- No se sobrescribe ningún archivo sin preguntar; con `--no-sobrescribir`
  se renombran como `archivo (1).ext`.
- Todas las rutas se validan antes de operar.
- El **modo restringido** impide actuar fuera de los directorios autorizados.
- El **modo simulación** muestra las operaciones sin ejecutarlas.
- Cada operación queda registrada en `logs/file-manager.log`.

## Estructura del proyecto

```
file-manager/
├── main.py               # CLI: argparse + menú interactivo
├── modules/
│   ├── mover.py          # Mover archivos/carpetas
│   ├── borrar.py         # Borrado seguro con papelera
│   ├── organizar.py      # Clasificación automática
│   ├── renombrar.py      # Renombrado por lotes
│   ├── buscar.py         # Motor de búsqueda y filtros
│   ├── informacion.py    # Fichas de metadatos
│   ├── crear.py          # Creación de carpetas
│   ├── acciones.py       # Coordinador de acciones personalizadas
│   ├── acciones_catalogo.py # Plantilla, carga y validación del catálogo
│   ├── acciones_ia.py    # Pasos clasificar/renombrar con IA
│   └── _resultado.py     # Contador éxito/omitidos/errores
├── utils/
│   ├── config.py         # Configuración central y fábricas
│   ├── errores.py        # Excepciones propias con mensajes humanos
│   ├── seguridad.py      # Confirmaciones, rutas, papelera, dry-run
│   ├── logger.py         # Logging a logs/file-manager.log
│   ├── interfaz.py       # Colores, tablas y menús (rich)
│   └── ia.py             # Cliente OpenAI opcional con fallback sin red
├── acciones.json         # Acciones personalizadas del usuario
├── tests/
│   ├── conftest.py       # Aislamiento en tmp_path y captura de salida
│   └── test_cli.py       # Camino feliz y 3 casos feos
├── logs/
├── requirements.txt
├── requirements-dev.txt  # pytest
└── README.md
```

## Ampliar con nuevas funcionalidades

1. Crea `modules/mi_operacion.py` con una clase que reciba `Seguridad`
   (y opcionalmente `Interfaz`) en su constructor, devuelva un `Resultado`
   e implemente `menu_interactivo()`.
2. Registra la clase en `modules/__init__.py`.
3. Añade la suborden en `crear_parser()` y su handler en `HANDLERS`
   dentro de `main.py`.

## Código de salida

| Código | Significado                          |
| ------ | ------------------------------------ |
| `0`    | Operación completada sin errores.    |
| `1`    | Completada con errores parciales.    |
| `2`    | Error de argumentos o rutas.         |
| `130`  | Interrumpido por el usuario (Ctrl+C).|
