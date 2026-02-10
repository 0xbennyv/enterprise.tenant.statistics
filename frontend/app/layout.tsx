import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./styles/components.css";
import "./styles/globals.css";
import Navbar from "./components/Navbar";
import Toast from "./components/Toast";
import Header from "./components/Header";
import { SidebarProvider } from "./contexts/SidebarContext";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Enterprise Tenant Statistics",
  description: "View tenant statistics for your enterprise",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.className} antialiased`}>
        <SidebarProvider>
          <Navbar />
          <Header />
          <div className="my-5">
            {children}
          </div>
          <Toast />
        </SidebarProvider>
      </body>
    </html>
  );
}
