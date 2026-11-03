from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class RequisicaoCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    pedido: str = Field(..., alias="mensagem", description="Texto da solicitação de compra do usuário")
    solicitante: Optional[str] = Field("Usuário", description="Identificação do solicitante")


class ItemRequisicaoOut(BaseModel):
    id: Optional[int] = None
    produto_id: Optional[int] = None
    produto_nome: str
    quantidade: int
    preco_unitario: float
    subtotal: float
    criado_em: Optional[datetime] = None


class FerramentaChamada(BaseModel):
    ferramenta: str
    argumentos: Dict[str, Any]
    resultado_resumo: str
    status: str = "sucesso"


class RequisicaoOut(BaseModel):
    id: int
    solicitante: str
    pedido_original: str
    resposta_agente: Optional[str] = None
    valor_total: float
    status: str
    ferramentas_utilizadas: List[Dict[str, Any]] = Field(default_factory=list)
    itens: List[ItemRequisicaoOut] = Field(default_factory=list)
    criado_em: datetime


class ProcessarPedidoResponse(BaseModel):
    sucesso: bool
    resposta: str
    requisicao_id: Optional[int] = None
    valor_total: Optional[float] = None
    itens: List[Dict[str, Any]] = Field(default_factory=list)
    ferramentas_chamadas: List[FerramentaChamada] = Field(default_factory=list)
    erro: Optional[str] = None
