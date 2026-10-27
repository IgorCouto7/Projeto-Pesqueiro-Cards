from pydantic import BaseModel

class ItemCreate(BaseModel):
    comanda_id: int
    nome_produto: str
    quantidade: int
    preco_unitario: float

class ItemResponse(ItemCreate):
    id: int
    
    class Config:
        from_attributes = True