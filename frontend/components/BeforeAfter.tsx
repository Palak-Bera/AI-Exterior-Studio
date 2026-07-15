"use client";

import { useState } from "react";

import { mediaUrl } from "@/lib/config";

interface Props {
  beforeUrl: string;
  afterUrl: string;
}

export default function BeforeAfter({ beforeUrl, afterUrl }: Props) {
  const [pos, setPos] = useState(50);

  return (
    <div className="space-y-3">
      <div className="relative select-none overflow-hidden rounded-xl border border-[var(--line)] bg-slate-100">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={mediaUrl(beforeUrl)} alt="before" className="block w-full" />
        <div
          className="absolute inset-0 overflow-hidden"
          style={{ width: `${pos}%` }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={mediaUrl(afterUrl)}
            alt="after"
            className="block h-full max-w-none"
            style={{ width: `${(100 / pos) * 100}%` }}
          />
        </div>
        <div
          className="absolute top-0 h-full w-0.5 bg-white shadow"
          style={{ left: `${pos}%` }}
        />
      </div>
      <input
        type="range"
        min={0}
        max={100}
        value={pos}
        onChange={(e) => setPos(Number(e.target.value))}
        className="w-full accent-[var(--accent)]"
      />
      <div className="flex justify-between text-xs font-medium text-[var(--muted)]">
        <span>Original</span>
        <span>Redesign</span>
      </div>
    </div>
  );
}
