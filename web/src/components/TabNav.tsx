"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { TABS } from "@/lib/characters";

export function TabNav() {
  const pathname = usePathname();

  return (
    <nav className="tab-list mb-6 flex gap-0.5 overflow-x-auto" aria-label="Sections">
      {TABS.map((tab) => (
        <Link
          key={tab.key}
          href={tab.href}
          className="tab"
          aria-selected={pathname === tab.href}
          role="tab"
        >
          <span aria-hidden>{tab.icon}</span> {tab.label}
        </Link>
      ))}
    </nav>
  );
}
