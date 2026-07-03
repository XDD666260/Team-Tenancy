import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "重庆房价洞察 — 数据驱动决策",
  description:
    "基于 50,507 条真实二手房数据，提供房价预测、市场聚类、关联规则挖掘等深度分析",
  keywords: ["重庆", "房价", "二手房", "数据分析", "机器学习"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <head>
        {/* Roboto Mono — 等宽数字 */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@300;400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen bg-bg-dark text-white antialiased">
        {children}
      </body>
    </html>
  );
}
