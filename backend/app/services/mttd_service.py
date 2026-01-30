# app/services/mttd_service.py

import asyncio
import datetime
import logging
from typing import Dict, Any, List

from app.api.org_api import OrgApiClient
from app.api.cases_api import CasesApiClient
from app.api.case_detections_api import CaseDetectionsApiClient
from app.aggregator.mttd_aggregator import MTTDAggregator

logger = logging.getLogger(__name__)

class MTTDService:
    def __init__(
        self,
        org_client: OrgApiClient,
        cases_client: CasesApiClient,
        detections_client: CaseDetectionsApiClient,
    ):
        self.org_client = org_client
        self.cases_client = cases_client
        self.detections_client = detections_client

    async def collect_mttd(
        self,
        created_after: datetime,
        created_before: datetime,
    ) -> Dict[str, Any]:
        tenants = await self.org_client.list_tenants()
        # print("[MTTD] Fetched %d tenants", len(tenants))

        async def fetch_tenant_detections(tenant):
            try:
                cases = await self.cases_client.list_cases(
                    api_host=tenant["apiHost"],
                    tenant_id=tenant["id"],
                    created_after=created_after,
                    created_before=created_before,
                    # IMPORTANT: no status filter
                )

                detections: List[Dict[str, Any]] = []

                case_count = 0
                for case in cases:
                    print("[MTTD] Processing case %s for tenant %s", case["id"], tenant["id"])

                    # FOR TESTING, LIMIT TO FIRST 5 CASES ONLY
                    # if case_count >= 5:
                    #     break
                    # case_count += 1
                    
                    case_id = case["id"]
                    if not case_id:
                        continue
                    
                    try:
                        case_detections = await self.detections_client.list_detections(
                            api_host=tenant["apiHost"],
                            tenant_id=tenant["id"],
                            case_id=case_id,
                        )

                        print(
                            "[MTTD] Case %s (tenant=%s): detections fetched = %d",
                            case_id,
                            tenant["id"],
                            len(case_detections) if "_error" not in case_detections else 0,
                        )
                    
                        detections.extend(case_detections)
                    except Exception as exc:
                        logger.warning(
                            "Skipping detections for case %s in tenant %s: %s",
                            case_id,
                            tenant["id"],
                            exc,
                        )
            except Exception as exc:
                logger.error(
                    "Failed to fetch cases for tenant %s: %s",
                    tenant["id"],
                    exc,
                )
                return tenant["id"], tenant["name"], []

            return tenant["id"], tenant["name"], detections
        results = await asyncio.gather(
            *[fetch_tenant_detections(t) for t in tenants],
            return_exceptions=False,
        )

        detections_by_tenant = {
            (tenant_id, tenant_name): detections
            for tenant_id, tenant_name, detections in results
        }

        return MTTDAggregator.aggregate(detections_by_tenant)
