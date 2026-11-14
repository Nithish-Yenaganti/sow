import posthog from "posthog-js";

posthog.init("phc_test", { api_host: "https://us.i.posthog.com" });

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html>
      <head>
        <link href="https://fonts.googleapis.com/css2?family=Inter" rel="stylesheet" />
      </head>
      <body>{children}</body>
    </html>
  );
}
