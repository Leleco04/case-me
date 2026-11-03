import React from 'react';
import { Requisicao } from '../types';
import { X, RefreshCw, FileText, Calendar, Package } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  requisicoes: Requisicao[];
  loading: boolean;
  onRefresh: () => void;
}

export const HistoryModal: React.FC<Props> = ({
  isOpen,
  onClose,
  requisicoes,
  loading,
  onRefresh
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs">
      <div className="bg-white w-full max-w-2xl rounded-2xl shadow-xl border border-slate-200 overflow-hidden flex flex-col max-h-[85vh] animate-in fade-in zoom-in-95 duration-150">
        {/* Header do Modal */}
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-brand-50 text-brand-600 border border-brand-100">
              <FileText className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-slate-800 text-sm">Histórico de Requisições</h3>
              <p className="text-xs text-slate-500">Registros persistidos no banco de dados PostgreSQL</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onRefresh}
              disabled={loading}
              className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-100 text-slate-600 text-xs transition-colors disabled:opacity-50"
              title="Recarregar do banco"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-100 text-slate-600 text-xs transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Lista de Requisições */}
        <div className="p-5 overflow-y-auto space-y-3.5 flex-1">
          {requisicoes.length === 0 ? (
            <div className="text-center py-12 text-slate-400 space-y-2">
              <Package className="w-10 h-10 mx-auto stroke-1" />
              <p className="text-sm font-medium">Nenhuma requisição criada ainda.</p>
              <p className="text-xs text-slate-500 max-w-xs mx-auto">
                Faça uma solicitação de compra no chat para que o agente decida gravar a compra no banco.
              </p>
            </div>
          ) : (
            requisicoes.map((req) => (
              <div
                key={req.id}
                className="p-4 rounded-xl border border-slate-200 bg-white hover:border-brand-200 transition-colors shadow-2xs space-y-3"
              >
                <div className="flex items-start justify-between">
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-900 font-mono text-sm">
                        Requisição #{req.id}
                      </span>
                      <span className="px-2 py-0.5 rounded-md text-[10px] font-semibold uppercase bg-emerald-50 text-emerald-700 border border-emerald-200">
                        {req.status}
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 italic">
                      "{req.pedido_original}"
                    </p>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] text-slate-400 font-medium block">Total</span>
                    <span className="text-sm font-extrabold text-slate-900 font-mono">
                      ${Number(req.valor_total).toFixed(2)}
                    </span>
                  </div>
                </div>

                {/* Itens */}
                {req.itens && req.itens.length > 0 && (
                  <div className="bg-slate-50 rounded-lg p-2.5 border border-slate-100 text-xs space-y-1">
                    <span className="font-semibold text-slate-600 block text-[11px] mb-1">
                      Itens Aprovados ({req.itens.length}):
                    </span>
                    {req.itens.map((it, idx) => (
                      <div key={idx} className="flex justify-between text-slate-700 font-mono text-[11px]">
                        <span>• {it.produto_nome} (x{it.quantidade})</span>
                        <span className="font-semibold">${Number(it.subtotal).toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                )}

                <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1 border-t border-slate-100">
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {new Date(req.criado_em).toLocaleString('pt-BR')}
                  </span>
                  <span>Solicitante: {req.solicitante}</span>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Rodapé do Modal */}
        <div className="px-5 py-3 border-t border-slate-100 bg-slate-50/50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-xl bg-slate-900 text-white text-xs font-semibold hover:bg-slate-800 transition-colors"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
};
