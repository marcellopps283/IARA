import { useState, useRef, useEffect } from 'react';
import { Search, Loader2, CheckCircle2, Copy, Download, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import MarkdownRenderer from '@/components/MarkdownRenderer';
import PageHeader from '@/components/PageHeader';

const REPORT_START_MARKER = '[REPORT_START]';

type StepStatus = 'pending' | 'running' | 'completed';

interface ResearchStep {
  id: number;
  message: string;
  status: StepStatus;
}

export default function DeepResearch() {
  const [topic, setTopic] = useState('');
  const [type, setType] = useState('Deixar Iara decidir');
  const [isResearching, setIsResearching] = useState(false);
  const [steps, setSteps] = useState<ResearchStep[]>([]);
  const [feed, setFeed] = useState('');
  const [report, setReport] = useState<string | null>(null);
  const feedEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    feedEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [feed, steps]);

  const handleResearch = async () => {
    if (!topic.trim()) return;

    setIsResearching(true);
    setReport(null);
    setFeed('');
    setSteps([{ id: 1, message: 'Iniciando pesquisa profunda...', status: 'running' }]);

    try {
      const response = await fetch('/api/research/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: topic.trim(),
          tipo: type !== 'Deixar Iara decidir' ? type : undefined,
        }),
      });

      if (!response.body) throw new Error('Sem corpo de resposta');

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');

      let reportMode = false;
      let reportBuffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          if (reportBuffer) setReport(reportBuffer);
          setSteps((prev) => prev.map((s) => ({ ...s, status: 'completed' })));
          break;
        }

        const chunk = decoder.decode(value, { stream: true });

        for (const line of chunk.split('\n')) {
          if (!line.startsWith('data: ')) continue;
          const data = line.slice(6);

          if (data.includes(REPORT_START_MARKER)) {
            reportMode = true;
            setSteps((prev) => prev.map((s) => ({ ...s, status: 'completed' as StepStatus })));
            continue;
          }

          if (reportMode) {
            reportBuffer += data;
            setReport(reportBuffer);
          } else {
            setFeed((prev) => prev + data + '\n');
            if (data.includes('🔎') || data.includes('✓') || data.includes('🔄')) {
              setSteps((prev) => [
                ...prev.map((s) => ({ ...s, status: 'completed' as StepStatus })),
                { id: Date.now(), message: data.replace(/\*\*/g, '').trim().slice(0, 80), status: 'running' },
              ]);
            }
          }
        }
      }
    } catch (error) {
      setFeed((prev) => prev + '\n[ERRO] Falha ao executar a pesquisa.');
      setSteps((prev) => prev.map((s) => ({ ...s, status: 'completed' })));
    } finally {
      setIsResearching(false);
    }
  };

  const handleCopy = () => {
    if (report) navigator.clipboard.writeText(report);
  };

  const handleDownload = () => {
    if (!report) return;
    const blob = new Blob([report], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `pesquisa_${new Date().toISOString().slice(0, 10)}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col h-full bg-[#0f172a] p-4 md:p-8 overflow-auto">
      <div className="max-w-5xl mx-auto w-full">
        <PageHeader
          title="Deep Research"
          description="Motor de busca iterativo multi-queries avançado"
          icon={Search}
        />

        <div className="space-y-6">
          <div className="bg-[#1e293b] p-6 rounded-xl border border-slate-700 shadow-sm space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Tema da Pesquisa Profunda
              </label>
              <Textarea
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="Ex: Compare as arquiteturas de microserviços vs monolitos em 2024..."
                className="min-h-[100px] resize-none bg-slate-800 border-slate-600 text-white placeholder:text-slate-500 focus-visible:ring-[#38bdf8]"
                disabled={isResearching}
              />
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="w-full sm:w-1/2">
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Tipo de Relatório
                </label>
                <select
                  value={type}
                  onChange={(e) => setType(e.target.value)}
                  disabled={isResearching}
                  className="w-full h-10 px-3 py-2 bg-slate-800 border border-slate-600 text-white rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-[#38bdf8]"
                >
                  <option>Deixar Iara decidir</option>
                  <option value="FACTUAL">Factual</option>
                  <option value="COMPARATIVA">Comparativa</option>
                  <option value="EXPLORATÓRIA">Exploratória</option>
                  <option value="OPERACIONAL">Operacional</option>
                </select>
              </div>

              <Button
                onClick={handleResearch}
                disabled={!topic.trim() || isResearching}
                className="w-full sm:w-auto mt-auto bg-[#38bdf8] hover:bg-[#0284c7] text-[#0f172a] font-semibold"
              >
                {isResearching ? (
                  <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Processando...</>
                ) : (
                  <><Search className="mr-2 h-4 w-4" /> Pesquisar</>
                )}
              </Button>
            </div>
          </div>

          {(isResearching || (steps.length > 0 && !report)) && (
            <div className="bg-[#1e293b] p-6 rounded-xl border border-slate-700 shadow-sm">
              <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2">
                <Clock className="text-[#38bdf8]" size={20} />
                Progresso da Pesquisa
              </h3>
              <div className="space-y-3 mb-6">
                {steps.map((step) => (
                  <div key={step.id} className="flex items-center gap-3 text-sm">
                    {step.status === 'pending' && <Clock size={16} className="text-slate-500" />}
                    {step.status === 'running' && <Loader2 size={16} className="text-[#38bdf8] animate-spin" />}
                    {step.status === 'completed' && <CheckCircle2 size={16} className="text-green-500" />}
                    <span className={step.status === 'pending' ? 'text-slate-500' : 'text-slate-200'}>
                      {step.message}
                    </span>
                  </div>
                ))}
              </div>
              <div className="bg-slate-900 border border-slate-800 rounded-md p-4 h-48 overflow-y-auto font-mono text-xs text-slate-400 whitespace-pre-wrap">
                {feed || 'Aguardando fluxo de dados...'}
                <div ref={feedEndRef} />
              </div>
            </div>
          )}

          {report && (
            <div className="bg-[#1e293b] p-6 rounded-xl border border-slate-700 shadow-sm">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 border-b border-slate-700 pb-4">
                <h3 className="text-xl font-bold text-white flex items-center gap-2">
                  <CheckCircle2 className="text-green-500" size={24} />
                  Relatório Concluído
                </h3>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={handleCopy} className="border-slate-600 text-slate-300 hover:text-white hover:bg-slate-700">
                    <Copy className="mr-2 h-4 w-4" /> Copiar tudo
                  </Button>
                  <Button variant="outline" size="sm" onClick={handleDownload} className="border-slate-600 text-slate-300 hover:text-white hover:bg-slate-700">
                    <Download className="mr-2 h-4 w-4" /> Baixar .md
                  </Button>
                </div>
              </div>
              <div className="bg-[#0f172a] p-6 rounded-lg border border-slate-800">
                <MarkdownRenderer content={report} />
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
