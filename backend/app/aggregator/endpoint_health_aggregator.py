# app/aggregator/endpoint_health_aggregator.py

from typing import Dict, Any


class EndpointHealthAggregator:
    @staticmethod
    def aggregate(health_by_tenant: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        incidents = []

        global_totals = {
            # "total_endpoints": 0,
            "notFullyProtected": 0,
            "tamperProtectionDisabled": 0,
        }

        for (tenant_id, tenant_name), health in health_by_tenant.items():
            endpoint = health.get("endpoint", {})
            protection = endpoint.get("protection", {})
            tamper = endpoint.get("tamperProtection", {})

            tenant_totals = {
                "tenantId": tenant_id,
                "tenantName": tenant_name,
                # "total_endpoints": 0,
                "notFullyProtected": 0,
                "tamperProtectionDisabled": 0,
                "details": [],
            }

            for endpoint_type in ("computer", "server"):
                p = protection.get(endpoint_type, {})
                t = tamper.get(endpoint_type, {})

                # total = p.get("total", 0)
                not_protected = p.get("notFullyProtected", 0)
                # total += t.get("total", 0)
                tamper_disabled = t.get("disabled", 0)

                print("Tenant ID", tenant_id, "Not Protected:", not_protected, "Tamper Disabled:", tamper_disabled)
                
                # unhealthy = (
                #     not_protected
                #     + tamper_disabled
                #     # if not p.get("snoozed", False) and not t.get("snoozed", False)
                #     # else total
                # )

                # tenant_totals["total_endpoints"] += total
                tenant_totals["notFullyProtected"] += not_protected
                # tenant_totals["unhealthy"] += unhealthy
                tenant_totals["tamperProtectionDisabled"] += tamper_disabled

                if not_protected > 0 or tamper_disabled > 0:
                    tenant_totals["details"].append({
                        "type": endpoint_type,
                        # "total": total,
                        "notFullyProtected": not_protected,
                        "tamperProtectionDisabled": tamper_disabled,
                        # "snoozed": p.get("snoozed", False) or t.get("snoozed", False),
                    })

            incidents.append(tenant_totals)

            for k in global_totals:
                global_totals[k] += tenant_totals[k]

        return {
            "tenants": incidents,
            "global": global_totals,
        }
