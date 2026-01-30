"use client";

import { useState } from "react";
import { toast } from "react-toastify";

type TableData = {
  jobId: string;
  createdAt: string;
  status: string;
  downloadUrl?: string;
};

type SortConfig = {
  key: keyof TableData | null;
  direction: "asc" | "desc";
};

type DataTableProps = {
  data: TableData[];
};

const DataTable = ({ data }: DataTableProps) => {
  const [sortConfig, setSortConfig] = useState<SortConfig>({
    key: null,
    direction: "asc",
  });
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 10;

  const handleSort = (key: keyof TableData) => {
    let direction: "asc" | "desc" = "asc";
    if (sortConfig.key === key && sortConfig.direction === "asc") {
      direction = "desc";
    }
    setSortConfig({ key, direction });
    // Reset to first page when sorting changes
    setCurrentPage(1);
  };

  const sortedData = [...data].sort((a, b) => {
    if (!sortConfig.key) return 0;

    let aValue: any = a[sortConfig.key];
    let bValue: any = b[sortConfig.key];

    if (aValue === undefined || bValue === undefined) return 0;

    // Handle date strings for createdAt column
    if (sortConfig.key === "createdAt") {
      const aDate = new Date(aValue).getTime();
      const bDate = new Date(bValue).getTime();
      if (sortConfig.direction === "asc") {
        return aDate - bDate;
      } else {
        return bDate - aDate;
      }
    }

    // Handle string comparison for other columns
    if (sortConfig.direction === "asc") {
      return aValue > bValue ? 1 : -1;
    } else {
      return aValue < bValue ? 1 : -1;
    }
  });

  const handleDownload = async (jobId: string) => {
    try {
      // URL encode the jobId to handle special characters
      const job_id = encodeURIComponent(jobId);
      // Call the API route instead of directly calling the backend
      const response = await fetch(`/api/telemetry/${job_id}/download`, {
        method: "GET",
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || "Failed to download file");
      }

      // Get the blob from the response
      const blob = await response.blob();

      // Get filename from Content-Disposition header or use default
      const contentDisposition = response.headers.get("content-disposition");
      let filename = `export-${jobId}.xlsx`;
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename=["']?([^"';]+)["']?/i);
        if (filenameMatch) {
          // Remove trailing underscores from file extension (e.g., .xlsx_ -> .xlsx)
          filename = filenameMatch[1].trim().replace(/(\.[a-zA-Z0-9]+)_+$/i, '$1');
        }
      }

      // Create a temporary URL for the blob
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();

      // Cleanup
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Download error:", error);
      toast.error(error instanceof Error ? error.message : "Failed to download file");
    }
  };

  const getStatusBadgeClass = (status: string) => {
    const statusLower = status.toLowerCase();
    switch (statusLower) {
      case "running":
        return "bg-green-500 text-white";
      case "pending":
        return "bg-orange-300 text-white";
      case "completed":
      case "done":
        return "bg-blue-200 text-white";
      case "failed":
      case "error":
        return "bg-red-500 text-white";
      default:
        return "bg-gray-400 text-white";
    }
  };

  const formatStatus = (status: string) => {
    const statusLower = status.toLowerCase();
    switch (statusLower) {
      case "running":
        return "Running";
      case "done":
        return "Completed";
      case "error":
        return "Failed";
      default:
        return status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();
    }
  };

  const isCompleted = (status: string): boolean => {
    const statusLower = status.toLowerCase();
    return statusLower === "completed" || statusLower === "done";
  };

  // Calculate pagination
  const totalPages = Math.ceil(sortedData.length / rowsPerPage);
  const startIndex = (currentPage - 1) * rowsPerPage;
  const endIndex = startIndex + rowsPerPage;
  const paginatedData = sortedData.slice(startIndex, endIndex);

  const handlePageChange = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
    }
  };

  // Generate page numbers to display
  const getPageNumbers = () => {
    const pages = [];
    const maxVisiblePages = 5;

    if (totalPages <= maxVisiblePages) {
      // Show all pages if total is less than max visible
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      // Show first page, last page, and pages around current
      if (currentPage <= 3) {
        // Near the start
        for (let i = 1; i <= 4; i++) {
          pages.push(i);
        }
        pages.push(-1); // Ellipsis
        pages.push(totalPages);
      } else if (currentPage >= totalPages - 2) {
        // Near the end
        pages.push(1);
        pages.push(-1); // Ellipsis
        for (let i = totalPages - 3; i <= totalPages; i++) {
          pages.push(i);
        }
      } else {
        // In the middle
        pages.push(1);
        pages.push(-1); // Ellipsis
        for (let i = currentPage - 1; i <= currentPage + 1; i++) {
          pages.push(i);
        }
        pages.push(-1); // Ellipsis
        pages.push(totalPages);
      }
    }

    return pages;
  };

  return (
    <div className="data-table w-full overflow-x-auto">
      <table className="w-full border-collapse">
        <thead>
          <tr className="border-b border-gray-200">
            <th
              className="text-left py-3 px-6 text-list font-semibold text-gray-900 cursor-pointer hover:bg-gray-50"
              onClick={() => handleSort("jobId")}
            >
              <div className="flex items-center gap-2">
                Job Id
                <div className="flex flex-col">
                  <svg
                    className={`w-3 h-3 ${sortConfig.key === "jobId" && sortConfig.direction === "asc"
                      ? "text-sophos-blue"
                      : "text-gray-400"
                      }`}
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path d="M5 12l5-5 5 5H5z" />
                  </svg>
                  <svg
                    className={`w-3 h-3 -mt-1 ${sortConfig.key === "jobId" && sortConfig.direction === "desc"
                      ? "text-sophos-blue"
                      : "text-gray-400"
                      }`}
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path d="M5 8l5 5 5-5H5z" />
                  </svg>
                </div>
              </div>
            </th>
            <th
              className="text-left py-3 px-6 text-list font-semibold text-gray-900 cursor-pointer hover:bg-gray-50"
              onClick={() => handleSort("createdAt")}
            >
              <div className="flex items-center gap-2">
                Created At
                <div className="flex flex-col">
                  <svg
                    className={`w-3 h-3 ${sortConfig.key === "createdAt" && sortConfig.direction === "asc"
                      ? "text-sophos-blue"
                      : "text-gray-400"
                      }`}
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path d="M5 12l5-5 5 5H5z" />
                  </svg>
                  <svg
                    className={`w-3 h-3 -mt-1 ${sortConfig.key === "createdAt" && sortConfig.direction === "desc"
                      ? "text-sophos-blue"
                      : "text-gray-400"
                      }`}
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path d="M5 8l5 5 5-5H5z" />
                  </svg>
                </div>
              </div>
            </th>
            <th
              className="text-left py-3 px-6 text-list font-semibold text-gray-900 cursor-pointer hover:bg-gray-50"
              onClick={() => handleSort("status")}
            >
              <div className="flex items-center gap-2">
                Status
                <div className="flex flex-col">
                  <svg
                    className={`w-3 h-3 ${sortConfig.key === "status" && sortConfig.direction === "asc"
                      ? "text-sophos-blue"
                      : "text-gray-400"
                      }`}
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path d="M5 12l5-5 5 5H5z" />
                  </svg>
                  <svg
                    className={`w-3 h-3 -mt-1 ${sortConfig.key === "status" && sortConfig.direction === "desc"
                      ? "text-sophos-blue"
                      : "text-gray-400"
                      }`}
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path d="M5 8l5 5 5-5H5z" />
                  </svg>
                </div>
              </div>
            </th>
            <th className="text-left py-3 px-6 text-list font-semibold text-gray-900">
              Action
            </th>
          </tr>
        </thead>
        <tbody>
          {paginatedData.length === 0 ? (
            <tr>
              <td colSpan={4} className="text-center py-8 text-gray-500">
                No data available
              </td>
            </tr>
          ) : (
            paginatedData.map((row, index) => (
              <tr
                key={row.jobId}
                className="border-b border-gray-200 hover:bg-gray-50 transition-colors"
              >
                <td className="py-4 px-6">{row.jobId}</td>
                <td className="py-4 px-6 ">{row.createdAt}</td>
                <td className="py-4 px-6">
                  <span
                    className={`inline-block px-3 py-1 rounded-full text-ps font-semibold ${getStatusBadgeClass(
                      row.status
                    )}`}
                  >
                    {formatStatus(row.status)}
                  </span>
                </td>
                <td className="py-4 px-6">
                  <button
                    onClick={() => handleDownload(row.jobId)}
                    disabled={!isCompleted(row.status)}
                    className={`font-medium text-list transition-colors ${isCompleted(row.status)
                      ? "text-sophos-blue hover:text-blue-600 cursor-pointer"
                      : "text-gray-400 cursor-not-allowed opacity-50"
                      }`}
                    aria-label={`Download ${row.jobId}`}
                  >
                    Download
                  </button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>

      {/* Pagination Controls */}
      {sortedData.length > 0 && (
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200">
          <div className="text-sm text-gray-600">
            Showing {startIndex + 1} to {Math.min(endIndex, sortedData.length)} of {sortedData.length} entries
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage === 1}
              className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-200 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              aria-label="Previous page"
            >
              Previous
            </button>

            <div className="flex items-center gap-1">
              {getPageNumbers().map((page, index) => {
                if (page === -1) {
                  return (
                    <span key={`ellipsis-${index}`} className="px-2 text-gray-500">
                      ...
                    </span>
                  );
                }
                return (
                  <button
                    key={page}
                    onClick={() => handlePageChange(page)}
                    className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${currentPage === page
                      ? "bg-sophos-blue text-white"
                      : "text-gray-700 bg-white border border-gray-200 hover:bg-gray-50"
                      }`}
                    aria-label={`Go to page ${page}`}
                    aria-current={currentPage === page ? "page" : undefined}
                  >
                    {page}
                  </button>
                );
              })}
            </div>

            <button
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
              className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-200 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              aria-label="Next page"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default DataTable;
