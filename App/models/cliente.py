from sqlalchemy import Column, Integer, String
from App.db.connection import Base

class Cliente(Base):
    # Nome da tabela no banco de dados
    __tablename__ = "clientes"

    # As colunas da tabela
    id = Column(Integer, primary_key=True, index=True) # Identidade única (1, 2, 3...)
    nome = Column(String, nullable=False)              # Nome é obrigatório
    cpf = Column(String, unique=True, index=True)      # CPF não pode repetir
    telefone = Column(String)
    email = Column(String)