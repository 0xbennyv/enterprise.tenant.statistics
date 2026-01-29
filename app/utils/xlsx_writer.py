# app/utils/xlsx_writer.py

from datetime import date
from typing import Dict, Any
from io import BytesIO
from openpyxl import Workbook
from app.utils.helper import safe_sheet_title


def write_telemetry_xlsx(
    alerts: Dict[str, Any],
    sla: Dict[str, Any],
    date_from: date,
    date_to: date,
) -> bytes:
    wb = Workbook()
    ws_all = wb.active
    ws_all.title = "All Tenants"

    # -------- All Tenants Sheet --------
    ws_all.append(["Metric", "Value"])

    ws_all.append(["Total Incidents", alerts["total_incident_count"]])

    for k, v in alerts["total_incident_severity"].items():
        ws_all.append([f"Severity: {k}", v])

    for k, v in alerts["total_incident_category"].items():
        ws_all.append([f"Category: {k}", v])

    for k, v in alerts["total_tenant_monthly"].items():
        ws_all.append([f"Month: {k}", v])

    for k, v in sla["total_incident_sla_metrics"].items():
        ws_all.append([f"SLA: {k}", v])

    # -------- Per-Tenant Sheets --------
    tenants_by_id = {
        t["tenantId"]: t
        for t in alerts["incidents"]
    }

    for sla_tenant in sla["incidents"]:
        tenant_id = sla_tenant["tenantId"]
        tenant_name = sla_tenant["tenantName"]

        alert_tenant = tenants_by_id.get(tenant_id)
        if not alert_tenant:
            continue

        sheet_title = safe_sheet_title(tenant_name[:31])
        ws = wb.create_sheet(title=sheet_title)

        ws.append(["Tenant ID", tenant_id])
        ws.append(["Tenant Name", tenant_name])
        ws.append([])

        ws.append(["Total Incidents", alert_tenant["total_incidents"]])
        ws.append([])

        ws.append(["Severity", "Count"])
        for k, v in alert_tenant["severity"].items():
            ws.append([k, v])

        ws.append([])
        ws.append(["Category", "Count"])
        for k, v in alert_tenant["category"].items():
            ws.append([k, v])

        ws.append([])
        ws.append(["Month", "Count"])
        for k, v in alert_tenant["monthly"].items():
            ws.append([k, v])

        ws.append([])
        ws.append(["SLA Bucket", "Count"])
        for k, v in sla_tenant["sla_metrics"].items():
            ws.append([k, v])

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return buffer.read()
