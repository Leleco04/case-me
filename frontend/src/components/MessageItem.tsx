import React from 'react';
import { ChatMessage } from '../types';
import { ToolCallBadge } from './ToolCallBadge';
import { Bot, User, CheckCircle, AlertTriangle } from 'lucide-react';

interface Props {
  message: ChatMessage;
}

export const MessageItem: React.FC<Props> = ({ message }) => {
  const isAgent = message.sender === 'agent';

  return (
    <div className={`flex gap-3 my-4 ${isAgent ? 'justify-start' : 'justify-end'}`}>
      {isAgent && (
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-600 to-sky-400 flex items-center justify-center text-white shadow-sm shrink-0 mt-0.5">
          <Bot className="w-5 h-5" />
        </div>
      )}

      <div className={`max-w-[85%] md:max-w-[75%] space-y-2`}>
        {/* Balão de mensagem principal */}
        <div
          className={`p-4 rounded-2xl shadow-2xs leading-relaxed text-sm ${
            isAgent
              ? 'bg-white border border-slate-200/80 text-slate-800 rounded-tl-xs'
              : 'bg-brand-600 text-white rounded-tr-xs'
          }`}
        >
          {/* Header interno do remetente */}
          <div className="flex items-center justify-between gap-4 mb-1.5 pb-1 border-b border-slate-100/10 text-[11px] opacity-80">
            <span className="font-semibold">{isAgent ? 'Agente de Compras' : 'Você'}</span>
            <span>{message.timestamp}</span>
          </div>

          {/* Ferramentas MCP chamadas (Diferencial 2) */}
          {isAgent && message.ferramentas_chamadas && message.ferramentas_chamadas.length > 0 && (
            <ToolCallBadge ferramentas={message.ferramentas_chamadas} />
          )}

          {/* Mensagem de Erro ou Alerta (Resiliência DummyJSON / LLM) */}
          {message.erro && (
            <div className="my-2 p-3 rounded-xl bg-red-50 border border-red-200 text-red-800 flex items-start gap-2.5 text-xs">
              <AlertTriangle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Aviso de Falha no Catálogo / Sistema</p>
                <p className="mt-0.5">{message.erro}</p>
              </div>
            </div>
          )}

          {/* Conteúdo textual da resposta */}
          <div className="whitespace-pre-wrap font-normal">
            {message.text}
          </div>

          {/* Card Destacado de Requisição Criada no Banco */}
          {message.requisicao_id && (
            <div className="mt-3.5 p-3.5 rounded-xl bg-gradient-to-br from-emerald-50 to-teal-50/50 border border-emerald-200 text-slate-800 space-y-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="p-1 rounded-lg bg-emerald-500 text-white shadow-2xs">
                    <CheckCircle className="w-4 h-4" />
                  </span>
                  <div>
                    <h4 className="font-bold text-emerald-950 text-sm">
                      Requisição #{message.requisicao_id} Oficializada
                    </h4>
                    <span className="text-[11px] text-emerald-700">
                      Gravada com sucesso no PostgreSQL
                    </span>
                  </div>
                </div>
                {message.valor_total !== undefined && message.valor_total !== null && (
                  <div className="text-right">
                    <span className="text-[10px] uppercase font-semibold text-emerald-700 block">Total</span>
                    <span className="text-base font-extrabold text-emerald-950 font-mono">
                      ${Number(message.valor_total).toFixed(2)}
                    </span>
                  </div>
                )}
              </div>

              {/* Tabela de itens da requisição se houver */}
              {message.itens && message.itens.length > 0 && (
                <div className="mt-2 border border-emerald-200/80 rounded-lg overflow-hidden bg-white/90">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-emerald-100/60 text-emerald-900 font-semibold border-b border-emerald-200/80">
                      <tr>
                        <th className="py-1.5 px-2.5">Produto</th>
                        <th className="py-1.5 px-2 text-center">Qtd</th>
                        <th className="py-1.5 px-2 text-right">Unitário</th>
                        <th className="py-1.5 px-2.5 text-right">Subtotal</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-emerald-100/60 font-mono text-[11px]">
                      {message.itens.map((item, i) => (
                        <tr key={i} className="hover:bg-emerald-50/40">
                          <td className="py-1.5 px-2.5 font-sans font-medium text-slate-800">
                            {item.produto_nome}
                          </td>
                          <td className="py-1.5 px-2 text-center text-slate-600">{item.quantidade}</td>
                          <td className="py-1.5 px-2 text-right text-slate-600">
                            ${Number(item.preco_unitario).toFixed(2)}
                          </td>
                          <td className="py-1.5 px-2.5 text-right font-semibold text-slate-900">
                            ${Number(item.subtotal).toFixed(2)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {!isAgent && (
        <div className="w-9 h-9 rounded-xl bg-slate-700 flex items-center justify-center text-white shadow-sm shrink-0 mt-0.5">
          <User className="w-5 h-5" />
        </div>
      )}
    </div>
  );
};
