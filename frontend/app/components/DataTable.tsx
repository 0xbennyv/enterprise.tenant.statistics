"use client";

import { useState } from "react";
import { toast } from "react-toastify";
import { Tooltip } from "react-tooltip";
import ConfirmationModal from "./ConfirmationModal";

type TableData = {
  jobId: string;
  tenantId?: string | null;
  createdAt: string;
  status: string;
  downloadUrl?: string;
  dateFrom?: string;
  dateTo?: string;
};

type SortConfig = {
  key: keyof TableData | null;
  direction: "asc" | "desc";
};

type DataTableProps = {
  data: TableData[];
  onDelete?: () => void;
};

const DataTable = ({ data, onDelete }: DataTableProps) => {
  const [sortConfig, setSortConfig] = useState<SortConfig>({
    key: null,
    direction: "asc",
  });
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 10;
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [rowToDelete, setRowToDelete] = useState<TableData | null>(null);

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

    // Handle null/undefined values - treat as empty string for sorting
    if (aValue === undefined || aValue === null) aValue = "";
    if (bValue === undefined || bValue === null) bValue = "";

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

  const handleDownload = async (row: TableData) => {
    try {
      // Get backend URL from environment variable or use localhost for development
      const backendUrl = process.env.NEXT_PUBLIC_DOWNLOAD_URL;

      // Call the backend directly: http://localhost:5006/exports/{job_id}/download
      const endpoint = `${backendUrl}/exports/${encodeURIComponent(row.jobId)}/download`;

      const response = await fetch(endpoint, {
        method: "GET",
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || errorData.error || "Failed to download file");
      }

      // Get the blob from the response
      const blob = await response.blob();

      // Generate filename using date_from and date_to if available
      let filename = `export-${row.jobId}.xlsx`;
      if (row.dateFrom && row.dateTo) {
        // Format dates as YYYY-MM-DD for filename
        const dateFrom = row.dateFrom.replace(/-/g, '');
        const dateTo = row.dateTo.replace(/-/g, '');
        filename = `export_${dateFrom}_to_${dateTo}.xlsx`;
      }

      // Override with filename from Content-Disposition header if present
      const contentDisposition = response.headers.get("content-disposition");
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename=["']?([^"';]+)["']?/i);
        if (filenameMatch) {
          // Remove trailing underscores from file extension (e.g., .xlsx_ -> .xlsx)
          const headerFilename = filenameMatch[1].trim().replace(/(\.[a-zA-Z0-9]+)_+$/i, '$1');
          // Only use header filename if dates are not available
          if (!row.dateFrom || !row.dateTo) {
            filename = headerFilename;
          }
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

      toast.success("File downloaded successfully");
    } catch (error) {
      console.error("Download error:", error);
      toast.error(error instanceof Error ? error.message : "Failed to download file");
    }
  };

  const handleDeleteClick = (row: TableData) => {
    // Only allow deletion of completed, queued, or failed jobs
    if (!canDelete(row.status)) {
      toast.error("Only completed, queued, or failed jobs can be deleted");
      return;
    }
    setRowToDelete(row);
    setDeleteModalOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!rowToDelete) return;

    try {
      const response = await fetch(`/api/telemetry/${encodeURIComponent(rowToDelete.jobId)}`, {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || data.detail || "Failed to delete export");
      }

      toast.success("Job deleted successfully");

      // Refresh table data if callback provided
      if (onDelete) {
        onDelete();
      }

      // Close modal and reset state
      setDeleteModalOpen(false);
      setRowToDelete(null);
    } catch (error) {
      console.error("Delete error:", error);
      toast.error(error instanceof Error ? error.message : "Failed to delete export");
      setDeleteModalOpen(false);
      setRowToDelete(null);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteModalOpen(false);
    setRowToDelete(null);
  };

  const getStatusBadgeClass = (status: string) => {
    const statusLower = status.toLowerCase();
    switch (statusLower) {
      case "running":
        return "bg-blue-500 text-white";
      case "pending":
      case "queued":
        return "bg-gray-400 text-white";
      case "completed":
      case "done":
        return "bg-green-500 text-white";
      case "cancelled":
        return "bg-orange-500 text-white";
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

  const canDelete = (status: string): boolean => {
    const statusLower = status.toLowerCase();
    // Only allow deletion for completed, queued, or failed jobs
    // Explicitly exclude running jobs
    return (
      statusLower === "completed" ||
      statusLower === "done" ||
      statusLower === "queued" ||
      statusLower === "failed" ||
      statusLower === "error"
    );
  };

  const MAX_ID_LENGTH = 24;

  const truncateWithEllipsis = (
    value: string | null | undefined,
    maxLen: number
  ): { display: string; full: string } => {
    const str = value ?? "";
    if (str.length <= maxLen) return { display: str, full: str };
    return { display: str.slice(0, maxLen) + "...", full: str };
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
              onClick={() => handleSort("dateFrom")}
            >
              <div className="flex items-center gap-2">
                Date From
                <div className="flex flex-col">
                  <svg
                    className={`w-3 h-3 ${sortConfig.key === "dateFrom" && sortConfig.direction === "asc"
                      ? "text-sophos-blue"
                      : "text-gray-400"
                      }`}
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path d="M5 12l5-5 5 5H5z" />
                  </svg>
                  <svg
                    className={`w-3 h-3 -mt-1 ${sortConfig.key === "dateFrom" && sortConfig.direction === "desc"
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
              onClick={() => handleSort("dateTo")}
            >
              <div className="flex items-center gap-2">
                Date To
                <div className="flex flex-col">
                  <svg
                    className={`w-3 h-3 ${sortConfig.key === "dateTo" && sortConfig.direction === "asc"
                      ? "text-sophos-blue"
                      : "text-gray-400"
                      }`}
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path d="M5 12l5-5 5 5H5z" />
                  </svg>
                  <svg
                    className={`w-3 h-3 -mt-1 ${sortConfig.key === "dateTo" && sortConfig.direction === "desc"
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
              onClick={() => handleSort("tenantId")}
            >
              <div className="flex items-center gap-2">
                Tenant ID
                <div className="flex flex-col">
                  <svg
                    className={`w-3 h-3 ${sortConfig.key === "tenantId" && sortConfig.direction === "asc"
                      ? "text-sophos-blue"
                      : "text-gray-400"
                      }`}
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path d="M5 12l5-5 5 5H5z" />
                  </svg>
                  <svg
                    className={`w-3 h-3 -mt-1 ${sortConfig.key === "tenantId" && sortConfig.direction === "desc"
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
            <th className="text-center py-3 px-6 text-list font-semibold text-gray-900">
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
          {paginatedData.length === 0 ? (
            <tr>
              <td colSpan={6} className="text-center py-8 text-gray-500">
                No data available
              </td>
            </tr>
          ) : (
            paginatedData.map((row, index) => (
              <tr
                key={row.jobId}
                className="border-b border-gray-200 hover:bg-gray-50 transition-colors"
              >
                <td className="py-4 px-6">{row.dateFrom ?? "-"}</td>
                <td className="py-4 px-6">{row.dateTo ?? "-"}</td>
                <td className="py-4 px-6 max-w-48">
                  <span
                    className="block truncate"
                    {...((row.tenantId?.length ?? 0) > MAX_ID_LENGTH
                      ? {
                          "data-tooltip-id": "tenant-id-tooltip",
                          "data-tooltip-content": row.tenantId ?? "",
                        }
                      : {})}
                  >
                    {row.tenantId
                      ? truncateWithEllipsis(row.tenantId, MAX_ID_LENGTH).display
                      : "-"}
                  </span>
                </td>
                <td className="py-4 px-6 ">{row.createdAt} (UTC)</td>
                <td className="py-4 px-6">
                  <span
                    className={`inline-block px-3 py-1 rounded-full text-ps font-semibold ${getStatusBadgeClass(
                      row.status
                    )}`}
                  >
                    {formatStatus(row.status)}
                  </span>
                </td>
                <td className="py-4 px-6 text-center">
                  <div className="flex items-center justify-center gap-4">
                    <button
                      onClick={() => handleDownload(row)}
                      disabled={!isCompleted(row.status)}
                      className={`font-medium text-list transition-colors ${isCompleted(row.status)
                        ? "text-sophos-blue hover:text-blue-600 cursor-pointer"
                        : "text-gray-400 cursor-not-allowed opacity-50"
                        }`}
                      aria-label={`Download ${row.jobId}`}
                    >
                      Download
                    </button>
                    <button
                      onClick={() => handleDeleteClick(row)}
                      disabled={!canDelete(row.status)}
                      className={`font-medium text-list transition-colors ${!canDelete(row.status)
                        ? "text-gray-400 cursor-not-allowed opacity-50"
                        : "text-red-600 hover:text-red-700 cursor-pointer"
                        }`}
                      aria-label={`Delete ${row.jobId}`}
                    >
                      Delete
                    </button>
                  </div>
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

      <ConfirmationModal
        isOpen={deleteModalOpen}
        title="Delete Export Job"
        message={
          rowToDelete
            ? `Are you sure you want to delete export job ${rowToDelete.jobId}? This action cannot be undone.`
            : ""
        }
        confirmText="Delete"
        cancelText="Cancel"
        onConfirm={handleDeleteConfirm}
        onCancel={handleDeleteCancel}
      />

      <Tooltip id="tenant-id-tooltip" clickable />
    </div>
  );
};

export default DataTable;
