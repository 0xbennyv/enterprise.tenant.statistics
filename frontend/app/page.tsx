"use client";

import { useState, useEffect } from "react";
import DatePickerCard from "./components/DatePickerCard";
import DataTable from "./components/DataTable";

type TelemetryExport = {
  id: number;
  job_id: string;
  date_from: string;
  date_to: string;
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
  createdAt: string;
  status: string;
  downloadUrl?: string;
};

const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  const options: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  };
  return date.toLocaleString("en-US", options);
};

export default function Home() {
  const [tableData, setTableData] = useState<TableData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
          createdAt: formatDate(item.created_at),
          status: item.status,
          downloadUrl: item.file_path || undefined,
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
    <div className="bg-white rounded-md w-full pb-10">
      <h2 className=" text-h4 text-sophos-blue border-b border-gray-200 pb-4 px-6 pt-5">Select Date Range</h2>
      <div className="card-container bg-gray-50 border-gray-200 border rounded-md mx-6 mt-5">
        <DatePickerCard onSuccess={fetchTelemetryData} />
      </div>
      <div className="card-container bg-gray-50 border-gray-200 border rounded-md mx-6 mt-5">
        <div className="input">
          <label className="px-6 pt-6 pb-1">Tenant Queue</label>
          <div className="px-6 pb-6">
            {isLoading ? (
              <div className="text-center py-8 text-gray-500">Loading...</div>
            ) : error ? (
              <div className="text-center py-8 text-orange-500">{error}</div>
            ) : (
              <DataTable data={tableData} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
