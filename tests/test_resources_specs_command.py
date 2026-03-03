from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from inspire import config as config_module
from inspire.cli.main import main as cli_main


def _patch_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cfg = config_module.Config(
        username="user",
        password="pass",
        base_url="https://qz.sii.edu.cn",
        job_cache_path=str(tmp_path / "jobs.json"),
        log_cache_dir=str(tmp_path / "logs"),
    )
    cfg.workspaces = {
        "gpu": "ws-gpu",
    }
    monkeypatch.setattr(
        config_module.Config,
        "from_files_and_env",
        classmethod(lambda cls, **kwargs: (cfg, {})),
    )


def test_resources_specs_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_config(monkeypatch, tmp_path)

    from inspire.cli.commands.resources import resources_specs as specs_module

    class _DummySession:
        workspace_id = "ws-session-default"

    monkeypatch.setattr(specs_module, "get_web_session", lambda: _DummySession())
    monkeypatch.setattr(
        specs_module.browser_api_module,
        "list_notebook_compute_groups",
        lambda **kwargs: [
            {"logic_compute_group_id": "lcg-cpu-2", "name": "CPU资源-2"},
            {"id": "lcg-hpc-2", "name": "HPC-可上网区资源-2"},
        ],
    )

    def _fake_prices(**kwargs):
        gid = kwargs["logic_compute_group_id"]
        if gid == "lcg-cpu-2":
            return [
                {
                    "quota_id": "quota-cpu-55-500",
                    "cpu_count": 55,
                    "memory_size_gib": 500,
                    "gpu_count": 0,
                    "gpu_info": {"gpu_type_display": "CPU"},
                }
            ]
        return [
            {
                "quota_id": "quota-cpu-32-256",
                "cpu_count": 32,
                "memory_size_gib": 256,
                "gpu_count": 0,
                "gpu_info": {"gpu_type_display": "CPU"},
            }
        ]

    monkeypatch.setattr(specs_module.browser_api_module, "get_resource_prices", _fake_prices)

    runner = CliRunner()
    result = runner.invoke(cli_main, ["--json", "resources", "specs", "--workspace", "gpu"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["data"]["workspace_id"] == "ws-gpu"
    assert payload["data"]["total"] == 2
    first = payload["data"]["specs"][0]
    assert "logic_compute_group_id" in first
    assert "spec_id" in first
    assert "cpu_count" in first
    assert "memory_size_gib" in first
    assert "gpu_count" in first
    assert "gpu_type" in first


def test_resources_specs_include_empty(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_config(monkeypatch, tmp_path)

    from inspire.cli.commands.resources import resources_specs as specs_module

    class _DummySession:
        workspace_id = "ws-session-default"

    monkeypatch.setattr(specs_module, "get_web_session", lambda: _DummySession())
    monkeypatch.setattr(
        specs_module.browser_api_module,
        "list_notebook_compute_groups",
        lambda **kwargs: [
            {"logic_compute_group_id": "lcg-empty", "name": "Empty Group"},
        ],
    )
    monkeypatch.setattr(specs_module.browser_api_module, "get_resource_prices", lambda **kwargs: [])

    runner = CliRunner()
    result = runner.invoke(cli_main, ["--json", "resources", "specs", "--include-empty"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["data"]["total"] == 1
    row = payload["data"]["specs"][0]
    assert row["logic_compute_group_id"] == "lcg-empty"
    assert row["spec_id"] == ""
