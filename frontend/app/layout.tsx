import "./globals.css";
import { ReactNode } from "react";

export const metadata = {
  title: "P&ID Digitization",
  description: "Upload and process P&ID diagrams",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}


