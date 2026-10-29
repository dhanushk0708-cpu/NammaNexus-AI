import React from "react";

export default function VidhanaSoudhaIllustration({ className = "w-full h-16" }: { className?: string }) {
  return (
    <div className={`relative flex items-end justify-center overflow-hidden ${className}`}>
      {/* Decorative Karnataka Vidhana Soudha Architectural Silhouette */}
      <svg
        viewBox="0 0 320 80"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full object-contain filter drop-shadow-xs"
        preserveAspectRatio="xMidYMax meet"
      >
        <defs>
          <linearGradient id="soudhaGradient" x1="0%" y1="100%" x2="0%" y2="0%">
            <stop offset="0%" stopColor="#C8102E" />
            <stop offset="50%" stopColor="#EA580C" />
            <stop offset="100%" stopColor="#F59E0B" />
          </linearGradient>
          <linearGradient id="baseGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#C8102E" />
            <stop offset="50%" stopColor="#F59E0B" />
            <stop offset="100%" stopColor="#C8102E" />
          </linearGradient>
        </defs>

        {/* Outer decorative pillars & wings */}
        <rect x="20" y="55" width="280" height="20" fill="url(#soudhaGradient)" opacity="0.95" rx="2" />
        <rect x="10" y="70" width="300" height="8" fill="url(#baseGradient)" rx="1" />

        {/* Left Wing & Portico */}
        <rect x="35" y="42" width="60" height="15" fill="url(#soudhaGradient)" />
        <rect x="40" y="32" width="12" height="12" fill="url(#soudhaGradient)" />
        <rect x="58" y="32" width="12" height="12" fill="url(#soudhaGradient)" />
        <rect x="76" y="32" width="12" height="12" fill="url(#soudhaGradient)" />
        <polygon points="32,42 98,42 90,36 40,36" fill="url(#soudhaGradient)" />
        {/* Left minaret / chhatri */}
        <rect x="24" y="34" width="8" height="22" fill="url(#soudhaGradient)" />
        <polygon points="28,22 22,34 34,34" fill="#F59E0B" />
        <circle cx="28" cy="20" r="2" fill="#FDE047" />

        {/* Right Wing & Portico */}
        <rect x="225" y="42" width="60" height="15" fill="url(#soudhaGradient)" />
        <rect x="232" y="32" width="12" height="12" fill="url(#soudhaGradient)" />
        <rect x="250" y="32" width="12" height="12" fill="url(#soudhaGradient)" />
        <rect x="268" y="32" width="12" height="12" fill="url(#soudhaGradient)" />
        <polygon points="222,42 288,42 280,36 230,36" fill="url(#soudhaGradient)" />
        {/* Right minaret / chhatri */}
        <rect x="288" y="34" width="8" height="22" fill="url(#soudhaGradient)" />
        <polygon points="292,22 286,34 298,34" fill="#F59E0B" />
        <circle cx="292" cy="20" r="2" fill="#FDE047" />

        {/* Main Central Façade */}
        <rect x="105" y="35" width="110" height="22" fill="url(#soudhaGradient)" />
        {/* Grand Steps */}
        <polygon points="120,57 200,57 210,72 110,72" fill="#990B22" />
        {/* Central Columns */}
        <rect x="120" y="40" width="5" height="16" fill="#FEF08A" opacity="0.9" />
        <rect x="135" y="40" width="5" height="16" fill="#FEF08A" opacity="0.9" />
        <rect x="150" y="40" width="5" height="16" fill="#FEF08A" opacity="0.9" />
        <rect x="165" y="40" width="5" height="16" fill="#FEF08A" opacity="0.9" />
        <rect x="180" y="40" width="5" height="16" fill="#FEF08A" opacity="0.9" />
        <rect x="195" y="40" width="5" height="16" fill="#FEF08A" opacity="0.9" />

        {/* Central Pediment */}
        <polygon points="115,35 205,35 160,20" fill="url(#soudhaGradient)" />

        {/* Grand Central Dome (Kalasam) */}
        <rect x="145" y="16" width="30" height="6" fill="url(#soudhaGradient)" rx="1" />
        <path d="M 142 16 Q 160 -2 178 16 Z" fill="url(#soudhaGradient)" />
        {/* Ashoka Stambh / Kalasa Spire */}
        <rect x="158" y="1" width="4" height="6" fill="#FDE047" />
        <circle cx="160" cy="1" r="2" fill="#FEF08A" />

        {/* Flanking Domes */}
        <path d="M 112 25 Q 120 12 128 25 Z" fill="url(#soudhaGradient)" />
        <rect x="119" y="9" width="2" height="4" fill="#FDE047" />
        <circle cx="120" cy="8" r="1.5" fill="#FEF08A" />

        <path d="M 192 25 Q 200 12 208 25 Z" fill="url(#soudhaGradient)" />
        <rect x="199" y="9" width="2" height="4" fill="#FDE047" />
        <circle cx="200" cy="8" r="1.5" fill="#FEF08A" />
      </svg>
    </div>
  );
}
