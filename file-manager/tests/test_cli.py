def test_mover_archivo_existente_devuelve_cero_y_conserva_contenido(cli, tmp_path):
    origen = tmp_path / "origen.txt"
    origen.write_text("contenido", encoding="utf-8")
    destino = tmp_path / "destino"
    destino.mkdir()

    codigo, salida = cli("mover", str(origen), str(destino), "-y")

    assert codigo == 0
    assert (destino / "origen.txt").read_text(encoding="utf-8") == "contenido"
    assert not origen.exists()
    assert "Archivo movido" in salida


def test_catalogo_json_roto_devuelve_error_sin_traceback(cli, tmp_path):
    roto = tmp_path / "roto.json"
    roto.write_text("{", encoding="utf-8")

    codigo, salida = cli("acciones", "-a", str(roto))

    assert codigo == 2
    assert "JSON válido" in salida
    assert "Traceback" not in salida


def test_mover_origen_inexistente_no_crea_destino_y_no_lanza(cli, tmp_path):
    destino = tmp_path / "destino"
    destino.mkdir()
    origen = tmp_path / "noexiste.txt"

    codigo, salida = cli("mover", str(origen), str(destino), "-y")

    assert codigo == 1
    assert "No existe el origen" in salida
    assert list(destino.iterdir()) == []
    assert "Traceback" not in salida


def test_modo_restringido_bloquea_ruta_fuera_de_permitido(cli, tmp_path):
    origen = tmp_path / "origen.txt"
    origen.write_text("contenido", encoding="utf-8")
    permitido = tmp_path / "permitido"
    permitido.mkdir()
    destino = tmp_path / "destino"
    destino.mkdir()

    codigo, salida = cli(
        "mover",
        str(origen),
        str(destino),
        "-y",
        "--restringido",
        "--permitido",
        str(permitido),
    )

    assert codigo == 1
    assert "bloqueada por el modo restringido" in salida
    assert origen.exists()
    assert not (destino / "origen.txt").exists()
    assert "Traceback" not in salida
