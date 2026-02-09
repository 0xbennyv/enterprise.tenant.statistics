"use client";

import { useState, useEffect } from "react";
import SideNav from "../../components/SideNav";
import TenantsDataTable from "../../components/TenantsDataTable";
import { usePathname } from "next/navigation";
import { useSidebar } from "../../contexts/SidebarContext";

type Tenant = {
  id: string;
  showAs: string;
  name: string;
  dataRegion: string;
  status: string;
};

type TenantData = {
  id: string;
  showAs: string;
  name: string;
  dataRegion: string;
  status: string;
};

export default function TenantsPage() {
  const pathname = usePathname();
  const activeItem = pathname === "/tenants" ? "tenants" : "exports";
  const { isCollapsed } = useSidebar();
  const [tableData, setTableData] = useState<TenantData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTenantsData = async (showLoading = false) => {
    if (showLoading) {
      setIsLoading(true);
    }
    setError(null);
    try {
      const response = await fetch("/api/tenants");
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to fetch tenants data");
      }

      // Handle different response structures - could be array directly or wrapped in object
      let tenantsArray: Tenant[] = [];
      if (Array.isArray(data)) {
        tenantsArray = data;
      } else if (data && Array.isArray(data.tenants)) {
        tenantsArray = data.tenants;
      } else if (data && Array.isArray(data.data)) {
        tenantsArray = data.data;
      } else if (data && Array.isArray(data.items)) {
        tenantsArray = data.items;
      } else {
        console.error("Unexpected response format:", data);
        throw new Error("Invalid response format from API");
      }

      // Map API response to table data format
      const mappedData: TenantData[] = tenantsArray.map((item) => ({
        id: item.id,
        showAs: item.showAs,
        name: item.name,
        dataRegion: item.dataRegion,
        status: item.status,
      }));

      setTableData(mappedData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
      // Only clear data on initial load, not on polling errors
      if (showLoading) {
        setTableData([]);
      }
    } finally {
      if (showLoading) {
        setIsLoading(false);
      }
    }
  };

  useEffect(() => {
    // Initial fetch with loading state
    fetchTenantsData(true);

    // Set up polling every 1 hour (3600000 milliseconds)
    const intervalId = setInterval(() => {
      fetchTenantsData(false);
    }, 3600000);

    // Cleanup interval on component unmount
    return () => {
      clearInterval(intervalId);
    };
  }, []);

  return (
    <div className="flex min-h-screen px-8">
      <SideNav activeItem={activeItem} />
      <main className={`flex-1 min-h-screen transition-all duration-300 ${isCollapsed ? "ml-14" : "ml-64"}`}>
        <div className="bg-white rounded-md w-full pb-10">
          <h2 className="text-h4 text-sophos-blue border-b border-gray-200 pb-4 px-6 pt-5">View Tenants</h2>
          <div className="card-container bg-gray-50 border-gray-200 border rounded-md mx-6 mt-5">
            <div className="input">
              <label className="px-6 pt-6 pb-1">Tenants</label>
              <div className="px-6 pb-6">
                {isLoading ? (
                  <div className="text-center py-8 text-gray-500">Loading...</div>
                ) : error ? (
                  <div className="text-center py-8 text-orange-500">{error}</div>
                ) : (
                  <TenantsDataTable data={tableData} />
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
