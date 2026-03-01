"""Proxy helpers for Playwright-based operations."""

from __future__ import annotations

import os
from urllib.parse import urlsplit
from typing import Optional


def _looks_like_qizhi_host(base_url: str) -> bool:
    try:
        host = urlsplit(base_url).hostname or ""
    except Exception:
        host = ""
    host = host.lower()
    return host == "qz.sii.edu.cn" or host.endswith(".sii.edu.cn")


def get_playwright_proxy() -> Optional[dict]:
    # Explicit override for browser automation only.
    proxy = (
        os.environ.get("INSPIRE_PLAYWRIGHT_PROXY")
        or os.environ.get("inspire_playwright_proxy")
        or os.environ.get("PLAYWRIGHT_PROXY")
    )
    if proxy:
        return {"server": proxy}

    # Inspire/QiZhi deployments commonly require split proxy routing:
    # requests/curl -> 8888 (HTTP), Playwright -> 1080 (SOCKS5).
    # Keep this auto-fallback narrow to .sii.edu.cn base URLs.
    base_url = os.environ.get("INSPIRE_BASE_URL", "")
    http_proxy = os.environ.get("http_proxy") or os.environ.get("HTTP_PROXY") or ""
    https_proxy = os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY") or ""
    if _looks_like_qizhi_host(base_url):
        chosen_http_proxy = https_proxy or http_proxy
        if chosen_http_proxy.startswith("http://127.0.0.1:8888"):
            return {"server": "socks5://127.0.0.1:1080"}

    proxy = https_proxy or http_proxy
    if proxy:
        return {"server": proxy}
    return None
