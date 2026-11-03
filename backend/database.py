import os
import json
import logging
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger("backend_db")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin@postgres:5432/compras")


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def listar_requisicoes() -> List[Dict[str, Any]]:
    """
    Retorna o histórico de requisições registradas no banco, ordenadas pela mais recente,
    incluindo a lista aninhada dos seus respectivos itens.
    """
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, solicitante, pedido_original, resposta_agente,
                       valor_total, status, ferramentas_utilizadas, criado_em
                FROM requisicoes
                ORDER BY criado_em DESC;
                """
            )
            requisicoes = cur.fetchall()

            for req in requisicoes:
                # Converte tipos numéricos e datas para JSON-friendly
                req["valor_total"] = float(req["valor_total"]) if req.get("valor_total") is not None else 0.0
                if isinstance(req.get("ferramentas_utilizadas"), str):
                    try:
                        req["ferramentas_utilizadas"] = json.loads(req["ferramentas_utilizadas"])
                    except Exception:
                        req["ferramentas_utilizadas"] = []
                elif req.get("ferramentas_utilizadas") is None:
                    req["ferramentas_utilizadas"] = []

                cur.execute(
                    """
                    SELECT id, produto_id, produto_nome, quantidade, preco_unitario, subtotal, criado_em
                    FROM itens_requisicao
                    WHERE requisicao_id = %s
                    ORDER BY id ASC;
                    """,
                    (req["id"],)
                )
                itens = cur.fetchall()
                for item in itens:
                    item["preco_unitario"] = float(item["preco_unitario"])
                    item["subtotal"] = float(item["subtotal"])
                req["itens"] = itens

            return requisicoes
    except Exception as e:
        logger.error("Erro ao listar requisições do banco de dados: %s", str(e))
        return []
    finally:
        if conn:
            conn.close()


def buscar_requisicao_por_id(requisicao_id: int) -> Optional[Dict[str, Any]]:
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, solicitante, pedido_original, resposta_agente,
                       valor_total, status, ferramentas_utilizadas, criado_em
                FROM requisicoes
                WHERE id = %s;
                """,
                (requisicao_id,)
            )
            req = cur.fetchone()
            if not req:
                return None

            req["valor_total"] = float(req["valor_total"]) if req.get("valor_total") is not None else 0.0
            if isinstance(req.get("ferramentas_utilizadas"), str):
                try:
                    req["ferramentas_utilizadas"] = json.loads(req["ferramentas_utilizadas"])
                except Exception:
                    req["ferramentas_utilizadas"] = []

            cur.execute(
                """
                SELECT id, produto_id, produto_nome, quantidade, preco_unitario, subtotal, criado_em
                FROM itens_requisicao
                WHERE requisicao_id = %s
                ORDER BY id ASC;
                """,
                (req["id"],)
            )
            itens = cur.fetchall()
            for item in itens:
                item["preco_unitario"] = float(item["preco_unitario"])
                item["subtotal"] = float(item["subtotal"])
            req["itens"] = itens

            return req
    except Exception as e:
        logger.error("Erro ao buscar requisição #%s: %s", requisicao_id, str(e))
        return None
    finally:
        if conn:
            conn.close()


def atualizar_requisicao_pos_agente(
    requisicao_id: int,
    resposta_agente: str,
    ferramentas_utilizadas: List[Dict[str, Any]],
    pedido_original: Optional[str] = None
) -> bool:
    """Atualiza a resposta final do agente e as ferramentas chamadas na requisição."""
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE requisicoes
                SET resposta_agente = %s,
                    ferramentas_utilizadas = %s,
                    pedido_original = COALESCE(%s, pedido_original)
                WHERE id = %s;
                """,
                (resposta_agente, json.dumps(ferramentas_utilizadas), pedido_original, requisicao_id)
            )
            conn.commit()
            return True
    except Exception as e:
        logger.error("Erro ao atualizar requisição #%s: %s", requisicao_id, str(e))
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()
