import { useState, useEffect, useRef } from 'react';
import { Terminal, Trash2, Pause, Play } from 'lucide-react';
import { Button } from '@/components/ui/button';
import PageHeader from '@/components/PageHeader';

export default function Logs() {
    const [logs, setLogs] = useState<string[]>([]);
    const [autoScroll, setAutoScroll] = useState(true);
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        fetchLogs();
        const interval = setInterval(fetchLogs, 3000);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        if (autoScroll && scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs, autoScroll]);

    const fetchLogs = async () => {
        try {
            const response = await fetch('/api/logs');
            const data = await response.json();
            if (data.logs) setLogs(data.logs);
        } catch (error) { }
    };

    const getColorClass = (line: string) => {
        if (line.includes('ERROR')) return 'text-red-400';
        if (line.includes('WARNING')) return 'text-yellow-400';
        if (line.includes('INFO')) return 'text-[#38bdf8]';
        return 'text-slate-300';
    };

    return (
        <div className="flex flex-col h-full bg-[#0f172a] p-4 md:p-6 lg:p-8 overflow-auto">
            <div className="max-w-6xl mx-auto w-full h-full flex flex-col">
                <PageHeader
                    title="Sistema de Logs"
                    description="Terminal de monitoramento central da comunicação de back-end"
                    icon={Terminal}
                />

                <div className="flex items-center justify-between mb-0 mt-2 bg-[#1e293b] p-4 rounded-t-xl border border-slate-700 border-b-0 shadow-sm relative z-10 w-full">
                    <h2 className="text-md font-bold text-white hidden sm:flex items-center gap-2">
                        <Terminal className="text-[#38bdf8]" size={16} /> Console Outputs
                    </h2>
                    <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={() => setAutoScroll(!autoScroll)} className={`border-slate-600 ${autoScroll ? 'bg-[#38bdf8]/20 text-[#38bdf8] border-[#38bdf8]/50' : 'text-slate-300 hover:text-white'}`}>
                            {autoScroll ? <><Pause className="mr-2 h-4 w-4" /> Pausar Scroll</> : <><Play className="mr-2 h-4 w-4" /> Retomar Scroll</>}
                        </Button>
                        <Button variant="outline" size="sm" onClick={() => setLogs([])} className="border-slate-600 text-slate-300 hover:text-red-400 hover:bg-red-950/30">
                            <Trash2 className="mr-2 h-4 w-4" /> Limpar Visualização
                        </Button>
                    </div>
                </div>
                <div ref={scrollRef} className="flex-1 bg-black border border-slate-700 rounded-b-xl p-4 overflow-y-auto font-mono text-sm">
                    {logs.length === 0 ? (
                        <div className="text-slate-500 italic">Aguardando logs do sistema...</div>
                    ) : (
                        logs.map((line, index) => (
                            <div key={index} className={`whitespace-pre-wrap break-all ${getColorClass(line)} leading-relaxed`}>{line}</div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}
