# ADR 0001: Acciones predefinidas como configuración externa

- Estado: Aceptado
- Fecha: 2026-11-24
- Componentes: `file-manager/modules/acciones.py`, `file-manager/acciones.json`

## Contexto

El CLI necesita operaciones compuestas: limpieza de temporales, respaldos,
organización de descargas, reportes de tamaño, etc. Si cada acción se
escribe como código, cambiar una ruta o el orden de los pasos obliga a
editar Python, probar de nuevo y distribuir una versión nueva. Además, cada
usuario tiene directorios distintos y no debería necesitar tocar el
programa para adaptarlo.

## Decisión

Las acciones viven en un fichero JSON (`acciones.json`, o la ruta que
indique `-a`). El código se limita a interpretar un esquema pequeño de pasos
(`crear`, `mover`, `copiar`, `organizar`, `renombrar`, `buscar`, `tamano`,
`ejecutar`) y delega cada paso en los módulos ya existentes.

El catálogo se valida por completo antes de ejecutar nada. Si falta un campo
o tiene un tipo incorrecto, el error indica la acción, el número de paso y
el campo afectado, y no se produce ningún efecto parcial.

## Consecuencias

Positivas:

- Añadir o modificar una acción no exige tocar código ni reinstalar el CLI.
- La misma operación se reutiliza con otras rutas y se puede comprobar antes
  con `--dry-run`.
- La validación centralizada evita ejecuciones a medias y mensajes crípticos.

Límites:

- Solo se pueden combinar las operaciones ya implementadas; introducir una
  operación nueva sí requiere código.
- El JSON no admite variables ni condicionales: es configuración, no script.
- Hay que mantener alineados el esquema del README, la plantilla de
  `acciones --crear` y esta validación.

## Alternativas consideradas

- Acciones escritas directamente en Python: descartado; cada ajuste
  exigiría una nueva versión del programa.
- Scripts de shell como mecanismo principal: descartado; son difíciles de
  validar y de simular. Se mantiene `ejecutar` como vía de escape, con
  confirmación explícita y respeto a `--dry-run`.
