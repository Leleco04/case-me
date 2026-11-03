import os
import logging
from typing import List, Dict, Any
import httpx

logger = logging.getLogger("mcp_client")

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://mcp-server:8001")
MCP_TIMEOUT = float(os.getenv("MCP_TIMEOUT", "15.0"))


class MCPClient:
    def __init__(self, base_url: str = MCP_SERVER_URL, timeout: float = MCP_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def listar_ferramentas_openai(self) -> List[Dict[str, Any]]:
        """
        Consulta as ferramentas no MCP Server e as converte para o schema aceito
        pelo endpoint de chat completions (OpenAI / OpenRouter tool format).
        """
        url = f"{self.base_url}/tools"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url)
                resp.raise_for_status()
                data = resp.json()
                raw_tools = data.get("tools", [])

                openai_tools = []
                for t in raw_tools:
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": t["name"],
                            "description": t["description"],
                            "parameters": t.get("parameters", {"type": "object", "properties": {}})
                        }
                    })
                return openai_tools
        except httpx.ConnectError:
            logger.error("Não foi possível conectar ao MCP Server em %s", self.base_url)
            raise ConnectionError(f"Servidor MCP inacessível em {self.base_url}. Verifique se o container mcp-server está ativo.")
        except Exception as e:
            logger.error("Erro ao listar ferramentas do MCP Server: %s", str(e))
            raise

    def executar_ferramenta(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Envia a instrução de execução de uma ferramenta para o container do MCP Server.
        """
        url = f"{self.base_url}/tools/call"
        payload = {
            "name": name,
            "arguments": arguments
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get("result", {})
        except httpx.TimeoutException:
            logger.error("Timeout de %ss ao executar ferramenta %s no MCP Server", self.timeout, name)
            return {
                "sucesso": False,
                "erro": f"Tempo limite ({self.timeout}s) excedido ao comunicar com o servidor de ferramentas para '{name}'."
            }
        except httpx.HTTPStatusError as e:
            logger.error("Erro HTTP %s ao executar ferramenta %s: %s", e.response.status_code, name, e.response.text)
            return {
                "sucesso": False,
                "erro": f"Erro do Servidor MCP ({e.response.status_code}): {e.response.text}"
            }
        except Exception as e:
            logger.error("Falha ao invocar ferramenta %s: %s", name, str(e))
            return {
                "sucesso": False,
                "erro": f"Falha ao executar ferramenta {name}: {str(e)}"
            }
