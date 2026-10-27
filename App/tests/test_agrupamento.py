"""Agrupamento de leitura com banco isolado, sem tocar nos arquivos reais."""
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from App.api.main import app, get_db
from App.db.connection import Base
from App.models.cliente import Cliente
from App.models.comanda import Comanda
from App.models.item import ItemComanda


class TestAgrupamento(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine)
        self.previous_overrides = app.dependency_overrides.copy()

        def override_db():
            with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)
        with self.sessions() as db:
            cliente = Cliente(nome="Mesa 5", cpf="agrupamento")
            db.add(cliente)
            db.flush()
            comandas = [Comanda(cliente_id=cliente.id) for _ in range(2)]
            db.add_all(comandas)
            db.commit()
            self.ids = [c.id for c in comandas]

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        self.engine.dispose()

    def adicionar(self, nome, quantidade, preco, comanda=None):
        response = self.client.post("/itens", json={
            "comanda_id": comanda or self.ids[0], "nome_produto": nome,
            "quantidade": quantidade, "preco_unitario": preco,
        })
        self.assertEqual(response.status_code, 200)
        return response.json()

    def consultar(self):
        response = self.client.get(f"/comandas/{self.ids[0]}")
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_soma_sem_perder_lancamentos_e_isola_comandas(self):
        primeiro = self.adicionar("Cerveja", 2, 8)
        segundo = self.adicionar("Cerveja", 1, 8)
        self.adicionar("Cerveja", 10, 8, self.ids[1])
        data = self.consultar()
        self.assertEqual(data["itens_agrupados"], [{
            "nome_produto": "Cerveja", "quantidade": 3,
            "preco_unitario": 8, "valor_total": 24,
        }])
        self.assertEqual({i["id"] for i in data["itens"]},
                         {primeiro["id"], segundo["id"]})
        self.assertEqual([i["quantidade"] for i in data["itens"]], [2, 1])
        self.assertEqual(data["valor_total"], 24)
        self.assertEqual(self.consultar(), data)
        with self.sessions() as db:
            self.assertEqual(db.query(ItemComanda).count(), 3)

    def test_preserva_precos_historicos_produtos_e_checkout(self):
        self.adicionar("Cerveja", 2, 8)
        self.adicionar("Cerveja", 1, 10)
        self.adicionar("Agua", 1, 0.1)
        self.adicionar("Agua", 2, 0.1)
        data = self.consultar()
        self.assertEqual(len(data["itens_agrupados"]), 3)
        self.assertEqual([i["valor_total"] for i in data["itens_agrupados"]],
                         [16, 10, 0.3])
        self.assertEqual([i["preco_unitario"] for i in data["itens"]],
                         [8, 10, 0.1, 0.1])
        self.assertAlmostEqual(data["valor_total"], 26.3)
        response = self.client.put(f"/comandas/{self.ids[0]}/checkout")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["itens_agrupados"], data["itens_agrupados"])
        self.assertEqual(self.consultar()["status"], "PAGA")

    def test_comanda_vazia_e_inexistente(self):
        self.assertEqual(self.consultar()["itens_agrupados"], [])
        self.assertEqual(self.client.get("/comandas/99999").status_code, 404)
