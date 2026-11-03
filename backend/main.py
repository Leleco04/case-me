import os
import logging
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from models import RequisicaoCreate, ProcessarPedidoResponse, RequisicaoOut
from agent import PurchasingAgent
import database

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("backend_api")

app = FastAPI(
    title="API do Agente de Compras",
    version="1.0.0",
    description="Backend orquestrador do Agente de Compras com OpenRouter e MCP"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instância única do Agente de Compras
agent = PurchasingAgent()


@app.get("/health")
def health_check():
    """Verifica a integridade do backend e da conexao com o banco de dados."""
    db_type = "none"
    db_ok = False
    conn = database.get_connection()
    if conn:
        try:
            conn.close()
            db_ok = True
            db_type = "postgresql"
        except Exception:
            pass

    if not db_ok:
        try:
            s_conn = database.get_sqlite_connection()
            s_conn.close()
            db_ok = True
            db_type = "sqlite_fallback"
        except Exception:
            pass

    return {
        "status": "ok" if db_ok else "error",
        "service": "backend",
        "database_connected": db_ok,
        "database_type": db_type,
        "model": agent.model
    }


@app.post(
    "/requisicoes",
    response_model=ProcessarPedidoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Processa um novo pedido de compra via Agente LLM"
)
def criar_ou_processar_requisicao(payload: RequisicaoCreate):
    """
    Endpoint principal:
    1. Recebe a solicitação do usuário.
    2. Invoca o Agente LLM (OpenRouter) com acesso ao catálogo via ferramentas MCP.
    3. O LLM decide autonomamente se pesquisa, detalha produtos e se grava a requisição no PostgreSQL.
    4. Retorna a resposta, o ID da requisição gerada (se aplicável) e as ferramentas MCP acionadas.
    """
    pedido = payload.pedido.strip()
    if not pedido:
        raise HTTPException(status_code=400, detail="O pedido/mensagem não pode ser vazio.")

    logger.info("Nova requisição recebida: '%s'", pedido)
    resultado = agent.processar_pedido(pedido_usuario=pedido, solicitante=payload.solicitante or "Usuário")

    return resultado


@app.get(
    "/requisicoes",
    response_model=List[RequisicaoOut],
    summary="Lista todo o histórico de requisições de compras"
)
def listar_historico_requisicoes():
    """
    Retorna o histórico completo de requisições registradas no banco de dados PostgreSQL,
    incluindo os itens comprados, subtotais e ferramentas MCP utilizadas pelo agente.
    """
    try:
        return database.listar_requisicoes()
    except Exception as e:
        logger.error("Erro ao listar histórico de requisições: %s", str(e))
        raise HTTPException(status_code=500, detail="Erro interno ao consultar histórico de requisições.")


@app.get(
    "/requisicoes/{requisicao_id}",
    response_model=RequisicaoOut,
    summary="Detalha uma requisição específica pelo ID"
)
def obter_requisicao(requisicao_id: int):
    req = database.buscar_requisicao_por_id(requisicao_id)
    if not req:
        raise HTTPException(status_code=404, detail=f"Requisição #{requisicao_id} não encontrada.")
    return req


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
