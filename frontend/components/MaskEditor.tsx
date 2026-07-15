"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { mediaUrl } from "@/lib/config";

type Tool = "brush" | "eraser";

interface Props {
  imageUrl: string;
  maskUrl: string | null;
  /** CSS color for mask overlay e.g. #ef4444 */
  maskColor: string;
  width: number;
  height: number;
  categoryLabel: string;
  saving?: boolean;
  onCancel: () => void;
  onSave: (maskDataUrl: string) => void;
}

function hexToRgb(hex: string): { r: number; g: number; b: number } {
  const h = hex.replace("#", "");
  const full =
    h.length === 3
      ? h
          .split("")
          .map((c) => c + c)
          .join("")
      : h;
  return {
    r: parseInt(full.slice(0, 2), 16) || 239,
    g: parseInt(full.slice(2, 4), 16) || 68,
    b: parseInt(full.slice(4, 6), 16) || 68,
  };
}

/**
 * Brush / eraser editor for refining a category mask on top of the photo.
 */
export default function MaskEditor({
  imageUrl,
  maskUrl,
  maskColor,
  width,
  height,
  categoryLabel,
  saving,
  onCancel,
  onSave,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const drawing = useRef(false);
  const last = useRef<{ x: number; y: number } | null>(null);

  const [tool, setTool] = useState<Tool>("brush");
  const [brushSize, setBrushSize] = useState(28);
  const [ready, setReady] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const paintAt = useCallback(
    (x: number, y: number, prev: { x: number; y: number } | null) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      const { r, g, b } = hexToRgb(maskColor);
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.lineWidth = brushSize;

      if (tool === "eraser") {
        ctx.globalCompositeOperation = "destination-out";
        ctx.strokeStyle = "rgba(0,0,0,1)";
      } else {
        ctx.globalCompositeOperation = "source-over";
        ctx.strokeStyle = `rgba(${r},${g},${b},0.85)`;
      }

      ctx.beginPath();
      if (prev) {
        ctx.moveTo(prev.x, prev.y);
        ctx.lineTo(x, y);
      } else {
        ctx.moveTo(x, y);
        ctx.lineTo(x + 0.01, y);
      }
      ctx.stroke();
    },
    [brushSize, maskColor, tool]
  );

  const pointerPos = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY,
    };
  };

  // Initialize canvas from existing tinted mask (alpha channel).
  useEffect(() => {
    let cancelled = false;
    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, width, height);
    setReady(false);
    setLoadError(null);

    if (!maskUrl) {
      setReady(true);
      return;
    }

    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      if (cancelled) return;
      const off = document.createElement("canvas");
      off.width = width;
      off.height = height;
      const octx = off.getContext("2d");
      if (!octx) return;
      octx.drawImage(img, 0, 0, width, height);
      const data = octx.getImageData(0, 0, width, height);
      const { r, g, b } = hexToRgb(maskColor);
      const out = ctx.createImageData(width, height);
      for (let i = 0; i < data.data.length; i += 4) {
        const a = data.data[i + 3];
        const lum = (data.data[i] + data.data[i + 1] + data.data[i + 2]) / 3;
        const on = a > 30 || lum > 40;
        if (on) {
          out.data[i] = r;
          out.data[i + 1] = g;
          out.data[i + 2] = b;
          out.data[i + 3] = 200;
        }
      }
      ctx.putImageData(out, 0, 0);
      setReady(true);
    };
    img.onerror = () => {
      if (!cancelled) {
        setLoadError("Could not load the existing mask — you can still paint a new one.");
        setReady(true);
      }
    };

    // Fetch as blob so CORS-tainted canvas issues are avoided when possible.
    void (async () => {
      try {
        const res = await fetch(mediaUrl(maskUrl), { mode: "cors" });
        if (!res.ok) throw new Error("fetch failed");
        const blob = await res.blob();
        if (cancelled) return;
        img.src = URL.createObjectURL(blob);
      } catch {
        if (!cancelled) img.src = mediaUrl(maskUrl);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [maskUrl, width, height, maskColor]);

  const clearMask = () => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  };

  const handleSave = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    onSave(canvas.toDataURL("image/png"));
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-[var(--ink)]">
            Edit mask — {categoryLabel}
          </h3>
          <p className="text-xs text-[var(--muted)]">
            Brush to add · Eraser to remove areas the model over-detected
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className={`rounded-lg border px-3 py-1.5 text-sm font-medium ${
              tool === "brush"
                ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--ink)]"
                : "border-[var(--line)] bg-white text-[var(--muted)]"
            }`}
            onClick={() => setTool("brush")}
          >
            Brush
          </button>
          <button
            type="button"
            className={`rounded-lg border px-3 py-1.5 text-sm font-medium ${
              tool === "eraser"
                ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--ink)]"
                : "border-[var(--line)] bg-white text-[var(--muted)]"
            }`}
            onClick={() => setTool("eraser")}
          >
            Eraser
          </button>
          <button
            type="button"
            className="rounded-lg border border-[var(--line)] bg-white px-3 py-1.5 text-sm text-[var(--muted)] hover:bg-slate-50"
            onClick={clearMask}
          >
            Clear
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3 text-sm text-[var(--muted)]">
        <label className="flex items-center gap-2">
          Size
          <input
            type="range"
            min={8}
            max={80}
            value={brushSize}
            onChange={(e) => setBrushSize(Number(e.target.value))}
            className="w-36 accent-[var(--accent)]"
          />
          <span className="w-8 tabular-nums">{brushSize}</span>
        </label>
      </div>

      {loadError && (
        <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
          {loadError}
        </p>
      )}

      <div
        ref={wrapRef}
        className="relative overflow-hidden rounded-xl border border-[var(--line)] bg-slate-100"
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={mediaUrl(imageUrl)}
          alt="edit base"
          className="block w-full select-none"
          draggable={false}
        />
        <canvas
          ref={canvasRef}
          className={`absolute inset-0 h-full w-full touch-none ${
            tool === "eraser" ? "cursor-cell" : "cursor-crosshair"
          } ${ready ? "" : "pointer-events-none opacity-50"}`}
          onPointerDown={(e) => {
            e.currentTarget.setPointerCapture(e.pointerId);
            drawing.current = true;
            const p = pointerPos(e);
            last.current = p;
            paintAt(p.x, p.y, null);
          }}
          onPointerMove={(e) => {
            if (!drawing.current) return;
            const p = pointerPos(e);
            paintAt(p.x, p.y, last.current);
            last.current = p;
          }}
          onPointerUp={() => {
            drawing.current = false;
            last.current = null;
          }}
          onPointerLeave={() => {
            drawing.current = false;
            last.current = null;
          }}
        />
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={saving || !ready}
          onClick={handleSave}
          className="btn-primary"
        >
          {saving ? "Saving…" : "Save mask"}
        </button>
        <button type="button" disabled={saving} onClick={onCancel} className="btn-secondary">
          Cancel
        </button>
      </div>
    </div>
  );
}
