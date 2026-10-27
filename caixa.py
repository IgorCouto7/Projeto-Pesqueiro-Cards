"""Caixa local. Valores em centavos; quantidades em milésimos; transações atômicas."""
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, ConfigDict
from runtime_paths import resource_root, default_database

ROOT = resource_root()
DB = Path(os.environ.get('PESQUEIRO_DB', str(default_database())))
TOKEN = secrets.token_urlsafe(32)
app = FastAPI(title='Rancho da tia nina • Caixa local', docs_url=None, redoc_url=None)

def now():
    return datetime.now().astimezone().isoformat(timespec='seconds')

@contextmanager
def connection(write=False):
    db = sqlite3.connect(DB, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        if write:
            db.execute('BEGIN IMMEDIATE')
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def backup():
    folder = DB.parent / 'backups'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.sqlite3')
    with connection() as source, sqlite3.connect(path) as target:
        source.backup(target)
    return path.name

def initialize():
    new_database = not DB.exists()
    DB.parent.mkdir(parents=True, exist_ok=True)
    with connection() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS produtos (
          id INTEGER PRIMARY KEY, nome TEXT NOT NULL UNIQUE COLLATE NOCASE,
          unidade TEXT NOT NULL, preco INTEGER NOT NULL CHECK(preco>=0),
          controla INTEGER NOT NULL, minimo INTEGER NOT NULL CHECK(minimo>=0));
        CREATE TABLE IF NOT EXISTS saldos (
          produto INTEGER REFERENCES produtos(id), local TEXT NOT NULL,
          quantidade INTEGER NOT NULL CHECK(quantidade>=0), PRIMARY KEY(produto,local));
        CREATE TABLE IF NOT EXISTS comandas (
          id INTEGER PRIMARY KEY, nome TEXT NOT NULL, mesa TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'ABERTA', aberta TEXT NOT NULL, fechada TEXT,
          forma TEXT, recebido INTEGER, troco INTEGER, total INTEGER);
        CREATE TABLE IF NOT EXISTS itens (
          id INTEGER PRIMARY KEY, comanda INTEGER NOT NULL REFERENCES comandas(id),
          produto INTEGER NOT NULL REFERENCES produtos(id), nome TEXT NOT NULL,
          quantidade INTEGER NOT NULL CHECK(quantidade>0), preco INTEGER NOT NULL,
          total INTEGER NOT NULL, local TEXT NOT NULL, cancelado INTEGER NOT NULL DEFAULT 0,
          motivo TEXT, chave TEXT UNIQUE NOT NULL);
        CREATE TABLE IF NOT EXISTS movimentos (
          id INTEGER PRIMARY KEY, produto INTEGER REFERENCES produtos(id),
          local TEXT NOT NULL, quantidade INTEGER NOT NULL, tipo TEXT NOT NULL,
          motivo TEXT NOT NULL, criado TEXT NOT NULL, comanda INTEGER);
        CREATE TABLE IF NOT EXISTS fechamentos (
          dia TEXT PRIMARY KEY, total INTEGER NOT NULL, dinheiro INTEGER NOT NULL,
          pix INTEGER NOT NULL, cartao INTEGER NOT NULL, contado INTEGER NOT NULL,
          diferenca INTEGER NOT NULL, criado TEXT NOT NULL);
        ''')
        if new_database:
            db.execute("INSERT OR IGNORE INTO produtos(nome,unidade,preco,controla,minimo) VALUES ('Piscina','UN',2000,0,0)")
    backup()
    # Consolidação atômica: saldos antigos migram uma vez; histórico é preservado.
    with connection(True) as db:
        for saldo in db.execute("SELECT produto,quantidade FROM saldos WHERE local='FREEZER'").fetchall():
            if saldo['quantidade']:
                move(db, saldo['produto'], 'DEPOSITO', saldo['quantidade'], 'CONSOLIDACAO', 'Saldo do antigo freezer incorporado ao depósito')
                move(db, saldo['produto'], 'FREEZER', -saldo['quantidade'], 'CONSOLIDACAO', 'Saldo incorporado ao depósito')
        db.execute("DELETE FROM saldos WHERE local='FREEZER'")

@app.middleware('http')
async def local_only(request: Request, call_next):
    host = request.headers.get('host', '').split(':')[0]
    if host not in ('127.0.0.1', 'localhost', 'testserver'):
        return JSONResponse({'detail': 'Acesso permitido somente no computador do caixa.'}, 403)
    if request.method not in ('GET', 'HEAD'):
        if not secrets.compare_digest(request.headers.get('x-caixa-token', ''), TOKEN):
            return JSONResponse({'detail': 'Reabra a página do caixa e tente novamente.'}, 403)
    return await call_next(request)

class Input(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid', allow_inf_nan=False)

class Produto(Input):
    nome: str = Field(min_length=1, max_length=100)
    unidade: Literal['UN', 'KG'] = 'UN'
    preco: Decimal = Field(ge=0, le=100000, decimal_places=2)
    controla: bool = True
    minimo: Decimal = Field(ge=0, le=100000, decimal_places=3)

class Comanda(Input):
    nome: str = Field(min_length=1, max_length=100)
    mesa: str = Field(default='', max_length=30)

class Movimento(Input):
    produto: int
    tipo: Literal['ENTRADA', 'PERDA', 'AJUSTE']
    local: Literal['DEPOSITO'] = 'DEPOSITO'
    quantidade: Decimal = Field(ge=0, le=100000, decimal_places=3)
    motivo: str = Field(min_length=3, max_length=200)

class Item(Input):
    produto: int
    quantidade: Decimal = Field(gt=0, le=100000, decimal_places=3)
    local: Literal['DEPOSITO'] = 'DEPOSITO'
    chave: str = Field(min_length=8, max_length=100)

class Motivo(Input):
    motivo: str = Field(min_length=3, max_length=200)

class Pagamento(Input):
    forma: Literal['DINHEIRO', 'PIX', 'CARTAO']
    recebido: Decimal = Field(ge=0, le=10000000, decimal_places=2)

class Fechamento(Input):
    dia: date
    contado: Decimal = Field(ge=0, le=10000000, decimal_places=2)

def cents(value):
    return int((Decimal(value) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

def quantity(value, product):
    if product['unidade'] == 'UN' and value != int(value):
        raise HTTPException(422, 'Produto por unidade exige quantidade inteira.')
    return int(value * 1000)

def row(db, table, id):
    result = db.execute(f'SELECT * FROM {table} WHERE id=?', (id,)).fetchone()
    if result is None:
        raise HTTPException(404, 'Registro não encontrado.')
    return result

def opened(db, id):
    result = row(db, 'comandas', id)
    if result['status'] != 'ABERTA':
        raise HTTPException(409, 'Esta comanda já foi encerrada.')
    return result

def move(db, product, local, delta, tipo, motivo, comanda=None):
    db.execute('INSERT OR IGNORE INTO saldos VALUES (?,?,0)', (product, local))
    saldo = db.execute('SELECT quantidade FROM saldos WHERE produto=? AND local=?', (product, local)).fetchone()[0]
    if saldo + delta < 0:
        raise HTTPException(409, f'Estoque insuficiente em {local.lower()}: disponível {saldo / 1000:g}.')
    db.execute('UPDATE saldos SET quantidade=quantidade+? WHERE produto=? AND local=?', (delta, product, local))
    db.execute('INSERT INTO movimentos(produto,local,quantidade,tipo,motivo,criado,comanda) VALUES (?,?,?,?,?,?,?)',
               (product, local, delta, tipo, motivo, now(), comanda))

def detail(db, id):
    result = dict(row(db, 'comandas', id))
    result['itens'] = [dict(r) for r in db.execute('SELECT * FROM itens WHERE comanda=? ORDER BY id', (id,))]
    result['total'] = sum(i['total'] for i in result['itens'] if not i['cancelado'])
    return result

@app.get('/')
@app.get('/cards', include_in_schema=False)
def home():
    return FileResponse(ROOT / 'caixa.html', headers={'Cache-Control': 'no-store'})


@app.get('/classico', include_in_schema=False)
def classic():
    return FileResponse(ROOT / 'caixa-classico.html', headers={'Cache-Control': 'no-store'})


@app.get('/melhorias.js', include_in_schema=False)
def improvements():
    return FileResponse(ROOT / 'melhorias.js', media_type='application/javascript',
                        headers={'Cache-Control': 'no-store'})

@app.get('/api/sessao')
def session():
    return JSONResponse({'token': TOKEN}, headers={'Cache-Control': 'no-store'})

@app.get('/api/produtos')
def products():
    with connection() as db:
        result = []
        for p in db.execute('SELECT * FROM produtos ORDER BY nome'):
            p = dict(p)
            p['saldos'] = dict(db.execute('SELECT local,quantidade FROM saldos WHERE produto=?', (p['id'],)).fetchall())
            p['baixo'] = bool(p['controla'] and sum(p['saldos'].values()) <= p['minimo'])
            result.append(p)
        return result

@app.post('/api/produtos')
def create_product(data: Produto):
    minimum = quantity(data.minimo, {'unidade': data.unidade})
    with connection(True) as db:
        try:
            cur = db.execute('INSERT INTO produtos(nome,unidade,preco,controla,minimo) VALUES (?,?,?,?,?)',
                             (data.nome, data.unidade, cents(data.preco), data.controla, minimum))
        except sqlite3.IntegrityError:
            raise HTTPException(409, 'Já existe um produto com esse nome.')
        return {'id': cur.lastrowid}

@app.put('/api/produtos/{id}')
def update_product(id: int, data: Produto):
    with connection(True) as db:
        old = row(db, 'produtos', id)
        if old['unidade'] != data.unidade or old['controla'] != data.controla:
            raise HTTPException(409, 'Mantenha a unidade e o controle de estoque; cadastre outro produto para mudar esses campos.')
        try:
            db.execute('UPDATE produtos SET nome=?,preco=?,minimo=? WHERE id=?',
                       (data.nome, cents(data.preco), quantity(data.minimo, old), id))
        except sqlite3.IntegrityError:
            raise HTTPException(409, 'Já existe um produto com esse nome.')
    return {'ok': True}

@app.post('/api/estoque')
def stock(data: Movimento):
    with connection(True) as db:
        p = row(db, 'produtos', data.produto)
        if not p['controla']:
            raise HTTPException(422, 'Este produto não controla estoque.')
        q = quantity(data.quantidade, p)
        if data.tipo != 'AJUSTE' and q <= 0:
            raise HTTPException(422, 'Informe uma quantidade maior que zero.')
        if data.tipo == 'AJUSTE':
            current = db.execute('SELECT quantidade FROM saldos WHERE produto=? AND local=?', (p['id'], data.local)).fetchone()
            q -= current[0] if current else 0
        if data.tipo == 'PERDA':
            q = -q
        move(db, p['id'], data.local, q, data.tipo, data.motivo)
    return {'ok': True}

@app.get('/api/movimentos')
def movements():
    with connection() as db:
        return [dict(r) for r in db.execute('SELECT m.*,p.nome FROM movimentos m JOIN produtos p ON p.id=m.produto ORDER BY m.id DESC LIMIT 200')]

@app.post('/api/comandas')
def create_order(data: Comanda):
    with connection(True) as db:
        if data.mesa and db.execute("SELECT id FROM comandas WHERE mesa=? COLLATE NOCASE AND status='ABERTA'", (data.mesa,)).fetchone():
            raise HTTPException(409, 'Essa mesa já tem uma comanda aberta.')
        cur = db.execute('INSERT INTO comandas(nome,mesa,aberta) VALUES (?,?,?)', (data.nome, data.mesa, now()))
        return detail(db, cur.lastrowid)

@app.get('/api/comandas')
def orders(status: Literal['ABERTA', 'PAGA', 'CANCELADA'] = 'ABERTA'):
    with connection() as db:
        return [detail(db, r[0]) for r in db.execute('SELECT id FROM comandas WHERE status=? ORDER BY id DESC', (status,)).fetchall()]

@app.get('/api/comandas/{id}')
def order(id: int):
    with connection() as db:
        return detail(db, id)

@app.post('/api/comandas/{id}/itens')
def add_item(id: int, data: Item):
    with connection(True) as db:
        existing = db.execute('SELECT * FROM itens WHERE chave=?', (data.chave,)).fetchone()
        if existing:
            if (existing['comanda'], existing['produto'], existing['quantidade'], existing['local']) != (id, data.produto, int(data.quantidade * 1000), data.local):
                raise HTTPException(409, 'Identificador de lançamento já utilizado.')
            return detail(db, id)
        opened(db, id)
        p = row(db, 'produtos', data.produto)
        q = quantity(data.quantidade, p)
        total = int((Decimal(p['preco']) * q / 1000).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        if p['controla']:
            move(db, p['id'], data.local, -q, 'VENDA', 'Consumo na comanda', id)
        db.execute('INSERT INTO itens(comanda,produto,nome,quantidade,preco,total,local,chave) VALUES (?,?,?,?,?,?,?,?)',
                   (id, p['id'], p['nome'], q, p['preco'], total, data.local, data.chave))
        return detail(db, id)

@app.post('/api/itens/{id}/cancelar')
def cancel_item(id: int, data: Motivo):
    with connection(True) as db:
        i = row(db, 'itens', id)
        opened(db, i['comanda'])
        if i['cancelado']:
            raise HTTPException(409, 'Item já cancelado.')
        p = row(db, 'produtos', i['produto'])
        if p['controla']:
            move(db, p['id'], 'DEPOSITO', i['quantidade'], 'ESTORNO', data.motivo, i['comanda'])
        db.execute('UPDATE itens SET cancelado=1,motivo=? WHERE id=?', (data.motivo, id))
        return detail(db, i['comanda'])

@app.post('/api/comandas/{id}/cancelar')
def cancel_order(id: int, data: Motivo):
    with connection(True) as db:
        opened(db, id)
        if db.execute('SELECT id FROM itens WHERE comanda=? AND cancelado=0', (id,)).fetchone():
            raise HTTPException(409, 'Cancele os itens antes de cancelar a comanda.')
        db.execute("UPDATE comandas SET status='CANCELADA',fechada=? WHERE id=?", (now(), id))
    return {'ok': True}

@app.post('/api/comandas/{id}/pagar')
def pay(id: int, data: Pagamento):
    with connection(True) as db:
        opened(db, id)
        day = date.today().isoformat()
        if db.execute('SELECT dia FROM fechamentos WHERE dia=?', (day,)).fetchone():
            raise HTTPException(409, 'O caixa de hoje está fechado. Reabra para registrar pagamentos.')
        total = detail(db, id)['total']
        received = cents(data.recebido)
        if total <= 0:
            raise HTTPException(422, 'Comanda sem valor a receber. Cancele a comanda vazia.')
        if received < total or (data.forma != 'DINHEIRO' and received != total):
            raise HTTPException(422, 'Valor recebido inválido. Pix e cartão devem ser iguais ao total.')
        db.execute("UPDATE comandas SET status='PAGA',fechada=?,forma=?,recebido=?,troco=?,total=? WHERE id=?",
                   (now(), data.forma, received, received-total, total, id))
        result = detail(db, id)
    try:
        backup()
    except OSError:
        result['aviso'] = 'Pagamento salvo, mas o backup falhou. Faça uma cópia pela aba Caixa.'
    except sqlite3.Error:
        result['aviso'] = 'Pagamento salvo, mas o backup falhou. Faça uma cópia pela aba Caixa.'
    return result

def report(db, day):
    totals = {'DINHEIRO': 0, 'PIX': 0, 'CARTAO': 0}
    for r in db.execute("SELECT forma,SUM(total) FROM comandas WHERE status='PAGA' AND substr(fechada,1,10)=? GROUP BY forma", (day,)):
        totals[r[0]] = r[1]
    closing = db.execute('SELECT * FROM fechamentos WHERE dia=?', (day,)).fetchone()
    return {'dia': day, 'formas': totals, 'total': sum(totals.values()), 'fechamento': dict(closing) if closing else None}

@app.get('/api/caixa')
def cash(dia: date):
    with connection() as db:
        return report(db, dia.isoformat())

@app.post('/api/caixa/fechar')
def close_cash(data: Fechamento):
    if data.dia > date.today():
        raise HTTPException(422, 'Não é possível fechar uma data futura.')
    with connection(True) as db:
        day = data.dia.isoformat()
        r = report(db, day)
        if r['fechamento']:
            raise HTTPException(409, 'Esse dia já está fechado.')
        counted = cents(data.contado)
        db.execute('INSERT INTO fechamentos VALUES (?,?,?,?,?,?,?,?)',
                   (day, r['total'], r['formas']['DINHEIRO'], r['formas']['PIX'], r['formas']['CARTAO'], counted, counted-r['formas']['DINHEIRO'], now()))
    return {'ok': True}

@app.post('/api/caixa/reabrir')
def reopen_cash(data: Fechamento):
    with connection(True) as db:
        db.execute('DELETE FROM fechamentos WHERE dia=?', (data.dia.isoformat(),))
    return {'ok': True}

@app.post('/api/backup')
def manual_backup():
    return {'arquivo': backup()}


class ResetData(Input):
    confirmacao: Literal['APAGAR TUDO']


@app.post('/api/admin/apagar-tudo')
def reset_all(data: ResetData):
    # Impede outra gravação entre a cópia e a limpeza. Falhas revertem tudo.
    with connection(True) as db:
        try:
            filename = backup()
            with sqlite3.connect(DB.parent / 'backups' / filename) as saved:
                if saved.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise sqlite3.DatabaseError('Backup inválido')
        except (OSError, sqlite3.Error):
            raise HTTPException(503, 'Não foi possível criar e verificar o backup. Nenhum dado foi apagado.')
        for table in ('itens', 'movimentos', 'saldos', 'comandas', 'fechamentos', 'produtos'):
            db.execute(f'DELETE FROM {table}')
    return {'ok': True, 'arquivo': filename}

initialize()
