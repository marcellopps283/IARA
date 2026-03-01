import { useState, useEffect } from 'react';
import { Brain, Trash2, Plus, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import PageHeader from '@/components/PageHeader';

interface MemoryFact {
    id: string;
    category: string;
    content: string;
    confidence: number;
}

export default function Memory() {
    const [facts, setFacts] = useState<MemoryFact[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [newCategory, setNewCategory] = useState('');
    const [newContent, setNewContent] = useState('');
    const [isAdding, setIsAdding] = useState(false);

    useEffect(() => { fetchMemory(); }, []);

    const fetchMemory = async () => {
        try {
            const response = await fetch('/api/memory');
            const data = await response.json();
            setFacts(data.core_facts || data.coreFacts || []);
        } catch (error) {
            console.error('Erro ao buscar memória:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleAddFact = async () => {
        if (!newCategory.trim() || !newContent.trim()) return;
        setIsAdding(true);
        try {
            const response = await fetch('/api/memory', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ category: newCategory, content: newContent }),
            });
            if (response.ok) {
                setNewCategory('');
                setNewContent('');
                await fetchMemory();
            }
        } catch (error) {
            console.error('Erro ao adicionar fato:', error);
        } finally {
            setIsAdding(false);
        }
    };

    const handleDelete = async (id: string) => {
        try {
            const response = await fetch(`/api/memory/${id}`, { method: 'DELETE' });
            if (response.ok) setFacts((prev) => prev.filter((fact) => fact.id !== id));
        } catch (error) {
            console.error('Erro ao deletar fato:', error);
        }
    };

    return (
        <div className="flex flex-col h-full bg-[#0f172a] p-4 md:p-6 lg:p-8 overflow-auto">
            <div className="max-w-4xl mx-auto w-full space-y-6">
                <PageHeader
                    title="Memória Núcleo"
                    description="Consolidação e adição de fatos permanentes na arquitetura base da IARA"
                    icon={Brain}
                />

                <Card className="bg-[#1e293b] border-slate-700 shadow-sm mt-4">
                    <CardContent className="p-6 space-y-4">
                        <h2 className="text-md font-bold text-white flex items-center gap-2 mb-4">
                            <Plus className="text-[#38bdf8]" size={16} /> Adicionar Novo Fato à Memória
                        </h2>
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                            <div className="md:col-span-1">
                                <label className="block text-sm font-medium text-slate-300 mb-1">Categoria</label>
                                <Input value={newCategory} onChange={(e) => setNewCategory(e.target.value)} placeholder="Ex: Usuário" className="bg-slate-800 border-slate-600 text-white placeholder:text-slate-500 focus-visible:ring-[#38bdf8]" disabled={isAdding} />
                            </div>
                            <div className="md:col-span-3 flex flex-col sm:flex-row gap-4">
                                <div className="flex-1">
                                    <label className="block text-sm font-medium text-slate-300 mb-1">Conteúdo do Fato</label>
                                    <Textarea value={newContent} onChange={(e) => setNewContent(e.target.value)} placeholder="Ex: O usuário mora no Brasil e prefere respostas curtas." className="h-10 min-h-[40px] resize-none bg-slate-800 border-slate-600 text-white placeholder:text-slate-500 focus-visible:ring-[#38bdf8]" disabled={isAdding} />
                                </div>
                                <Button onClick={handleAddFact} disabled={!newCategory.trim() || !newContent.trim() || isAdding} className="mt-auto shrink-0 bg-[#38bdf8] hover:bg-[#0284c7] text-[#0f172a] font-semibold">
                                    {isAdding ? <Loader2 className="h-4 w-4 animate-spin" /> : <><Plus className="mr-2 h-4 w-4" /> Adicionar</>}
                                </Button>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <div className="space-y-4">
                    <h3 className="text-md font-medium text-slate-300">Fatos Estabelecidos ({facts.length})</h3>
                    {isLoading ? (
                        <div className="flex justify-center p-8"><Loader2 className="h-8 w-8 animate-spin text-[#38bdf8]" /></div>
                    ) : facts.length === 0 ? (
                        <div className="text-center p-8 text-slate-500 bg-[#1e293b] rounded-xl border border-slate-700">A memória núcleo está vazia no momento.</div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {facts.map((fact) => (
                                <Card key={fact.id} className="bg-[#1e293b] border-slate-700 shadow-sm hover:border-slate-600 transition-colors">
                                    <CardContent className="p-4 flex gap-4 items-start justify-between">
                                        <div className="space-y-2 flex-1 min-w-0">
                                            <div className="flex items-center gap-2">
                                                <Badge variant="outline" className="border-[#38bdf8] text-[#38bdf8] bg-[#38bdf8]/10 text-xs">{fact.category}</Badge>
                                                <span className="text-xs text-slate-500">{(fact.confidence * 100).toFixed(0)}% Confiança</span>
                                            </div>
                                            <p className="text-slate-200 text-sm break-words">{fact.content}</p>
                                        </div>
                                        <Button variant="ghost" size="icon" onClick={() => handleDelete(fact.id)} className="text-slate-500 hover:text-red-400 hover:bg-red-950/30 shrink-0">
                                            <Trash2 size={16} />
                                        </Button>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
