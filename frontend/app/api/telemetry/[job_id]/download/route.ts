import { NextRequest, NextResponse } from "next/server";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ job_id: string }> }
) {
  try {
    const { job_id } = await params;

    if (!job_id) {
      return NextResponse.json(
        { error: "Job ID is required" },
        { status: 400 }
      );
    }

    // Decode the job_id in case it was URL encoded
    const decodedJobId = decodeURIComponent(job_id);

    // Get backend URL from environment variable
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
    const endpoint = `${backendUrl}/exports/${decodedJobId}/download`;

    // Forward the GET request to the external endpoint
    const response = await fetch(endpoint, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: errorData.error || "Failed to download file" },
        { status: response.status }
      );
    }

    // Get the file data
    const blob = await response.blob();
    const contentType = response.headers.get("content-type") || "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
    let contentDisposition = response.headers.get("content-disposition") || `attachment; filename=export-${decodedJobId}.xlsx`;

    // Remove trailing underscores from file extension (e.g., .xlsx_ -> .xlsx)
    contentDisposition = contentDisposition.replace(/filename=["']?([^"';]+)["']?/i, (match, filename) => {
      // Remove trailing underscores from file extension (matches .xlsx_, .xlsx__, etc.)
      const cleanedFilename = filename.trim().replace(/(\.[a-zA-Z0-9]+)_+$/i, '$1');
      return `filename="${cleanedFilename}"`;
    });

    // Return the file as a response
    return new NextResponse(blob, {
      status: 200,
      headers: {
        "Content-Type": contentType,
        "Content-Disposition": contentDisposition,
      },
    });
  } catch (error) {
    console.error("Error in download API route:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
