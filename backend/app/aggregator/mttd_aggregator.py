# app/aggregator/mttd_aggregator.py

from datetime import datetime
from typing import Dict, List, Any


class MTTDAggregator:
    @staticmethod
    def _parse_time(ts: str) -> datetime:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))

    @staticmethod
    def aggregate(
        detections_by_tenant: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        incidents = []
        global_total_seconds = 0.0
        global_detection_count = 0

        for (tenant_id, tenant_name), detections in detections_by_tenant.items():
            tenant_total_seconds = 0.0
            tenant_detection_count = len(detections)
            global_detection_count += tenant_detection_count
            
            # print("Processing tenant:", tenant_id, "with", tenant_detection_count, "detections")

            for detection in detections:
                # print("Tenant ID:", tenant_id)
                # print("Detection ID:", detection.get("id"))
                sensor_time = detection.get("sensorGeneratedAt")
                detected_time = detection.get("time")

                if not sensor_time or not detected_time:
                    continue

                delta = (
                    MTTDAggregator._parse_time(detected_time)
                    - MTTDAggregator._parse_time(sensor_time)
                ).total_seconds()

                if delta < 0:
                    continue

                tenant_total_seconds += delta
                # tenant_detection_count += 1
                global_total_seconds += delta
                # global_detection_count += 1

            incidents.append({
                "tenantId": tenant_id,
                "tenantName": tenant_name,
                "mttd_seconds": (
                    tenant_total_seconds / tenant_detection_count
                    if tenant_detection_count > 0 else 0
                ),
                "total_detections": tenant_detection_count,
            })

        return {
            "incidents": incidents,
            "all_tenants_mttd_seconds": (
                global_total_seconds / global_detection_count
                if global_detection_count > 0 else 0
            ),
            "total_detections": global_detection_count,
        }
