from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from App.db.connection import Base

class Comanda(Base):
    __tablename__ = "comandas"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id")) 
    
    status = Column(String, default="ABERTA") 
    valor_total = Column(Float, default=0.0)  
    criado_em = Column(DateTime(timezone=True), server_default=func.now()) 

    # --- RELACIONAMENTOS ---
    # 1. Permite listar os pedidos desta comanda e os apaga se a comanda for deletada
    itens = relationship("ItemComanda", cascade="all, delete-orphan")
    
    # 2. Relacionamento com CLIENTE
    cliente = relationship("Cliente")