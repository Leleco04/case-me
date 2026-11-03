import pytest
from unittest.mock import patch, MagicMock
import httpx
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools import buscar_produtos, detalhar_produto, criar_requisicao
from server import app


@pytest.fixture
def client():
    return TestClient(app)


# ============================================================================
# 1. TESTES UNITÁRIOS: buscar_produtos
# ============================================================================

def test_buscar_produtos_sucesso():
    fake_response = {
        "products": [
            {
                "id": 1,
                "title": "Essence Mascara Lash Princess",
                "description": "Popular mascara for lashes",
                "category": "beauty",
                "price": 9.99,
                "discountPercentage": 7.17,
                "rating": 4.94,
                "stock": 5,
                "brand": "Essence"
            }
        ]
    }

    with patch("httpx.Client.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = fake_response
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        resultado = buscar_produtos("mascara")

        assert resultado["sucesso"] is True
        assert resultado["total"] == 1
        assert len(resultado["produtos"]) == 1
        assert resultado["produtos"][0]["id"] == 1
        assert resultado["produtos"][0]["title"] == "Essence Mascara Lash Princess"
        assert resultado["produtos"][0]["price"] == 9.99


def test_buscar_produtos_termo_vazio():
    resultado = buscar_produtos("")
    assert resultado["sucesso"] is False
    assert "vazio" in resultado["erro"].lower()
    assert resultado["total"] == 0


def test_buscar_produtos_timeout():
    with patch("httpx.Client.get", side_effect=httpx.TimeoutException("Connection timed out")):
        resultado = buscar_produtos("laptop")
        assert resultado["sucesso"] is False
        assert "excedido" in resultado["erro"].lower() or "timeout" in resultado["erro"].lower()
        assert resultado["produtos"] == []


def test_buscar_produtos_http_error():
    req = httpx.Request("GET", "https://dummyjson.com/products/search?q=laptop")
    resp = httpx.Response(status_code=500, request=req)
    with patch("httpx.Client.get", side_effect=httpx.HTTPStatusError("Server Error", request=req, response=resp)):
        resultado = buscar_produtos("laptop")
        assert resultado["sucesso"] is False
        assert "500" in resultado["erro"]


# ============================================================================
# 2. TESTES UNITÁRIOS: detalhar_produto
# ============================================================================

def test_detalhar_produto_sucesso():
    fake_produto = {
        "id": 5,
        "title": "Red Nail Polish",
        "description": "Vibrant red polish",
        "category": "beauty",
        "price": 8.99,
        "discountPercentage": 2.5,
        "rating": 4.5,
        "stock": 20,
        "brand": "NailArt",
        "sku": "NAIL-001",
        "weight": 50,
        "warrantyInformation": "1 year warranty",
        "shippingInformation": "Ships in 2 days",
        "availabilityStatus": "In Stock"
    }

    with patch("httpx.Client.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = fake_produto
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        resultado = detalhar_produto(5)

        assert resultado["sucesso"] is True
        assert resultado["produto"]["id"] == 5
        assert resultado["produto"]["title"] == "Red Nail Polish"
        assert resultado["produto"]["price"] == 8.99
        assert resultado["produto"]["brand"] == "NailArt"


def test_detalhar_produto_nao_encontrado_404():
    with patch("httpx.Client.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        resultado = detalhar_produto(999999)
        assert resultado["sucesso"] is False
        assert "encontrado" in resultado["erro"].lower()


def test_detalhar_produto_timeout():
    with patch("httpx.Client.get", side_effect=httpx.TimeoutException("Timeout")):
        resultado = detalhar_produto(1)
        assert resultado["sucesso"] is False
        assert "excedido" in resultado["erro"].lower() or "timeout" in resultado["erro"].lower()


def test_detalhar_produto_id_invalido():
    resultado = detalhar_produto("abc")
    assert resultado["sucesso"] is False
    assert "invalido" in resultado["erro"].lower() or "inválido" in resultado["erro"].lower()


# ============================================================================
# 3. TESTES UNITÁRIOS: criar_requisicao (Diferencial)
# ============================================================================

def test_criar_requisicao_sucesso():
    itens = [
        {
            "produto_id": 1,
            "produto_nome": "Smartphone Modelo X",
            "quantidade": 2,
            "preco_unitario": 350.00,
            "subtotal": 700.00
        }
    ]

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"id": 42, "criado_em": "2026-01-01T00:00:00Z"}
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch("psycopg2.connect", return_value=mock_conn):
        resultado = criar_requisicao(
            itens=itens,
            valor_total=700.00,
            pedido_original="Comprar 2 smartphones",
            solicitante="Diretoria TI"
        )

        assert resultado["sucesso"] is True
        assert resultado["requisicao_id"] == 42
        assert resultado["valor_total"] == 700.00
        assert resultado["total_itens"] == 1
        assert "sucesso" in resultado["mensagem"].lower()
        mock_conn.commit.assert_called_once()


def test_criar_requisicao_itens_vazios():
    resultado = criar_requisicao(itens=[], valor_total=100.0)
    assert resultado["sucesso"] is False
    assert "ao menos um item" in resultado["erro"].lower()


def test_criar_requisicao_valor_invalido():
    resultado = criar_requisicao(itens=[{"produto_nome": "Teste"}], valor_total="invalido")
    assert resultado["sucesso"] is False
    assert "invalido" in resultado["erro"].lower() or "inválido" in resultado["erro"].lower()


# ============================================================================
# 4. TESTES DA API HTTP & JSON-RPC DO SERVIDOR MCP
# ============================================================================

def test_endpoint_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_endpoint_list_tools(client):
    response = client.get("/tools")
    assert response.status_code == 200
    tools = response.json()["tools"]
    tool_names = [t["name"] for t in tools]
    assert "buscar_produtos" in tool_names
    assert "detalhar_produto" in tool_names
    assert "criar_requisicao" in tool_names


def test_endpoint_call_tool(client):
    with patch("server.buscar_produtos") as mock_buscar:
        mock_buscar.return_value = {"sucesso": True, "produtos": [], "total": 0}
        response = client.post("/tools/call", json={"name": "buscar_produtos", "arguments": {"termo": "phone"}})
        assert response.status_code == 200
        assert response.json()["name"] == "buscar_produtos"
        assert response.json()["result"]["sucesso"] is True


def test_endpoint_jsonrpc_tools_list(client):
    payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "tools/list",
        "params": {}
    }
    response = client.post("/jsonrpc", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert "tools" in data["result"]
    assert len(data["result"]["tools"]) == 3


def test_endpoint_jsonrpc_tools_call(client):
    with patch("server.detalhar_produto") as mock_detalhe:
        mock_detalhe.return_value = {"sucesso": True, "produto": {"id": 1, "title": "Produto Teste"}}
        payload = {
            "jsonrpc": "2.0",
            "id": "2",
            "method": "tools/call",
            "params": {"name": "detalhar_produto", "arguments": {"id": 1}}
        }
        response = client.post("/mcp", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "2"
        assert "content" in data["result"]
