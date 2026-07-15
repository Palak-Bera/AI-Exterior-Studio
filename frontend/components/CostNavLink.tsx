"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

/** Cost nav link — returns to last studio page when coming from the header. */
export default function CostNavLink() {
  const pathname = usePathname();
  const [href, setHref] = useState("/cost");

  useEffect(() => {
    if (pathname?.startsWith("/studio/")) {
      try {
        sessionStorage.setItem("aes_last_studio", pathname);
      } catch {
        /* ignore */
      }
      setHref(`/cost?return=${encodeURIComponent(pathname)}`);
      return;
    }
    try {
      const last = sessionStorage.getItem("aes_last_studio");
      if (last?.startsWith("/studio/")) {
        setHref(`/cost?return=${encodeURIComponent(last)}`);
        return;
      }
    } catch {
      /* ignore */
    }
    setHref("/cost");
  }, [pathname]);

  return (
    <Link href={href} className="font-medium text-[var(--ink)] hover:text-[var(--accent)]">
      Cost
    </Link>
  );
}
