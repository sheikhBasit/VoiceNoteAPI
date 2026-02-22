import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import Providers from "./providers";
import { ErrorBoundary } from "@/components/ErrorBoundary";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "VoiceNote AI Admin Dashboard",
  description: "Advanced management portal for VoiceNote AI",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <ErrorBoundary>
          <Providers>
            <DashboardLayout>{children}</DashboardLayout>
          </Providers>
        </ErrorBoundary>
      </body>
    </html>
  );
}
