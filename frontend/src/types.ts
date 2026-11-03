export interface FerramentaChamada {
  ferramenta: string;
  argumentos: Record<string, any>;
  resultado_resumo: string;
  status: 'sucesso' | 'erro';
}

export interface ItemRequisicao {
  id?: number;
  produto_id?: number;
  produto_nome: string;
  quantidade: number;
  preco_unitario: number;
  subtotal: number;
}

export interface Requisicao {
  id: number;
  solicitante: string;
  pedido_original: string;
  resposta_agente?: string;
  valor_total: number;
  status: string;
  ferramentas_utilizadas: FerramentaChamada[];
  itens: ItemRequisicao[];
  criado_em: string;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'agent';
  text: string;
  timestamp: string;
  requisicao_id?: number | null;
  valor_total?: number | null;
  itens?: ItemRequisicao[];
  ferramentas_chamadas?: FerramentaChamada[];
  erro?: string | null;
}
