# app/aggregator/alert_aggregator.py

from collections import Counter
from datetime import datetime
from typing import Dict, List, Any


class AlertTelemetryAggregator:
    @staticmethod
    def aggregate(alerts_by_tenant: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        incidents = []

        total_severity = Counter()
        total_category = Counter()
        total_monthly = Counter()
        total_incident_count = 0

        for (tenant_id, tenant_name), alerts in alerts_by_tenant.items():
            # print("Alerts:", tenant_id, tenant_name, alerts)
            # break
            severity = Counter()
            category = Counter()
            monthly = Counter()

            for alert in alerts:
                severity[alert["severity"]] += 1
                category[alert["category"]] += 1

                dt = datetime.fromisoformat(
                    alert["raisedAt"].replace("Z", "+00:00")
                )
                month_key = dt.strftime("%B %Y")
                monthly[month_key] += 1

            tenant_total = len(alerts)

            incidents.append({
                "tenantId": tenant_id,
                "tenantName": tenant_name,
                "severity": dict(severity),
                "category": dict(category),
                "monthly": dict(monthly),
                "total_incidents": tenant_total,
            })

            # Roll up into global totals
            total_severity.update(severity)
            total_category.update(category)
            total_monthly.update(monthly)
            total_incident_count += tenant_total

        return {
            "incidents": incidents,
            "total_incident_count": total_incident_count,
            "total_incident_severity": dict(total_severity),
            "total_incident_category": dict(total_category),
            "total_tenant_monthly": dict(total_monthly),
        }
