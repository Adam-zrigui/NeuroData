import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NeuroData Finder",
  description: "Search public neuroscience datasets with evidence for every match.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
