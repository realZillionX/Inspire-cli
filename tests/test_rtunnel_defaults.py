from __future__ import annotations

from inspire.config.rtunnel_defaults import default_rtunnel_download_url


def test_default_rtunnel_download_url_linux_amd64() -> None:
    assert default_rtunnel_download_url(system="Linux", machine="x86_64").endswith(
        "/rtunnel-linux-amd64.tar.gz"
    )


def test_default_rtunnel_download_url_darwin_arm64() -> None:
    assert default_rtunnel_download_url(system="Darwin", machine="arm64").endswith(
        "/rtunnel-darwin-arm64.tar.gz"
    )


def test_default_rtunnel_download_url_windows_arm64() -> None:
    assert default_rtunnel_download_url(system="Windows", machine="aarch64").endswith(
        "/rtunnel-windows-arm64.zip"
    )
