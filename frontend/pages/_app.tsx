import type { AppProps } from "next/app";
import Script from "next/script";
import { useRouter } from "next/router";
import { useEffect } from "react";

import "../styles/globals.css";

const googleAnalyticsId = "G-JFRRFCHEMY";

declare global {
  interface Window {
    dataLayer: unknown[];
    gtag?: (...args: unknown[]) => void;
  }
}

export default function App({ Component, pageProps }: AppProps) {
  const router = useRouter();
  const analyticsEnabled = process.env.NODE_ENV === "production";

  useEffect(() => {
    if (!analyticsEnabled) return;

    function trackPageView(url: string) {
      window.gtag?.("config", googleAnalyticsId, { page_path: url });
    }

    router.events.on("routeChangeComplete", trackPageView);
    return () => router.events.off("routeChangeComplete", trackPageView);
  }, [analyticsEnabled, router.events]);

  return (
    <>
      <Component {...pageProps} />
      {analyticsEnabled ? (
        <>
          <Script src={`https://www.googletagmanager.com/gtag/js?id=${googleAnalyticsId}`} strategy="afterInteractive" />
          <Script id="google-analytics" strategy="afterInteractive">
            {`
              window.dataLayer = window.dataLayer || [];
              function gtag(){window.dataLayer.push(arguments);}
              window.gtag = gtag;
              gtag('js', new Date());
              gtag('config', '${googleAnalyticsId}');
            `}
          </Script>
        </>
      ) : null}
    </>
  );
}
