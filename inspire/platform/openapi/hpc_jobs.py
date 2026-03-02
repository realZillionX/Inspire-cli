"""HPC job helpers for the Inspire OpenAPI client."""

from __future__ import annotations

from typing import Any, Dict

from inspire.platform.openapi.errors import InspireAPIError, _translate_api_error


def create_hpc_job(
    api,  # noqa: ANN001
    *,
    name: str,
    logic_compute_group_id: str,
    project_id: str,
    workspace_id: str,
    image: str,
    image_type: str,
    entrypoint: str,
    spec_id: str,
    instance_count: int = 1,
    task_priority: int = 6,
    number_of_tasks: int = 1,
    cpus_per_task: int = 1,
    memory_per_cpu: int = 4,
    enable_hyper_threading: bool = False,
) -> Dict[str, Any]:
    """Create an HPC job via /openapi/v1/hpc_jobs/create."""
    api._check_authentication()
    api._validate_required_params(
        name=name,
        logic_compute_group_id=logic_compute_group_id,
        project_id=project_id,
        workspace_id=workspace_id,
        image=image,
        image_type=image_type,
        entrypoint=entrypoint,
        spec_id=spec_id,
    )

    payload = {
        "name": name,
        "logic_compute_group_id": logic_compute_group_id,
        "project_id": project_id,
        "workspace_id": workspace_id,
        "image": image,
        "image_type": image_type,
        "entrypoint": entrypoint,
        "spec_id": spec_id,
        "instance_count": instance_count,
        "task_priority": task_priority,
        "number_of_tasks": number_of_tasks,
        "cpus_per_task": cpus_per_task,
        "memory_per_cpu": memory_per_cpu,
        "enable_hyper_threading": enable_hyper_threading,
    }

    result = api._make_request("POST", api.endpoints.HPC_JOB_CREATE, payload)
    if result.get("code") == 0:
        return result

    error_code = result.get("code")
    error_msg = result.get("message", "Unknown error")
    friendly_msg = _translate_api_error(error_code, error_msg)
    raise InspireAPIError(f"Failed to create HPC job: {friendly_msg}")


def get_hpc_job_detail(api, job_id: str) -> Dict[str, Any]:  # noqa: ANN001
    """Get HPC job details via /openapi/v1/hpc_jobs/detail."""
    api._check_authentication()
    api._validate_required_params(job_id=job_id)

    payload = {"job_id": job_id}
    result = api._make_request("POST", api.endpoints.HPC_JOB_DETAIL, payload)
    if result.get("code") == 0:
        return result

    error_code = result.get("code")
    error_msg = result.get("message", "Unknown error")
    friendly_msg = _translate_api_error(error_code, error_msg)
    raise InspireAPIError(f"Failed to get HPC job details: {friendly_msg}")


def stop_hpc_job(api, job_id: str) -> bool:  # noqa: ANN001
    """Stop HPC job via /openapi/v1/hpc_jobs/stop."""
    api._check_authentication()
    api._validate_required_params(job_id=job_id)

    payload = {"job_id": job_id}
    result = api._make_request("POST", api.endpoints.HPC_JOB_STOP, payload)
    if result.get("code") == 0:
        return True

    error_code = result.get("code")
    error_msg = result.get("message", "Unknown error")
    friendly_msg = _translate_api_error(error_code, error_msg)
    raise InspireAPIError(f"Failed to stop HPC job: {friendly_msg}")


__all__ = ["create_hpc_job", "get_hpc_job_detail", "stop_hpc_job"]
