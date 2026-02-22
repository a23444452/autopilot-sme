import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AppShell } from "./app-shell";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AutoPilot SME",
  description: "AI-powered manufacturing scheduling automation",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-TW">
      <body className={inter.className}>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
