import "./globals.css";
export const metadata = { title: "Ciaran Fitness Tracker", description: "Biometric Engine" };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (<html lang="en"><body className="antialiased">{children}</body></html>);
}
