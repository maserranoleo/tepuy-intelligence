import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tepuy Intelligence",
  description: "Latin America Energy Intelligence — Elevated Vantage",
};

const FONTS_HREF =
  "https://fonts.googleapis.com/css2" +
  "?family=Fraunces:opsz,wght@9..144,400;9..144,500" +
  "&family=Geist:wght@300;400;500" +
  "&family=Geist+Mono:wght@400;500" +
  "&display=swap";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin=""
        />
        <link rel="stylesheet" href={FONTS_HREF} />
      </head>
      <body>{children}</body>
    </html>
  );
}
