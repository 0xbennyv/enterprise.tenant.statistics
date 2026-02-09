"use client";

import { useState } from "react";
import DatePicker from "react-datepicker";
import { toast } from "react-toastify";
import "react-datepicker/dist/react-datepicker.css";

type DatePickerCardProps = {
  onSuccess?: () => void;
};

const DatePickerCard = ({ onSuccess }: DatePickerCardProps) => {
  const [startDate, setStartDate] = useState<Date | null>(null);
  const [endDate, setEndDate] = useState<Date | null>(null);
  const [tenantId, setTenantId] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);

  const formatDate = (date: Date | null): string | null => {
    if (!date) return null;
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  };

  const handleStartDateChange = (date: Date | null) => {
    setStartDate(date);
    // If end date is before the new start date, reset end date
    if (date && endDate && endDate < date) {
      setEndDate(null);
    }
  };

  const handleEndDateChange = (date: Date | null) => {
    setEndDate(date);
  };

  const handleSubmit = async () => {
    if (!startDate || !endDate) {
      toast.error("Please select both start date and end date");
      return;
    }

    // Validate that end date is not before start date
    if (endDate < startDate) {
      toast.error("End date cannot be before start date");
      return;
    }

    setIsLoading(true);

    try {
      const formattedStartDate = formatDate(startDate);
      const formattedEndDate = formatDate(endDate);

      const requestBody: { date_from: string; date_to: string; tenant_id?: string } = {
        date_from: formattedStartDate!,
        date_to: formattedEndDate!,
      };

      if (tenantId.trim()) {
        requestBody.tenant_id = tenantId.trim();
      }

      const response = await fetch("/api/telemetry", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to submit request");
      }

      // Clear date values on successful submission
      setStartDate(null);
      setEndDate(null);
      setTenantId("");
      toast.success("Request submitted successfully!");

      // Call GET request to fetch updated telemetry data
      try {
        await fetch("/api/telemetry", {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
          },
        });
      } catch (fetchError) {
        console.error("Error fetching telemetry data after submit:", fetchError);
      }

      // Refresh table data if callback provided
      if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div>
      <div className="flex items-end gap-x-4 p-6">
        <div className="input flex-1">
          <label htmlFor="start-date">
            Start Date
          </label>
          <div className="input-inner">
            <DatePicker
              id="start-date"
              selected={startDate}
              onChange={handleStartDateChange}
              dateFormat="yyyy-MM-dd"
              placeholderText="Select start date"
              className="w-full border-0 outline-none bg-transparent"
              wrapperClassName="w-full"
            />
          </div>
        </div>
        <div className="input">
          <label htmlFor="end-date">
            End Date
          </label>
          <div className="input-inner">
            <DatePicker
              id="end-date"
              selected={endDate}
              onChange={handleEndDateChange}
              minDate={startDate || undefined}
              dateFormat="yyyy-MM-dd"
              placeholderText="Select end date"
              className="w-full border-0 outline-none bg-transparent"
              wrapperClassName="w-full"
            />
          </div>
        </div>
        <div className="input flex-1">
          <label htmlFor="tenant-id">
            Tenant ID
          </label>
          <div className="input-inner">
            <input
              id="tenant-id"
              type="text"
              value={tenantId}
              onChange={(e) => setTenantId(e.target.value)}
              placeholder="Enter tenant ID (optional)"
              className="w-full border-0 outline-none bg-transparent"
              aria-label="Tenant ID (optional)"
            />
          </div>
        </div>
        <div className="mt-2">
          <button
            onClick={handleSubmit}
            disabled={isLoading || !startDate || !endDate || (startDate && endDate && endDate < startDate)}
            className="px-4 py-2 bg-sophos-blue text-white rounded-md font-medium hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            aria-label="Submit date range"
          >
            {isLoading ? "Submitting..." : "Submit"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default DatePickerCard;
