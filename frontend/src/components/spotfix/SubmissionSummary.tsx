'use client';

import React, { useState } from "react";
import {
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Send,
  Sparkles,
  MapPin,
  Tag,
  FileText,
  Building2,
  AlertTriangle,
  Share2,
  Mail,
  ShieldCheck,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface ComplaintResult {
  id: string;
  status: "DRAFT" | "APPROVED" | "SUBMITTED" | string;
  category: string | null;
  description: string | null;
  latitude: number | null;
  longitude: number | null;
  image_storage_key: string | null;
  confidence: number | null;
  severity: string | null;
  visual_explanation: string | null;
  impact_score: number | null;
  priority: string | null;
  impact_reason: string | null;
  authority: string | null;
  department: string | null;
  routing_reason: string | null;
  subject: string | null;
  complaint_text: string | null;
  submitted_at: string | null;
  recipient_email: string | null;
  instagram_post_id: string | null;
}

interface SubmissionSummaryProps {
  imageStorageKey: string;
  imagePreviewUrl: string;
  latitude: number;
  longitude: number;
  onReset: () => void;
}

const CATEGORIES = [
  "POTHOLE",
  "GARBAGE",
  "WATER_LEAKAGE",
  "WATERLOGGING",
  "STREET_LIGHT",
  "FALLEN_TREE",
];

export default function SubmissionSummary({
  imageStorageKey,
  imagePreviewUrl,
  latitude,
  longitude,
  onReset,
}: SubmissionSummaryProps) {
  const [description, setDescription] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [isSubmittingOfficial, setIsSubmittingOfficial] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [complaintResult, setComplaintResult] = useState<ComplaintResult | null>(null);

  const [editedSubject, setEditedSubject] = useState("");
  const [editedComplaintText, setEditedComplaintText] = useState("");

  const handleCreateDraft = async () => {
    setIsAnalyzing(true);
    setError(null);

    const payload = {
      image_storage_key: imageStorageKey,
      latitude: latitude,
      longitude: longitude,
      description: description.trim() || null,
      category: selectedCategory || null,
    };

    try {
      const response = await fetch(`${API_BASE}/spotfix/complaints`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to analyze and create complaint draft.");
      }

      setComplaintResult(data);
      setEditedSubject(data.subject || "");
      setEditedComplaintText(data.complaint_text || "");
    } catch (err: any) {
      console.error("Draft creation error:", err);
      setError(err.message || "Failed to analyze complaint. Please try again.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleApprove = async () => {
    if (!complaintResult) return;
    setIsApproving(true);
    setError(null);

    try {
      if (
        editedSubject !== (complaintResult.subject || "") ||
        editedComplaintText !== (complaintResult.complaint_text || "")
      ) {
        const patchRes = await fetch(`${API_BASE}/spotfix/complaints/${complaintResult.id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            subject: editedSubject,
            complaint_text: editedComplaintText,
          }),
        });
        if (!patchRes.ok) {
          const patchData = await patchRes.json();
          throw new Error(patchData.detail || "Failed to update complaint draft.");
        }
      }

      const approveRes = await fetch(`${API_BASE}/spotfix/complaints/${complaintResult.id}/approve`, {
        method: "POST",
      });
      const approveData = await approveRes.json();

      if (!approveRes.ok) {
        throw new Error(approveData.detail || "Failed to approve complaint.");
      }

      setComplaintResult(approveData);
    } catch (err: any) {
      console.error("Approval error:", err);
      setError(err.message || "Failed to approve complaint.");
    } finally {
      setIsApproving(false);
    }
  };

  const handleSubmitOfficial = async () => {
    if (!complaintResult) return;
    setIsSubmittingOfficial(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/spotfix/complaints/${complaintResult.id}/submit`, {
        method: "POST",
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to submit complaint.");
      }

      setComplaintResult(data);
    } catch (err: any) {
      console.error("Submission error:", err);
      setError(err.message || "Failed to submit official complaint.");
    } finally {
      setIsSubmittingOfficial(false);
    }
  };

  if (complaintResult) {
    const isDraft = complaintResult.status === "DRAFT";
    const isApproved = complaintResult.status === "APPROVED";
    const isSubmitted = complaintResult.status === "SUBMITTED";

    return (
      <div className="w-full bg-white border border-slate-200 rounded-2xl p-6 shadow-xs text-slate-900 space-y-6">
        {/* Header Badge */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
          <div>
            <h2 className="text-xl font-extrabold text-slate-900 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-[#C8102E]" />
              SpotFix AI Analysis & Workflow
            </h2>
            <p className="text-xs text-slate-500 mt-0.5 font-mono">
              ID: {complaintResult.id}
            </p>
          </div>
          <span
            className={`px-3 py-1 text-xs font-bold rounded-full border ${
              isSubmitted
                ? "bg-emerald-50 text-emerald-800 border-emerald-300"
                : isApproved
                ? "bg-blue-50 text-blue-800 border-blue-300"
                : "bg-amber-50 text-amber-800 border-amber-300"
            }`}
          >
            Status: {complaintResult.status}
          </span>
        </div>

        {/* 1. AI Analysis */}
        <div className="bg-slate-50/80 border border-slate-200 rounded-xl p-5 space-y-4">
          <span className="text-xs font-bold text-[#C8102E] uppercase tracking-wider flex items-center gap-1.5">
            <Sparkles className="w-4 h-4 text-amber-600" />
            1. Gemini Vision AI Analysis
          </span>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            <div className="p-3.5 bg-white rounded-lg border border-slate-200 shadow-2xs">
              <span className="text-slate-500 font-semibold block mb-1">Category</span>
              <span className="font-bold text-slate-900 text-sm">
                {complaintResult.category || "Unclassified"}
              </span>
            </div>

            <div className="p-3.5 bg-white rounded-lg border border-slate-200 shadow-2xs">
              <span className="text-slate-500 font-semibold block mb-1">Severity</span>
              <span
                className={`font-bold text-xs px-2.5 py-1 rounded-md inline-block ${
                  complaintResult.severity === "CRITICAL"
                    ? "bg-rose-100 text-rose-800 border border-rose-300"
                    : complaintResult.severity === "HIGH"
                    ? "bg-amber-100 text-amber-900 border border-amber-300"
                    : complaintResult.severity === "MEDIUM"
                    ? "bg-yellow-100 text-yellow-900 border border-yellow-300"
                    : "bg-emerald-100 text-emerald-900 border border-emerald-300"
                }`}
              >
                {complaintResult.severity || "NORMAL"}
              </span>
            </div>

            <div className="p-3.5 bg-white rounded-lg border border-slate-200 shadow-2xs">
              <span className="text-slate-500 font-semibold block mb-1">Confidence</span>
              <span className="font-bold text-slate-900 text-sm font-mono">
                {complaintResult.confidence
                  ? `${(complaintResult.confidence * 100).toFixed(1)}%`
                  : "N/A"}
              </span>
            </div>
          </div>

          {complaintResult.visual_explanation && (
            <div className="p-3.5 bg-white rounded-lg border border-slate-200 text-xs">
              <span className="text-slate-700 font-bold block mb-1">Visual Explanation</span>
              <p className="text-slate-600 leading-relaxed">{complaintResult.visual_explanation}</p>
            </div>
          )}
        </div>

        {/* 2. Predictive Impact */}
        <div className="bg-slate-50/80 border border-slate-200 rounded-xl p-5 space-y-4">
          <span className="text-xs font-bold text-amber-800 uppercase tracking-wider flex items-center gap-1.5">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            2. Predictive Impact Assessment
          </span>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div className="p-3.5 bg-white rounded-lg border border-slate-200 shadow-2xs">
              <span className="text-slate-500 font-semibold block mb-1">Impact Score</span>
              <span className="font-extrabold text-[#C8102E] text-lg font-mono">
                {complaintResult.impact_score !== null ? `${complaintResult.impact_score}/100` : "N/A"}
              </span>
            </div>

            <div className="p-3.5 bg-white rounded-lg border border-slate-200 shadow-2xs">
              <span className="text-slate-500 font-semibold block mb-1">Calculated Priority</span>
              <span className="font-bold text-slate-900 text-sm">
                {complaintResult.priority || "STANDARD"}
              </span>
            </div>
          </div>

          {complaintResult.impact_reason && (
            <div className="p-3.5 bg-white rounded-lg border border-slate-200 text-xs">
              <span className="text-slate-700 font-bold block mb-1">Impact Reason</span>
              <p className="text-slate-600 leading-relaxed">{complaintResult.impact_reason}</p>
            </div>
          )}
        </div>

        {/* 3. Routing Engine */}
        <div className="bg-slate-50/80 border border-slate-200 rounded-xl p-5 space-y-4">
          <span className="text-xs font-bold text-blue-900 uppercase tracking-wider flex items-center gap-1.5">
            <Building2 className="w-4 h-4 text-blue-600" />
            3. Deterministic Routing Engine
          </span>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div className="p-3.5 bg-white rounded-lg border border-slate-200 shadow-2xs">
              <span className="text-slate-500 font-semibold block mb-1">Target Authority</span>
              <span className="font-bold text-slate-900 text-sm">
                {complaintResult.authority || "N/A"}
              </span>
            </div>

            <div className="p-3.5 bg-white rounded-lg border border-slate-200 shadow-2xs">
              <span className="text-slate-500 font-semibold block mb-1">Department</span>
              <span className="font-bold text-slate-900 text-sm">
                {complaintResult.department || "N/A"}
              </span>
            </div>
          </div>

          {complaintResult.routing_reason && (
            <div className="p-3.5 bg-white rounded-lg border border-slate-200 text-xs">
              <span className="text-slate-700 font-bold block mb-1">Routing Reason</span>
              <p className="text-slate-600 leading-relaxed">{complaintResult.routing_reason}</p>
            </div>
          )}
        </div>

        {/* 4. Complaint Draft */}
        <div className="bg-slate-50/80 border border-slate-200 rounded-xl p-5 space-y-4">
          <span className="text-xs font-bold text-purple-900 uppercase tracking-wider flex items-center gap-1.5">
            <FileText className="w-4 h-4 text-purple-600" />
            4. AI Complaint Writer Draft
          </span>

          <div className="space-y-3 text-xs">
            <div>
              <label className="text-slate-700 font-bold block mb-1">Subject</label>
              {isDraft ? (
                <input
                  type="text"
                  value={editedSubject}
                  onChange={(e) => setEditedSubject(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:border-[#C8102E] font-medium"
                />
              ) : (
                <p className="p-3 bg-white rounded-lg border border-slate-200 text-slate-900 font-semibold">
                  {complaintResult.subject}
                </p>
              )}
            </div>

            <div>
              <label className="text-slate-700 font-bold block mb-1">Complaint Text</label>
              {isDraft ? (
                <textarea
                  value={editedComplaintText}
                  onChange={(e) => setEditedComplaintText(e.target.value)}
                  rows={4}
                  className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-xs text-slate-900 focus:outline-none focus:border-[#C8102E] resize-none font-mono"
                />
              ) : (
                <div className="p-3 bg-white rounded-lg border border-slate-200 text-slate-800 font-mono whitespace-pre-wrap leading-relaxed">
                  {complaintResult.complaint_text}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        {/* Action Buttons & Submission Summary */}
        {isDraft && (
          <button
            type="button"
            onClick={handleApprove}
            disabled={isApproving}
            className="w-full py-3.5 bg-[#C8102E] hover:bg-[#A60C24] text-white font-bold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {isApproving ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin text-amber-300" />
                Approving Complaint...
              </>
            ) : (
              <>
                <ShieldCheck className="w-4 h-4 text-amber-300" />
                Approve Complaint
              </>
            )}
          </button>
        )}

        {isApproved && (
          <div className="space-y-4">
            <div className="p-3.5 bg-blue-50 border border-blue-200 rounded-xl text-blue-900 text-xs flex items-center gap-2 font-semibold">
              <CheckCircle2 className="w-4 h-4 text-blue-600 shrink-0" />
              <span>Complaint Approved! Click below to dispatch official email to authority and publish to Instagram.</span>
            </div>

            <button
              type="button"
              onClick={handleSubmitOfficial}
              disabled={isSubmittingOfficial}
              className="w-full py-3.5 bg-[#C8102E] hover:bg-[#A60C24] text-white font-bold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {isSubmittingOfficial ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin text-amber-300" />
                  Sending Official Email & Publishing to Instagram...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4 text-amber-300" />
                  Submit Official Complaint
                </>
              )}
            </button>
          </div>
        )}

        {isSubmitted && (
          <div className="bg-emerald-50/60 border border-emerald-200 rounded-2xl p-6 space-y-5">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-full bg-emerald-600 text-white flex items-center justify-center shrink-0 shadow-xs">
                <CheckCircle2 className="w-7 h-7" />
              </div>
              <div>
                <h3 className="text-lg font-extrabold text-slate-900">Submission Completed Successfully!</h3>
                <p className="text-xs text-slate-600">
                  Official civic submission and social alert dispatch complete.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="p-4 bg-white rounded-xl border border-emerald-200 shadow-2xs space-y-1.5">
                <span className="text-slate-700 font-bold flex items-center gap-1.5">
                  <Mail className="w-4 h-4 text-emerald-600" />
                  Official Email Submission
                </span>
                <p className="text-slate-800 font-mono leading-relaxed">
                  Status: <span className="text-emerald-700 font-bold">Sent</span><br />
                  To: {complaintResult.recipient_email || "Authority Email"}<br />
                  Time: {complaintResult.submitted_at ? new Date(complaintResult.submitted_at).toLocaleString() : "Just now"}
                </p>
              </div>

              <div className="p-4 bg-white rounded-xl border border-pink-200 shadow-2xs space-y-1.5">
                <span className="text-slate-700 font-bold flex items-center gap-1.5">
                  <Share2 className="w-4 h-4 text-pink-600" />
                  Instagram Social Awareness
                </span>
                <p className="text-slate-800 font-mono leading-relaxed">
                  {complaintResult.instagram_post_id ? (
                    <>
                      Status: <span className="text-pink-600 font-bold">Published</span><br />
                      Post ID: <span className="text-slate-900 font-bold">{complaintResult.instagram_post_id}</span>
                    </>
                  ) : (
                    <>
                      Status: Not Published<br />
                      <span className="text-slate-500 text-[11px]">(Credentials or base URL not configured)</span>
                    </>
                  )}
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={onReset}
              className="w-full py-3 bg-white hover:bg-slate-100 text-slate-800 font-bold text-xs rounded-xl border border-slate-300 shadow-2xs transition-all"
            >
              Submit Another SpotFix Report
            </button>
          </div>
        )}
      </div>
    );
  }

  // Initial State before Draft Creation
  return (
    <div className="w-full bg-white border border-slate-200 rounded-2xl p-6 shadow-xs text-slate-900 space-y-6">
      <div className="border-b border-slate-100 pb-4">
        <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
          <Send className="w-5 h-5 text-[#C8102E]" />
          Step 3: Review Intake Details & Analyze
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          Review your photo intake and map location, then run SpotFix AI analysis.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
          <span className="text-xs font-bold text-slate-700 uppercase tracking-wider block">
            Intake Image
          </span>
          <div className="relative w-full h-36 rounded-lg overflow-hidden border border-slate-200 bg-slate-100 flex items-center justify-center">
            <img src={imagePreviewUrl} alt="Intake preview" className="max-h-36 object-contain" />
          </div>
        </div>

        <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3 flex flex-col justify-between">
          <div>
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-2">
              Confirmed Map Location
            </span>
            <div className="space-y-1.5 text-xs font-mono">
              <div className="p-2 bg-white rounded border border-slate-200 text-slate-800">
                Lat: {latitude}
              </div>
              <div className="p-2 bg-white rounded border border-slate-200 text-slate-800">
                Lng: {longitude}
              </div>
            </div>
          </div>
          <div className="text-[11px] text-slate-500 font-mono truncate">
            Ref: {imageStorageKey}
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-xs font-bold text-slate-700 mb-1.5 flex items-center gap-1.5">
            <Tag className="w-3.5 h-3.5 text-[#C8102E]" />
            Optional Problem Category (Leave blank for AI Auto-Detection)
          </label>
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-xl text-sm text-slate-900 focus:outline-none focus:border-[#C8102E]"
          >
            <option value="">-- Let Gemini Vision AI Auto-Detect --</option>
            {CATEGORIES.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs font-bold text-slate-700 mb-1.5 flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5 text-[#C8102E]" />
            Optional Description / Citizen Remarks
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            placeholder="Add any extra context, nearby landmarks, or specific notes..."
            className="w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-xl text-sm text-slate-900 focus:outline-none focus:border-[#C8102E] placeholder:text-slate-400 resize-none"
          />
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
          <p>{error}</p>
        </div>
      )}

      <button
        type="button"
        onClick={handleCreateDraft}
        disabled={isAnalyzing}
        className="w-full py-3.5 bg-[#C8102E] hover:bg-[#A60C24] text-white font-bold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2 disabled:opacity-50"
      >
        {isAnalyzing ? (
          <>
            <RefreshCw className="w-4 h-4 animate-spin text-amber-300" />
            Analyzing Image & Creating Draft...
          </>
        ) : (
          <>
            <Send className="w-4 h-4 text-amber-300" />
            Analyze & Create Complaint Draft
          </>
        )}
      </button>
    </div>
  );
}
