import type { Metadata } from "next";
import Link from "next/link";
import { Manrope } from "next/font/google";
import "./globals.css";

import BrandMark from "@/components/BrandMark";
import CostNavLink from "@/components/CostNavLink";
import SystemReadinessGate from "@/components/SystemReadinessGate";

const manrope = Manrope({
  subsets: ["latin"],
  variable: "--font-manrope",
  display: "swap",
});

export const metadata: Metadata = {
  title: "AI Exterior Studio",
  description: "Detect facade elements and restyle them with paint or textures.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={manrope.variable}>
      <body className="font-[family-name:var(--font-manrope)] antialiased">
        <header className="border-b border-[var(--line)] bg-white/90 backdrop-blur">
          <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-3.5">
            <Link href="/" className="flex shrink-0 items-center" aria-label="AI Exterior Studio home">
              <BrandMark variant="header" />
            </Link>
            <nav className="flex items-center gap-4 text-sm">
              <CostNavLink />
              <span className="hidden text-[var(--muted)] sm:inline">
                Detect · Finish · Render · Estimate
              </span>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-6 py-8 pb-16">
          <SystemReadinessGate>{children}</SystemReadinessGate>
        </main>
      </body>
    </html>
  );
}
