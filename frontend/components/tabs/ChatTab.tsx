"use client";
import { useState, useRef, useEffect } from "react";
import SyntaxHighlighter from "react-syntax-highlighter";
import { atomOneDark } from "react-syntax-highlighter/dist/esm/styles/hljs";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Array<{ file: string; lines: string; name: string }>;
}

interface Props {
  analysisId: string;
}

export function ChatTab({ analysisId }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const question = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setLoading(true);

    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    let assistantContent = "";
    let sources: Message["sources"] = [];

    try {
      const res = await fetch(`${apiBase}/api/chat/${analysisId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: question }),
      });

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();

      // Add placeholder
      setMessages((prev) => [...prev, { role: "assistant", content: "", sources: [] }]);

      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value);
        for (const line of text.split("\n")) {
          if (!line.startsWith("data: ")) continue;
          try {
            const event = JSON.parse(line.slice(6));
            if (event.type === "sources") {
              sources = event.sources;
              setMessages((prev) => {
                const copy = [...prev];
                copy[copy.length - 1] = { ...copy[copy.length - 1], sources };
                return copy;
              });
            } else if (event.type === "chunk") {
              assistantContent += event.content;
              setMessages((prev) => {
                const copy = [...prev];
                copy[copy.length - 1] = { ...copy[copy.length - 1], content: assistantContent };
                return copy;
              });
            }
          } catch {}
        }
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Hata: ${err.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-220px)] min-h-[500px] bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-slate-400 dark:text-slate-500 mt-20">
            <p className="text-lg mb-2">Repoyla konuş</p>
            <p className="text-sm">Örnek: "Auth nasıl çalışıyor?", "En riskli modül hangisi?"</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="border-t border-slate-100 dark:border-slate-700 p-3 flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Repo hakkında soru sor..."
          disabled={loading}
          className="flex-1 px-4 py-2.5 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-50 dark:disabled:bg-slate-800"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="px-4 py-2.5 bg-blue-500 hover:bg-blue-600 disabled:bg-slate-200 dark:disabled:bg-slate-700 text-white text-sm font-medium rounded-lg transition-colors"
        >
          {loading ? "..." : "Gönder"}
        </button>
      </form>
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-2xl ${isUser ? "bg-blue-500 text-white" : "bg-slate-50 text-slate-800 dark:bg-slate-700 dark:text-slate-100"} rounded-2xl px-4 py-3 text-sm`}>
        <p className="whitespace-pre-wrap leading-relaxed">
          {message.content || (isUser ? "" : <span className="animate-pulse text-slate-400 dark:text-slate-500">...</span>)}
        </p>

        {/* Sources accordion */}
        {!isUser && message.sources?.length ? (
          <div className="mt-3 border-t border-slate-200 dark:border-slate-600 pt-2">
            <button
              onClick={() => setSourcesOpen((o) => !o)}
              className="text-xs text-blue-600 dark:text-blue-300 hover:underline"
            >
              {sourcesOpen ? "Kaynakları Gizle" : `${message.sources.length} Kaynak Göster`}
            </button>
            {sourcesOpen && (
              <div className="mt-2 space-y-2">
                {message.sources.map((s, i) => (
                  <div key={i} className="bg-slate-900 rounded-lg text-xs overflow-hidden">
                    <div className="px-3 py-1.5 bg-slate-800 text-slate-300 font-mono">
                      {s.file}:{s.lines}
                    </div>
                    <div className="px-3 py-1.5 text-slate-400">{s.name}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}
