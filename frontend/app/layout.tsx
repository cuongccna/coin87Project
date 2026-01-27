import "./globals.css";
import { Metadata, Viewport } from "next";
import { ServiceWorkerRegister } from "../components/ServiceWorkerRegister";

export const metadata: Metadata = {
  title: "Coin87",
  description: "Information Reliability Interface. On Information, Trust, and Silence.",
  manifest: "/manifest.json",
  icons: {
    icon: "/icon-192.png", // Start with 192, browser picks best
    apple: "/icon-192.png", 
  },
};

export const viewport: Viewport = {
  themeColor: "#09090b",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false, // App-like feel
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-background text-primary antialiased selection:bg-surface_highlight">
        <ServiceWorkerRegister />
        {children}
      </body>
    </html>
  );
}

