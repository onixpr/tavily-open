"""
Search provider abstractions and concrete implementations.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Optional, Protocol

import httpx
from loguru import logger

from searcrawl.config import (
    BRAVE_SEARCH_API_BASE,
    BRAVE_SEARCH_API_KEY,
    SEARCH_LANGUAGE,
    SEARXNG_API_BASE,
    SEARXNG_HOST,
    SEARXNG_PORT,
    SEARXNG_TIMEOUT_SECONDS,
)


@dataclass
class SearchHit:
    """Normalized search result hit."""

    url: str
    title: str
    snippet: str
    provider: str

    def to_dict(self) -> dict[str, str]:
        """Serialize the hit for API responses."""
        return asdict(self)


@dataclass
class SearchProviderRequest:
    """Normalized request passed into search providers."""

    query: str
    limit: int
    provider: str
    disabled_engines: str = ""
    enabled_engines: str = ""


@dataclass
class SearchProviderResponse:
    """Normalized provider response."""

    provider: str
    hits: list[SearchHit]
    request_ms: float


class SearchProvider(Protocol):
    """Shared protocol for search providers."""

    async def search(self, request: SearchProviderRequest) -> SearchProviderResponse:
        """Run a search and return normalized hits."""


class SearXNGSearchProvider:
    """Provider backed by a SearXNG instance."""

    def __init__(self, client: Optional[httpx.AsyncClient] = None) -> None:
        self.client = client

    async def search(self, request: SearchProviderRequest) -> SearchProviderResponse:
        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=httpx.Timeout(SEARXNG_TIMEOUT_SECONDS))
        started = time.perf_counter()
        try:
            form_data = {
                "q": request.query,
                "format": "json",
                "language": SEARCH_LANGUAGE,
                "time_range": "week",
                "safesearch": "2",
                "pageno": "1",
                "category_general": "1",
            }
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
            }
            response = await client.post(SEARXNG_API_BASE, data=form_data, headers=headers)
            response.raise_for_status()
            payload = response.json()
            hits = [
                SearchHit(
                    url=result["url"],
                    title=result.get("title", ""),
                    snippet=result.get("content", ""),
                    provider="searxng",
                )
                for result in payload.get("results", [])[: request.limit]
                if "url" in result
            ]
            request_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.info(f"SearXNG provider request completed in {request_ms:.2f}ms")
            return SearchProviderResponse(provider="searxng", hits=hits, request_ms=request_ms)
        except httpx.HTTPStatusError as exc:
            logger.error(
                f"SearXNG request failed with status {exc.response.status_code}: {exc.response.text}"
            )
            raise Exception(f"Search request failed: {exc.response.text}") from exc
        except Exception as exc:
            logger.error(f"SearXNG request failed: {str(exc)}")
            raise Exception(f"Search request failed: {str(exc)}") from exc
        finally:
            if owns_client:
                await client.aclose()


class BraveSearchProvider:
    """Provider backed by Brave Search API."""

    def __init__(
        self,
        client: Optional[httpx.AsyncClient] = None,
        api_key: str = BRAVE_SEARCH_API_KEY,
        api_base: str = BRAVE_SEARCH_API_BASE,
    ) -> None:
        self.client = client
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")

    async def search(self, request: SearchProviderRequest) -> SearchProviderResponse:
        if not self.api_key:
            raise ValueError("BRAVE_SEARCH_API_KEY is required for the brave provider")

        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=httpx.Timeout(SEARXNG_TIMEOUT_SECONDS))
        started = time.perf_counter()
        try:
            response = await client.get(
                f"{self.api_base}/web/search",
                params={"q": request.query, "count": request.limit},
                headers={"X-Subscription-Token": self.api_key, "Accept": "application/json"},
            )
            response.raise_for_status()
            payload = response.json()
            hits = [
                SearchHit(
                    url=result["url"],
                    title=result.get("title", ""),
                    snippet=result.get("description", ""),
                    provider="brave",
                )
                for result in payload.get("web", {}).get("results", [])[: request.limit]
                if "url" in result
            ]
            request_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.info(f"Brave provider request completed in {request_ms:.2f}ms")
            return SearchProviderResponse(provider="brave", hits=hits, request_ms=request_ms)
        except httpx.HTTPStatusError as exc:
            logger.error(
                f"Brave request failed with status {exc.response.status_code}: {exc.response.text}"
            )
            raise Exception(f"Search request failed: {exc.response.text}") from exc
        except Exception as exc:
            logger.error(f"Brave request failed: {str(exc)}")
            raise Exception(f"Search request failed: {str(exc)}") from exc
        finally:
            if owns_client:
                await client.aclose()


def create_search_provider(
    provider_name: str,
    client: Optional[httpx.AsyncClient] = None,
) -> SearchProvider:
    """Create a search provider by name."""
    normalized_name = provider_name.strip().lower()
    if normalized_name == "searxng":
        return SearXNGSearchProvider(client=client)
    if normalized_name == "brave":
        return BraveSearchProvider(client=client)
    raise ValueError(f"Unsupported search provider: {provider_name}")
