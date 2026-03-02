"""Browser (web-session) APIs for HPC jobs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from inspire.platform.web.browser_api.core import _browser_api_path, _get_base_url, _request_json
from inspire.platform.web.session import DEFAULT_WORKSPACE_ID, WebSession, get_web_session

__all__ = [
    "HPCJobInfo",
    "list_hpc_jobs",
]


@dataclass
class HPCJobInfo:
    """HPC job information."""

    job_id: str
    name: str
    status: str
    entrypoint: str
    created_at: str
    finished_at: Optional[str]
    created_by_name: str
    created_by_id: str
    project_id: str
    project_name: str
    compute_group_name: str
    workspace_id: str

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "HPCJobInfo":
        created_by = data.get("created_by", {}) if isinstance(data.get("created_by"), dict) else {}
        return cls(
            job_id=data.get("job_id", ""),
            name=data.get("name", ""),
            status=data.get("status", ""),
            entrypoint=data.get("entrypoint", data.get("command", "")),
            created_at=data.get("created_at", ""),
            finished_at=data.get("finished_at"),
            created_by_name=created_by.get("name", ""),
            created_by_id=created_by.get("id", ""),
            project_id=data.get("project_id", ""),
            project_name=data.get("project_name", ""),
            compute_group_name=data.get("logic_compute_group_name", ""),
            workspace_id=data.get("workspace_id", ""),
        )


def list_hpc_jobs(
    workspace_id: Optional[str] = None,
    created_by: Optional[str] = None,
    status: Optional[str] = None,
    page_num: int = 1,
    page_size: int = 50,
    session: Optional[WebSession] = None,
) -> tuple[list[HPCJobInfo], int]:
    """List HPC jobs using the browser API."""
    if session is None:
        session = get_web_session()

    if workspace_id is None:
        workspace_id = session.workspace_id or DEFAULT_WORKSPACE_ID

    body: dict[str, Any] = {
        "workspace_id": workspace_id,
        "page_num": page_num,
        "page_size": page_size,
    }
    if created_by:
        body["created_by"] = created_by
    if status:
        body["status"] = status

    data = _request_json(
        session,
        "POST",
        _browser_api_path("/hpc_jobs/list"),
        referer=f"{_get_base_url()}/jobs/highPerformanceComputing",
        body=body,
        timeout=30,
    )

    if data.get("code") != 0:
        raise ValueError(f"API error: {data.get('message')}")

    payload = data.get("data", {})
    jobs_data = payload.get("jobs")
    if not isinstance(jobs_data, list):
        jobs_data = payload.get("items")
    if not isinstance(jobs_data, list):
        jobs_data = []

    total = payload.get("total")
    if not isinstance(total, int):
        total = len(jobs_data)

    jobs = [HPCJobInfo.from_api_response(item) for item in jobs_data if isinstance(item, dict)]
    return jobs, total
