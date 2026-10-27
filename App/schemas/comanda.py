from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional 
from App.schemas.item import ItemResponse 

class ComandaBase(BaseModel):
    cliente_id: int

class ComandaCreate(ComandaBase):
    pass

class ComandaResponse(ComandaBase):
    id: int
    status: str
    valor_total: float
    criado_em: datetime
    
    # O CAMPO ESSENCIAL: Permite que o retorno inclua a lista detalhada de pedidos
    itens: Optional[List[ItemResponse]] = None 

    class Config:
        from_attributes = True