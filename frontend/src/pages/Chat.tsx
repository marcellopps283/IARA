import { useState, useRef, useEffect } from 'react';
import {
    Plus,
    SlidersHorizontal,
    Mic,
    AudioLines,
    Send,
    Camera,
    Image as ImageIcon,
    FileUp,
    X,
    Loader2
} from "lucide-react";
import MarkdownRenderer from '@/components/MarkdownRenderer';

interface Message {
    role: 'user' | 'assistant';
    content: string;
}

export default function Chat() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isThinking, setIsThinking] = useState(false);
    const [showAttachMenu, setShowAttachMenu] = useState(false);

    const scrollRef = useRef<HTMLDivElement>(null);
    const menuRef = useRef<HTMLDivElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages, isThinking]);

    useEffect(() => {
        function handleClickOutside(e: MouseEvent) {
            if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
                setShowAttachMenu(false);
            }
        }
        if (showAttachMenu) {
            document.addEventListener("mousedown", handleClickOutside);
        }
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, [showAttachMenu]);

    const handleSend = async () => {
        if (!input.trim()) return;

        const userMessage = input.trim();
        setInput('');
        setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
        setIsThinking(true);
        setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: userMessage }),
            });

            if (!response.body) throw new Error('Sem corpo de resposta');

            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let assistantMessage = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                for (const line of chunk.split('\n')) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        assistantMessage += data;
                        setMessages((prev) => {
                            const newMessages = [...prev];
                            newMessages[newMessages.length - 1].content = assistantMessage;
                            return newMessages;
                        });
                    }
                }
            }
        } catch (error) {
            setMessages((prev) => {
                const newMessages = [...prev];
                newMessages[newMessages.length - 1].content = '⚠️ Ocorreu um erro ao conectar com o backend.';
                return newMessages;
            });
        } finally {
            setIsThinking(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            handleSend();
        }
    };

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        fileInputRef.current!.value = ''; // reset after selection
        const formData = new FormData();
        formData.append('file', file);
        try {
            const response = await fetch('/api/upload', { method: 'POST', body: formData });
            if (response.ok) {
                const data = await response.json();
                setInput((prev) => `${prev}\n[Arquivo anexado: ${data.filepath}]`);
            }
        } catch (error) {
            console.error('Erro no upload', error);
        }
    };

    return (
        <div className="flex h-full flex-col bg-[#0f172a]">
            {/* Área de mensagens com scroll */}
            <div
                ref={scrollRef}
                className="flex-1 overflow-y-auto px-4 py-8 md:px-8 space-y-8"
            >
                {messages.length === 0 && (
                    <div className="flex flex-col gap-8 py-12">
                        <div>
                            <p className="text-lg text-slate-400">Olá, Marcello</p>
                            <h1 className="text-3xl font-semibold text-white text-balance">
                                Por onde começamos?
                            </h1>
                        </div>
                    </div>
                )}

                {messages.map((msg, i) => (
                    <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div
                            className={`max-w-[90%] md:max-w-[70%] p-4 rounded-2xl ${msg.role === 'user'
                                ? 'bg-[#38bdf8] text-[#0f172a] rounded-br-sm'
                                : 'bg-[#1e293b] text-slate-200 border border-slate-800 rounded-bl-sm shadow-sm'
                                }`}
                        >
                            {msg.role === 'user' ? (
                                <div className="whitespace-pre-wrap">{msg.content}</div>
                            ) : (
                                <MarkdownRenderer content={msg.content} />
                            )}
                        </div>
                    </div>
                ))}
                {isThinking && (
                    <div className="flex justify-start">
                        <div className="bg-[#1e293b] border border-slate-800 p-4 rounded-2xl rounded-bl-sm flex items-center gap-3 text-slate-400 shadow-sm">
                            <Loader2 className="animate-spin text-[#38bdf8]" size={18} />
                            <span className="text-sm">Pensando profundamente...</span>
                        </div>
                    </div>
                )}
            </div>

            {/* Input fixo no rodapé baseado no v0 */}
            <div className="border-t border-slate-800 bg-[#0f172a] px-4 pb-2 pt-2 shrink-0">
                {/* Campo de input */}
                <div className="max-w-4xl mx-auto">
                    <div className="flex items-center gap-2 rounded-2xl bg-[#1e293b] border border-slate-800 px-4 py-2 shadow-sm focus-within:ring-1 focus-within:ring-[#38bdf8]/50 transition-shadow">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Peça ao Gemini ou IARA..."
                            className="flex-1 bg-transparent text-white placeholder:text-slate-500 focus:outline-none py-1"
                            style={{ fontSize: "16px" }}
                            disabled={isThinking}
                        />
                        {input.trim() ? (
                            <button
                                onClick={handleSend}
                                disabled={isThinking}
                                className="flex h-9 w-9 items-center justify-center rounded-full bg-[#38bdf8] text-[#0f172a] transition-colors hover:bg-[#0284c7] disabled:opacity-50"
                                aria-label="Enviar mensagem"
                            >
                                <Send className="h-4 w-4" />
                            </button>
                        ) : (
                            <button
                                className="flex h-9 w-9 items-center justify-center rounded-full text-slate-400 transition-colors hover:bg-slate-800 hover:text-white"
                                aria-label="Gravar áudio"
                            >
                                <Mic className="h-5 w-5" />
                            </button>
                        )}
                    </div>

                    {/* Barra de ações */}
                    <div className="mt-2 flex items-center justify-between">
                        <div className="relative flex items-center gap-2" ref={menuRef}>
                            <button
                                onClick={() => setShowAttachMenu((prev) => !prev)}
                                className="flex h-9 w-9 items-center justify-center rounded-full text-slate-400 transition-colors hover:bg-slate-800 hover:text-white"
                                aria-label="Adicionar anexo"
                            >
                                {showAttachMenu ? <X className="h-5 w-5" /> : <Plus className="h-5 w-5" />}
                            </button>

                            {/* Menu de anexos flutuante */}
                            {showAttachMenu && (
                                <div className="absolute bottom-12 left-0 z-50 flex flex-col gap-1 rounded-xl border border-slate-700 bg-[#1e293b] p-2 shadow-xl animate-in fade-in slide-in-from-bottom-2">
                                    <button
                                        onClick={() => {
                                            fileInputRef.current?.setAttribute('capture', 'environment');
                                            fileInputRef.current?.setAttribute('accept', 'image/*');
                                            fileInputRef.current?.click();
                                            setShowAttachMenu(false);
                                        }}
                                        className="flex items-center gap-3 rounded-lg px-4 py-2.5 text-sm text-slate-200 transition-colors hover:bg-slate-700"
                                    >
                                        <Camera className="h-4 w-4 text-slate-400" /> Câmera
                                    </button>
                                    <button
                                        onClick={() => {
                                            fileInputRef.current?.removeAttribute('capture');
                                            fileInputRef.current?.setAttribute('accept', 'image/*,video/*');
                                            fileInputRef.current?.click();
                                            setShowAttachMenu(false);
                                        }}
                                        className="flex items-center gap-3 rounded-lg px-4 py-2.5 text-sm text-slate-200 transition-colors hover:bg-slate-700"
                                    >
                                        <ImageIcon className="h-4 w-4 text-slate-400" /> Fotos
                                    </button>
                                    <button
                                        onClick={() => {
                                            fileInputRef.current?.removeAttribute('capture');
                                            fileInputRef.current?.setAttribute('accept', '*/*');
                                            fileInputRef.current?.click();
                                            setShowAttachMenu(false);
                                        }}
                                        className="flex items-center gap-3 rounded-lg px-4 py-2.5 text-sm text-slate-200 transition-colors hover:bg-slate-700"
                                    >
                                        <FileUp className="h-4 w-4 text-slate-400" /> Arquivo
                                    </button>
                                </div>
                            )}

                            {/* Input escondido mágico pra anexos reais */}
                            <input
                                ref={fileInputRef}
                                type="file"
                                className="hidden"
                                onChange={handleFileUpload}
                                aria-hidden="true"
                            />

                            <button
                                className="flex h-9 w-9 items-center justify-center rounded-full text-slate-400 transition-colors hover:bg-slate-800 hover:text-white disabled:opacity-50"
                                aria-label="Configurações"
                            >
                                <SlidersHorizontal className="h-5 w-5" />
                            </button>
                        </div>

                        <div className="flex items-center gap-2">
                            <button className="rounded-full border border-slate-700 px-4 py-1.5 text-sm font-medium text-slate-300 transition-colors hover:bg-slate-800 hover:text-white">
                                Raciocínio
                            </button>
                            <button
                                className="flex h-9 w-9 items-center justify-center rounded-full text-slate-400 transition-colors hover:bg-slate-800 hover:text-white"
                                aria-label="Áudio Modo"
                            >
                                <AudioLines className="h-5 w-5" />
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
