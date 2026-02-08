"use client";

import { useSidebar } from "../contexts/SidebarContext";

const Header = () => {
  const { isCollapsed } = useSidebar();

  return (
    <div className={`bg-white p-5 transition-all duration-300 ${isCollapsed ? "pl-20" : "pl-72"}`}>
      <h2 className="text-h3">Tenant Statistics</h2>
    </div>
  );
};

export default Header;
