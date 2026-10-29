'use client';

import React from "react";
import { Bot, Loader2, Star } from "lucide-react";
import type { ProviderItem } from "./NearbyProvidersList";

interface AIReviewSummaryCardProps { provider: ProviderItem | null; serviceName: string; }

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

type SummaryResponse = {
  summary?: string | null;
  source: string;
  source_url?: string | null;
  limitations: string[];
  generated_by: string;
};

export default function AIReviewSummaryCard({ provider }: AIReviewSummaryCardProps) {
  const [reviewUrl, setReviewUrl] = React.useState("");
  const [reviewText, setReviewText] = React.useState("");
  const [summary, setSummary] = React.useState<SummaryResponse | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [isLoading, setIsLoading] = React.useState(false);

  async function generateSummary() {
    setIsLoading(true);
    setError(null);
    setSummary(null);
    try {
      const response = await fetch(`${API_BASE}/nammaserve/reviews/summary`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          review_url: reviewUrl.trim() || undefined,
          review_text: reviewText.trim() || undefined,
        }),
      });
      const data = await response.json() as SummaryResponse & { detail?: string };
      if (!response.ok) throw new Error(data.detail || "Review summary could not be generated.");
      setSummary(data);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Review summary could not be generated.");
    } finally {
      setIsLoading(false);
    }
  }

  return <div className="w-full bg-white border border-slate-200/90 rounded-2xl p-4 sm:p-5 shadow-2xs space-y-3">
    <div className="flex items-center gap-2 pb-2 border-b border-slate-100"><Bot className="w-4 h-4 text-emerald-600" /><h3 className="text-sm font-extrabold text-slate-900">AI Review Summary</h3></div>
    {provider && <><h4 className="text-xs font-extrabold text-slate-900">{provider.name}</h4>{provider.rating !== null && provider.reviewsCount !== null ? <p className="flex items-center gap-1 text-xs text-slate-700"><Star className="w-3.5 h-3.5 fill-amber-500 text-amber-500" />{provider.rating.toFixed(1)} from {provider.reviewsCount} source-reported reviews</p> : <p className="text-xs text-slate-500">No source-reported rating or reviews are available.</p>}</>}
    <p className="text-[11px] text-slate-500">Paste review text for a grounded summary. A Google sharing link is validated but not scraped.</p>
    <input value={reviewUrl} onChange={(event) => setReviewUrl(event.target.value)} placeholder="Google review-sharing link (optional)" className="w-full rounded-lg border border-slate-200 px-3 py-2 text-xs focus:outline-hidden focus:ring-2 focus:ring-emerald-100" />
    <textarea value={reviewText} onChange={(event) => setReviewText(event.target.value)} maxLength={12000} placeholder="Paste review text here (up to 12,000 characters)" rows={4} className="w-full rounded-lg border border-slate-200 px-3 py-2 text-xs focus:outline-hidden focus:ring-2 focus:ring-emerald-100" />
    <button type="button" onClick={generateSummary} disabled={isLoading || (!reviewUrl.trim() && !reviewText.trim())} className="inline-flex items-center gap-2 rounded-lg bg-emerald-700 px-3 py-2 text-xs font-bold text-white disabled:opacity-50">
      {isLoading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}Generate Summary
    </button>
    {error && <p className="rounded-lg bg-rose-50 p-2 text-[11px] text-rose-700">{error}</p>}
    {summary && <div className="space-y-2 rounded-xl border border-emerald-100 bg-emerald-50/50 p-3 text-[11px] text-slate-700"><p className="whitespace-pre-wrap">{summary.summary || "No review content was available to summarize."}</p><p className="font-semibold">Source: {summary.source}</p>{summary.source_url && <a href={summary.source_url} target="_blank" rel="noopener noreferrer" className="block break-all text-emerald-800 underline">Validated source link</a>}{summary.limitations.map((limitation) => <p key={limitation} className="text-slate-500">Limitation: {limitation}</p>)}</div>}
  </div>;
}
