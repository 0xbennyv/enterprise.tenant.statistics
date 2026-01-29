# app/services/telemetry/mttr_aggregator.py

from datetime import datetime
from typing import Dict, List, Any


class MTTRAggregator:
    @staticmethod
    def _parse_time(ts: str) -> datetime:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))

    @staticmethod
    def aggregate(
        cases_by_tenant: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        incidents = []
        global_total_seconds = 0.0
        global_case_count = 0

        for (tenant_id, tenant_name), cases in cases_by_tenant.items():
            tenant_total_seconds = 0.0
            tenant_case_count = 0

            for case in cases:
                # print("Processing case ID:", case.get("id"), "for tenant:", tenant_id)
                # print("Case data:", case)
                # break
                resolved_at = case.get("resolvedAt")
                initial_detection = case.get("initialDetection", {})
                detection_time = initial_detection.get("time")
                print("Case ID:", case.get("id"), "Detection Time:", detection_time, "Resolved At:", resolved_at)
                # if not created_at:
                #     if not detection_time:
                #         assigned_time = case.get("assignedAt")
                #     continue

                if resolved_at is not None:
                    if detection_time is not None:
                        delta = (
                            MTTRAggregator._parse_time(resolved_at)
                            - MTTRAggregator._parse_time(detection_time)
                        ).total_seconds()
                    else:
                        print("No detection time for case ID:", case.get("id"))
                        assigned_time = case.get("assignedAt")
                        print("Assigned At:", assigned_time)
                        if assigned_time is not None:
                            delta = abs(
                                MTTRAggregator._parse_time(assigned_time)
                                - MTTRAggregator._parse_time(resolved_at)
                            ).total_seconds()
                        else:
                            continue

                if delta < 0:
                    continue
                print("Delta:", delta)
                tenant_total_seconds += delta
                tenant_case_count += 1
                global_total_seconds += delta
                global_case_count += 1

            incidents.append({
                "tenantId": tenant_id,
                "tenantName": tenant_name,
                "mttr_seconds": (
                    tenant_total_seconds / tenant_case_count
                    if tenant_case_count > 0 else 0
                ),
                "total_cases": tenant_case_count,
            })

        return {
            "incidents": incidents,
            "mttr_seconds": (
                global_total_seconds / global_case_count
                if global_case_count > 0 else 0
            ),
            "total_cases": global_case_count,
        }
