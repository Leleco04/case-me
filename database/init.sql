-- Script de inicialização do banco de dados do Agente de Compras
-- Executado automaticamente pelo entrypoint do PostgreSQL

CREATE TABLE IF NOT EXISTS requisicoes (
    id SERIAL PRIMARY KEY,
    solicitante VARCHAR(100) DEFAULT 'Usuário',
    pedido_original TEXT NOT NULL,
    resposta_agente TEXT,
    valor_total NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    status VARCHAR(50) NOT NULL DEFAULT 'CRIADA',
    ferramentas_utilizadas JSONB DEFAULT '[]'::jsonb,
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS itens_requisicao (
    id SERIAL PRIMARY KEY,
    requisicao_id INTEGER NOT NULL REFERENCES requisicoes(id) ON DELETE CASCADE,
    produto_id INTEGER,
    produto_nome VARCHAR(255) NOT NULL,
    quantidade INTEGER NOT NULL DEFAULT 1,
    preco_unitario NUMERIC(10, 2) NOT NULL,
    subtotal NUMERIC(10, 2) NOT NULL,
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_requisicoes_criado_em ON requisicoes(criado_em DESC);
CREATE INDEX IF NOT EXISTS idx_itens_requisicao_id ON itens_requisicao(requisicao_id);
