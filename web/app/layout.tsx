import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Synthetic ESG Runs",
  description: "Reusable run dashboard for the synthetic ESG generator.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
