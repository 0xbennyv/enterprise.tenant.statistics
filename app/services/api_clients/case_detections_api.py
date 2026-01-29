# app/services/api_clients/case_detections_api.py

from typing import List, Dict, Any
import logging

from app.services.api_clients.base import BaseApiClient

logger = logging.getLogger(__name__)


class CaseDetectionsApiClient(BaseApiClient):
    async def list_detections(
        self,
        api_host: str,
        tenant_id: str,
        case_id: str,
    ) -> List[Dict[str, Any]]:
        url = f"{api_host}/cases/v1/cases/{case_id}/detections"

        all_items: List[Dict[str, Any]] = []
        page = 1

        while True:
            response = await self.get(
                url=url,
                headers={"X-Tenant-ID": tenant_id},
                params={
                    "sort": "time:asc",
                    "page": page,
                },
            )

            # Error responses (404 / 5xx handled upstream)
            if isinstance(response, dict) and "_error" in response:
                logger.debug(
                    "Skipping detections for case %s (reason=%s)",
                    case_id,
                    response["_error"],
                )
                break

            # Defensive: unexpected response shape
            if not isinstance(response, dict):
                logger.error(
                    "Unexpected detections response type for case %s: %s",
                    case_id,
                    type(response),
                )
                break

            items = response.get("items", [])
            pages = response.get("pages", {})

            all_items.extend(items)

            total_pages = pages.get("total", 1)
            current_page = pages.get("current", page)

            logger.debug(
                "[MTTD] Case %s page %d/%d fetched (%d items)",
                case_id,
                current_page,
                total_pages,
                len(items),
            )

            if current_page >= total_pages:
                break

            page += 1

        logger.info(
            "[MTTD] Case %s (tenant=%s): total detections fetched = %d",
            case_id,
            tenant_id,
            len(all_items),
        )

        return all_items
