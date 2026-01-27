import "../styles/globals.css";
import { AppShell } from "../components/layout/AppShell";

export const metadata = {
  title: "coin87 — IC Decision Risk",
  description: "Read-only IC dashboard for decision hygiene and governance.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}

