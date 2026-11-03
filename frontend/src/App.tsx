import React, { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { MessageItem } from './components/MessageItem';
import { HistoryModal } from './components/HistoryModal';
import { ChatMessage, Requisicao } from './types';
import { Send, Sparkles, Loader2 } from 'lucide-react';

const INITIAL_MESSAGE: ChatMessage = {
  id: 'msg-welcome',
  sender: 'agent',
  text: `Ola. Sou o Agente de Compras Corporativo autonomo.\n\nPosso consultar produtos no catalogo DummyJSON atraves do protocolo MCP, verificar precos e disponibilidade, respeitar limites de orcamento e registrar requisicoes no banco de dados.\n\nComo posso ajudar?`,
  timestamp: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
};

const QUICK_PROMPTS = [
  { label: 'Smartphone (ate $1000)', prompt: 'Compre 1 iPhone ou smartphone similar com orcamento de ate $1000 para a equipe de vendas.' },
  { label: '2 Perfumes e 1 Batom', prompt: 'Preciso de 2 perfumes e 1 batom para kits comemorativos da empresa sem restricao de orcamento.' },
  { label: '5 Laptops por $50 (Estouro)', prompt: 'Gostaria de comprar 5 laptops gamer com um orcamento total de apenas $50.' },
  { label: 'Produto Inexistente (Anti-alucinacao)', prompt: 'Compre 3 unidades de nave espacial interestelar com limite de $5000.' },
  { label: 'Detalhar Produto ID 1', prompt: 'Compre 2 unidades do produto id 1 (Essence Mascara) com orcamento de ate $50.' }
];

export const App: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([INITIAL_MESSAGE]);
  const [inputMessage, setInputMessage] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [requisicoes, setRequisicoes] = useState<Requisicao[]>([]);
  const [isHistoryOpen, setIsHistoryOpen] = useState<boolean>(false);
  const [loadingHistory, setLoadingHistory] = useState<boolean>(false);
  const [serverStatus, setServerStatus] = useState<'online' | 'offline' | 'checking'>('checking');

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  // Checagem de conectividade do backend
  const checkHealth = async () => {
    try {
      const res = await fetch('/api/health');
      if (res.ok) {
        setServerStatus('online');
      } else {
        setServerStatus('offline');
      }
    } catch {
      setServerStatus('offline');
    }
  };

  // Carrega histórico de requisições do PostgreSQL
  const carregarRequisicoes = async () => {
    setLoadingHistory(true);
    try {
      const res = await fetch('/api/requisicoes');
      if (res.ok) {
        const data = await res.json();
        setRequisicoes(data);
      }
    } catch (err) {
      console.error('Falha ao obter histórico de requisições:', err);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    checkHealth();
    carregarRequisicoes();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend || inputMessage).trim();
    if (!text || loading) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text,
      timestamp: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputMessage('');
    setLoading(true);

    try {
      const res = await fetch('/api/requisicoes', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ pedido: text, solicitante: 'Colaborador' })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Erro HTTP ${res.status}`);
      }

      const data = await res.json();

      const agentMsg: ChatMessage = {
        id: `agent-${Date.now()}`,
        sender: 'agent',
        text: data.resposta || 'Resposta processada pelo agente.',
        timestamp: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
        requisicao_id: data.requisicao_id,
        valor_total: data.valor_total,
        itens: data.itens,
        ferramentas_chamadas: data.ferramentas_chamadas,
        erro: data.erro
      };

      setMessages((prev) => [...prev, agentMsg]);

      // Se gerou requisição, atualiza o histórico
      if (data.requisicao_id) {
        carregarRequisicoes();
      }
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        sender: 'agent',
        text: 'Não foi possível completar o processamento do seu pedido devido a um erro de comunicação.',
        timestamp: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
        erro: err.message || 'Falha ao conectar à API ou catálogo DummyJSON.'
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex flex-col h-screen bg-slate-50">
      <Header
        onOpenHistory={() => setIsHistoryOpen(true)}
        onClearChat={() => setMessages([INITIAL_MESSAGE])}
        historyCount={requisicoes.length}
        serverStatus={serverStatus}
      />

      {/* Área Central de Conversa */}
      <main className="flex-1 overflow-y-auto px-4 py-4 max-w-4xl mx-auto w-full">
        {messages.map((msg) => (
          <MessageItem key={msg.id} message={msg} />
        ))}

        {loading && (
          <div className="flex gap-3 my-4 justify-start animate-pulse">
            <div className="w-9 h-9 rounded-xl bg-brand-600 flex items-center justify-center text-white shrink-0 mt-0.5 shadow-sm">
              <Loader2 className="w-5 h-5 animate-spin" />
            </div>
            <div className="bg-white border border-slate-200/80 rounded-2xl rounded-tl-xs p-4 text-xs text-slate-500 shadow-2xs space-y-2">
              <div className="flex items-center gap-2 font-medium text-slate-700">
                <Sparkles className="w-4 h-4 text-brand-600 animate-spin" />
                <span>O agente está pensando e consultando ferramentas MCP...</span>
              </div>
              <div className="flex gap-1.5 pt-1">
                <span className="w-2 h-2 rounded-full bg-brand-400 animate-bounce"></span>
                <span className="w-2 h-2 rounded-full bg-brand-400 animate-bounce delay-150"></span>
                <span className="w-2 h-2 rounded-full bg-brand-400 animate-bounce delay-300"></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </main>

      {/* Barra de Ações Rápidas & Input */}
      <footer className="bg-white border-t border-slate-200/80 p-3 sm:p-4 sticky bottom-0 z-20 shadow-lg">
        <div className="max-w-4xl mx-auto space-y-2.5">
          {/* Sugestões de teste rápido */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider shrink-0 mr-1 flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-brand-500" /> Testes Rápidos:
            </span>
            {QUICK_PROMPTS.map((qp, i) => (
              <button
                key={i}
                onClick={() => handleSendMessage(qp.prompt)}
                disabled={loading}
                className="whitespace-nowrap px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-brand-50 hover:text-brand-700 hover:border-brand-200 border border-slate-200 text-slate-700 transition-colors text-xs font-medium shrink-0 disabled:opacity-40"
              >
                {qp.label}
              </button>
            ))}
          </div>

          {/* Campo de Envio */}
          <div className="relative flex items-center">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              placeholder="Digite sua requisição de compra... (ex: 'Compre 2 perfumes e 1 batom')"
              className="w-full bg-slate-50 border border-slate-300 focus:border-brand-500 focus:bg-white focus:ring-2 focus:ring-brand-200 rounded-xl px-4 py-3 pr-12 text-sm text-slate-900 placeholder-slate-400 outline-none transition-all"
            />
            <button
              onClick={() => handleSendMessage()}
              disabled={!inputMessage.trim() || loading}
              className="absolute right-2 p-2 rounded-lg bg-brand-600 hover:bg-brand-700 text-white disabled:opacity-40 disabled:hover:bg-brand-600 transition-all shadow-xs"
              title="Enviar mensagem"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
          <div className="flex items-center justify-between text-[11px] text-slate-400 px-1">
            <span>Orquestrado via Docker Compose • Proxy Nginx embutido • Zero-CORS</span>
            <span>DummyJSON Catálogo + OpenRouter</span>
          </div>
        </div>
      </footer>

      {/* Modal de Histórico de Requisições */}
      <HistoryModal
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        requisicoes={requisicoes}
        loading={loadingHistory}
        onRefresh={carregarRequisicoes}
      />
    </div>
  );
};

export default App;
