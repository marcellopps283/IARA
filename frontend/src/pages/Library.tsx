import { useState, useEffect } from 'react';
import { FileText, Download, Calendar, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import MarkdownRenderer from '@/components/MarkdownRenderer';
import PageHeader from '@/components/PageHeader';
import { Library as LibraryIcon } from 'lucide-react';

export default function Library() {
    const [reports, setReports] = useState<string[]>([]);
    const [selectedReport, setSelectedReport] = useState<string | null>(null);
    const [reportContent, setReportContent] = useState<string>('');
    const [isLoadingList, setIsLoadingList] = useState(true);
    const [isLoadingContent, setIsLoadingContent] = useState(false);

    useEffect(() => { fetchReports(); }, []);

    const fetchReports = async () => {
        try {
            const response = await fetch('/api/research');
            const data = await response.json();
            setReports(data.reports || []);
            if (data.reports && data.reports.length > 0 && window.innerWidth >= 768) {
                handleSelectReport(data.reports[0]);
            }
        } catch (error) {
            console.error('Erro ao buscar relatórios:', error);
        } finally {
            setIsLoadingList(false);
        }
    };

    const handleSelectReport = async (filename: string) => {
        setSelectedReport(filename);
        setIsLoadingContent(true);
        setReportContent('');
        try {
            const response = await fetch(`/api/research/${filename}`);
            if (!response.ok) throw new Error('Falha ao carregar conteúdo');
            const text = await response.text();
            setReportContent(text);
        } catch (error) {
            setReportContent('> ⚠️ Erro ao carregar o conteúdo do relatório.');
        } finally {
            setIsLoadingContent(false);
        }
    };

    const handleDownload = (filename: string, content: string, e?: React.MouseEvent) => {
        if (e) e.stopPropagation();
        const blob = new Blob([content], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    const formatReportInfo = (filename: string) => {
        const match = filename.match(/^(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})_(.*)\.md$/);
        if (match) {
            const [, year, month, day, hour, min, , theme] = match;
            return {
                date: `${day}/${month}/${year} às ${hour}:${min}`,
                title: theme.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase()),
            };
        }
        return { date: 'Data desconhecida', title: filename.replace('.md', '') };
    };

    return (
        <div className="flex flex-col h-full bg-[#0f172a] p-4 md:p-6 lg:p-8 overflow-auto">
            <div className="max-w-7xl mx-auto w-full h-full flex flex-col">
                <PageHeader
                    title="Biblioteca"
                    description="Consulte, baixe e gerencie todos os relatórios processados pelo Deep Research"
                    icon={LibraryIcon}
                />
                <div className="flex flex-col md:flex-row flex-1 min-h-0 bg-[#0f172a] rounded-xl border border-slate-800 shadow-sm">
                    <div className="w-full md:w-80 flex-shrink-0 bg-[#1e293b] border-r border-slate-800 flex flex-col h-[40vh] md:h-full rounded-l-xl">
                        <div className="p-4 border-b border-slate-700 bg-slate-800/50">
                            <h2 className="text-lg font-bold text-white flex items-center gap-2">
                                <FileText className="text-[#38bdf8]" size={20} /> Relatórios Salvos
                            </h2>
                        </div>
                        <ScrollArea className="flex-1">
                            {isLoadingList ? (
                                <div className="flex justify-center items-center p-8 text-slate-500">
                                    <Loader2 className="animate-spin" size={24} />
                                </div>
                            ) : reports.length === 0 ? (
                                <div className="p-8 text-center text-slate-500 text-sm">Nenhum relatório encontrado.</div>
                            ) : (
                                <div className="p-2 space-y-1">
                                    {reports.map((filename) => {
                                        const info = formatReportInfo(filename);
                                        const isSelected = selectedReport === filename;
                                        return (
                                            <button
                                                key={filename}
                                                onClick={() => handleSelectReport(filename)}
                                                className={`w-full text-left px-3 py-3 rounded-lg transition-colors border ${isSelected ? 'bg-[#38bdf8]/10 border-[#38bdf8]/30 text-[#38bdf8]' : 'border-transparent text-slate-300 hover:bg-slate-800 hover:text-white'
                                                    }`}
                                            >
                                                <div className="font-medium text-sm truncate mb-1">{info.title}</div>
                                                <div className="flex items-center text-xs opacity-70 gap-1">
                                                    <Calendar size={12} /> {info.date}
                                                </div>
                                            </button>
                                        );
                                    })}
                                </div>
                            )}
                        </ScrollArea>
                    </div>

                    <div className="flex-1 flex flex-col min-w-0 bg-[#0f172a] h-[60vh] md:h-full border-t md:border-t-0 border-slate-700">
                        {!selectedReport ? (
                            <div className="flex h-full items-center justify-center text-slate-600 flex-col gap-4">
                                <FileText size={48} className="opacity-20" />
                                <p>Selecione um relatório para visualizar</p>
                            </div>
                        ) : (
                            <>
                                <div className="p-4 md:p-6 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[#0f172a] sticky top-0 z-10">
                                    <div>
                                        <h1 className="text-xl font-bold text-white break-words">{formatReportInfo(selectedReport).title}</h1>
                                        <p className="text-sm text-slate-500 mt-1 flex items-center gap-1">
                                            <Calendar size={14} /> Gerado em {formatReportInfo(selectedReport).date}
                                        </p>
                                    </div>
                                    <Button onClick={(e) => handleDownload(selectedReport, reportContent, e)} variant="outline" className="border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white shrink-0">
                                        <Download className="mr-2 h-4 w-4" /> Baixar
                                    </Button>
                                </div>
                                <div className="flex-1 overflow-y-auto p-4 md:p-8">
                                    {isLoadingContent ? (
                                        <div className="flex justify-center items-center h-full text-[#38bdf8]">
                                            <Loader2 className="animate-spin" size={32} />
                                        </div>
                                    ) : (
                                        <div className="max-w-4xl mx-auto">
                                            <MarkdownRenderer content={reportContent} />
                                        </div>
                                    )}
                                </div>
                            </>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
