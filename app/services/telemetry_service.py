# app/services/telemetry_service.py

import asyncio
from typing import Any, Any, List, Dict
from datetime import datetime
from collections import defaultdict

from app.services.api_clients.alerts_api import AlertsApiClient
from app.services.api_clients.org_api import OrgApiClient
from app.services.token_manager import TokenManager

def aggregate_alerts(alerts: List[Dict]) -> List[Dict]:
    """
    Aggregates alerts per tenant, per month, with severity and category counts.
    
    Returns a list of dicts:
    [
        {
            "month": "YYYY-MM",
            "severity_counts": {"high": 10, "medium": 5, "low": 3},
            "category_counts": {"malware": 5, "policy": 3}
        }
    ]
    """
    aggregation = defaultdict(lambda: {"severity_counts": defaultdict(int),
                                       "category_counts": defaultdict(int)})

    for alert in alerts:
        # Parse alert timestamp
        raised_at = datetime.fromisoformat(alert["raisedAt"].replace("Z", "+00:00"))
        month_key = raised_at.strftime("%Y-%m")
        severity = alert.get("severity", "unknown")
        category = alert.get("category", "unknown")

        aggregation[month_key]["severity_counts"][severity] += 1
        aggregation[month_key]["category_counts"][category] += 1

    # Convert defaultdicts to dicts
    result = []
    for month, counts in aggregation.items():
        result.append({
            "month": month,
            "severity_counts": dict(counts["severity_counts"]),
            "category_counts": dict(counts["category_counts"])
        })
    return result


async def collect_telemetry(token_manager: TokenManager,
                            from_time: datetime,
                            to_time: datetime) -> Dict[str, Any]:
    """
    Collects telemetry for all tenants:
      - Fetch tenants from Org API
      - Fetch alerts for each tenant concurrently
      - Aggregate by month, severity, category
    Returns:
      {
          tenant_id: [
              {
                  "month": "YYYY-MM",
                  "severity_counts": {...},
                  "category_counts": {...}
              },
              ...
          ]
      }
    """
    org_client = OrgApiClient(token_manager)
    alerts_client = AlertsApiClient(token_manager)

    tenants = await org_client.list_tenants()
    telemetry: Dict[str, Any] = {}

    # Fetch alerts for all tenants concurrently
    async def process_tenant(tenant):
        tenant_id = tenant["id"]
        api_host = tenant["apiHost"]
        print("tenant_id", tenant_id)
        print("api_host", api_host)
        alerts = await alerts_client.list_alerts(api_host, tenant_id, from_time, to_time)
        print("alerts", alerts)
        aggregated = aggregate_alerts(alerts)
        telemetry[tenant_id] = aggregated

    await asyncio.gather(*[process_tenant(t) for t in tenants])
    return telemetry