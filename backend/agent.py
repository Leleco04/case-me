import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
import httpx

from mcp_client import MCPClient
from models import ProcessarPedidoResponse, FerramentaChamada
import database

logger = logging.getLogger("purchasing_agent")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Configuracao da Chave OpenRouter via Variaveis de Ambiente
RAW_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()

# Sanitizacao: Corrige se foi passada com 'vl' no lugar de 'v1'
if RAW_KEY.startswith("sk-or-vl-"):
    OPENROUTER_API_KEY = "sk-or-v1-" + RAW_KEY[len("sk-or-vl-"):]
else:
    OPENROUTER_API_KEY = RAW_KEY

OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_TIMEOUT = float(os.getenv("OPENROUTER_TIMEOUT", "60.0"))

SYSTEM_PROMPT = """Você é o Agente de Compras Corporativo oficial de uma empresa.
Sua missão é atender às requisições de compras dos colaboradores com extrema precisão, disciplina fiscal e autonomia.

REGRAS DE CONDUTA E DIRETRIZES FUNDAMENTAIS:
1. SEM FLUXO FIXO: Você decide de forma totalmente autônoma quando e quais ferramentas consultar para atender à demanda.
2. CONSULTA AO CATÁLOGO:
   - Use a ferramenta `buscar_produtos(termo)` para pesquisar produtos disponíveis na base DummyJSON.
   - Use `detalhar_produto(id)` se precisar de informações mais aprofundadas sobre garantia, estoque ou especificações.
3. VERACIDADE E RESPEITO AO ORÇAMENTO (REGRA DE OURO):
   - NUNCA invente produtos, marcas, estoques ou preços. Baseie-se estritamente nos dados retornados pelas ferramentas.
   - Se o usuário estipular um orçamento máximo (ex: "até $1000", "limite de $50"):
     a) Calcule os preços reais dos produtos encontrados.
     b) Se o valor total ultrapassar o orçamento estipulado, NÃO CRIE A REQUISIÇÃO! NÃO chame a ferramenta `criar_requisicao`.
        Em vez disso, responda educadamente explicando com clareza quais produtos foram localizados, quais os preços reais de cada um,
        quanto o orçamento foi excedido e que a compra não pôde ser aprovada por estouro de orçamento.
   - Se o produto solicitado não existir no catálogo (ex: itens inexistentes ou termo sem resultados):
     NÃO invente dados. Informe honestamente que o produto não foi encontrado no catálogo e encerre sem criar requisição.
4. GRAVAÇÃO DA REQUISIÇÃO NO BANCO (FERRAMENTA MCP `criar_requisicao`):
   - Quando os produtos forem encontrados com sucesso e estiverem dentro do orçamento informado (ou quando não houver limite estipulado de orçamento):
     Você deve decidir autonomamente chamar a ferramenta `criar_requisicao` passando a lista de itens selecionados (com produto_id, produto_nome, quantidade, preco_unitario e subtotal) e o valor_total.
   - Assim que a requisição for gravada, a ferramenta retornará o número `requisicao_id`.
5. FORMATO DA RESPOSTA FINAL:
   - Sempre forneça uma resposta clara, estruturada e amigável em português.
   - Quando a compra for aprovada, inclua obrigatoriamente:
     • O número da Requisição criada (ex: Requisição #X)
     • A lista detalhada dos itens escolhidos (Nome do produto, Quantidade, Preço unitário e Subtotal)
     • O Valor Total da compra em dólares ($)
     • Confirmação de que o pedido foi registrado com sucesso.
   - Se a DummyJSON ou o serviço de ferramentas apresentar lentidão ou erro de timeout, informe isso com transparência e cordialidade ao usuário.
"""


class PurchasingAgent:
    def __init__(self, mcp_client: Optional[MCPClient] = None):
        self.mcp_client = mcp_client or MCPClient()
        self.api_key = OPENROUTER_API_KEY
        self.model = OPENROUTER_MODEL
        self.base_url = OPENROUTER_BASE_URL

    def _call_openrouter(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Faz a chamada à API de Chat Completions da OpenRouter."""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/purchasing-agent",
            "X-Title": "Purchasing Agent System",
            "User-Agent": "PurchasingAgent/1.0"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "temperature": 0.2
        }

        with httpx.Client(timeout=OPENROUTER_TIMEOUT) as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                logger.error("Erro da OpenRouter (%s): %s", resp.status_code, resp.text)
                resp.raise_for_status()
            return resp.json()

    def processar_pedido(self, pedido_usuario: str, solicitante: str = "Usuário") -> ProcessarPedidoResponse:
        """
        Executa o loop conversacional e de raciocínio autônomo do agente com tool-calling.
        """
        logger.info("Iniciando processamento de pedido: '%s' para '%s'", pedido_usuario, solicitante)

        if not self.api_key:
            return ProcessarPedidoResponse(
                sucesso=False,
                resposta="A chave da API OpenRouter (OPENROUTER_API_KEY) não foi configurada. Por favor, configure-a no arquivo .env ou no docker-compose.yml.",
                erro="OPENROUTER_API_KEY_NOT_FOUND"
            )

        # 1. Obter catálogo de ferramentas do MCP Server
        try:
            tools = self.mcp_client.listar_ferramentas_openai()
        except Exception as e:
            msg_erro = f"Falha ao conectar com o Servidor MCP: {str(e)}"
            logger.error(msg_erro)
            return ProcessarPedidoResponse(
                sucesso=False,
                resposta="Desculpe, o sistema de compras está temporariamente indisponível pois o servidor de ferramentas (MCP) não pôde ser acessado.",
                erro=msg_erro
            )

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Solicitante: {solicitante}\nPedido: {pedido_usuario}"}
        ]

        ferramentas_chamadas: List[FerramentaChamada] = []
        requisicao_id_criada: Optional[int] = None
        valor_total_criado: Optional[float] = None
        itens_criados: List[Dict[str, Any]] = []

        max_rodadas = 6
        rodada = 0

        while rodada < max_rodadas:
            rodada += 1
            logger.info("Rodada do agente #%d...", rodada)

            try:
                data = self._call_openrouter(messages, tools)
            except httpx.TimeoutException:
                return ProcessarPedidoResponse(
                    sucesso=False,
                    resposta="O modelo de inteligência artificial demorou muito para responder (timeout). Por favor, tente novamente.",
                    erro="Timeout na comunicação com a OpenRouter."
                )
            except Exception as e:
                logger.error("Erro ao chamar LLM: %s", str(e))
                return ProcessarPedidoResponse(
                    sucesso=False,
                    resposta=f"Ocorreu um erro ao comunicar com a inteligência artificial: {str(e)}",
                    erro=str(e)
                )

            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            tool_calls = message.get("tool_calls")

            # Se não houver chamadas de ferramentas, o agente chegou à sua resposta final
            if not tool_calls:
                resposta_final = message.get("content", "").strip()
                logger.info("Agente concluiu raciocínio com sucesso na rodada #%d.", rodada)

                # Se uma requisição foi criada pelo LLM durante as chamadas, atualiza os dados no banco
                if requisicao_id_criada:
                    database.atualizar_requisicao_pos_agente(
                        requisicao_id=requisicao_id_criada,
                        resposta_agente=resposta_final,
                        ferramentas_utilizadas=[f.model_dump() for f in ferramentas_chamadas],
                        pedido_original=pedido_usuario
                    )

                return ProcessarPedidoResponse(
                    sucesso=True,
                    resposta=resposta_final,
                    requisicao_id=requisicao_id_criada,
                    valor_total=valor_total_criado,
                    itens=itens_criados,
                    ferramentas_chamadas=ferramentas_chamadas
                )

            # Adiciona a mensagem do assistente contendo as chamadas de ferramentas ao histórico
            messages.append(message)

            # Executa cada ferramenta requerida pelo LLM
            for tool_call in tool_calls:
                call_id = tool_call.get("id")
                func = tool_call.get("function", {})
                tool_name = func.get("name")
                raw_args = func.get("arguments", "{}")

                try:
                    arguments = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except Exception:
                    arguments = {}

                # Executa no container MCP
                resultado = self.mcp_client.executar_ferramenta(tool_name, arguments)

                # Resumo visual amigável para exibição no chat
                status_call = "sucesso" if resultado.get("sucesso", True) else "erro"
                resumo = ""
                if tool_name == "buscar_produtos":
                    total_p = resultado.get("total", len(resultado.get("produtos", [])))
                    resumo = f"{total_p} produto(s) encontrado(s) no catálogo"
                elif tool_name == "detalhar_produto":
                    prod = resultado.get("produto") or {}
                    resumo = f"Produto ID {prod.get('id')}: {prod.get('title')} (${prod.get('price')})"
                elif tool_name == "criar_requisicao":
                    if resultado.get("sucesso"):
                        requisicao_id_criada = resultado.get("requisicao_id")
                        valor_total_criado = resultado.get("valor_total")
                        itens_criados = resultado.get("itens", [])
                        resumo = f"Requisição #{requisicao_id_criada} gravada com sucesso! Total: ${valor_total_criado:.2f}"
                    else:
                        resumo = f"Falha ao salvar: {resultado.get('erro')}"
                else:
                    resumo = str(resultado)[:120]

                ferramentas_chamadas.append(FerramentaChamada(
                    ferramenta=tool_name,
                    argumentos=arguments,
                    resultado_resumo=resumo,
                    status=status_call
                ))

                # Insere o retorno da ferramenta como mensagem 'tool'
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps(resultado, ensure_ascii=False)
                })

        # Caso exceda as rodadas máximas de proteção
        return ProcessarPedidoResponse(
            sucesso=False,
            resposta="O agente atingiu o limite de passos para este pedido. Por favor, tente simplificar sua solicitação.",
            ferramentas_chamadas=ferramentas_chamadas,
            erro="Limite de iterações excedido."
        )
