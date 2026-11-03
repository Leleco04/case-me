# Agente de Compras Corporativo

Sistema de Agente de Compras Autonomo baseado no protocolo MCP (Model Context Protocol) e orquestracao de LLMs via OpenRouter, projetado com arquitetura distribuida de microsservicos e provisionamento Plug & Play via Docker Compose.

---

## 1. Visao Geral e Inicio Rapido

O projeto foi estruturado para execucao imediata sem necessidade de configuracao manual de dependencias no ambiente do host.

### Pre-requisitos
- Docker Engine e Docker Compose instalados.

### Execucao em Um Comando

1. Copie o arquivo de exemplo de variaveis de ambiente e configure sua chave:
```bash
cp .env.example .env
```

2. Inicialize todos os servicos da aplicacao:
```bash
docker compose up --build
```

### URLs de Acesso

- Interface Web (Chat): http://localhost:3000 (ou http://localhost:80)
- Documentacao Interativa da API (Swagger UI): http://localhost:8000/docs
- Catalogo de Ferramentas MCP: http://localhost:8001/tools

---

## 2. Execucao de Testes Automatizados

O sistema conta com duas suites de testes automatizados executaveis diretamente via Docker:

### Testes Unitarios do Servidor MCP
Testa o isolamento de rede, resiliencia a falhas HTTP, timeouts e tratamento de dados com mocks completos, sem consumir tokens de LLM:
```bash
docker compose run --rm mcp-server pytest
```

### Validacao Comportamental do Agente LLM
Executa os 5 cenarios corporativos de validacao para verificar a integridade fiscal, conformidade orcamentaria e prevencao de alucinacoes:
```bash
docker compose run --rm backend python test_agent.py
```

---

## 3. Uso de IA e Metodologia SDD (Specification-Driven Development)

O desenvolvimento deste projeto foi integralmente conduzido sob a metodologia **SDD (Specification-Driven Development)**, combinada com praticas avancadas de Engenharia de Software Assistida por Inteligencia Artificial.

### Fundamentos do SDD no Ciclo de Vida do Projeto

1. **Especificacao Formal Previa de Contratos (Contracts-First):**
   - **Contratos MCP:** As ferramentas expostas ao agente (`buscar_produtos`, `detalhar_produto` e `criar_requisicao`) foram formalizadas segundo a especificacao JSON-RPC 2.0 / MCP, com schemas estritos de entrada (`inputSchema`) e modelos tipados via Pydantic.
   - **Contratos de Persistencia:** O schema relacional do PostgreSQL foi formalizado no `init.sql`, assegurando atomicidade, integridade referencial via foreign keys (`ON DELETE CASCADE`) e indexacao para consultas frequentes.
   - **Contratos de Integracao Frontend-Backend:** Roteamento unificado atraves de proxy reverso no Nginx (`/api/`), eliminando atritos de Cross-Origin Resource Sharing (CORS) e desacoplando os containers.

2. **Engenharia e Sintese de Codigo Guiadas por IA:**
   - **Governança de Raciocinio do LLM:** O comportamento do agente foi especificado atraves de um system prompt declarativo que impoe regras de governanca fiscal. O agente nao possui um fluxo rigido prescritivo; ele avalia autonomamente o estado da consulta, analisa precos reais do catalogo e decide quando persistir a compra ou rejeita-la com justificativa clara.
   - **Garantia de Zero Alucinacao (Integridade de Dados):** O modelo opera sob a diretriz estrita de consultar ferramentas externas antes de validar qualquer declaracao de disponibilidade ou preco. Caso um produto nao exista na base DummyJSON, o agente e instruido formalmente a declarar a indisponibilidade, abstendo-se de gerar registros no banco de dados.

3. **Verificacao e Validacao Baseadas em Especificacao:**
   - Para cada requisito funcional, foram criados casos de teste automatizados correspondentes antes da integracao final, permitindo validacao cruzada automatizada de cada componente.

---

## 4. Arquitetura da Solucao

O sistema e composto por quatro containers desacoplados e orquestrados na mesma rede interna:

```
                      +-------------------------------------------+
                      |             Navegador Web                 |
                      |        http://localhost:3000              |
                      +---------------------+---------------------+
                                            |
                                            v
                      +-------------------------------------------+
                      |         4. Frontend (React + Nginx)       |
                      |  - Interface de Chat Responsiva           |
                      |  - Proxy Reverso /api/ -> backend:8000    |
                      |  - Indicadores Visuais de Ferramentas MCP |
                      +---------------------+---------------------+
                                            |
                                            v
                      +-------------------------------------------+
                      |           2. Backend (FastAPI)            |
                      |  - Orquestrador do Agente Inteligente     |
                      |  - Integracao OpenRouter (GPT-4o)         |
                      |  - Endpoints POST e GET /requisicoes      |
                      +--------------+-----------------+----------+
                                     |                 |
                                     v                 v
        +------------------------------------+    +-----------------------------------+
        |       3. Servidor MCP (Python)     |    |      1. Banco (PostgreSQL 16)     |
        |  - buscar_produtos (DummyJSON)     |    |  - Tabelas: requisicoes,          |
        |  - detalhar_produto (DummyJSON)    |    |             itens_requisicao      |
        |  - criar_requisicao (Diferencial)  |--->|  - Inicializacao via init.sql     |
        +------------------------------------+    +-----------------------------------+
```

### Componentes

1. **PostgreSQL 16 (`postgres`):**
   - Imagem oficial com inicializacao automatica via `/docker-entrypoint-initdb.d/init.sql`.
   - Tabelas normalizadas: `requisicoes` e `itens_requisicao`.

2. **Servidor MCP (`mcp-server`):**
   - Servico isolado em Python expondo ferramentas padronizadas.
   - Cliente HTTP resiliente para a DummyJSON com configuracao de `User-Agent` compativel com politicas de protecao da API, gestao de timeouts e retentativas.
   - Ferramenta diferencial `criar_requisicao` que permite ao LLM oficializar a compra no PostgreSQL somente apos aprovacao orcamentaria.

3. **Backend (`backend`):**
   - Desenvolvido em Python com FastAPI e Uvicorn.
   - Orquestra o loop conversacional de tool-calling com o modelo `openai/gpt-4o` via OpenRouter.
   - Endpoint `POST /requisicoes` para processamento do pedido e retorno das ferramentas acionadas.
   - Endpoint `GET /requisicoes` para listagem de historico de compras.

4. **Frontend (`frontend`):**
   - Single Page Application construida em React 18, Vite e Tailwind CSS.
   - Servida por Nginx alpine que atua simultaneamente como servidor estatico e proxy reverso para `/api/`, garantindo funcionamento Zero-CORS em qualquer ambiente.

---

## 5. Diferenciais de Engenharia Implementados

| Diferencial | Descricao Tecnica |
|---|---|
| **Gravacao Autonoma via MCP** | A persistencia de requisicoes no banco nao e forcada pelo backend. O LLM avalia os precos reais do catalogo e decide chamar a ferramenta `criar_requisicao` apenas quando o pedido atende aos limites estabelecidos. |
| **Transparencia Visual de Ferramentas** | A interface web exibe cartoes expansiveis detalhando cada chamada de ferramenta MCP efetuada pelo agente, com argumentos enviados e status da execucao. |
| **Bateria de Testes Automatizada (`test_agent.py`)** | Script estruturado cobrindo cinco cenarios fundamentais: compra simples dentro do orcamento, pedido com multiplos itens, estouro de orcamento (rejeicao fiscal), busca por item inexistente (anti-alucinacao) e pedido com especificacao tecnica. |

---

## 6. Seguranca e Boas Praticas

- Variaveis de ambiente sensiveis sao mantidas fora do versionamento atraves do `.gitignore`.
- Arquivo `.env.example` fornecido como modelo de configuracao.
- Imagens Docker multi-stage build para reducao de superficie de ataque e consumo de recursos.
- Healthchecks configurados em todos os servicos dependentes para garantir ordem estrita de inicializacao.
