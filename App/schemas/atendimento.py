"""Entrada e resumo para os cards de atendimento por nome."""
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class AtendimentoCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=120)

    @field_validator("nome")
    @classmethod
    def limpar_nome(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Informe o nome da pessoa.")
        return value


class ComandaCard(BaseModel):
    id: int
    nome_cliente: str
    status: str
    valor_total: float
    criado_em: datetime
