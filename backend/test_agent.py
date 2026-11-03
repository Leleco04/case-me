"""
Script de Validação Automatizada do Agente de Compras (Diferencial 3)
Executa 5 cenários de teste reais para validar o raciocínio autônomo,
uso de ferramentas MCP, integridade fiscal e prevenção de alucinações.

Pode ser executado via Docker Compose:
    docker compose run --rm backend python test_agent.py
"""

import os
import sys
import time
import json
import httpx

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
DIRECT_AGENT = os.getenv("TEST_DIRECT_AGENT", "false").lower() in ("true", "1", "yes")

# Cores ANSI para saída no terminal
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


CENARIOS = [
    {
        "id": 1,
        "titulo": "Compra individual dentro do orçamento (Smartphone)",
        "pedido": "Compre 1 iPhone ou smartphone similar com orçamento de até $1200 para a equipe de vendas.",
        "deve_criar_requisicao": True,
        "validacao": lambda r: r.get("requisicao_id") is not None and len(r.get("ferramentas_chamadas", [])) > 0
    },
    {
        "id": 2,
        "titulo": "Compra de múltiplos itens e quantidades específicas",
        "pedido": "Preciso de 2 perfumes e 1 batom para kits de boas-vindas da empresa.",
        "deve_criar_requisicao": True,
        "validacao": lambda r: r.get("requisicao_id") is not None and r.get("valor_total", 0) > 0
    },
    {
        "id": 3,
        "titulo": "Estouro de Orçamento (Integridade fiscal)",
        "pedido": "Gostaria de comprar 5 laptops gamer de última geração com um orçamento total de apenas $50.",
        "deve_criar_requisicao": False,
        "validacao": lambda r: r.get("requisicao_id") is None and ("orçamento" in r.get("resposta", "").lower() or "insuficiente" in r.get("resposta", "").lower() or "excede" in r.get("resposta", "").lower() or "ultrapassa" in r.get("resposta", "").lower())
    },
    {
        "id": 4,
        "titulo": "Produto Inexistente (Anti-alucinação)",
        "pedido": "Quero comprar 3 unidades de propulsor de teletransporte quântico interestelar com limite de $10000.",
        "deve_criar_requisicao": False,
        "validacao": lambda r: r.get("requisicao_id") is None and ("não" in r.get("resposta", "").lower() or "encontrado" in r.get("resposta", "").lower() or "catálogo" in r.get("resposta", "").lower())
    },
    {
        "id": 5,
        "titulo": "Compra com restrição específica de limite",
        "pedido": "Compre 2 unidades do produto id 1 (ou máscara Essence) com orçamento de até $50.",
        "deve_criar_requisicao": True,
        "validacao": lambda r: r.get("requisicao_id") is not None and r.get("valor_total", 0) <= 50.0
    }
]


def testar_via_api(pedido: str) -> dict:
    url = f"{BACKEND_URL}/requisicoes"
    with httpx.Client(timeout=90.0) as client:
        resp = client.post(url, json={"pedido": pedido, "solicitante": "Validador Automático"})
        resp.raise_for_status()
        return resp.json()


def testar_direto_agente(pedido: str) -> dict:
    from agent import PurchasingAgent
    agente = PurchasingAgent()
    resp = agente.processar_pedido(pedido_usuario=pedido, solicitante="Validador Automático")
    return {
        "sucesso": resp.sucesso,
        "resposta": resp.resposta,
        "requisicao_id": resp.requisicao_id,
        "valor_total": resp.valor_total,
        "itens": resp.itens,
        "ferramentas_chamadas": [f.model_dump() for f in resp.ferramentas_chamadas],
        "erro": resp.erro
    }


def executar_testes():
    print(f"\n{BOLD}{CYAN}========================================================================={RESET}")
    print(f"{BOLD}{CYAN}      BATERIA DE TESTES AUTOMATIZADOS DO AGENTE DE COMPRAS (LLM)       {RESET}")
    print(f"{BOLD}{CYAN}========================================================================={RESET}\n")

    modo = "Chamada direta ao Agente" if DIRECT_AGENT else f"API HTTP Backend ({BACKEND_URL})"
    print(f"{BOLD}Modo de execução:{RESET} {modo}\n")

    acertos = 0
    total = len(CENARIOS)

    for cenario in CENARIOS:
        cid = cenario["id"]
        titulo = cenario["titulo"]
        pedido = cenario["pedido"]
        deve_criar = cenario["deve_criar_requisicao"]

        print(f"{BOLD}{BLUE}[Teste {cid}/{total}] {titulo}{RESET}")
        print(f"  {BOLD}Prompt:{RESET} \"{pedido}\"")
        inicio = time.time()

        try:
            if DIRECT_AGENT:
                res = testar_direto_agente(pedido)
            else:
                try:
                    res = testar_via_api(pedido)
                except httpx.ConnectError:
                    print(f"  {YELLOW}Aviso: Backend HTTP não alcançado em {BACKEND_URL}. Executando diretamente pelo Agente...{RESET}")
                    res = testar_direto_agente(pedido)

            duracao = time.time() - inicio
            req_id = res.get("requisicao_id")
            ferramentas = [f.get("ferramenta") for f in res.get("ferramentas_chamadas", [])]
            passou = cenario["validacao"](res)

            print(f"  {BOLD}Duração:{RESET} {duracao:.2f}s")
            print(f"  {BOLD}Ferramentas acionadas:{RESET} {ferramentas}")
            print(f"  {BOLD}Requisição gerada:{RESET} {f'#{req_id} (Total: ${res.get(\"valor_total\")})' if req_id else 'Nenhuma (Correto para este cenário)'}")
            print(f"  {BOLD}Trecho da resposta:{RESET} \"{res.get('resposta', '')[:140]}...\"")

            if passou:
                print(f"  {BOLD}Status:{RESET} {GREEN}[PASS] APROVADO{RESET}\n")
                acertos += 1
            else:
                print(f"  {BOLD}Status:{RESET} {RED}[FAIL] FALHOU{RESET} (Comportamento inesperado para os critérios estabelecidos)\n")

        except Exception as e:
            print(f"  {RED}Erro durante execução do teste: {str(e)}{RESET}\n")

    print(f"{BOLD}{CYAN}========================================================================={RESET}")
    print(f"{BOLD}RESULTADO FINAL:{RESET} {GREEN if acertos == total else YELLOW}{acertos}/{total} testes passaram com sucesso!{RESET}")
    print(f"{BOLD}{CYAN}========================================================================={RESET}\n")

    if acertos == total:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    executar_testes()
