import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DesignAdvisor · 27-设计",
  description:
    "27-设计-Design Level 行业 Web 项目 · 设计资产库 / 评审 / AI 草稿",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
