import { useState, useEffect } from 'react';
import { Activity, Cpu, Server, Database, Clock, Zap, Loader2 } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import PageHeader from '@/components/PageHeader';

interface StatusData {
    status: string;
    uptime: string;
    working_messages: number;
    episodes: number;
    active_llm: string;
    system_info: any;
}

interface WorkerInfo {
    name: string;
    host: string;
    skills: string[];
    status: string;
}

export default function Status() {
    const [statusData, setStatusData] = useState<StatusData | null>(null);
    const [workers, setWorkers] = useState<WorkerInfo[]>([]);

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 5000);
        return () => clearInterval(interval);
    }, []);

    const fetchData = async () => {
        try {
            const [statusRes, workersRes] = await Promise.all([fetch('/api/status'), fetch('/api/workers')]);
            if (statusRes.ok) {
                const data = await statusRes.json();
                setStatusData({ ...data, working_messages: data.working_messages || data.workingMessages || 0, active_llm: data.active_llm || data.activeLlm || 'Desconhecido' });
            }
            if (workersRes.ok) {
                const wData = await workersRes.json();
                setWorkers(wData.workers || []);
            }
        } catch (error) { }
    };

    if (!statusData) {
        return (
            <div className="flex h-full items-center justify-center bg-[#0f172a] text-[#38bdf8]">
                <Loader2 className="animate-spin" size={32} />
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full bg-[#0f172a] p-4 md:p-6 lg:p-8 overflow-auto">
            <div className="max-w-6xl mx-auto w-full space-y-6">
                <PageHeader
                    title="Painel de Controle"
                    description="Monitoramento em tempo real de hardware, dados estruturais e Swarm workers"
                    icon={Activity}
                />

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    <Card className="bg-[#1e293b] border-slate-700"><CardContent className="p-6 flex items-center gap-4"><div className="p-3 bg-blue-900/30 text-blue-400 rounded-lg"><Database size={24} /></div><div><p className="text-sm text-slate-400">Mensagens na RAM</p><p className="text-2xl font-bold text-white">{statusData.working_messages}</p></div></CardContent></Card>
                    <Card className="bg-[#1e293b] border-slate-700"><CardContent className="p-6 flex items-center gap-4"><div className="p-3 bg-purple-900/30 text-purple-400 rounded-lg"><Server size={24} /></div><div><p className="text-sm text-slate-400">Episódios Salvos</p><p className="text-2xl font-bold text-white">{statusData.episodes}</p></div></CardContent></Card>
                    <Card className="bg-[#1e293b] border-slate-700"><CardContent className="p-6 flex items-center gap-4"><div className="p-3 bg-orange-900/30 text-orange-400 rounded-lg"><Zap size={24} /></div><div><p className="text-sm text-slate-400">LLM Ativo</p><p className="text-lg font-bold text-white truncate max-w-[120px]">{statusData.active_llm}</p></div></CardContent></Card>
                    <Card className="bg-[#1e293b] border-slate-700"><CardContent className="p-6 flex items-center gap-4"><div className="p-3 bg-green-900/30 text-green-400 rounded-lg"><Clock size={24} /></div><div><p className="text-sm text-slate-400">Uptime</p><p className="text-lg font-bold text-white">{statusData.uptime}</p></div></CardContent></Card>
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <Card className="bg-[#1e293b] border-slate-700"><CardContent className="p-6"><h3 className="text-md font-bold text-slate-200 mb-4 flex items-center gap-2"><Cpu size={18} className="text-[#38bdf8]" /> System Info</h3><div className="bg-black border border-slate-800 rounded-lg p-4 overflow-auto max-h-[300px]"><pre className="text-xs text-green-400 font-mono whitespace-pre-wrap">{typeof statusData.system_info === 'object' ? JSON.stringify(statusData.system_info, null, 2) : (statusData.system_info || 'Informação de hardware indisponível')}</pre></div></CardContent></Card>
                    <Card className="bg-[#1e293b] border-slate-700"><CardContent className="p-6"><h3 className="text-md font-bold text-slate-200 mb-4 flex items-center gap-2"><Activity size={18} className="text-[#38bdf8]" /> Workers / Agentes</h3>{workers.length === 0 ? (<div className="flex items-center justify-center text-slate-500 border border-slate-800 border-dashed rounded-lg p-4">Nenhum worker conectado.</div>) : (<div className="grid grid-cols-1 gap-3 overflow-y-auto max-h-[300px] pr-2">{workers.map((worker, i) => (<div key={i} className="bg-slate-800 border border-slate-700 rounded-lg p-4 flex flex-col gap-2"><div className="flex justify-between items-start"><div className="font-medium text-white">{worker.name}</div><div className={`text-xs px-2 py-1 rounded-full border ${worker.status === 'online' || worker.status === 'idle' ? 'bg-green-900/20 text-green-400 border-green-800/50' : 'bg-yellow-900/20 text-yellow-400 border-yellow-800/50'}`}>{worker.status.toUpperCase()}</div></div><div className="text-xs text-slate-400 flex items-center gap-1"><Server size={12} /> {worker.host || 'Host desconhecido'}</div><div className="mt-1 flex flex-wrap gap-1">{worker.skills.map((skill, j) => (<span key={j} className="text-[10px] bg-slate-700 text-slate-300 px-2 py-0.5 rounded-md">{skill}</span>))}</div></div>))}</div>)}</CardContent></Card>
                </div>
            </div>
        </div>
    );
}
