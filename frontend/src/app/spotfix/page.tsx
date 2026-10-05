'use client';

import React, { useState } from "react";
import ImageIntake from "@/components/spotfix/ImageIntake";
import LocationPickerMap from "@/components/spotfix/LocationPickerMap";
import SubmissionSummary from "@/components/spotfix/SubmissionSummary";
import { Camera, MapPin, CheckCircle2, ShieldAlert, ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function SpotFixPage() {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [imageStorageKey, setImageStorageKey] = useState<string | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const [latitude, setLatitude] = useState<number | null>(null);
  const [longitude, setLongitude] = useState<number | null>(null);

  const handleImageUploaded = (storageKey: string, previewUrl: string) => {
    setImageStorageKey(storageKey);
    setImagePreviewUrl(previewUrl);
    setStep(2);
  };

  const handleLocationConfirmed = (lat: number, lng: number) => {
    setLatitude(lat);
    setLongitude(lng);
    setStep(3);
  };

  const handleReset = () => {
    setImageStorageKey(null);
    setImagePreviewUrl(null);
    setLatitude(null);
    setLongitude(null);
    setStep(1);
  };

  return (
    <main className="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-6 flex-1 w-full">
      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs relative overflow-hidden flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#C8102E] via-[#FFC72C] to-[#C8102E]" />

        <div>
          <div className="flex items-center gap-2 text-[#C8102E] font-bold text-xs tracking-wider uppercase mb-1">
            <ShieldAlert className="w-4 h-4 text-amber-600" />
            NammaNexus SpotFix AI Intake
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
            Report Civic Issue
          </h1>
          <p className="text-xs sm:text-sm text-slate-600 mt-1">
            Upload a photo of potholes, garbage, or water leakage for AI verification and civic authority routing.
          </p>
        </div>

        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 px-3 py-2 rounded-lg border border-slate-200 transition-colors shrink-0"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Home
        </Link>
      </div>

      {/* 3-Step Wizard Navigation */}
      <div className="grid grid-cols-3 gap-2 p-1.5 bg-white rounded-2xl border border-slate-200 shadow-2xs text-xs font-bold">
        <button
          type="button"
          onClick={() => setStep(1)}
          className={`py-3 px-3 rounded-xl flex items-center justify-center gap-2 transition-all ${
            step === 1
              ? "bg-[#C8102E] text-white shadow-sm"
              : imageStorageKey
              ? "text-[#C8102E] bg-red-50 hover:bg-red-100/60 border border-red-200"
              : "text-slate-400 bg-slate-50 hover:bg-slate-100"
          }`}
        >
          <Camera className="w-4 h-4" />
          <span className="hidden sm:inline">1. Photo Intake</span>
        </button>

        <button
          type="button"
          onClick={() => imageStorageKey && setStep(2)}
          disabled={!imageStorageKey}
          className={`py-3 px-3 rounded-xl flex items-center justify-center gap-2 transition-all ${
            step === 2
              ? "bg-[#C8102E] text-white shadow-sm"
              : latitude !== null
              ? "text-[#C8102E] bg-red-50 hover:bg-red-100/60 border border-red-200"
              : "text-slate-400 bg-slate-50 hover:bg-slate-100"
          } disabled:opacity-40 disabled:cursor-not-allowed`}
        >
          <MapPin className="w-4 h-4" />
          <span className="hidden sm:inline">2. Map Location</span>
        </button>

        <button
          type="button"
          onClick={() => imageStorageKey && latitude !== null && setStep(3)}
          disabled={!imageStorageKey || latitude === null}
          className={`py-3 px-3 rounded-xl flex items-center justify-center gap-2 transition-all ${
            step === 3
              ? "bg-[#C8102E] text-white shadow-sm"
              : "text-slate-400 bg-slate-50 hover:bg-slate-100"
          } disabled:opacity-40 disabled:cursor-not-allowed`}
        >
          <CheckCircle2 className="w-4 h-4" />
          <span className="hidden sm:inline">3. Review & Submit</span>
        </button>
      </div>

      {/* Step Components */}
      {step === 1 && (
        <ImageIntake
          onImageUploaded={handleImageUploaded}
          existingStorageKey={imageStorageKey}
          existingPreviewUrl={imagePreviewUrl}
        />
      )}

      {step === 2 && (
        <LocationPickerMap
          onLocationConfirmed={handleLocationConfirmed}
          initialLat={latitude}
          initialLng={longitude}
        />
      )}

      {step === 3 && imageStorageKey && imagePreviewUrl && latitude !== null && longitude !== null && (
        <SubmissionSummary
          imageStorageKey={imageStorageKey}
          imagePreviewUrl={imagePreviewUrl}
          latitude={latitude}
          longitude={longitude}
          onReset={handleReset}
        />
      )}
    </main>
  );
}
