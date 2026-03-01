import { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Shield, Layers, BrainCircuit } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import PageHeader from '@/components/PageHeader';

interface Provider {
  name: string;
  model: string;
  baseUrl: string;
  apiKey: string;
  supportsStreaming: boolean;
  supportsTools: boolean;
}

export default function Settings() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [cot, setCot] = useState(false);
  const [reflect, setReflect] = useState(false);

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const response = await fetch('/api/config');
      const data = await response.json();
      setProviders(data.llmProviders || data.llm_providers || []);
      if (typeof data.cotEnabled === 'boolean') setCot(data.cotEnabled);
      if (typeof data.reflectEnabled === 'boolean') setReflect(data.reflectEnabled);
    } catch (error) {
      console.error('Erro ao buscar configurações:', error);
    }
  };

  const handleToggle = async (type: 'cot' | 'reflect', newValue: boolean) => {
    if (type === 'cot') setCot(newValue);
    if (type === 'reflect') setReflect(newValue);
    try {
      await fetch('/api/config/toggles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cot: type === 'cot' ? newValue : cot,
          reflect: type === 'reflect' ? newValue : reflect,
        }),
      });
    } catch (error) {
      if (type === 'cot') setCot(!newValue);
      if (type === 'reflect') setReflect(!newValue);
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#0f172a] p-4 md:p-6 lg:p-8 overflow-auto">
      <div className="max-w-4xl mx-auto w-full space-y-8">

        <PageHeader
          title="Configurações"
          description="Gerencie provedores LLM conectados e os comportamentos lógicos profundos da IARA."
          icon={SettingsIcon}
        />

        <section className="space-y-4">
          <h3 className="text-lg font-medium text-slate-200 flex items-center gap-2">
            <BrainCircuit size={18} className="text-[#38bdf8]" />
            Comportamento de Raciocínio
          </h3>
          <Card className="bg-[#1e293b] border-slate-700 shadow-sm">
            <CardContent className="p-0 divide-y divide-slate-700/50">
              <div className="flex items-center justify-between p-6">
                <div>
                  <h4 className="text-white font-medium">Chain of Thought (CoT) Explícito</h4>
                  <p className="text-sm text-slate-400 mt-1">Exibe o pensamento lógico da IA antes da resposta final.</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" checked={cot} onChange={(e) => handleToggle('cot', e.target.checked)} />
                  <div className="w-11 h-6 bg-slate-600 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#38bdf8]"></div>
                </label>
              </div>
              <div className="flex items-center justify-between p-6">
                <div>
                  <h4 className="text-white font-medium">Auto-reflexão (Reflection)</h4>
                  <p className="text-sm text-slate-400 mt-1">Permite que a IARA critique e melhore a própria resposta antes de enviar.</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" checked={reflect} onChange={(e) => handleToggle('reflect', e.target.checked)} />
                  <div className="w-11 h-6 bg-slate-600 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#38bdf8]"></div>
                </label>
              </div>
            </CardContent>
          </Card>
        </section>

        <section className="space-y-4">
          <h3 className="text-lg font-medium text-slate-200 flex items-center gap-2">
            <Layers size={18} className="text-[#38bdf8]" />
            Cascata de LLMs (Providers)
          </h3>
          <div className="space-y-3">
            {providers.length === 0 ? (
              <div className="text-slate-500 italic p-4 bg-slate-800/50 rounded-lg border border-slate-700">
                Carregando provedores...
              </div>
            ) : (
              providers.map((p, index) => (
                <Card key={index} className="bg-[#1e293b] border-slate-700 shadow-sm relative overflow-hidden">
                  <div className="absolute top-0 left-0 w-1 h-full bg-[#38bdf8] opacity-50"></div>
                  <CardContent className="p-5 flex flex-col sm:flex-row gap-4 justify-between sm:items-center">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-slate-500">#{index + 1}</span>
                        <h4 className="text-white font-bold">{p.name || 'Provedor Desconhecido'}</h4>
                        <Badge variant="outline" className="border-slate-600 text-slate-300 text-[10px] ml-2">
                          {p.model}
                        </Badge>
                      </div>
                      <p className="text-xs text-slate-400 font-mono mt-1 break-all">
                        {p.baseUrl || 'URL Nativa'}
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <div className="flex items-center gap-2 bg-slate-800 px-3 py-1.5 rounded-md border border-slate-700">
                        <Shield size={14} className="text-green-400" />
                        <span className="text-xs font-mono text-slate-300">{p.apiKey}</span>
                      </div>
                      <div className="flex gap-2">
                        {p.supportsStreaming && <span className="text-[10px] bg-blue-900/30 text-blue-400 px-2 py-0.5 rounded border border-blue-800/50">Streaming</span>}
                        {p.supportsTools && <span className="text-[10px] bg-purple-900/30 text-purple-400 px-2 py-0.5 rounded border border-purple-800/50">Tools</span>}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
          <p className="text-xs text-slate-500 mt-2 text-right">
            Os provedores são configurados via backend no arquivo <code className="text-slate-400">config.py</code>.
          </p>
        </section>

      </div>
    </div>
  );
}
