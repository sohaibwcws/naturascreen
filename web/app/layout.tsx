import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/shell/sidebar";
import { SafetyBanner } from "@/components/shell/safety-banner";

const sans = Inter({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });

export const metadata: Metadata = {
  title: "NaturaScreen — natural-compound screening against cancer",
  description:
    "NaturaScreen screens open natural compounds against cancer proteins and tumor neoantigens, ranks candidates as research hypotheses, and visualizes the predicted effect in real time. Not a treatment or cure.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const year = new Date().getFullYear();
  return (
    <html lang="en" className={`${sans.variable} ${mono.variable}`}>
      <body className="min-h-screen">
        <div className="flex min-h-screen">
          <Sidebar />
          <div className="flex min-h-screen flex-1 flex-col">
            <SafetyBanner />
            <main className="flex-1 px-5 py-6 sm:px-8 sm:py-8">{children}</main>
            <footer className="border-t border-base-700 px-5 py-4 text-center text-xs text-ink-faint sm:px-8">
              Created &amp; Developed By{" "}
              <a
                href="https://sohaib.com"
                target="_blank"
                rel="noopener noreferrer"
                className="text-ink-muted underline-offset-2 hover:text-accent hover:underline"
              >
                Sohaib Khan
              </a>{" "}
              &copy; {year}
            </footer>
          </div>
        </div>
      </body>
    </html>
  );
}
