"""Fluxo por nome em banco em memória, incluindo compatibilidade da tela antiga."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from App.api.main import app, get_db
from App.db.connection import Base
from App.models.cliente import Cliente
from App.models.comanda import Comanda


@pytest.fixture
def client_cards():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)

    def db_override():
        with sessions() as db:
            yield db

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = db_override
    try:
        with TestClient(app) as client:
            yield client, sessions
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        engine.dispose()


def test_abre_por_nome_persiste_e_lista_sem_cpf_inventado(client_cards):
    client, sessions = client_cards
    assert client.get("/comandas").json() == []
    response = client.post("/atendimentos", json={"nome": "  João e família  "})
    assert response.status_code == 200
    card = response.json()
    assert card["nome_cliente"] == "João e família"
    assert card["status"] == "ABERTA"
    assert card["valor_total"] == 0
    assert client.get("/comandas").json() == [card]
    with sessions() as db:
        assert db.query(Cliente).one().cpf is None
        assert db.query(Comanda).count() == 1
    # Clientes criados pelo novo fluxo continuam consultáveis na versão antiga.
    clientes = client.get("/clientes")
    assert clientes.status_code == 200
    assert clientes.json()[0]["nome"] == card["nome_cliente"]
    assert clientes.json()[0]["cpf"] is None


def test_homonimos_e_nova_visita_nao_misturam_contas(client_cards):
    client, _ = client_cards
    primeiro = client.post("/atendimentos", json={"nome": "João"}).json()
    segundo = client.post("/atendimentos", json={"nome": "João"}).json()
    assert primeiro["id"] != segundo["id"]
    for quantidade in [2, 1]:
        assert client.post("/itens", json={
            "comanda_id": primeiro["id"], "nome_produto": "Cerveja",
            "quantidade": quantidade, "preco_unitario": 8,
        }).status_code == 200
    resumo = client.get(f'/comandas/{primeiro["id"]}').json()
    assert resumo["itens_agrupados"][0]["quantidade"] == 3
    assert len(resumo["itens"]) == 2
    assert client.put(f'/comandas/{primeiro["id"]}/checkout').status_code == 200
    cards = {c["id"]: c for c in client.get("/comandas").json()}
    assert cards[primeiro["id"]]["status"] == "PAGA"
    assert cards[primeiro["id"]]["valor_total"] == 24
    assert cards[segundo["id"]]["valor_total"] == 0
    terceiro = client.post("/atendimentos", json={"nome": "João"}).json()
    assert terceiro["id"] not in cards
    assert terceiro["status"] == "ABERTA"


@pytest.mark.parametrize("nome", ["", "   ", "a" * 121])
def test_nome_invalido_nao_cria_registros(client_cards, nome):
    client, sessions = client_cards
    assert client.post("/atendimentos", json={"nome": nome}).status_code == 422
    with sessions() as db:
        assert db.query(Cliente).count() == 0
        assert db.query(Comanda).count() == 0


def test_listagem_inclui_comandas_da_versao_anterior(client_cards):
    client, _ = client_cards
    cliente = client.post("/clientes", json={
        "nome": "Maria", "cpf": "123", "telefone": "", "email": "",
    }).json()
    comanda = client.post("/comandas", json={"cliente_id": cliente["id"]}).json()
    cards = client.get("/comandas").json()
    assert cards[0]["id"] == comanda["id"]
    assert cards[0]["nome_cliente"] == "Maria"


def test_as_duas_telas_continuam_disponiveis(client_cards):
    client, _ = client_cards
    cards = client.get("/cards")
    classico = client.get("/classico")
    assert cards.status_code == classico.status_code == 200
    assert 'id="formNova"' in cards.text
    assert 'href="/classico"' in cards.text
    assert 'id="listaClientes"' in classico.text
    assert "montarListaPedidos(data.itens_agrupados)" in classico.text
