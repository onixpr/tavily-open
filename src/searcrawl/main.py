"""
Sear-Crawl4AI - An open-source search and crawling tool based on SearXNG and Crawl4AI.
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Literal, Optional

import aiohttp
import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from loguru import logger
from pydantic import BaseModel
from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

import searcrawl.logger as log_module
from searcrawl.cache import CacheManager
from searcrawl.config import (
    API_HOST,
    API_PORT,
    CACHE_ENABLED,
    CACHE_TTL_HOURS,
    DEFAULT_SEARCH_LIMIT,
    DISABLED_ENGINES,
    ENABLED_ENGINES,
    HTTP_EXTRACTOR_ENABLED,
    HTTP_EXTRACTOR_MAX_CONCURRENCY,
    HTTP_EXTRACTOR_TIMEOUT_SECONDS,
    READER_ENABLED,
    READER_MAX_CONCURRENCY,
    READER_TIMEOUT_SECONDS,
    REDIS_URL,
    SEARCH_PROVIDER,
    SEARCH_CACHE_TTL_SECONDS,
    SEARXNG_TIMEOUT_SECONDS,
)
from searcrawl.crawler import WebCrawler
from searcrawl.search_providers import SearchProviderRequest, create_search_provider

from searcrawl.config import API_KEY

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(key: str = Security(api_key_header)):
    if API_KEY and key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")


cache_manager: Optional[CacheManager] = None
search_client: Optional[httpx.AsyncClient] = None
page_client: Optional[httpx.AsyncClient] = None
reader_session: Optional[aiohttp.ClientSession] = None
reader_semaphore: Optional[asyncio.Semaphore] = None
http_semaphore: Optional[asyncio.Semaphore] = None
crawler_service: Optional[WebCrawler] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    global cache_manager, crawler_service, http_semaphore, page_client, reader_semaphore, reader_session, search_client

    log_module.setup_logger("INFO")
    logger.info("Sear-Crawl4AI service starting...")

    if CACHE_ENABLED:
        try:
            logger.info(f"Initializing cache manager with Redis: {REDIS_URL}")
            cache_manager = CacheManager(REDIS_URL, CACHE_TTL_HOURS, SEARCH_CACHE_TTL_SECONDS)
            if await cache_manager.initialize():
                logger.info("Cache manager initialized successfully")
                logger.info(f"Cache stats: {await cache_manager.get_cache_stats()}")
            else:
                logger.warning("Cache manager initialized but Redis is not available")
                cache_manager = None
        except Exception as exc:
            logger.error(f"Failed to initialize cache manager: {str(exc)}")
            logger.warning("Continuing without cache")
            cache_manager = None

    search_client = httpx.AsyncClient(
        timeout=httpx.Timeout(SEARXNG_TIMEOUT_SECONDS),
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
    )
    page_client = httpx.AsyncClient(
        timeout=httpx.Timeout(HTTP_EXTRACTOR_TIMEOUT_SECONDS),
        limits=httpx.Limits(max_keepalive_connections=50, max_connections=200),
    )
    logger.info("Initialized shared HTTP clients for SearXNG and page extraction")

    if READER_ENABLED:
        reader_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=READER_TIMEOUT_SECONDS),
            connector=aiohttp.TCPConnector(
                limit=READER_MAX_CONCURRENCY,
                limit_per_host=READER_MAX_CONCURRENCY,
            ),
        )
        reader_semaphore = asyncio.Semaphore(READER_MAX_CONCURRENCY)
    else:
        reader_session = None
        reader_semaphore = None

    http_semaphore = (
        asyncio.Semaphore(HTTP_EXTRACTOR_MAX_CONCURRENCY) if HTTP_EXTRACTOR_ENABLED else None
    )
    crawler_service = WebCrawler(
        cache_manager=cache_manager,
        reader_session=reader_session,
        reader_semaphore=reader_semaphore,
        page_client=page_client,
        http_semaphore=http_semaphore,
    )
    logger.info(f"API service running at: http://{API_HOST}:{API_PORT}")
    logger.info("Sear-Crawl4AI service startup completed")

    yield

    logger.info("Starting graceful shutdown...")
    if crawler_service:
        await crawler_service.close()
        crawler_service = None
    if reader_session:
        await reader_session.close()
        reader_session = None
    if page_client:
        await page_client.aclose()
        page_client = None
    if search_client:
        await search_client.aclose()
        search_client = None
    if cache_manager:
        await cache_manager.close()
        cache_manager = None
    logger.info("Sear-Crawl4AI service shut down")


# Initialize FastAPI application with lifespan
app = FastAPI(
    title="Sear-Crawl4AI API",
    description="An open-source search and crawling tool based on SearXNG and Crawl4AI, "
    "serving as an open-source alternative to Tavily",
    version="1.0.0",
    lifespan=lifespan,
)


# Request model definitions
class SearchRequest(BaseModel):
    """Search request model

    Attributes:
        query: Search query string
        limit: Limit on number of results to return, default is 10
        disabled_engines: List of disabled search engines, comma-separated
        enabled_engines: List of enabled search engines, comma-separated
    """

    query: str
    limit: int = DEFAULT_SEARCH_LIMIT
    disabled_engines: str = DISABLED_ENGINES
    enabled_engines: str = ENABLED_ENGINES
    mode: Literal["crawl", "search"] = "crawl"
    provider: str = SEARCH_PROVIDER


class CrawlRequest(BaseModel):
    """
    Crawl request model

    Attributes:
        urls: List of URLs to crawl
        instruction: Crawling instruction, typically a search query
    """

    urls: list[str]
    instruction: str


async def crawl(request: CrawlRequest):
    """
    API endpoint function to crawl multiple URLs and process content

    Args:
        request: Crawl request containing URLs and instruction

    Returns:
        Dict: Dictionary containing processed content, success count, and failed URLs

    Raises:
        HTTPException: Raised when an error occurs during crawling
    """
    global crawler_service
    if crawler_service is None:
        raise HTTPException(status_code=503, detail="Crawler service not initialized")

    result = await crawler_service.crawl_urls(request.urls, request.instruction)
    result.setdefault("timings_ms", {})["pool_wait"] = 0.0
    return result


def build_search_cache_fingerprint(request: SearchRequest) -> dict[str, str | int]:
    """Build a stable fingerprint for search cache isolation."""
    return {
        "provider": request.provider,
        "mode": request.mode,
        "limit": request.limit,
        "disabled_engines": request.disabled_engines,
        "enabled_engines": request.enabled_engines,
    }


def build_search_only_response(
    provider_response,
    search_total_ms: float,
) -> dict:
    """Build the response for search-only mode."""
    effective_total_ms = max(search_total_ms, provider_response.request_ms)
    timings_ms = {
        "search_provider_request": provider_response.request_ms,
        "search_total": round(effective_total_ms, 2),
    }
    if provider_response.provider == "searxng":
        timings_ms["searxng_request"] = provider_response.request_ms

    return {
        "mode": "search",
        "provider": provider_response.provider,
        "results": [serialize_search_hit(hit) for hit in provider_response.hits],
        "success_count": len(provider_response.hits),
        "failed_urls": [],
        "cache_hits": 0,
        "newly_crawled": 0,
        "timings_ms": timings_ms,
    }


def get_search_provider(provider_name: str, client: Optional[httpx.AsyncClient]):
    """Resolve a search provider by name."""
    return create_search_provider(provider_name, client=client)


def serialize_search_hit(hit) -> dict[str, str]:
    """Serialize a normalized hit from either a dataclass or a test double."""
    if hasattr(hit, "to_dict"):
        return hit.to_dict()
    return {
        "url": hit.url,
        "title": hit.title,
        "snippet": hit.snippet,
        "provider": hit.provider,
    }


@app.get("/cache/stats")
async def get_cache_stats():
    """
    Get cache statistics endpoint

    Returns cache statistics including total entries and memory usage

    Returns:
        Dict: Cache statistics
    """
    global cache_manager
    try:
        if not cache_manager:
            logger.warning("Cache manager not available")
            return {"status": "unavailable", "message": "Cache is not enabled or not available"}

        stats = await cache_manager.get_cache_stats()
        logger.info(f"Cache stats retrieved: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/cache/clear")
async def clear_cache():
    """
    Clear all cache entries endpoint

    Clears all cached crawl results

    Returns:
        Dict: Operation result
    """
    global cache_manager
    try:
        if not cache_manager:
            logger.warning("Cache manager not available")
            return {"status": "unavailable", "message": "Cache is not enabled or not available"}

        success = await cache_manager.clear_all()
        if success:
            logger.info("Cache cleared successfully")
            return {"status": "success", "message": "Cache cleared successfully"}
        else:
            logger.warning("Failed to clear cache")
            return {"status": "error", "message": "Failed to clear cache"}
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/search")
async def search(request: SearchRequest, _=Depends(verify_api_key)):
    """
    Search API endpoint

    Receives search request, calls SearXNG search engine to get results,
    then crawls the search result pages

    Args:
        request: Search request object containing query string and configuration parameters

    Returns:
        Dict: Dictionary containing processed content, success count, and failed URLs

    Raises:
        HTTPException: Raised when an error occurs during search or crawling
    """
    global cache_manager
    global search_client
    search_started = time.perf_counter()
    try:
        # Add status feedback
        logger.info(f"Starting search: {request.query}")
        cache_fingerprint = build_search_cache_fingerprint(request)

        # Check cache for search results
        if cache_manager:
            cached_result = await cache_manager.get_search_cache(request.query, cache_fingerprint)
            if cached_result:
                logger.info(f"Search cache hit for query: {request.query}")
                cached_result.setdefault("timings_ms", {})["search_total"] = round(
                    (time.perf_counter() - search_started) * 1000,
                    2,
                )
                return cached_result

        provider = get_search_provider(request.provider, search_client)
        provider_response = await provider.search(
            SearchProviderRequest(
                query=request.query,
                limit=request.limit,
                provider=request.provider,
                disabled_engines=request.disabled_engines,
                enabled_engines=request.enabled_engines,
            )
        )

        if not provider_response.hits:
            logger.warning("No search results found")
            raise HTTPException(status_code=404, detail="No search results found")

        if request.mode == "search":
            search_result = build_search_only_response(
                provider_response=provider_response,
                search_total_ms=(time.perf_counter() - search_started) * 1000,
            )
            if cache_manager:
                await cache_manager.set_search_cache(request.query, search_result, cache_fingerprint)
            return search_result

        # Limit result count and extract URLs
        urls = [hit.url for hit in provider_response.hits]
        if not urls:
            logger.warning("No valid URLs found")
            raise HTTPException(status_code=404, detail="No valid URLs found")

        logger.info(f"Found {len(urls)} URLs, starting to crawl")

        # Call crawl function to process URLs
        crawl_result = await crawl(CrawlRequest(urls=urls, instruction=request.query))
        crawl_result["search_provider"] = provider_response.provider
        crawl_result.setdefault("timings_ms", {})["search_provider_request"] = (
            provider_response.request_ms
        )
        if provider_response.provider == "searxng":
            crawl_result["timings_ms"]["searxng_request"] = provider_response.request_ms
        crawl_result.setdefault("timings_ms", {})["search_total"] = round(
            max((time.perf_counter() - search_started) * 1000, provider_response.request_ms),
            2,
        )

        # Cache the search result
        if cache_manager:
            await cache_manager.set_search_cache(request.query, crawl_result, cache_fingerprint)

        return crawl_result
    except HTTPException:
        # Directly re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log other exceptions and convert to HTTP exception
        logger.error(f"Exception occurred during search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e


def main():
    """Main entry point for the application"""
    logger.info("Starting Sear-Crawl4AI service via command line")
    uvicorn.run(app, host=API_HOST, port=API_PORT)


if __name__ == "__main__":
    main()
