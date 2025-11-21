"use client";

import "./globals.css";
import { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ToastProvider } from "./components/ToastProvider";

function TopNav() {
  const pathname = usePathname();
  const links = [
    { href: "/", label: "Home" },
    { href: "/console", label: "Console" },
    { href: "/settings", label: "Settings" },
  ];
  return (
    <nav className="mt-6 flex flex-wrap items-center gap-2 text-fluid-sm font-medium">
      {links.map((link) => {
        const active = pathname === link.href;
        return (
          <Link
            key={link.href}
            href={link.href}
            className={`rounded-full border px-4 py-2 transition-all duration-200 focus-ring ${
              active
                ? "border-cyan-400/70 bg-cyan-500/15 text-cyan-100 font-semibold"
                : "border-slate-800 text-slate-200 hover:border-cyan-400/40 hover:bg-slate-800/50"
            }`}
            aria-current={active ? "page" : undefined}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-950 text-slate-100 min-h-screen">
        <ToastProvider>
          <div className="container-fluid py-8">
            <header className="mb-8">
              <h1 className="text-fluid-3xl font-bold text-primary mb-3">
                Cognitive Load Estimator (Python) UI
              </h1>
              <p className="text-fluid-lg text-secondary mb-4 leading-relaxed">
                Real-time load state, EMA prompt handling, and hook status.
              </p>
              <TopNav />
            </header>
            {children}
          </div>
        </ToastProvider>
      </body>
    </html>
  );
}
