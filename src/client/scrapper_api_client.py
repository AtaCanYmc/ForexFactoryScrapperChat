import logging
import os
from typing import List, Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)


class ScrapperAPIClient:
    """Utility client to interact with the decoupled ForexFactoryScrapper API."""

    def __init__(self, base_url: Optional[str] = None, timeout: int = 15):
        """Initialize the client with environment variables or explicit URL.

        Example base_url: http://127.0.0.1:5000
        """
        # API base url from env
        self.base_url = (base_url or os.getenv("FF_SCRAPPER_API_BASE_URL", "http://127.0.0.1:5000")).rstrip("/")
        self.timeout = timeout

        # HTTPX Client initialization with base URL and timeout configuration.
        # We can also add retry logic here if needed.
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            headers={"Content-Type": "application/json"}
        )

    def fetch_economic_data(
            self,
            source: str,
            start_date: str,
            end_date: str
    ) -> List[Dict[str, Any]]:
        """Fetch raw economic or crypto events from the Scrapper API.

        Args:
            source: 'forexfactory', 'cryptocraft', etc.
            start_date: Format 'YYYY-MM-DD'
            end_date: Format 'YYYY-MM-DD'

        Returns:
            List of event dictionaries. Returns an empty list [] on failure or empty days.
        """
        # Scrapper API query params
        params = {
            "source": source,
            "start_date": start_date,
            "end_date": end_date
        }
        endpoint = "/api/events"

        try:
            logger.info(f"Sending request to Scrapper API: GET {endpoint} with params {params}")

            response = self.client.get(endpoint, params=params)

            # Eğer 4xx veya 5xx hatası dönerse HTTPError fırlatır ama catch bloğuna düşürür
            response.raise_for_status()

            # API'den gelen veriyi parse ediyoruz
            data = response.json()

            # API mimarine göre eğer data doğrudan liste değilse, örn: {"events": []} gibiyse
            # burayı data.get("events", []) olarak güncelleyebilirsin.
            if isinstance(data, list):
                logger.info(f"Successfully fetched {len(data)} events from Scrapper API.")
                return data

            return data.get("events", [])

        except httpx.HTTPStatusError as exc:
            logger.error(f"Scrapper API returned error status {exc.response.status_code} for {exc.request.url}")
            return []
        except httpx.RequestError as exc:
            logger.error(f"An error occurred while requesting Scrapper API: {exc}")
            # API kapalıysa veya ulaşılamıyorsa sistemi çökertmek yerine boş liste dönerek
            # LLM katmanındaki 'Hamsi Kontrolü' (Defensive Guard) mekanizmasını tetikliyoruz.
            return []
        except Exception as exc:
            logger.error(f"Unexpected error parsing Scrapper API response: {exc}")
            return []

    def close(self):
        """Close the underlying HTTPX client session."""
        self.client.close()
