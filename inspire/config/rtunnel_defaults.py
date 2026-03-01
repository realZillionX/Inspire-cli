"""Platform-aware defaults for rtunnel client binaries."""

from __future__ import annotations

import platform

RTUNNEL_RELEASE_BASE_URL = "https://github.com/Sarfflow/rtunnel/releases/download/nightly"


def _normalize_arch(machine: str) -> str:
    machine_norm = str(machine or "").strip().lower()
    if machine_norm in {"arm64", "aarch64"}:
        return "arm64"
    return "amd64"


def _normalize_os(system: str) -> str:
    system_norm = str(system or "").strip().lower()
    if system_norm.startswith("darwin"):
        return "darwin"
    if system_norm.startswith("linux"):
        return "linux"
    if system_norm.startswith(("windows", "mingw", "msys", "cygwin")):
        return "windows"
    # Fallback keeps existing Linux behavior for unknown hosts.
    return "linux"


def default_rtunnel_download_url(*, system: str | None = None, machine: str | None = None) -> str:
    """Return the default nightly rtunnel archive URL for the local platform."""
    os_part = _normalize_os(system or platform.system())
    arch_part = _normalize_arch(machine or platform.machine())
    ext = "zip" if os_part == "windows" else "tar.gz"
    return f"{RTUNNEL_RELEASE_BASE_URL}/rtunnel-{os_part}-{arch_part}.{ext}"


__all__ = ["RTUNNEL_RELEASE_BASE_URL", "default_rtunnel_download_url"]
