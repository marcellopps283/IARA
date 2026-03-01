import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check } from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/components/ui/button';

interface CodeBlockProps {
  language: string;
  value: string;
}

const CodeBlock = ({ language, value }: CodeBlockProps) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group my-4 rounded-md overflow-hidden border border-slate-700">
      <div className="flex items-center justify-between px-4 py-1 bg-slate-800 text-xs text-slate-400">
        <span>{language || 'text'}</span>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 text-slate-400 hover:text-white"
          onClick={handleCopy}
        >
          {copied ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
        </Button>
      </div>
      <SyntaxHighlighter
        language={language}
        style={vscDarkPlus}
        customStyle={{ margin: 0, padding: '1rem', background: '#0f172a' }}
      >
        {value}
      </SyntaxHighlighter>
    </div>
  );
};

export default function MarkdownRenderer({ content }: { content: string }) {
  const hasAction = content.includes('[AÇÃO EXECUTADA]');
  const cleanContent = content.replace(/\[AÇÃO EXECUTADA\]/g, '');

  return (
    <div className="prose prose-invert max-w-none prose-p:leading-relaxed prose-pre:p-0">
      <ReactMarkdown
        components={{
          code({ className, children, ...props }: any) {
            const match = /language-(\w+)/.exec(className || '');
            return match ? (
              <CodeBlock language={match[1]} value={String(children).replace(/\n$/, '')} />
            ) : (
              <code className="bg-slate-800 px-1.5 py-0.5 rounded text-[#38bdf8]" {...props}>
                {children}
              </code>
            );
          },
        }}
      >
        {cleanContent}
      </ReactMarkdown>
      {hasAction && (
        <div className="mt-2 inline-flex items-center gap-1 px-2 py-1 bg-green-900/30 text-green-400 border border-green-800 rounded-md text-xs font-medium">
          ✅ Ação executada
        </div>
      )}
    </div>
  );
}
