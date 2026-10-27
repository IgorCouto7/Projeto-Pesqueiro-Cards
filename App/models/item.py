from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from App.db.connection import Base

class ItemComanda(Base):
    __tablename__ = "itens_comanda"

    id = Column(Integer, primary_key=True, index=True)
    comanda_id = Column(Integer, ForeignKey("comandas.id")) # Link com a Comanda
    
    nome_produto = Column(String) # Ex: "Cerveja", "Tilápia KG"
    quantidade = Column(Integer)
    preco_unitario = Column(Float)
    
    # Relacionamento inverso (opcional, mas útil)
    comanda = relationship("Comanda")