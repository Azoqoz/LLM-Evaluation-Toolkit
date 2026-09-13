import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "EVALROOM — AI Response Review System",
  description: "A considered review desk for AI responses. Inspect quality, compare evidence, and understand every verdict.",
};
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
