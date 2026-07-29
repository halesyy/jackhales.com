import { ArrowUpRight, Mail } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/router";
import type { ReactNode } from "react";

import { Reveal } from "./Motion";
import { SubscribeCard } from "./SubscribeCard";

type siteShellProps = {
  children: ReactNode;
};

export function SiteShell({ children }: siteShellProps) {
  const router = useRouter();
  const navigation = [
    { href: "/", label: "Home" },
    { href: "/articles", label: "Writing" },
    { href: "/background-and-experience", label: "Experience" },
  ];

  return (
    <div className="site-frame min-h-screen overflow-hidden">
      <div className="ambient ambient-left" />
      <div className="ambient ambient-right" />
      <header className="relative z-20 mx-auto w-full max-w-6xl px-5 pt-5 sm:px-8 sm:pt-8">
        <div className="site-nav">
          <Link href="/" className="brand-lockup" aria-label="Jack Hales home">
            <Image src="/jack-hales-picture-harbour.jpg" width={56} height={56} className="brand-avatar" alt="Jack Hales at Sydney Harbour" priority />
            <span>
              <strong>Jack Hales</strong>
              <small>AI engineer · Australia</small>
            </span>
          </Link>

          <nav className="nav-links" aria-label="Primary navigation">
            {navigation.map((item) => {
              const active = item.href === "/" ? router.pathname === "/" : item.href === "/articles" ? router.pathname.startsWith("/article") : router.pathname.startsWith(item.href);
              return (
                <Link key={item.href} href={item.href} className={active ? "nav-link active" : "nav-link"}>
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <a className="button button-dark nav-contact" href="mailto:me@jackhales.com">
            <Mail size={16} /> Let&apos;s talk
          </a>
        </div>
      </header>

      <main className="relative z-10 mx-auto w-full max-w-6xl px-5 pb-20 pt-10 sm:px-8 sm:pt-14">{children}</main>

      <footer className="relative z-10 mx-auto w-full max-w-6xl px-5 pb-8 sm:px-8">
        <Reveal>
          <SubscribeCard />
        </Reveal>
        <Reveal>
          <div className="footer-card">
            <div>
              <p className="eyebrow">Have a thoughtful problem?</p>
              <h2>Let&apos;s build something useful.</h2>
            </div>
            <div className="footer-actions">
              <a href="mailto:me@jackhales.com" className="button button-light">
                me@jackhales.com <ArrowUpRight size={16} />
              </a>
              <span>Australia</span>
            </div>
          </div>
        </Reveal>
        <div className="footer-meta">
          <span>© {new Date().getFullYear()} Jack Hales</span>
          <div className="footer-links">
            <a href="https://dataology.com.au" target="_blank" rel="noreferrer">
              Dataology <ArrowUpRight size={13} />
            </a>
            <a href="https://pharmaportal.com.au" target="_blank" rel="noreferrer">
              Pharma Portal <ArrowUpRight size={13} />
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
