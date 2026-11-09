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

## Instalación

Requisitos: Python 3.9 o superior.

```bash
cd file-manager
python3 -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

## Uso

### Menú interactivo

```bash
python main.py
```

### Comandos directos

```bash
python main.py organizar ~/Descargas
python main.py mover archivo.pdf ~/Documentos/
python main.py borrar archivo.pdf                 # a la papelera (seguro)
python main.py buscar "factura"
python main.py buscar "factura" -e pdf -t ">=1MB" -m "ultimo-30dias"
python main.py info archivo.pdf
python main.py renombrar archivo.pdf nuevo_nombre.pdf
python main.py crear ~/Proyectos/nuevo
```

### Subórdenes y ejemplos

#### mover

```bash
python main.py mover *.png ~/Imágenes/            # admite comodines
python main.py mover archivo.pdf ~/Documentos/ --no-sobrescribir
python main.py mover carpeta ~/backup/ -c         # crea el destino si falta
```

#### borrar

Por defecto borra **enviando a la papelera** (`~/.file-manager-papelera`
o la que indiques con `--papelera`):

```bash
python main.py borrar archivo.pdf                       # a la papelera
python main.py borrar archivo.pdf --papelera ~/papelera
python main.py borrar archivo.pdf --permanente          # borrado definitivo
python main.py borrar carpeta --permanente -r           # carpeta con contenido
```

#### organizar

```bash
python main.py organizar ~/Descargas                        # por extensión
python main.py organizar ~/Descargas --por fecha            # AAAA-MM
python main.py organizar ~/Descargas --por tamano           # rangos
python main.py organizar ~/Descargas -s                     # incluye subcarpetas
python main.py organizar ~/Descargas --dry-run              # simulación
```

Categorías por extensión: `Imagenes`, `Videos`, `Audio`, `Documentos`,
`Hojas_de_calculo`, `Comprimidos`, `Programacion`, `Ejecutables` y `Otros`.

#### renombrar

```bash
python main.py renombrar viejo.pdf nuevo.pdf            # individual
python main.py renombrar *.jpg --prefijo "vacaciones_"
python main.py renombrar *.jpg --sufijo "_editado"
python main.py renombrar *.pdf --buscar "borrador" --reemplazar "final"
python main.py renombrar *.txt --buscar '^(\d+)' --reemplazar 'doc_\1' --regex
python main.py renombrar *.jpg --numerar --plantilla "playa_{i:02d}"
```

#### buscar

```bash
python main.py buscar "informe"                 # texto en el nombre
python main.py buscar "*.iso"                   # comodines
python main.py buscar -e pdf -d ~/Documentos    # por extensión
python main.py buscar -t ">=100MB"              # o "<=1GB", "1MB-500MB"
python main.py buscar -m "ultimo-7dias"         # o ">2024-01-01", "<2024-12-31"
python main.py buscar "temp" --tipo carpeta
```

#### info y crear

```bash
python main.py info archivo.pdf ~/Descargas     # archivos y carpetas
python main.py crear ~/Proyectos/2026/informe   # equivalentes a mkdir -p
```

#### acciones (personalizadas)

Incluye `acciones.json` con 4 acciones de ejemplo. Cada acción es una
lista de pasos que reutilizan las operaciones del gestor:

```bash
python main.py acciones                          # listar acciones
python main.py acciones ordenar-descargas        # ejecutar una
python main.py acciones limpiar-temporales --dry-run
python main.py acciones --crear                  # generar plantilla nueva
python main.py acciones mi-accion -a otro.json   # catálogo alternativo
```

Acciones incluidas por defecto:

| Acción              | Qué hace                                              |
| ------------------- | ----------------------------------------------------- |
| `ordenar-descargas` | Clasifica `~/Descargas` por extensión.                |
| `limpiar-temporales`| Busca `*.tmp` y los envía a la papelera.              |
| `informes-mensuales`| Crea `informes/datos` y copia los CSV actuales.       |
| `reporte-tamano`    | Muestra el tamaño total y avisa si supera 500 MB.     |

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
      {"ejecutar": "echo hola"}
    ]
  }
}
```

Operaciones disponibles en cada paso: `crear`, `mover`, `copiar`,
`organizar`, `renombrar`, `buscar`, `tamano` y `ejecutar` (esta última
pide confirmación explícita salvo con `--yes`). Los comodines (`*.csv`)
se expanden sobre el directorio actual. Todas las acciones respetan
`--dry-run`, `--restringido` y las confirmaciones.

### Opciones globales de seguridad

| Opción               | Descripción                                             |
| -------------------- | ------------------------------------------------------- |
| `--dry-run`          | Simula la operación sin modificar nada.                 |
| `-y`, `--yes`        | No pedir confirmaciones (usar con precaución).          |
| `--restringido`      | Bloquea operaciones fuera de los directorios permitidos.|
| `--permitido RUTA`   | Directorio autorizado (repetible).                      |
| `--papelera RUTA`    | Carpeta usada como papelera de eliminación segura.      |

```bash
python main.py organizar ~/Descargas --dry-run
python main.py borrar ~/temp/* --permanente -y \
    --restringido --permitido ~/temp
```

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
│   ├── acciones.py       # Acciones personalizadas desde JSON
│   └── _resultado.py     # Contador éxito/omitidos/errores
├── utils/
│   ├── seguridad.py      # Confirmaciones, rutas, papelera, dry-run
│   ├── logger.py         # Logging a logs/file-manager.log
│   └── interfaz.py       # Colores, tablas y menús (rich)
├── acciones.json         # Acciones personalizadas del usuario
├── logs/
├── requirements.txt
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
