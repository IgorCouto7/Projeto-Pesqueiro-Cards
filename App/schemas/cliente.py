from pydantic import BaseModel

class ClienteBase(BaseModel):
    nome: str
    cpf: str
    telefone: str
    email: str

class ClienteCreate(ClienteBase):
    pass

class ClienteResponse(ClienteBase):
    id: int
    cpf: str | None

    class Config:
        from_attributes = True
