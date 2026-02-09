"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSidebar } from "../contexts/SidebarContext";

type NavItem = "tenants" | "exports";

type SideNavProps = {
  activeItem?: NavItem;
};

const SideNav = ({ activeItem }: SideNavProps) => {
  const { isCollapsed, toggleSidebar } = useSidebar();
  const pathname = usePathname();

  // Determine active item from pathname if not provided
  const currentActiveItem = activeItem || (pathname === "/tenants" ? "tenants" : pathname === "/exports" ? "exports" : "exports");

  return (
    <aside
      className={`bg-gray-800 text-gray-300 fixed left-0 top-12 h-[calc(100vh-3rem)] transition-all duration-300 ${isCollapsed ? "w-14" : "w-64"
        }`}
      aria-label="Sidebar navigation"
    >
      <div className="flex flex-col h-full">
        {/* Toggle Button */}
        <button
          onClick={toggleSidebar}
          className={`p-4 hover:bg-gray-700 transition-colors focus:outline-none ${isCollapsed ? "flex justify-center" : ""}`}
          aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          tabIndex={0}
        >
          <svg
            className={`w-5 h-5 transition-transform ${isCollapsed ? "rotate-180" : ""}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M11 19l-7-7 7-7m8 14l-7-7 7-7"
            />
          </svg>
        </button>

        {/* Menu Heading */}
        {!isCollapsed && (
          <div className="px-4 py-2">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-400">
              Menu
            </h2>
          </div>
        )}

        {/* Navigation Items */}
        <nav className="flex-1 px-2 py-2" aria-label="Main navigation">
          <ul className="space-y-1">
            <li>
              <Link
                href="/exports"
                className={`w-full flex items-center ${isCollapsed ? "justify-center px-0" : "gap-3 px-4"} py-3 rounded-md transition-colors focus:outline-none ${currentActiveItem === "exports"
                  ? "bg-blue-600 text-white"
                  : "text-gray-300 hover:bg-gray-700"
                  }`}
                aria-label="View Exports"
                aria-current={currentActiveItem === "exports" ? "page" : undefined}
                tabIndex={0}
              >
                <svg
                  className="w-5 h-5 shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                {!isCollapsed && (
                  <span className="text-sm font-medium">View Exports</span>
                )}
              </Link>
            </li>
            <li>
              <Link
                href="/tenants"
                className={`w-full flex items-center ${isCollapsed ? "justify-center px-0" : "gap-3 px-4"} py-3 rounded-md transition-colors focus:outline-none ${currentActiveItem === "tenants"
                  ? "bg-blue-600 text-white"
                  : "text-gray-300 hover:bg-gray-700"
                  }`}
                aria-label="View Tenants"
                aria-current={currentActiveItem === "tenants" ? "page" : undefined}
                tabIndex={0}
              >
                <svg
                  className="w-5 h-5 shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                  />
                </svg>
                {!isCollapsed && (
                  <span className="text-sm font-medium">View Tenants</span>
                )}
              </Link>
            </li>
          </ul>
        </nav>
      </div>
    </aside>
  );
};

export default SideNav;
