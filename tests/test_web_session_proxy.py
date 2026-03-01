from __future__ import annotations

import pytest

from inspire.platform.web.session.proxy import get_playwright_proxy


@pytest.fixture(autouse=True)
def clear_proxy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [
        "INSPIRE_PLAYWRIGHT_PROXY",
        "inspire_playwright_proxy",
        "PLAYWRIGHT_PROXY",
        "INSPIRE_BASE_URL",
        "http_proxy",
        "HTTP_PROXY",
        "https_proxy",
        "HTTPS_PROXY",
    ]:
        monkeypatch.delenv(key, raising=False)


def test_get_playwright_proxy_prefers_explicit_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INSPIRE_PLAYWRIGHT_PROXY", "socks5://127.0.0.1:1080")
    monkeypatch.setenv("https_proxy", "http://127.0.0.1:8888")

    assert get_playwright_proxy() == {"server": "socks5://127.0.0.1:1080"}


def test_get_playwright_proxy_auto_splits_qizhi_8888_to_1080(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INSPIRE_BASE_URL", "https://qz.sii.edu.cn")
    monkeypatch.setenv("http_proxy", "http://127.0.0.1:8888")

    assert get_playwright_proxy() == {"server": "socks5://127.0.0.1:1080"}


def test_get_playwright_proxy_falls_back_to_http_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INSPIRE_BASE_URL", "https://example.com")
    monkeypatch.setenv("https_proxy", "http://127.0.0.1:7897")

    assert get_playwright_proxy() == {"server": "http://127.0.0.1:7897"}
