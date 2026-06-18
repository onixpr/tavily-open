"""
Configuration Module - Loads configuration from environment variables

This module loads configuration from environment variables and provides
default values when environment variables are not set.
"""

import os
from typing import Any

from dotenv import load_dotenv
from loguru import logger

# Load environment variables from .env file
load_dotenv()
logger.info("Loading environment variable configuration")

# SearXNG Configuration
SEARXNG_HOST = os.getenv("SEARXNG_HOST", "localhost")
SEARXNG_PORT = int(os.getenv("SEARXNG_PORT", "8080"))
SEARXNG_BASE_PATH = os.getenv("SEARXNG_BASE_PATH", "/search")
SEARXNG_PROTOCOL = os.getenv("SEARXNG_PROTOCOL", "http")
SEARXNG_API_BASE = f"{SEARXNG_PROTOCOL}://{SEARXNG_HOST}:{SEARXNG_PORT}{SEARXNG_BASE_PATH}"
logger.info(f"SearXNG API base URL: {SEARXNG_API_BASE}")

# API Service Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "3000"))

# Reader Service Configuration
READER_ENABLED = os.getenv("READER_ENABLED", "true").lower() == "true"
READER_URL = os.getenv("READER_URL", "http://reader:3000")
READER_API_KEY = os.getenv("READER_API_KEY", "")
READER_TIMEOUT_SECONDS = float(os.getenv("READER_TIMEOUT_SECONDS", "30"))
READER_MAX_CONCURRENCY = int(os.getenv("READER_MAX_CONCURRENCY", "20"))
READER_MIN_CONTENT_LENGTH = int(os.getenv("READER_MIN_CONTENT_LENGTH", "300"))

# Crawler Configuration
DEFAULT_SEARCH_LIMIT = int(os.getenv("DEFAULT_SEARCH_LIMIT", "10"))
CONTENT_FILTER_THRESHOLD = float(os.getenv("CONTENT_FILTER_THRESHOLD", "0.6"))
WORD_COUNT_THRESHOLD = int(os.getenv("WORD_COUNT_THRESHOLD", "10"))
CRAWLER_POOL_SIZE = int(os.getenv("CRAWLER_POOL_SIZE", "4"))
SEARXNG_TIMEOUT_SECONDS = float(os.getenv("SEARXNG_TIMEOUT_SECONDS", "15"))
HTTP_EXTRACTOR_ENABLED = os.getenv("HTTP_EXTRACTOR_ENABLED", "true").lower() == "true"
HTTP_EXTRACTOR_TIMEOUT_SECONDS = float(os.getenv("HTTP_EXTRACTOR_TIMEOUT_SECONDS", "10"))
HTTP_EXTRACTOR_MAX_CONCURRENCY = int(os.getenv("HTTP_EXTRACTOR_MAX_CONCURRENCY", "20"))
HTTP_EXTRACTOR_MIN_CONTENT_LENGTH = int(os.getenv("HTTP_EXTRACTOR_MIN_CONTENT_LENGTH", "300"))

# Browser Fallback Configuration
BROWSER_BACKEND = os.getenv("BROWSER_BACKEND", "local").lower()
BROWSERLESS_WS_URL = os.getenv("BROWSERLESS_WS_URL", "").strip()
BROWSER_REMOTE_TIMEOUT_SECONDS = float(os.getenv("BROWSER_REMOTE_TIMEOUT_SECONDS", "45"))
BROWSER_REMOTE_MAX_CONCURRENCY = int(os.getenv("BROWSER_REMOTE_MAX_CONCURRENCY", "2"))
BROWSER_LOCAL_FALLBACK_ENABLED = (
    os.getenv("BROWSER_LOCAL_FALLBACK_ENABLED", "true").lower() == "true"
)
BROWSER_LOCAL_MAX_CONCURRENCY = int(os.getenv("BROWSER_LOCAL_MAX_CONCURRENCY", "1"))

# Cache Configuration
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL_HOURS = int(os.getenv("CACHE_TTL_HOURS", "24"))
SEARCH_CACHE_TTL_SECONDS = int(os.getenv("SEARCH_CACHE_TTL_SECONDS", "300"))

# Search Engine Configuration
SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "searxng").strip().lower()
DISABLED_ENGINES = os.getenv(
    "DISABLED_ENGINES",
    "wikipedia__general,currency__general,wikidata__general,duckduckgo__general,"
    "google__general,lingva__general,qwant__general,startpage__general,"
    "dictzone__general,mymemory translated__general,brave__general",
)
ENABLED_ENGINES = os.getenv("ENABLED_ENGINES", "baidu__general")
SEARCH_LANGUAGE = os.getenv("SEARCH_LANGUAGE", "auto")
BRAVE_SEARCH_API_BASE = os.getenv("BRAVE_SEARCH_API_BASE", "https://api.search.brave.com/res/v1")
BRAVE_SEARCH_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY", "").strip()

# Anti-Crawl Configuration
ANTI_CRAWL_ENABLED = os.getenv("ANTI_CRAWL_ENABLED", "true").lower() == "true"
ENABLE_PROXY_ROTATION = os.getenv("ENABLE_PROXY_ROTATION", "false").lower() == "true"
ENABLE_USER_AGENT_ROTATION = os.getenv("ENABLE_USER_AGENT_ROTATION", "true").lower() == "true"
ENABLE_REQUEST_DELAY = os.getenv("ENABLE_REQUEST_DELAY", "true").lower() == "true"
ENABLE_RANDOM_HEADERS = os.getenv("ENABLE_RANDOM_HEADERS", "true").lower() == "true"
ENABLE_BROWSER_HEADERS = os.getenv("ENABLE_BROWSER_HEADERS", "true").lower() == "true"
MIN_REQUEST_DELAY = float(os.getenv("MIN_REQUEST_DELAY", "0.5"))
MAX_REQUEST_DELAY = float(os.getenv("MAX_REQUEST_DELAY", "3.0"))
PROXY_ROTATION_MODE = os.getenv("PROXY_ROTATION_MODE", "random")  # "random" or "sequential"
USE_MOBILE_AGENTS = os.getenv("USE_MOBILE_AGENTS", "false").lower() == "true"

# Proxy Configuration (comma-separated list of proxy URLs)
# Format: http://proxy1:port,http://proxy2:port or http://user:pass@proxy:port
PROXY_LIST = os.getenv("PROXY_LIST", "").strip()

# Custom User-Agents (comma-separated list)
CUSTOM_USER_AGENTS = os.getenv("CUSTOM_USER_AGENTS", "").strip()


def get_config_info() -> dict[str, Any]:
    """Returns a dictionary of current configuration information

    Returns:
        dict: Dictionary containing all configuration parameters
    """
    return {
        "searxng": {
            "host": SEARXNG_HOST,
            "port": SEARXNG_PORT,
            "base_path": SEARXNG_BASE_PATH,
            "api_base": SEARXNG_API_BASE,
        },
        "api": {"host": API_HOST, "port": API_PORT},
        "reader": {
            "enabled": READER_ENABLED,
            "url": READER_URL,
            "timeout_seconds": READER_TIMEOUT_SECONDS,
            "max_concurrency": READER_MAX_CONCURRENCY,
            "min_content_length": READER_MIN_CONTENT_LENGTH,
        },
        "crawler": {
            "default_search_limit": DEFAULT_SEARCH_LIMIT,
            "content_filter_threshold": CONTENT_FILTER_THRESHOLD,
            "word_count_threshold": WORD_COUNT_THRESHOLD,
            "pool_size": CRAWLER_POOL_SIZE,
            "searxng_timeout_seconds": SEARXNG_TIMEOUT_SECONDS,
            "http_extractor_enabled": HTTP_EXTRACTOR_ENABLED,
            "http_extractor_timeout_seconds": HTTP_EXTRACTOR_TIMEOUT_SECONDS,
            "http_extractor_max_concurrency": HTTP_EXTRACTOR_MAX_CONCURRENCY,
            "http_extractor_min_content_length": HTTP_EXTRACTOR_MIN_CONTENT_LENGTH,
        },
        "browser": {
            "backend": BROWSER_BACKEND,
            "browserless_ws_url": BROWSERLESS_WS_URL,
            "remote_timeout_seconds": BROWSER_REMOTE_TIMEOUT_SECONDS,
            "remote_max_concurrency": BROWSER_REMOTE_MAX_CONCURRENCY,
            "local_fallback_enabled": BROWSER_LOCAL_FALLBACK_ENABLED,
            "local_max_concurrency": BROWSER_LOCAL_MAX_CONCURRENCY,
        },
        "cache": {
            "enabled": CACHE_ENABLED,
            "redis_url": REDIS_URL,
            "crawl_ttl_hours": CACHE_TTL_HOURS,
            "search_ttl_seconds": SEARCH_CACHE_TTL_SECONDS,
        },
        "search_engines": {"disabled": DISABLED_ENGINES, "enabled": ENABLED_ENGINES},
        "search_provider": {
            "default": SEARCH_PROVIDER,
            "brave_api_base": BRAVE_SEARCH_API_BASE,
            "brave_api_key_configured": bool(BRAVE_SEARCH_API_KEY),
        },
        "anti_crawl": {
            "enabled": ANTI_CRAWL_ENABLED,
            "enable_proxy_rotation": ENABLE_PROXY_ROTATION,
            "enable_user_agent_rotation": ENABLE_USER_AGENT_ROTATION,
            "enable_request_delay": ENABLE_REQUEST_DELAY,
            "enable_random_headers": ENABLE_RANDOM_HEADERS,
            "enable_browser_headers": ENABLE_BROWSER_HEADERS,
            "min_request_delay": MIN_REQUEST_DELAY,
            "max_request_delay": MAX_REQUEST_DELAY,
            "proxy_rotation_mode": PROXY_ROTATION_MODE,
            "use_mobile_agents": USE_MOBILE_AGENTS,
            "proxy_count": len(PROXY_LIST.split(",")) if PROXY_LIST else 0,
            "custom_user_agents_count": (
                len(CUSTOM_USER_AGENTS.split(",")) if CUSTOM_USER_AGENTS else 0
            ),
        },
    }
