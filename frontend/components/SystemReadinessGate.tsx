"use client";

import { useEffect, useState } from "react";

import BrandMark from "@/components/BrandMark";
import { activateModel, getModelStatus, getModels } from "@/lib/api";

const POLL_MS = 2500;
const STORAGE_KEY = "aes_segmentation_model";

/**
 * Startup gate: spinner + instruction while backend warms Grounded SAM.
 * Prefer waiting for server-side warmup; only call activate if still needed.
 */
export default function SystemReadinessGate({
  children,
}: {
  children: React.ReactNode;
}) {
  const [ready, setReady] = useState(false);
  const [phase, setPhase] = useState<"connecting" | "loading">("connecting");

  useEffect(() => {
    let cancelled = false;
    let requestedActivate = false;

    async function boot() {
      while (!cancelled) {
        try {
          const [status, mods] = await Promise.all([getModelStatus(), getModels()]);
          if (cancelled) return;

          const saved =
            typeof window !== "undefined"
              ? window.localStorage.getItem(STORAGE_KEY)
              : null;
          const preferred =
            (saved && mods.models.find((m) => m.key === saved && m.available)) ||
            mods.models.find((m) => m.active && m.available) ||
            mods.models.find((m) => m.default && m.available) ||
            mods.models.find((m) => m.available);

          if (!preferred) {
            setPhase("connecting");
            void status;
            await new Promise((r) => setTimeout(r, POLL_MS));
            continue;
          }

          const loaded =
            preferred.loaded === true ||
            (mods.active === preferred.key &&
              mods.models.find((m) => m.key === preferred.key)?.loaded === true);

          if (loaded) {
            if (typeof window !== "undefined") {
              window.localStorage.setItem(STORAGE_KEY, preferred.key);
            }
            setReady(true);
            return;
          }

          setPhase("loading");

          // Backend usually warms on startup — only trigger activate once as fallback.
          if (!requestedActivate) {
            requestedActivate = true;
            void activateModel(preferred.key)
              .then(() => {
                if (typeof window !== "undefined") {
                  window.localStorage.setItem(STORAGE_KEY, preferred.key);
                }
              })
              .catch(() => {
                requestedActivate = false;
              });
          }

          await new Promise((r) => setTimeout(r, POLL_MS));
        } catch {
          if (cancelled) return;
          setPhase("connecting");
          requestedActivate = false;
          await new Promise((r) => setTimeout(r, POLL_MS));
        }
      }
    }

    void boot();
    return () => {
      cancelled = true;
    };
  }, []);

  if (ready) {
    return <>{children}</>;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[var(--bg)]/80 backdrop-blur-sm">
      <div className="mx-4 flex max-w-sm flex-col items-center gap-4 text-center">
        <BrandMark
          variant="header"
          className="mb-1 h-20 w-auto max-w-[220px] object-contain"
        />
        <div
          className="h-12 w-12 animate-spin rounded-full border-[3px] border-[var(--line)] border-t-[var(--accent)]"
          role="status"
          aria-label="Loading model"
        />
        <div className="space-y-2">
          <p className="text-base font-semibold text-[var(--ink)]">
            {phase === "connecting" ? "Connecting to server…" : "Model is loading…"}
          </p>
          <p className="text-sm leading-relaxed text-[var(--muted)]">
            {phase === "connecting"
              ? "Waiting for the backend to become ready."
              : "Detection model is loading into memory. This can take a few minutes the first time — please wait."}
          </p>
        </div>
      </div>
    </div>
  );
}
