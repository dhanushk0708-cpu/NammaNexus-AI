'use client';

import React, { useState, useRef, useEffect } from "react";
import { Upload, Camera, RefreshCw, CheckCircle2, AlertCircle, Image as ImageIcon, Video } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface ImageIntakeProps {
  onImageUploaded: (storageKey: string, previewUrl: string) => void;
  existingStorageKey: string | null;
  existingPreviewUrl: string | null;
}

export default function ImageIntake({
  onImageUploaded,
  existingStorageKey,
  existingPreviewUrl,
}: ImageIntakeProps) {
  const [activeTab, setActiveTab] = useState<"file" | "camera">("file");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(existingPreviewUrl);
  const [storageKey, setStorageKey] = useState<string | null>(existingStorageKey);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Camera state
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);

  const startCamera = async () => {
    setCameraError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      mediaStreamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setIsCameraActive(true);
    } catch (err: any) {
      console.error("Camera access error:", err);
      setCameraError(
        "Could not access camera. Please allow camera permissions or upload a photo instead."
      );
      setIsCameraActive(false);
    }
  };

  const stopCamera = () => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
    setIsCameraActive(false);
  };

  useEffect(() => {
    if (activeTab === "camera" && !previewUrl) {
      startCamera();
    } else {
      stopCamera();
    }
    return () => {
      stopCamera();
    };
  }, [activeTab, previewUrl]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSelectedFile(file);
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    uploadImage(file);
  };

  const handleCapturePhoto = () => {
    if (!videoRef.current) return;
    const video = videoRef.current;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob((blob) => {
      if (!blob) return;
      const file = new File([blob], `camera_capture_${Date.now()}.jpg`, { type: "image/jpeg" });
      setSelectedFile(file);
      const url = URL.createObjectURL(blob);
      setPreviewUrl(url);
      stopCamera();
      uploadImage(file);
    }, "image/jpeg", 0.9);
  };

  const uploadImage = async (file: File) => {
    setIsUploading(true);
    setUploadError(null);

    const formData = new FormData();
    formData.append("image", file);

    try {
      const response = await fetch(`${API_BASE}/spotfix/uploads`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Image upload failed.");
      }

      setStorageKey(data.stored_filename);
      onImageUploaded(data.stored_filename, URL.createObjectURL(file));
    } catch (err: any) {
      console.error("Upload error:", err);
      setUploadError(err.message || "Failed to upload image. Please try again.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleReset = () => {
    setPreviewUrl(null);
    setStorageKey(null);
    setSelectedFile(null);
    setUploadError(null);
    if (activeTab === "camera") {
      startCamera();
    }
  };

  return (
    <div className="w-full bg-white border border-slate-200 rounded-2xl p-6 shadow-xs text-slate-900 space-y-6">
      <div className="border-b border-slate-100 pb-4">
        <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
          <ImageIcon className="w-5 h-5 text-[#C8102E]" />
          Step 1: Photo Intake
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          Upload an existing photo or capture a photo using your device camera.
        </p>
      </div>

      <div className="flex border-b border-slate-200 gap-2">
        <button
          type="button"
          onClick={() => {
            setActiveTab("file");
            if (previewUrl && !storageKey) handleReset();
          }}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-t-xl transition-all ${
            activeTab === "file"
              ? "bg-red-50 text-[#C8102E] border-b-2 border-[#C8102E]"
              : "text-slate-500 hover:text-slate-800 hover:bg-slate-50"
          }`}
        >
          <Upload className="w-4 h-4" />
          Upload Photo File
        </button>
        <button
          type="button"
          onClick={() => {
            setActiveTab("camera");
            if (previewUrl && !storageKey) handleReset();
          }}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-t-xl transition-all ${
            activeTab === "camera"
              ? "bg-red-50 text-[#C8102E] border-b-2 border-[#C8102E]"
              : "text-slate-500 hover:text-slate-800 hover:bg-slate-50"
          }`}
        >
          <Camera className="w-4 h-4" />
          Web Camera Capture
        </button>
      </div>

      {previewUrl ? (
        <div className="space-y-4">
          <div className="relative w-full max-h-80 rounded-xl overflow-hidden bg-slate-900 border border-slate-200 flex items-center justify-center p-2">
            <img src={previewUrl} alt="Selected Intake Preview" className="max-h-72 object-contain rounded-lg" />
            {isUploading && (
              <div className="absolute inset-0 bg-slate-900/80 backdrop-blur-xs flex flex-col items-center justify-center gap-2 text-white text-xs font-semibold">
                <RefreshCw className="w-6 h-6 animate-spin text-amber-400" />
                Uploading image to SpotFix storage...
              </div>
            )}
          </div>

          {storageKey && (
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                <div>
                  <p className="text-xs font-bold text-emerald-900">Photo Uploaded Successfully</p>
                  <p className="text-[11px] font-mono text-emerald-700 truncate max-w-xs sm:max-w-md">
                    Key: {storageKey}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={handleReset}
                className="px-3 py-1.5 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 text-xs font-semibold rounded-lg shadow-2xs transition-all"
              >
                Change Photo
              </button>
            </div>
          )}
        </div>
      ) : activeTab === "file" ? (
        <label className="flex flex-col items-center justify-center w-full h-64 border-2 border-dashed border-slate-300 rounded-2xl cursor-pointer bg-slate-50/50 hover:bg-red-50/30 hover:border-[#C8102E]/60 transition-all p-6 text-center group">
          <Upload className="w-10 h-10 text-slate-400 group-hover:text-[#C8102E] transition-colors mb-3" />
          <span className="text-sm font-bold text-slate-800">Click to select photo file</span>
          <span className="text-xs text-slate-500 mt-1">Supports JPG, PNG, WEBP (Max 10MB)</span>
          <input type="file" accept="image/*" onChange={handleFileSelect} className="hidden" />
        </label>
      ) : (
        <div className="space-y-4">
          <div className="relative w-full h-72 rounded-2xl overflow-hidden bg-slate-900 border border-slate-200 flex items-center justify-center">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              className={`w-full h-full object-cover ${isCameraActive ? "block" : "hidden"}`}
            />
            {!isCameraActive && (
              <div className="flex flex-col items-center justify-center p-6 text-center space-y-3">
                <Video className="w-10 h-10 text-slate-500" />
                <p className="text-xs text-slate-400">Camera preview will appear here</p>
                <button
                  type="button"
                  onClick={startCamera}
                  className="px-4 py-2 bg-[#C8102E] hover:bg-[#A60C24] text-white text-xs font-bold rounded-xl shadow-xs transition-all"
                >
                  Enable Camera
                </button>
              </div>
            )}
          </div>

          {cameraError && (
            <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
              <p>{cameraError}</p>
            </div>
          )}

          {isCameraActive && (
            <button
              type="button"
              onClick={handleCapturePhoto}
              className="w-full py-3 bg-[#C8102E] hover:bg-[#A60C24] text-white font-bold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
            >
              <Camera className="w-4 h-4 text-amber-300" />
              Capture Photo Now
            </button>
          )}
        </div>
      )}

      {uploadError && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
          <p>{uploadError}</p>
        </div>
      )}
    </div>
  );
}
