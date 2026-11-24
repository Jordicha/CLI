import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

import main


@pytest.fixture
def cli(monkeypatch, tmp_path, capsys):
    hogar = tmp_path / "home"
    hogar.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(hogar))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("IA_MODELO", raising=False)
    monkeypatch.delenv("IA_TIMEOUT", raising=False)

    def ejecutar(*args):
        codigo = main.main(list(args))
        salida = capsys.readouterr().out
        return codigo, salida

    return ejecutar
