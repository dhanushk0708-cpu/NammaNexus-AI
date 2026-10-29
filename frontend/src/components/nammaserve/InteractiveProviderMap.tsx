'use client';

import React, { useState, useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import { Phone, Navigation, Layers, Plus, Minus, Locate } from "lucide-react";
import type { ProviderItem } from "./NearbyProvidersList";

interface InteractiveProviderMapProps {
  centerLat: number;
  centerLng: number;
  providers: ProviderItem[];
  selectedProviderId: string | null;
  onSelectProvider: (provider: ProviderItem) => void;
}

// Map Controller helper to smoothly re-center map when props change
function MapController({ lat, lng, zoom }: { lat: number; lng: number; zoom: number }) {
  const map = useMap();
  useEffect(() => {
    map.flyTo([lat, lng], zoom, { duration: 1.2 });
  }, [lat, lng, zoom, map]);
  return null;
}

// Create custom colored numbered circular Leaflet pin
function createNumberedIcon(number: number, isSelected: boolean) {
  const colors = [
    { bg: "#EF4444", border: "#B91C1C", text: "#FFFFFF" }, // 1: Red
    { bg: "#3B82F6", border: "#1D4ED8", text: "#FFFFFF" }, // 2: Blue
    { bg: "#10B981", border: "#047857", text: "#FFFFFF" }, // 3: Green
  ];

  const color = colors[(number - 1) % colors.length] || { bg: "#C8102E", border: "#990B22", text: "#FFFFFF" };
  const size = isSelected ? 36 : 30;

  const html = `
    <div style="
      background-color: ${color.bg};
      color: ${color.text};
      width: ${size}px;
      height: ${size}px;
      border-radius: 50%;
      border: 2px solid ${isSelected ? "#FFFFFF" : color.border};
      box-shadow: 0 4px 10px rgba(0,0,0,0.3);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: ${isSelected ? "14px" : "12px"};
      font-family: inherit;
      transform: translate(-50%, -50%);
      transition: all 0.2s ease;
      cursor: pointer;
    ">
      ${number}
    </div>
  `;

  return L.divIcon({
    className: "custom-provider-marker",
    html: html,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

export default function InteractiveProviderMap({
  centerLat,
  centerLng,
  providers,
  selectedProviderId,
  onSelectProvider,
}: InteractiveProviderMapProps) {
  const [mapType, setMapType] = useState<"standard" | "satellite">("standard");

  const activeProvider = providers.find((p) => p.id === selectedProviderId);
  const targetLat = activeProvider ? activeProvider.latitude : centerLat;
  const targetLng = activeProvider ? activeProvider.longitude : centerLng;

  const tileUrls = {
    standard: {
      url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    },
    satellite: {
      url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      attribution: "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community",
    },
  };

  return (
    <div className="w-full bg-white border border-slate-200/90 rounded-2xl overflow-hidden shadow-2xs flex flex-col h-[480px]">
      {/* Top Map Toggle Bar matching screenshot */}
      <div className="p-2.5 border-b border-slate-100 bg-white flex items-center justify-between z-10 shrink-0">
        <div className="inline-flex p-1 bg-slate-100 rounded-xl gap-1">
          <button
            type="button"
            onClick={() => setMapType("standard")}
            className={`px-3 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              mapType === "standard"
                ? "bg-blue-600 text-white shadow-2xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Map
          </button>
          <button
            type="button"
            onClick={() => setMapType("satellite")}
            className={`px-3 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              mapType === "satellite"
                ? "bg-blue-600 text-white shadow-2xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Satellite
          </button>
        </div>

        <div className="text-[11px] font-semibold text-slate-500 pr-2">
          {providers.length} Pins Active
        </div>
      </div>

      {/* Map Canvas */}
      <div className="relative flex-1 w-full bg-slate-100">
        <MapContainer
          center={[targetLat, targetLng]}
          zoom={13}
          scrollWheelZoom={true}
          zoomControl={false}
          className="w-full h-full z-0"
        >
          <MapController lat={targetLat} lng={targetLng} zoom={activeProvider ? 15 : 13} />

          <TileLayer
            url={tileUrls[mapType].url}
            attribution={tileUrls[mapType].attribution}
          />

          {/* Provider Markers */}
          {providers.map((p) => {
            const isSelected = selectedProviderId === p.id;
            const icon = createNumberedIcon(p.number, isSelected);

            return (
              <Marker
                key={p.id}
                position={[p.latitude, p.longitude]}
                icon={icon}
                eventHandlers={{
                  click: () => onSelectProvider(p),
                }}
              >
                <Popup className="custom-leaflet-popup">
                  <div className="p-2 space-y-1 text-slate-900 min-w-[180px]">
                    <div className="flex items-center gap-1.5">
                      <span className="w-5 h-5 rounded-full bg-blue-600 text-white font-bold text-[10px] flex items-center justify-center">
                        {p.number}
                      </span>
                      <h4 className="font-extrabold text-xs">{p.name}</h4>
                    </div>
                    <p className="text-[11px] text-slate-500 font-medium">
                      {p.distanceKm !== null ? `${p.distanceKm.toFixed(1)} km away • ` : ""}
                      {p.locality}
                    </p>
                    <p className="text-xs font-black text-slate-900 pt-0.5">{p.priceDisplay}</p>
                    <div className="pt-2 flex items-center gap-1.5">
                      <a
                        href={`tel:${p.phone}`}
                        className="flex-1 bg-emerald-600 text-white text-[10px] font-bold py-1 px-2 rounded-md flex items-center justify-center gap-1"
                      >
                        <Phone className="w-3 h-3" />
                        <span>Call</span>
                      </a>
                      <a
                        href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
                          `${p.name} ${p.locality} Bengaluru`
                        )}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex-1 bg-blue-600 text-white text-[10px] font-bold py-1 px-2 rounded-md flex items-center justify-center gap-1"
                      >
                        <Navigation className="w-3 h-3" />
                        <span>Route</span>
                      </a>
                    </div>
                  </div>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>
      </div>

      {/* Bottom Legend Bar matching screenshot */}
      <div className="p-2.5 sm:p-3 bg-white border-t border-slate-100 flex flex-col gap-1 text-xs shrink-0 z-10">
        {providers.map((p) => {
          const colors = ["bg-red-600", "bg-blue-600", "bg-emerald-600"];
          const colorClass = colors[(p.number - 1) % colors.length];
          const isSelected = selectedProviderId === p.id;

          return (
            <button
              key={p.id}
              type="button"
              onClick={() => onSelectProvider(p)}
              className={`flex items-center justify-between w-full px-2 py-1 rounded-lg text-xs transition-colors cursor-pointer ${
                isSelected ? "bg-amber-50 font-bold ring-1 ring-amber-300" : "hover:bg-slate-50 text-slate-700"
              }`}
            >
              <div className="flex items-center gap-2 min-w-0">
                <span
                  className={`w-4 h-4 rounded-full ${colorClass} text-white font-black text-[9px] flex items-center justify-center shrink-0 shadow-2xs`}
                >
                  {p.number}
                </span>
                <span className="truncate text-slate-800 text-[11px] sm:text-xs">{p.name}</span>
              </div>
              {p.distanceKm !== null && (
                <span className="text-slate-500 text-[10px] sm:text-[11px] shrink-0 font-medium ml-2">
                  {p.distanceKm.toFixed(1)} km
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
