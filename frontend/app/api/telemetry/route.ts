import { NextRequest, NextResponse } from "next/server";

export async function GET() {
  try {
    // Get backend URL from environment variable
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
    const endpoint = `${backendUrl}/exports`;

    // Forward the GET request to the external endpoint
    const response = await fetch(endpoint, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    const data = await response.json();

    
    if (!response.ok) {
      return NextResponse.json(
        { error: data.error || "Failed to fetch telemetry data" },
        { status: response.status }
      );
    }

    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("Error in telemetry GET API route:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { date_from, date_to, tenant_id } = body;


    // Validate dates
    if (!date_from || !date_to) {
      return NextResponse.json(
        { error: "Start date and End date are required" },
        { status: 400 }
      );
    }

    // Validate date format (YYYY-MM-DD)
    const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
    if (!dateRegex.test(date_from) || !dateRegex.test(date_to)) {
      return NextResponse.json(
        { error: "Invalid date format. Expected YYYY-MM-DD" },
        { status: 400 }
      );
    }

    // Get backend URL from environment variable
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
    
    // Build URL with query parameters
    const url = new URL(`${backendUrl}/exports`);
    url.searchParams.append("date_from", date_from);
    url.searchParams.append("date_to", date_to);
    
    // Add tenant_id to query parameters if provided
    if (tenant_id && tenant_id.trim()) {
      url.searchParams.append("tenant_id", tenant_id.trim());
    }

    // Forward the request to the external endpoint with query parameters
    const response = await fetch(url.toString(), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { error: data.error || "Failed to fetch telemetry data" },
        { status: response.status }
      );
    }

    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("Error in telemetry API route:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
