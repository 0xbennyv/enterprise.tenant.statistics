# app/services/telemetry/case_aggregator.py

from collections import Counter
from datetime import datetime
from typing import Dict, List, Any


class CaseTelemetryAggregator:
    SLA_BUCKETS = ["< 1 min", "< 10 mins", "< 30 mins", "> 1 hour"]

    @staticmethod
    def _empty_buckets() -> Dict[str, int]:
        return {bucket: 0 for bucket in CaseTelemetryAggregator.SLA_BUCKETS}

    @staticmethod
    def aggregate(
        cases_by_tenant: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        per_tenant = []
        global_sla = Counter(CaseTelemetryAggregator._empty_buckets())
        global_total = 0

        for (tenant_id, tenant_name), cases in cases_by_tenant.items():
            tenant_sla = Counter(CaseTelemetryAggregator._empty_buckets())
            tenant_total = 0

            for case in cases:
                print("Case:", case)
                if case.get("status") != "resolved" or not case.get("resolvedAt"):
                    continue

                created_at = datetime.fromisoformat(
                    case["createdAt"].replace("Z", "+00:00")
                )
                resolved_at = datetime.fromisoformat(
                    case["resolvedAt"].replace("Z", "+00:00")
                )

                sla_seconds = (resolved_at - created_at).total_seconds()
                tenant_total += 1
                global_total += 1

                if sla_seconds < 60:
                    bucket = "< 1 min"
                elif sla_seconds < 600:
                    bucket = "< 10 mins"
                elif sla_seconds < 1800:
                    bucket = "< 30 mins"
                elif sla_seconds >= 3600:
                    bucket = "> 1 hour"
                else:
                    continue

                tenant_sla[bucket] += 1
                global_sla[bucket] += 1

            per_tenant.append({
                "tenantId": tenant_id,
                "tenantName": tenant_name,
                "sla_metrics": dict(tenant_sla),
                "total_incidents": tenant_total,
            })

        return {
            "incidents": per_tenant,
            "total_incident_count": global_total,
            "total_incident_sla_metrics": dict(global_sla),
        }
