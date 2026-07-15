import BrandMark from "@/components/BrandMark";
import UploadDropzone from "@/components/UploadDropzone";

export default function HomePage() {
  return (
    <div className="grid gap-8 lg:grid-cols-[1.15fr_1fr]">
      <section className="glass p-8 sm:p-10">
        <BrandMark
          variant="header"
          className="mb-6 h-16 w-auto max-w-[280px] object-contain"
        />
        <p className="text-sm font-semibold uppercase tracking-wider text-[var(--accent)]">
          Exterior restyling
        </p>
        <h1 className="mt-3 text-3xl font-semibold leading-tight tracking-tight text-[var(--ink)] sm:text-4xl">
          Redesign your home&apos;s exterior
        </h1>
        <p className="mt-4 max-w-prose text-[var(--muted)]">
          Upload a facade photo, detect walls and openings, then apply cladding,
          tiles, patterns, or rich paint — all in one render.
        </p>

        <ol className="mt-8 space-y-3 text-sm text-[var(--ink)]">
          <li className="flex gap-3">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--accent-soft)] text-xs font-bold text-[var(--accent)]">
              1
            </span>
            Upload a clear exterior photo
          </li>
          <li className="flex gap-3">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--accent-soft)] text-xs font-bold text-[var(--accent)]">
              2
            </span>
            Detect elements and assign finishes
          </li>
          <li className="flex gap-3">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--accent-soft)] text-xs font-bold text-[var(--accent)]">
              3
            </span>
            Render the redesigned facade
          </li>
        </ol>
      </section>

      <section className="glass p-8">
        <h2 className="mb-4 text-lg font-semibold text-[var(--ink)]">Upload a photo</h2>
        <UploadDropzone />
      </section>
    </div>
  );
}
