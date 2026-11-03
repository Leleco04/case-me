import React, { useState } from 'react';
import { FerramentaChamada } from '../types';
import { Search, Info, Database, CheckCircle2, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react';

interface Props {
  ferramentas: FerramentaChamada[];
}

export const ToolCallBadge: React.FC<Props> = ({ ferramentas }) => {
  const [expanded, setExpanded] = useState<boolean>(false);

  if (!ferramentas || ferramentas.length === 0) return null;

  const getToolIcon = (name: string) => {
    switch (name) {
      case 'buscar_produtos':
        return <Search className="w-3.5 h-3.5 text-blue-600" />;
      case 'detalhar_produto':
        return <Info className="w-3.5 h-3.5 text-amber-600" />;
      case 'criar_requisicao':
        return <Database className="w-3.5 h-3.5 text-emerald-600" />;
      default:
        return <Search className="w-3.5 h-3.5 text-slate-600" />;
    }
  };

  const getToolLabel = (name: string) => {
    switch (name) {
      case 'buscar_produtos':
        return 'Busca no Catálogo DummyJSON';
      case 'detalhar_produto':
        return 'Detalhamento do Produto';
      case 'criar_requisicao':
        return 'Gravação no Banco PostgreSQL';
      default:
        return name;
    }
  };

  return (
    <div className="my-2 border border-slate-200/90 bg-slate-50/80 rounded-xl overflow-hidden text-xs transition-all duration-200">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-slate-100/80 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="font-semibold text-slate-700 flex items-center gap-1.5">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
            </span>
            Ferramentas MCP Executadas ({ferramentas.length}):
          </span>
          <div className="flex flex-wrap gap-1">
            {ferramentas.map((f, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md font-mono bg-white border border-slate-200 text-slate-700 shadow-2xs"
              >
                {getToolIcon(f.ferramenta)}
                {f.ferramenta}
              </span>
            ))}
          </div>
        </div>
        <span className="text-slate-400 hover:text-slate-600">
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </span>
      </button>

      {expanded && (
        <div className="border-t border-slate-200 bg-white p-2.5 space-y-2">
          {ferramentas.map((item, idx) => (
            <div
              key={idx}
              className="flex items-start gap-2.5 p-2 rounded-lg bg-slate-50/70 border border-slate-100"
            >
              <div className="mt-0.5">
                {item.status === 'sucesso' ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-red-500" />
                )}
              </div>
              <div className="flex-1 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-mono font-medium text-slate-800 flex items-center gap-1.5">
                    {getToolIcon(item.ferramenta)}
                    {item.ferramenta}
                    <span className="text-[10px] font-sans font-normal text-slate-500">
                      ({getToolLabel(item.ferramenta)})
                    </span>
                  </span>
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                      item.status === 'sucesso'
                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        : 'bg-red-50 text-red-700 border border-red-200'
                    }`}
                  >
                    {item.status}
                  </span>
                </div>
                <div className="text-[11px] text-slate-600">
                  <span className="font-medium text-slate-500">Argumentos: </span>
                  <code className="bg-slate-100 px-1 py-0.2 rounded font-mono text-[10px] text-slate-800">
                    {JSON.stringify(item.argumentos)}
                  </code>
                </div>
                <div className="text-[11px] text-slate-600">
                  <span className="font-medium text-slate-500">Retorno: </span>
                  <span>{item.resultado_resumo}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
