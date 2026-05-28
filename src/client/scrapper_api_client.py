import logging
import os
from typing import List, Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)


class ScrapperAPIClient:
    """Utility client to interact with the decoupled ForexFactoryScrapper API using the Bundle endpoint."""

    def __init__(self, base_url: Optional[str] = None, timeout: int = 15):
        """Initialize the client with environment variables or explicit URL.

        Example base_url: http://127.0.0.1:5000
        """
        self.base_url = (base_url or os.getenv("FF_SCRAPPER_API_BASE_URL", "http://127.0.0.1:5000")).rstrip("/")
        self.timeout = timeout

        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            headers={"Content-Type": "application/json"}
        )

    def fetch_economic_data_bundle(
            self,
            sources: List[str],
            start_date: str,
            end_date: str,
            limit: Optional[int] = None,
            offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Fetch combined economic or crypto events from the Bundle API endpoint.

        Args:
            sources: List of sources to query, e.g., ['forex', 'crypto']
            start_date: Format 'YYYY-MM-DD'
            end_date: Format 'YYYY-MM-DD'
            limit: Optional maximum number of records to return
            offset: Optional number of records to skip

        Returns:
            List of combined event dictionaries. Returns [] on failure or empty results.
        """
        # Example: ['forex', 'crypto'] -> 'forex,crypto'
        sources_str = ",".join([s.strip().lower() for s in sources]) if isinstance(sources, list) else sources

        params = {
            "sources": sources_str,
            "start_date": start_date,
            "end_date": end_date
        }

        if limit is not None:
            params["limit"] = limit  # type: ignore
        if offset is not None:
            params["offset"] = offset  # type: ignore

        endpoint = "/api/bundle"

        try:
            logger.info(f"Sending request to Bundle API: GET {endpoint} with params {params}")

            response = self.client.get(endpoint, params=params)
            response.raise_for_status()
            body = response.json()

            if isinstance(body, dict):
                events = body.get("results", [])
                breakdown = body.get("source_breakdown", {})
                logger.info(f"Successfully fetched {len(events)} total events. Breakdown: {breakdown}")
                return events

            if isinstance(body, list):
                logger.warning("API returned a direct list instead of paginated envelope.")
                return body

            return []

        except httpx.HTTPStatusError as exc:
            logger.error(f"Bundle API returned error status {exc.response.status_code} for {exc.request.url}")
            return []
        except httpx.RequestError as exc:
            logger.error(f"An error occurred while requesting Bundle API: {exc}")
            return []
        except Exception as exc:
            logger.error(f"Unexpected error parsing Bundle API response: {exc}")
            return []

    def close(self):
        """Close the underlying HTTPX client session."""
        self.client.close()
