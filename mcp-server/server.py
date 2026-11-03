import os
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from tools import buscar_produtos, detalhar_produto, criar_requisicao

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("mcp_server")

app = FastAPI(
    title="MCP Server - Purchasing Agent",
    version="1.0.0",
    description="Servidor Model Context Protocol (MCP) com ferramentas para o Agente de Compras"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Definições padronizadas das ferramentas MCP (compatíveis com OpenAI tool schema)
TOOLS_REGISTRY = [
    {
        "name": "buscar_produtos",
        "description": "Busca produtos no catálogo da DummyJSON a partir de um termo de pesquisa (ex: 'laptop', 'perfume', 'phone'). Retorna lista de produtos com id, título, preço, estoque e avaliação.",
        "parameters": {
            "type": "object",
            "properties": {
                "termo": {
                    "type": "string",
                    "description": "Termo ou palavra-chave para buscar produtos no catálogo."
                }
            },
            "required": ["termo"]
        }
    },
    {
        "name": "detalhar_produto",
        "description": "Obtém detalhes completos de um produto específico através do seu ID numérico.",
        "parameters": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "integer",
                    "description": "Identificador numérico do produto (ex: 1, 2, 5)."
                }
            },
            "required": ["id"]
        }
    },
    {
        "name": "criar_requisicao",
        "description": "DIFERENCIAL: Salva e oficializa uma requisição de compra no banco de dados. Use APENAS quando os produtos estiverem selecionados e validados dentro do orçamento estipulado pelo usuário. NÃO chame se o orçamento estourar ou se produtos faltarem.",
        "parameters": {
            "type": "object",
            "properties": {
                "itens": {
                    "type": "array",
                    "description": "Lista de itens a serem requisitados.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "produto_id": {"type": "integer", "description": "ID do produto na DummyJSON"},
                            "produto_nome": {"type": "string", "description": "Nome ou título do produto"},
                            "quantidade": {"type": "integer", "description": "Quantidade desejada"},
                            "preco_unitario": {"type": "number", "description": "Preço unitário do produto em dólares"},
                            "subtotal": {"type": "number", "description": "Valor subtotal (quantidade * preço unitário)"}
                        },
                        "required": ["produto_nome", "quantidade", "preco_unitario"]
                    }
                },
                "valor_total": {
                    "type": "number",
                    "description": "Soma de todos os subtotais da requisição."
                },
                "justificativa": {
                    "type": "string",
                    "description": "Breve justificativa ou resumo da compra feita pelo agente."
                },
                "solicitante": {
                    "type": "string",
                    "description": "Nome do usuário solicitante (opcional, default: 'Usuário')."
                }
            },
            "required": ["itens", "valor_total"]
        }
    }
]


def execute_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Despacha a execução da ferramenta correspondente."""
    logger.info("Executando ferramenta MCP: %s com args: %s", name, arguments)
    if name == "buscar_produtos":
        termo = arguments.get("termo", "")
        return buscar_produtos(termo)
    elif name == "detalhar_produto":
        produto_id = arguments.get("id")
        return detalhar_produto(produto_id)
    elif name == "criar_requisicao":
        itens = arguments.get("itens", [])
        valor_total = arguments.get("valor_total", 0.0)
        solicitante = arguments.get("solicitante", "Usuário")
        justificativa = arguments.get("justificativa", "")
        pedido_original = arguments.get("pedido_original", "Solicitação via Agente")
        return criar_requisicao(
            itens=itens,
            valor_total=valor_total,
            pedido_original=pedido_original,
            solicitante=solicitante,
            justificativa=justificativa
        )
    else:
        raise ValueError(f"Ferramenta desconhecida: '{name}'")


class ToolCallRequest(BaseModel):
    name: str = Field(..., description="Nome da ferramenta MCP a ser executada")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Argumentos para a ferramenta")


@app.get("/health")
def health():
    return {"status": "ok", "service": "mcp-server"}


@app.get("/tools")
def list_tools():
    """Retorna o catálogo de ferramentas MCP registradas."""
    return {"tools": TOOLS_REGISTRY}


@app.post("/tools/call")
def call_tool(req: ToolCallRequest):
    """Executa uma ferramenta MCP pelo nome fornecido."""
    try:
        resultado = execute_tool(req.name, req.arguments)
        return {
            "name": req.name,
            "result": resultado
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Erro interno ao executar ferramenta %s: %s", req.name, str(e))
        raise HTTPException(status_code=500, detail=f"Erro interno ao executar ferramenta: {str(e)}")


@app.post("/tools/{tool_name}")
def call_tool_direct(tool_name: str, arguments: Dict[str, Any] = Body(...)):
    """Endpoint simplificado para invocar uma ferramenta pelo path."""
    try:
        resultado = execute_tool(tool_name, arguments)
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/jsonrpc")
@app.post("/mcp")
def handle_jsonrpc(payload: Dict[str, Any] = Body(...)):
    """
    Endpoint em conformidade com o protocolo JSON-RPC 2.0 / MCP Specification.
    Aceita requisições padrão MCP como 'initialize', 'tools/list' e 'tools/call'.
    """
    rpc_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False}
                },
                "serverInfo": {
                    "name": "purchasing-agent-mcp",
                    "version": "1.0.0"
                }
            }
        }
    elif method in ["tools/list", "tools.list"]:
        # Converte para schema padrão MCP
        mcp_tools = []
        for t in TOOLS_REGISTRY:
            mcp_tools.append({
                "name": t["name"],
                "description": t["description"],
                "inputSchema": t["parameters"]
            })
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "result": {"tools": mcp_tools}
        }
    elif method in ["tools/call", "tools.call"]:
        name = params.get("name")
        arguments = params.get("arguments", {})
        try:
            res = execute_tool(name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": rpc_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": str(res)
                        }
                    ],
                    "raw": res
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": rpc_id,
                "error": {
                    "code": -32000,
                    "message": str(e)
                }
            }
    else:
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "error": {
                "code": -32601,
                "message": f"Método não suportado: '{method}'"
            }
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
