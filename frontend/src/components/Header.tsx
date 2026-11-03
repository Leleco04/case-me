import React from 'react';
import { ShoppingCart, History, Trash2, CheckCircle2, AlertCircle } from 'lucide-react';

interface Props {
  onOpenHistory: () => void;
  onClearChat: () => void;
  historyCount: number;
  serverStatus: 'online' | 'offline' | 'checking';
}

export const Header: React.FC<Props> = ({
  onOpenHistory,
  onClearChat,
  historyCount,
  serverStatus
}) => {
  return (
    <header className="bg-white border-b border-slate-200/80 sticky top-0 z-30 shadow-2xs">
      <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-sky-500 flex items-center justify-center text-white shadow-sm">
            <ShoppingCart className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-slate-900 tracking-tight">
                Agente de Compras Corporativo
              </h1>
              <span className="hidden sm:inline-flex items-center gap-1 text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                Zero-Config
              </span>
            </div>
            <p className="text-xs text-slate-500 flex items-center gap-2">
              <span>MCP Protocol + OpenRouter LLM</span>
              <span className="inline-block w-1 h-1 rounded-full bg-slate-300"></span>
              <span className="flex items-center gap-1 font-medium">
                {serverStatus === 'online' ? (
                  <span className="text-emerald-600 flex items-center gap-0.5">
                    <CheckCircle2 className="w-3 h-3" /> Sistema Conectado
                  </span>
                ) : serverStatus === 'offline' ? (
                  <span className="text-red-500 flex items-center gap-0.5">
                    <AlertCircle className="w-3 h-3" /> Offline
                  </span>
                ) : (
                  <span className="text-slate-400">Verificando...</span>
                )}
              </span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onOpenHistory}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-2xs transition-colors"
            title="Ver requisições salvas no banco PostgreSQL"
          >
            <History className="w-3.5 h-3.5 text-slate-500" />
            <span>Histórico</span>
            {historyCount > 0 && (
              <span className="px-1.5 py-0.2 rounded-full bg-brand-50 text-brand-700 border border-brand-200 text-[10px] font-mono">
                {historyCount}
              </span>
            )}
          </button>

          <button
            onClick={onClearChat}
            className="p-1.5 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-500 hover:text-slate-800 text-xs transition-colors"
            title="Limpar histórico da conversa atual"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
