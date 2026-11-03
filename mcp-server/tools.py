import os
import logging
import sqlite3
from typing import List, Dict, Any, Optional
import httpx
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger("mcp_tools")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

DUMMYJSON_BASE_URL = os.getenv("DUMMYJSON_BASE_URL", "https://dummyjson.com")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:admin@postgres:5432/compras"
)
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "10.0"))
USER_AGENT = "PurchasingAgent/1.0 (Mozilla/5.0; Windows NT 10.0; Win64; x64)"
SQLITE_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "compras.db"))


def _get_http_headers() -> Dict[str, str]:
    return {
        "User-Agent": USER_AGENT,
        "Accept": "application/json"
    }


def _init_sqlite(conn: sqlite3.Connection):
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS requisicoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                solicitante TEXT DEFAULT 'Usuario',
                pedido_original TEXT NOT NULL,
                resposta_agente TEXT,
                valor_total REAL NOT NULL DEFAULT 0.00,
                status TEXT NOT NULL DEFAULT 'CRIADA',
                ferramentas_utilizadas TEXT DEFAULT '[]',
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS itens_requisicao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requisicao_id INTEGER NOT NULL REFERENCES requisicoes(id) ON DELETE CASCADE,
                produto_id INTEGER,
                produto_nome TEXT NOT NULL,
                quantidade INTEGER NOT NULL DEFAULT 1,
                preco_unitario REAL NOT NULL,
                subtotal REAL NOT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)


def buscar_produtos(termo: str) -> Dict[str, Any]:
    """
    Busca produtos no catalogo da DummyJSON utilizando o endpoint de busca.
    Trata erros de conexao, status HTTP e timeout de forma resiliente.
    """
    if not termo or not termo.strip():
        return {
            "sucesso": False,
            "erro": "Termo de busca nao pode ser vazio.",
            "total": 0,
            "produtos": []
        }

    url = f"{DUMMYJSON_BASE_URL}/products/search"
    params = {"q": termo.strip()}

    try:
        with httpx.Client(timeout=HTTP_TIMEOUT, headers=_get_http_headers()) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            produtos_brutos = data.get("products", [])
            produtos_formatados = []

            for p in produtos_brutos:
                produtos_formatados.append({
                    "id": p.get("id"),
                    "title": p.get("title"),
                    "description": p.get("description"),
                    "category": p.get("category"),
                    "price": p.get("price"),
                    "discountPercentage": p.get("discountPercentage"),
                    "rating": p.get("rating"),
                    "stock": p.get("stock"),
                    "brand": p.get("brand")
                })

            logger.info("Busca por '%s' retornou %d produtos.", termo, len(produtos_formatados))
            return {
                "sucesso": True,
                "termo": termo,
                "total": len(produtos_formatados),
                "produtos": produtos_formatados
            }

    except httpx.TimeoutException:
        logger.error("Timeout ao consultar DummyJSON para o termo '%s'", termo)
        return {
            "sucesso": False,
            "erro": f"Tempo limite de {HTTP_TIMEOUT}s excedido ao buscar produtos na DummyJSON. O servico pode estar lento.",
            "produtos": []
        }
    except httpx.HTTPStatusError as e:
        logger.error("Erro HTTP %s ao consultar DummyJSON: %s", e.response.status_code, e.response.text)
        return {
            "sucesso": False,
            "erro": f"A DummyJSON retornou erro HTTP {e.response.status_code}.",
            "produtos": []
        }
    except Exception as e:
        logger.error("Falha inesperada ao buscar produtos: %s", str(e))
        return {
            "sucesso": False,
            "erro": f"Falha de comunicacao com o catalogo: {str(e)}",
            "produtos": []
        }


def detalhar_produto(id: int) -> Dict[str, Any]:
    """
    Obtem os detalhes completos de um produto especifico por ID.
    """
    try:
        produto_id = int(id)
    except (ValueError, TypeError):
        return {
            "sucesso": False,
            "erro": f"ID de produto invalido: {id}"
        }

    url = f"{DUMMYJSON_BASE_URL}/products/{produto_id}"

    try:
        with httpx.Client(timeout=HTTP_TIMEOUT, headers=_get_http_headers()) as client:
            response = client.get(url)
            if response.status_code == 404:
                return {
                    "sucesso": False,
                    "erro": f"Produto com ID {produto_id} nao foi encontrado no catalogo.",
                    "produto": None
                }
            response.raise_for_status()
            data = response.json()

            produto_detalhado = {
                "id": data.get("id"),
                "title": data.get("title"),
                "description": data.get("description"),
                "category": data.get("category"),
                "price": data.get("price"),
                "discountPercentage": data.get("discountPercentage"),
                "rating": data.get("rating"),
                "stock": data.get("stock"),
                "brand": data.get("brand"),
                "sku": data.get("sku"),
                "weight": data.get("weight"),
                "warrantyInformation": data.get("warrantyInformation"),
                "shippingInformation": data.get("shippingInformation"),
                "availabilityStatus": data.get("availabilityStatus")
            }

            logger.info("Produto ID %d detalhado com sucesso.", produto_id)
            return {
                "sucesso": True,
                "produto": produto_detalhado
            }

    except httpx.TimeoutException:
        logger.error("Timeout ao detalhar produto ID %d na DummyJSON", produto_id)
        return {
            "sucesso": False,
            "erro": f"Tempo limite de {HTTP_TIMEOUT}s excedido ao detalhar produto ID {produto_id}.",
            "produto": None
        }
    except httpx.HTTPStatusError as e:
        logger.error("Erro HTTP %s ao detalhar produto ID %d", e.response.status_code, produto_id)
        return {
            "sucesso": False,
            "erro": f"Erro HTTP {e.response.status_code} da DummyJSON ao detalhar produto {produto_id}.",
            "produto": None
        }
    except Exception as e:
        logger.error("Falha inesperada ao detalhar produto ID %d: %s", produto_id, str(e))
        return {
            "sucesso": False,
            "erro": f"Falha ao obter detalhes do produto: {str(e)}",
            "produto": None
        }


def criar_requisicao(
    itens: List[Dict[str, Any]],
    valor_total: float,
    pedido_original: str = "Solicitacao de compra via Agente",
    solicitante: str = "Usuario",
    justificativa: str = ""
) -> Dict[str, Any]:
    """
    DIFERENCIAL: Ferramenta MCP para gravacao direta da requisicao no banco.
    Conecta ao PostgreSQL e utiliza SQLite como fallback transparente.
    """
    if not itens or not isinstance(itens, list):
        return {
            "sucesso": False,
            "erro": "A requisicao deve conter ao menos um item valido."
        }

    try:
        valor_total_float = float(valor_total)
    except (ValueError, TypeError):
        return {
            "sucesso": False,
            "erro": f"Valor total invalido: {valor_total}"
        }

    # 1. Tentativa via PostgreSQL
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO requisicoes (solicitante, pedido_original, resposta_agente, valor_total, status)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, criado_em;
                """,
                (solicitante, pedido_original, justificativa, valor_total_float, "CRIADA")
            )
            req_row = cur.fetchone()
            requisicao_id = req_row["id"]

            itens_inseridos = []
            for item in itens:
                produto_id = item.get("produto_id") or item.get("id")
                produto_nome = item.get("produto_nome") or item.get("title") or item.get("nome") or "Produto sem nome"
                quantidade = int(item.get("quantidade", 1))
                preco_unitario = float(item.get("preco_unitario") or item.get("price") or 0.0)
                subtotal = float(item.get("subtotal") or (quantidade * preco_unitario))

                cur.execute(
                    """
                    INSERT INTO itens_requisicao (requisicao_id, produto_id, produto_nome, quantidade, preco_unitario, subtotal)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (requisicao_id, produto_id, produto_nome, quantidade, preco_unitario, subtotal)
                )
                itens_inseridos.append({
                    "produto_id": produto_id,
                    "produto_nome": produto_nome,
                    "quantidade": quantidade,
                    "preco_unitario": preco_unitario,
                    "subtotal": subtotal
                })

            conn.commit()
            conn.close()
            logger.info("Requisicao #%d criada com sucesso no PostgreSQL com %d itens. Total: $%.2f", requisicao_id, len(itens_inseridos), valor_total_float)

            return {
                "sucesso": True,
                "requisicao_id": requisicao_id,
                "valor_total": valor_total_float,
                "total_itens": len(itens_inseridos),
                "itens": itens_inseridos,
                "mensagem": f"Requisicao #{requisicao_id} criada e registrada no banco de dados com sucesso!"
            }

    except psycopg2.OperationalError:
        logger.info("PostgreSQL inacessivel. Utilizando persistencia local SQLite.")
    except Exception as e:
        logger.error("Erro no PostgreSQL: %s", str(e))

    # 2. Fallback via SQLite (para execucao local direta sem Docker)
    try:
        s_conn = sqlite3.connect(SQLITE_DB_PATH)
        s_conn.row_factory = sqlite3.Row
        _init_sqlite(s_conn)

        cur = s_conn.cursor()
        cur.execute(
            """
            INSERT INTO requisicoes (solicitante, pedido_original, resposta_agente, valor_total, status)
            VALUES (?, ?, ?, ?, ?);
            """,
            (solicitante, pedido_original, justificativa, valor_total_float, "CRIADA")
        )
        requisicao_id = cur.lastrowid

        itens_inseridos = []
        for item in itens:
            produto_id = item.get("produto_id") or item.get("id")
            produto_nome = item.get("produto_nome") or item.get("title") or item.get("nome") or "Produto sem nome"
            quantidade = int(item.get("quantidade", 1))
            preco_unitario = float(item.get("preco_unitario") or item.get("price") or 0.0)
            subtotal = float(item.get("subtotal") or (quantidade * preco_unitario))

            cur.execute(
                """
                INSERT INTO itens_requisicao (requisicao_id, produto_id, produto_nome, quantidade, preco_unitario, subtotal)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (requisicao_id, produto_id, produto_nome, quantidade, preco_unitario, subtotal)
            )
            itens_inseridos.append({
                "produto_id": produto_id,
                "produto_nome": produto_nome,
                "quantidade": quantidade,
                "preco_unitario": preco_unitario,
                "subtotal": subtotal
            })

        s_conn.commit()
        s_conn.close()
        logger.info("Requisicao #%d criada com sucesso no SQLite com %d itens. Total: $%.2f", requisicao_id, len(itens_inseridos), valor_total_float)

        return {
            "sucesso": True,
            "requisicao_id": requisicao_id,
            "valor_total": valor_total_float,
            "total_itens": len(itens_inseridos),
            "itens": itens_inseridos,
            "mensagem": f"Requisicao #{requisicao_id} criada e registrada no banco de dados com sucesso!"
        }

    except Exception as e:
        logger.error("Erro ao persistir requisicao: %s", str(e))
        return {
            "sucesso": False,
            "erro": f"Erro de banco de dados ao salvar requisicao: {str(e)}"
        }
