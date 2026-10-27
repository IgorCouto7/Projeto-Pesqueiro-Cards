import importlib
import sqlite3
import sys
from datetime import date
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('PESQUEIRO_DB', str(tmp_path / 'caixa.sqlite3'))
    if 'caixa' in sys.modules:
        mod = importlib.reload(sys.modules['caixa'])
    else:
        mod = importlib.import_module('caixa')
    with TestClient(mod.app) as c:
        c.headers['X-Caixa-Token'] = c.get('/api/sessao').json()['token']
        yield c


def post(c, path, body):
    response = c.post('/api/' + path, json=body)
    assert response.status_code == 200, response.text
    return response.json()


def product(c, **kw):
    return post(c, 'produtos', dict(nome='Cerveja', unidade='UN', preco='10.00', controla=True, minimo=5, **kw))['id']


def order(c):
    return post(c, 'comandas', {'nome': 'João', 'mesa': '05'})['id']


def item(c, oid, pid, q=1, key='item-0001'):
    return post(c, f'comandas/{oid}/itens', {'produto': pid, 'quantidade': q, 'chave': key})


def test_stock_sale_cancel_and_history(client):
    c = client
    pid = product(c)
    post(c, 'estoque', {'produto': pid, 'tipo': 'ENTRADA', 'quantidade': 24, 'motivo': 'Compra inicial'})
    oid = order(c)
    o = item(c, oid, pid, 3)
    assert o['total'] == 3000
    p = next(p for p in c.get('/api/produtos').json() if p['id'] == pid)
    assert p['saldos'] == {'DEPOSITO': 21000}
    assert item(c, oid, pid, 3)['total'] == 3000  # retry does not double debit
    post(c, f"itens/{o['itens'][0]['id']}/cancelar", {'motivo': 'Pedido errado'})
    assert c.get('/api/comandas/' + str(oid)).json()['total'] == 0
    item(c, oid, pid, 2, 'item-0002')
    paid = post(c, f'comandas/{oid}/pagar', {'forma': 'DINHEIRO', 'recebido': 50})
    assert paid['troco'] == 3000
    assert order(c) != oid  # returning customer/table allowed after payment
    assert c.get('/api/comandas?status=PAGA').json()[0]['total'] == 2000
    assert c.post(f'/api/comandas/{oid}/pagar', json={'forma': 'DINHEIRO', 'recebido': 50}).status_code == 409


def test_weight_and_price_snapshot(client):
    c = client
    pid = post(c, 'produtos', {'nome': 'Tilápia', 'unidade': 'KG', 'preco': '29.90', 'controla': False, 'minimo': 0})['id']
    oid = order(c)
    assert item(c, oid, pid, '1.750')['total'] == 5233  # 52.325 -> 52.33
    assert c.put(f'/api/produtos/{pid}', json={'nome': 'Tilápia', 'unidade': 'KG', 'preco': 40, 'controla': False, 'minimo': 0}).status_code == 200
    assert c.get(f'/api/comandas/{oid}').json()['total'] == 5233


@pytest.mark.parametrize('q', [-1, 0, 1.5])
def test_invalid_unit_quantities(client, q):
    pid = product(client)
    oid = order(client)
    r = client.post(f'/api/comandas/{oid}/itens', json={'produto': pid, 'quantidade': q, 'chave': 'invalid-001'})
    assert r.status_code == 422


def test_insufficient_stock_atomicity(client):
    c = client
    pid = product(c)
    post(c, 'estoque', {'produto': pid, 'tipo': 'ENTRADA', 'quantidade': 2, 'motivo': 'Compra'})
    assert c.post('/api/estoque', json={'produto': pid, 'tipo': 'PERDA', 'quantidade': 3, 'motivo': 'Repor'}).status_code == 409
    assert next(p for p in c.get('/api/produtos').json() if p['id'] == pid)['saldos']['DEPOSITO'] == 2000
    oid = order(c)
    assert c.post(f'/api/comandas/{oid}/itens', json={'produto': pid, 'quantidade': 3, 'chave': 'no-stock-01'}).status_code == 409
    assert c.get(f'/api/comandas/{oid}').json()['itens'] == []


def test_closing_reopening_and_backup(client):
    c = client
    oid = order(c)
    item(c, oid, 1, 2)
    assert c.post(f'/api/comandas/{oid}/pagar', json={'forma': 'PIX', 'recebido': 50}).status_code == 422
    post(c, f'comandas/{oid}/pagar', {'forma': 'PIX', 'recebido': 40})
    day = date.today().isoformat()
    post(c, 'caixa/fechar', {'dia': day, 'contado': 0})
    r = c.get('/api/caixa?dia='+day).json()
    assert r['total'] == 4000 and r['fechamento']['diferenca'] == 0
    oid2 = order(c)
    item(c, oid2, 1, 1, 'piscina-002')
    assert c.post(f'/api/comandas/{oid2}/pagar', json={'forma': 'DINHEIRO', 'recebido': 20}).status_code == 409
    post(c, 'caixa/reabrir', {'dia': day, 'contado': 0})
    post(c, f'comandas/{oid2}/pagar', {'forma': 'DINHEIRO', 'recebido': 20})
    name = post(c, 'backup', {})['arquivo']
    mod = sys.modules['caixa']
    with sqlite3.connect(mod.DB.parent / 'backups' / name) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert db.execute("SELECT COUNT(*) FROM comandas WHERE status='PAGA'").fetchone()[0] == 2


def test_protection_and_no_reset(client):
    assert client.post('/api/comandas', json={'nome': 'Teste'}, headers={'X-Caixa-Token': ''}).status_code == 403
    assert client.get('/api/produtos', headers={'Host': 'evil.example'}).status_code == 403
    assert client.post('/admin/reset-db').status_code == 404
    assert client.get('/').status_code == 200


def test_concurrent_last_unit(client):
    c = client
    pid = product(c)
    post(c, 'estoque', {'produto': pid, 'tipo': 'ENTRADA', 'local': 'DEPOSITO', 'quantidade': 1, 'motivo': 'Última unidade'})
    oid = order(c)
    def sale(key):
        return c.post(f'/api/comandas/{oid}/itens', json={'produto': pid, 'quantidade': 1, 'chave': key}).status_code
    with ThreadPoolExecutor(2) as pool:
        statuses = list(pool.map(sale, ['concurrent-1', 'concurrent-2']))
    assert sorted(statuses) == [200, 409]
    assert c.get(f'/api/comandas/{oid}').json()['total'] == 1000


def test_existing_freezer_consolidated_once_and_cancel_returns_to_deposit(client):
    c = client
    pid = product(c)
    oid = order(c)
    mod = sys.modules['caixa']
    with mod.connection(True) as db:
        db.execute('INSERT INTO saldos VALUES (?,?,?)', (pid, 'DEPOSITO', 12000))
        db.execute('INSERT INTO saldos VALUES (?,?,?)', (pid, 'FREEZER', 9000))
        cur = db.execute('INSERT INTO itens(comanda,produto,nome,quantidade,preco,total,local,chave) VALUES (?,?,?,?,?,?,?,?)',
                         (oid, pid, 'Cerveja', 3000, 1000, 3000, 'FREEZER', 'legacy-sale'))
        iid = cur.lastrowid
    mod.initialize()
    mod.initialize()
    p = next(p for p in c.get('/api/produtos').json() if p['id'] == pid)
    assert p['saldos'] == {'DEPOSITO': 21000}
    post(c, f'itens/{iid}/cancelar', {'motivo': 'Pedido errado'})
    p = next(p for p in c.get('/api/produtos').json() if p['id'] == pid)
    assert p['saldos'] == {'DEPOSITO': 24000}
    assert c.post('/api/estoque', json={'produto': pid, 'tipo': 'ENTRADA', 'local': 'FREEZER', 'quantidade': 1, 'motivo': 'Teste'}).status_code == 422
    page = c.get('/').text
    assert 'Rancho da tia nina' in page
    assert 'Freezer' not in page and 'FREEZER' not in page


def test_reset_requires_confirmation_and_backup(client, monkeypatch):
    c = client
    pid = product(c)
    oid = order(c)
    item(c, oid, 1)
    assert c.post('/api/admin/apagar-tudo', json={'confirmacao': 'sim'}).status_code == 422
    assert c.post('/api/admin/apagar-tudo', json={'confirmacao': 'APAGAR TUDO'}, headers={'X-Caixa-Token': ''}).status_code == 403
    mod = sys.modules['caixa']
    def fail_backup():
        raise OSError('Disco indisponível')
    with monkeypatch.context() as m:
        m.setattr(mod, 'backup', fail_backup)
        assert c.post('/api/admin/apagar-tudo', json={'confirmacao': 'APAGAR TUDO'}).status_code == 503
    assert c.get(f'/api/comandas/{oid}').json()['total'] == 2000
    assert len(c.get('/api/produtos').json()) == 2
    result = post(c, 'admin/apagar-tudo', {'confirmacao': 'APAGAR TUDO'})
    with sqlite3.connect(mod.DB.parent / 'backups' / result['arquivo']) as db:
        assert db.execute('SELECT COUNT(*) FROM produtos').fetchone()[0] == 2
        assert db.execute('SELECT COUNT(*) FROM itens').fetchone()[0] == 1
    with mod.connection() as db:
        for table in ('itens', 'movimentos', 'saldos', 'comandas', 'fechamentos', 'produtos'):
            assert db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] == 0
    mod.initialize()
    assert c.get('/api/produtos').json() == []
    assert c.get('/api/comandas').json() == []

