"use client";

import { useRouter } from "next/navigation";
import { useCallback, useState } from "react";

import { uploadImage } from "@/lib/api";
import type { IngestWarning } from "@/lib/types";

export default function UploadDropzone() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<IngestWarning[]>([]);

  const handleFile = useCallback(
    async (file: File) => {
      setBusy(true);
      setError(null);
      setWarnings([]);
      try {
        const res = await uploadImage(file);
        setWarnings(res.warnings);
        router.push(`/studio/${res.project.id}`);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Upload failed");
        setBusy(false);
      }
    },
    [router]
  );

  return (
    <div>
      <label
        className="flex h-52 cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-[var(--line)] bg-slate-50 transition hover:border-[var(--accent)] hover:bg-[var(--accent-soft)]/40"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          const f = e.dataTransfer.files?.[0];
          if (f) void handleFile(f);
        }}
      >
        <span className="text-sm font-medium text-[var(--ink)]">
          {busy ? "Uploading & validating…" : "Drop a house photo or click to browse"}
        </span>
        <span className="mt-1 text-xs text-[var(--muted)]">JPEG / PNG / WebP · up to 20 MB</span>
        <input
          type="file"
          accept="image/*"
          className="hidden"
          disabled={busy}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void handleFile(f);
          }}
        />
      </label>

      {error && (
        <p className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </p>
      )}

      {warnings.length > 0 && (
        <ul className="mt-4 space-y-2">
          {warnings.map((w) => (
            <li
              key={w.code}
              className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-900"
            >
              {w.message}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
