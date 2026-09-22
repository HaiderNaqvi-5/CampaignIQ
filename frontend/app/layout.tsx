import type { Metadata } from "next";
import "./globals.css";
import { GoogleProvider } from "@/components/auth/google-provider";

export const metadata: Metadata = {
  title: "CampaignIQ — Grounded campaign outreach",
  description: "Create personalized, website-grounded campaign emails.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900">
        <GoogleProvider>{children}</GoogleProvider>
      </body>
    </html>
  );
}
