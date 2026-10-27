import sys
from pathlib import Path

from runtime_paths import default_database, resource_root


def test_fonte_preserva_caminho_do_banco_existente(monkeypatch):
    monkeypatch.delattr(sys, 'frozen', raising=False)
    assert default_database() == resource_root() / 'dados' / 'caixa.sqlite3'


def test_executavel_guarda_dados_fora_dos_recursos_temporarios(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'perfil'))
    esperado = tmp_path / 'perfil' / 'RanchoTiaNina' / 'dados' / 'caixa.sqlite3'
    assert default_database() == esperado
    monkeypatch.setattr(sys, 'executable', str(tmp_path / 'nova-versao' / 'RanchoTiaNina.exe'))
    assert default_database() == esperado
    assert resource_root() == Path(__file__).resolve().parents[1]
