"""Separa recursos empacotados dos dados persistentes do caixa."""
import os
import sys
from pathlib import Path


def resource_root():
    return Path(__file__).resolve().parent


def default_database():
    if getattr(sys, 'frozen', False):
        local = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
        return local / 'RanchoTiaNina' / 'dados' / 'caixa.sqlite3'
    return resource_root() / 'dados' / 'caixa.sqlite3'
