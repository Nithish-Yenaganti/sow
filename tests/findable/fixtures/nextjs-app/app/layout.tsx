import type { Metadata } from "next";

export const metadata: Metadata = {
  metadataBase: new URL("https://acme.test"),
  title: "Acme — widgets for teams",
  description: "Acme makes widgets for teams of every size.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body><nav><a href="/pricing">Pricing</a> <a href="/features">Features</a></nav>{children}</body></html>;
}
