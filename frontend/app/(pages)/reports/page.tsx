"use client";

import { useState, useEffect, Suspense } from "react";
import DatePickerCard from "../../components/DatePickerCard";
import DataTable from "../../components/DataTable";
import SideNav from "../../components/SideNav";
import { usePathname, useSearchParams } from "next/navigation";
import { useSidebar } from "../../contexts/SidebarContext";

type TelemetryExport = {
  id: number;
  job_id: string;
  date_from: string;
  date_to: string;
  tenant_id: string | null;
  status: string;
  progress: {
    stage: string;
    percent: number;
  };
  file_path: string | null;
  error: string | null;
  created_at: string;
};

type TableData = {
  jobId: string;
  tenantId?: string | null;
  createdAt: string;
  status: string;
  downloadUrl?: string;
  dateFrom?: string;
  dateTo?: string;
  rawDateFrom?: string;
  rawDateTo?: string;
  progress?: {
    stage: string;
    percent: number;
  };
};

const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  const options: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  };
  return date.toLocaleString("en-US", options);
};

/** Date only, e.g. "Feb 11, 2026" (no time). */
const formatDateOnly = (dateString: string): string => {
  const [y, m, d] = dateString.split("-").map(Number);
  const date = new Date(y, m - 1, d);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
};

function ReportsPageContent() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const activeItem = pathname === "/tenants" ? "tenants" : pathname === "/reports" ? "reports" : "reports";
  const { isCollapsed } = useSidebar();
  const [tableData, setTableData] = useState<TableData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Get tenant_id from URL search params
  const tenantIdFromUrl = searchParams.get("tenant_id") || undefined;

  const fetchTelemetryData = async (showLoading = false) => {
    if (showLoading) {
      setIsLoading(true);
    }
    setError(null);
    try {
      const response = await fetch("/api/telemetry");
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to fetch telemetry data");
      }

      // Map API response to table data format
      const mappedData: TableData[] = (data as TelemetryExport[]).map(
        (item) => ({
          jobId: item.job_id,
          tenantId: item.tenant_id || undefined,
          createdAt: formatDate(item.created_at),
          status: item.status,
          downloadUrl: item.file_path || undefined,
          dateFrom: item.date_from ? formatDateOnly(item.date_from) : undefined,
          dateTo: item.date_to ? formatDateOnly(item.date_to) : undefined,
          rawDateFrom: item.date_from ?? undefined,
          rawDateTo: item.date_to ?? undefined,
          progress: item.progress,
        })
      );

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
    fetchTelemetryData(true);

    // Set up polling every 1 minute (60000 milliseconds)
    const intervalId = setInterval(() => {
      fetchTelemetryData(false);
    }, 60000);

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
          <h2 className=" text-h4 text-sophos-blue border-b border-gray-200 pb-4 px-6 pt-5">Select Date Range</h2>
          <div className="card-container bg-gray-50 border-gray-200 border rounded-md mx-6 mt-5">
            <DatePickerCard onSuccess={fetchTelemetryData} initialTenantId={tenantIdFromUrl} />
          </div>
          <div className="card-container bg-gray-50 border-gray-200 border rounded-md mx-6 mt-5">
            <div className="input">
              <label className="px-6 pt-6 pb-1">Jobs Queue</label>
              <div className="px-6 pb-6">
                {isLoading ? (
                  <div className="text-center py-8 text-gray-500">Loading...</div>
                ) : error ? (
                  <div className="text-center py-8 text-orange-500">{error}</div>
                ) : (
                  <DataTable data={tableData} onDelete={fetchTelemetryData} onCancel={fetchTelemetryData} />
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default function ReportsPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen px-8">
        <SideNav activeItem="reports" />
        <main className="flex-1 min-h-screen transition-all duration-300 ml-64">
          <div className="bg-white rounded-md w-full pb-10">
            <div className="text-center py-8 text-gray-500">Loading...</div>
          </div>
        </main>
      </div>
    }>
      <ReportsPageContent />
    </Suspense>
  );
}
