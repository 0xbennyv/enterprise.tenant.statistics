import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./styles/components.css";
import "./styles/globals.css";
import Navbar from "./components/Navbar";
import Toast from "./components/Toast";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Telemetry Statistics",
  description: "View telemetry statistics for your tenants",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.className} antialiased`}>
        <Navbar />
        <div className="bg-white p-5">
          <h2 className="text-h3">Tenant Statistics</h2>
        </div>
        <div className="my-5 mx-8">
          {children}
        </div>
        <Toast />
      </body>
    </html>
  );
}
