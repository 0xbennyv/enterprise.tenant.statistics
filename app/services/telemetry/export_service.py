from datetime import date, datetime, time, timezone
from pathlib import Path
from io import BytesIO
from openpyxl import Workbook

from app.utils.helper import unique_sheet_title
from app.services.telemetry.alert_service import AlertTelemetryService
from app.services.telemetry.case_service import CaseTelemetryService
from app.services.telemetry.mttd_service import MTTDService
from app.services.telemetry.mtta_service import MTTAService
from app.services.telemetry.mttr_service import MTTRService
from app.services.telemetry.endpoint_health_service import EndpointHealthService
from app.exporters.excel.all_tenants_sheet import build_all_tenants_sheet
from app.exporters.excel.tenant_sheet import build_tenant_sheet


EXPORT_DIR = Path("/code/exports")  # <-- Docker-mounted volume for persistence
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


class TelemetryExportService:
    def __init__(
        self,
        alert_service: AlertTelemetryService,
        case_sla_service: CaseTelemetryService,
        mttd_service: MTTDService,
        mtta_service: MTTAService,
        mttr_service: MTTRService,
        endpoint_health_service: EndpointHealthService,
        progress_cb=None,
        is_cancelled_cb=None,
    ):
        self.alerts = alert_service
        self.sla = case_sla_service
        self.mttd = mttd_service
        self.mtta = mtta_service
        self.mttr = mttr_service
        self.endpoint_health = endpoint_health_service

        async def _noop_progress(_: dict):
            return

        async def _noop_cancel():
            return False
        
        self.progress_cb = progress_cb or _noop_progress
        self.is_cancelled_cb = is_cancelled_cb or _noop_cancel

    async def export_to_excel(self, date_from: date, date_to: date) -> str | None:
        """
        Export telemetry to Excel and return the full file path.
        Returns None if export was cancelled.
        """

        # 1️⃣ Collect telemetry
        await self.progress_cb({"stage": "collecting_alerts", "percent": 5})
        alerts = await self.alerts.collect(date_from, date_to)
        if await self.is_cancelled_cb():
            return None
        
        created_after = datetime.combine(
            date_from, time.min, tzinfo=timezone.utc
        )

        created_before = datetime.combine(
            date_to, time.min, tzinfo=timezone.utc
        )

        await self.progress_cb({"stage": "collecting_sla", "percent": 15})
        sla = await self.sla.collect_sla_metrics(created_after, created_before)
        if await self.is_cancelled_cb():
            return None

        await self.progress_cb({"stage": "collecting_mttd", "percent": 25})
        mttd = await self.mttd.collect_mttd(date_from, date_to)
        if await self.is_cancelled_cb():
            return None

        await self.progress_cb({"stage": "collecting_mtta", "percent": 35})
        mtta = await self.mtta.collect_mtta(created_after, created_before)
        if await self.is_cancelled_cb():
            return None

        await self.progress_cb({"stage": "collecting_mttr", "percent": 45})
        mttr = await self.mttr.collect_mttr(created_after, created_before)
        if await self.is_cancelled_cb():
            return None

        await self.progress_cb({"stage": "collecting_endpoint_health", "percent": 55})
        endpoint = await self.endpoint_health.collect_endpoint_health()
        if await self.is_cancelled_cb():
            return None

        # 2️⃣ Create workbook
        wb = Workbook()
        wb.remove(wb.active)

        await self.progress_cb({"stage": "building_all_tenants_sheet", "percent": 60})
        build_all_tenants_sheet(wb, alerts, sla, mttd, mtta, mttr, endpoint)
        if await self.is_cancelled_cb():
            return None

        # 3️⃣ Build per-tenant sheets
        total_tenants = len(alerts.get("incidents", {}))
        for idx, tenant in enumerate(alerts.get("incidents", {}), start=1):
            if await self.is_cancelled_cb():
                return None
            await self.progress_cb(
                {"stage": f"building_sheet_{tenant}", "percent": 60 + int(30 * idx / total_tenants)}
            )
            build_tenant_sheet(wb, tenant, alerts, sla, mttd, mtta, mttr, endpoint)

        # 4️⃣ Save file
        file_name = f"{date_from}_to_{date_to}.xlsx"
        file_path = EXPORT_DIR / file_name

        await self.progress_cb({"stage": "saving_file", "percent": 95})
        wb.save(file_path)
        await self.progress_cb({"stage": "done", "percent": 100})

        return str(file_path)
