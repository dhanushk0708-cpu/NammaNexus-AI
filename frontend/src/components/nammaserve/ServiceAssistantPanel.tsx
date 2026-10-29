'use client';

import React from "react";
import { Bot, Loader2, Send } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

type AssistantResponse = {
  reply: string;
  fallback_used?: boolean;
  error?: string | null;
};

export default function ServiceAssistantPanel() {
  const [message, setMessage] = React.useState("");
  const [reply, setReply] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [isLoading, setIsLoading] = React.useState(false);

  async function askAssistant() {
    if (!message.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/nammaserve/assistant`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: message.trim() }),
      });
      const data = await response.json() as AssistantResponse & { detail?: string };
      if (!response.ok) throw new Error(data.detail || "Assistant is temporarily unavailable.");
      setReply(data.reply);
    } catch (cause) {
      setReply(null);
      setError(cause instanceof Error ? cause.message : "Assistant is temporarily unavailable.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="rounded-2xl border border-emerald-100 bg-emerald-50/50 p-4 space-y-3">
      <div className="flex items-center gap-2">
        <Bot className="h-4 w-4 text-emerald-700" />
        <h2 className="text-sm font-extrabold text-slate-900">Ask NammaServe</h2>
      </div>
      <p className="text-[11px] text-slate-600">Describe a service and locality in English, Kannada transliteration, or Kannada when supported.</p>
      <div className="flex gap-2">
        <input value={message} onChange={(event) => setMessage(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void askAssistant(); }} placeholder="e.g. Nange AC service madisbeku Rajajinagar alli" className="min-w-0 flex-1 rounded-lg border border-emerald-200 bg-white px-3 py-2 text-xs focus:outline-hidden focus:ring-2 focus:ring-emerald-100" />
        <button type="button" onClick={() => void askAssistant()} disabled={isLoading || !message.trim()} className="inline-flex items-center gap-1 rounded-lg bg-emerald-700 px-3 py-2 text-xs font-bold text-white disabled:opacity-50">
          {isLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}Ask
        </button>
      </div>
      {error && <p className="rounded-lg bg-rose-50 p-2 text-[11px] text-rose-700">{error}</p>}
      {reply && <p className="whitespace-pre-wrap rounded-lg border border-emerald-100 bg-white p-3 text-xs text-slate-700">{reply}</p>}
    </section>
  );
}
