import os
import json
import logging
import sqlite3
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger("backend_db")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin@postgres:5432/compras")
SQLITE_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "compras.db"))


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


def get_connection():
    """Tenta conexao PostgreSQL; se falhar, retorna None."""
    try:
        return psycopg2.connect(DATABASE_URL)
    except psycopg2.OperationalError:
        return None


def get_sqlite_connection():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    _init_sqlite(conn)
    return conn


def listar_requisicoes() -> List[Dict[str, Any]]:
    """
    Retorna o historico de requisicoes registradas, com fallback transparente para SQLite.
    """
    pg_conn = get_connection()
    if pg_conn:
        try:
            with pg_conn.cursor(cursor_factory=RealDictCursor) as cur:
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
            logger.error("Erro no PostgreSQL ao listar requisicoes: %s", str(e))
        finally:
            pg_conn.close()

    # Fallback SQLite
    try:
        s_conn = get_sqlite_connection()
        cur = s_conn.cursor()
        cur.execute(
            """
            SELECT id, solicitante, pedido_original, resposta_agente,
                   valor_total, status, ferramentas_utilizadas, criado_em
            FROM requisicoes
            ORDER BY id DESC;
            """
        )
        rows = cur.fetchall()
        requisicoes = []
        for r in rows:
            req = dict(r)
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
                WHERE requisicao_id = ?
                ORDER BY id ASC;
                """,
                (req["id"],)
            )
            itens_rows = cur.fetchall()
            req["itens"] = [dict(it) for it in itens_rows]
            requisicoes.append(req)

        s_conn.close()
        return requisicoes
    except Exception as e:
        logger.error("Erro no SQLite ao listar requisicoes: %s", str(e))
        return []


def buscar_requisicao_por_id(requisicao_id: int) -> Optional[Dict[str, Any]]:
    pg_conn = get_connection()
    if pg_conn:
        try:
            with pg_conn.cursor(cursor_factory=RealDictCursor) as cur:
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
                if req:
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
                    req["itens"] = cur.fetchall()
                    return req
        finally:
            pg_conn.close()

    # Fallback SQLite
    try:
        s_conn = get_sqlite_connection()
        cur = s_conn.cursor()
        cur.execute(
            """
            SELECT id, solicitante, pedido_original, resposta_agente,
                   valor_total, status, ferramentas_utilizadas, criado_em
            FROM requisicoes
            WHERE id = ?;
            """,
            (requisicao_id,)
        )
        row = cur.fetchone()
        if not row:
            s_conn.close()
            return None

        req = dict(row)
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
            WHERE requisicao_id = ?
            ORDER BY id ASC;
            """,
            (requisicao_id,)
        )
        req["itens"] = [dict(it) for it in cur.fetchall()]
        s_conn.close()
        return req
    except Exception as e:
        logger.error("Erro ao buscar requisicao #%d: %s", requisicao_id, str(e))
        return None


def atualizar_requisicao_pos_agente(
    requisicao_id: int,
    resposta_agente: str,
    ferramentas_utilizadas: List[Dict[str, Any]],
    pedido_original: Optional[str] = None
) -> bool:
    pg_conn = get_connection()
    if pg_conn:
        try:
            with pg_conn.cursor() as cur:
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
                pg_conn.commit()
                return True
        except Exception:
            pg_conn.rollback()
        finally:
            pg_conn.close()

    # Fallback SQLite
    try:
        s_conn = get_sqlite_connection()
        with s_conn:
            s_conn.execute(
                """
                UPDATE requisicoes
                SET resposta_agente = ?,
                    ferramentas_utilizadas = ?,
                    pedido_original = COALESCE(?, pedido_original)
                WHERE id = ?;
                """,
                (resposta_agente, json.dumps(ferramentas_utilizadas), pedido_original, requisicao_id)
            )
        s_conn.close()
        return True
    except Exception as e:
        logger.error("Erro ao atualizar requisicao no SQLite: %s", str(e))
        return False
