# Changelog

Todos los cambios relevantes se documentan aquí.

## [1.0.0] - 2026-11-24

### Added

- Instalación en una orden con `pipx install git+https://github.com/Jordicha/CLI`
  o `uv tool install git+https://github.com/Jordicha/CLI`.
- Comando `file-manager` disponible en cualquier carpeta.
- Suite `pytest` con un camino feliz y tres casos feos, ejecutada en GitHub Actions.
- Acciones IA opcionales `clasificar-con-ia` y `renombrar-con-ia` con fallback sin red.
- Excepciones propias y mensajes humanos sin traceback para entradas previsibles.
- Configuración centralizada y fábricas para seguridad, acciones y proveedor IA.

### Changed

- `acciones.json` se empaqueta con el CLI y se localiza también después de instalarlo.
- README con ejemplos del comando instalado y tabla de auditoría de las pruebas.

### Fixed

- El catálogo se valida por completo antes de ejecutar cualquier paso.
- El modo restringido y `--dry-run` se aplican también a las acciones personalizadas.

[1.0.0]: https://github.com/Jordicha/CLI/releases/tag/v1.0
