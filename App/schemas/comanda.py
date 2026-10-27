from decimal import Decimal
from pydantic import BaseModel, computed_field
from datetime import datetime
from typing import List, Optional 
from App.schemas.item import ItemResponse 

class ComandaBase(BaseModel):
    cliente_id: int

class ComandaCreate(ComandaBase):
    pass

class ItemAgrupado(BaseModel):
    nome_produto: str
    quantidade: int
    preco_unitario: float
    valor_total: float

class ComandaResponse(ComandaBase):
    id: int
    status: str
    valor_total: float
    criado_em: datetime
    
    # O CAMPO ESSENCIAL: Permite que o retorno inclua a lista detalhada de pedidos
    itens: Optional[List[ItemResponse]] = None 

    @computed_field
    @property
    def itens_agrupados(self) -> List[ItemAgrupado]:
        # Sem catálogo de produtos, a identidade é o nome exato e o preço
        # histórico. Nunca altera ou substitui os lançamentos originais.
        grupos = {}
        totais = {}
        for item in self.itens or []:
            preco = Decimal(str(item.preco_unitario))
            chave = (item.nome_produto, preco)
            if chave not in grupos:
                grupos[chave] = ItemAgrupado(
                    nome_produto=item.nome_produto, quantidade=0,
                    preco_unitario=item.preco_unitario, valor_total=0,
                )
                totais[chave] = Decimal(0)
            grupos[chave].quantidade += item.quantidade
            totais[chave] += preco * item.quantidade
            grupos[chave].valor_total = float(totais[chave])
        return list(grupos.values())

    class Config:
        from_attributes = True
