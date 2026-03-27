import importlib
from types import SimpleNamespace

from click.testing import CliRunner

from inspire.cli.main import main as cli_main


def test_cli_help_includes_top_level_groups() -> None:
    runner = CliRunner()
    result = runner.invoke(cli_main, ["--help"])
    assert result.exit_code == 0
    assert "job" in result.output
    assert "notebook" in result.output
    assert "image" in result.output
    assert "resources" in result.output
    assert "tunnel" in result.output
    assert "hpc" in result.output


def test_job_help_includes_key_subcommands() -> None:
    runner = CliRunner()
    result = runner.invoke(cli_main, ["job", "--help"])
    assert result.exit_code == 0
    assert "create" in result.output
    assert "logs" in result.output


def test_bridge_help_explains_exec_and_scp_semantics() -> None:
    runner = CliRunner()
    result = runner.invoke(cli_main, ["bridge", "--help"])
    assert result.exit_code == 0
    assert "INSPIRE_TARGET_DIR" in result.output
    assert "Transfer files to/from Bridge via SCP." in result.output
    assert "never rebuilds tunnels" in result.output


def test_notebook_help_includes_key_subcommands() -> None:
    runner = CliRunner()
    result = runner.invoke(cli_main, ["notebook", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "status" in result.output
    assert "ssh" in result.output


def test_notebook_ssh_help_mentions_bootstrap_and_save_as() -> None:
    runner = CliRunner()
    result = runner.invoke(cli_main, ["notebook", "ssh", "--help"])
    assert result.exit_code == 0
    assert "bootstrap" in result.output.lower()
    assert "--save-as" in result.output
    assert "bridge ssh" in result.output
    assert "rebuilt automatically" in result.output


def test_hpc_help_includes_key_subcommands() -> None:
    runner = CliRunner()
    result = runner.invoke(cli_main, ["hpc", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "create" in result.output
    assert "status" in result.output
    assert "stop" in result.output


def test_resources_help_includes_key_subcommands() -> None:
    runner = CliRunner()
    result = runner.invoke(cli_main, ["resources", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "nodes" in result.output


def test_tunnel_help_includes_key_subcommands() -> None:
    runner = CliRunner()
    result = runner.invoke(cli_main, ["tunnel", "--help"])
    assert result.exit_code == 0
    assert "add" in result.output
    assert "list" in result.output
    assert "status" in result.output
    assert "notebook ssh <id> --save-as" in result.output
    assert "There is no ``tunnel start`` subcommand" in result.output


def test_sync_help_mentions_transport_model() -> None:
    runner = CliRunner()
    result = runner.invoke(cli_main, ["sync", "--help"])
    assert result.exit_code == 0
    assert "--transport" in result.output
    assert "--source" in result.output
    assert "bridge scp" not in result.output


def test_run_help_mentions_watch_implies_sync_and_priority_level() -> None:
    runner = CliRunner()
    result = runner.invoke(cli_main, ["run", "--help"])
    assert result.exit_code == 0
    assert "implies --sync" in result.output
    assert "priority_level" in result.output


def test_job_logs_help_mentions_ssh_fast_path_and_workflow_fallback() -> None:
    runner = CliRunner()
    result = runner.invoke(cli_main, ["job", "logs", "--help"])
    assert result.exit_code == 0
    assert "SSH tunnel fast path" in result.output
    assert "Otherwise, fetches logs via Gitea workflow" in result.output


def test_run_watch_announces_sync_before_submission(monkeypatch) -> None:
    run_module = importlib.import_module("inspire.cli.commands.run")
    runner = CliRunner()

    class FakeConfig:
        job_priority = None
        job_image = "docker.sii.shaipower.online/inspire-studio/demo:latest"
        target_dir = None
        remote_env = {}
        project_order = None
        project_shared_path_groups = None
        shm_size = None

        def get_expanded_cache_path(self) -> str:
            return "/tmp/cache.json"

    class FakeProject:
        project_id = "project-123"
        name = "demo-project"

        def get_quota_status(self) -> str:
            return ""

    fake_submission = SimpleNamespace(
        job_id="job-123",
        data={"job_id": "job-123"},
        result={"data": {"job_id": "job-123"}},
        log_path=None,
        wrapped_command="bash -c 'echo hi'",
        max_time_ms="1000",
    )

    monkeypatch.setattr(
        run_module.Config,
        "from_files_and_env",
        lambda *args, **kwargs: (FakeConfig(), None),
    )
    monkeypatch.setattr(
        run_module.AuthManager, "get_api", lambda *args, **kwargs: SimpleNamespace()
    )
    monkeypatch.setattr(run_module, "_check_uncommitted_changes", lambda: False)
    monkeypatch.setattr(run_module, "_run_inspire_subcommand", lambda args: 0)
    monkeypatch.setattr(run_module, "_exec_inspire_subcommand", lambda args: None)
    monkeypatch.setattr(
        run_module,
        "_resolve_run_resource_and_location",
        lambda *args, **kwargs: ("8xH200", "cuda12.8"),
    )
    monkeypatch.setattr(run_module, "select_workspace_id", lambda *args, **kwargs: "workspace-123")
    monkeypatch.setattr(
        run_module.job_submit,
        "select_project_for_workspace",
        lambda *args, **kwargs: (FakeProject(), None),
    )
    monkeypatch.setattr(
        run_module.job_submit,
        "submit_training_job",
        lambda *args, **kwargs: fake_submission,
    )
    monkeypatch.setattr(run_module.time, "sleep", lambda *args, **kwargs: None)

    result = runner.invoke(cli_main, ["run", "echo hi", "--watch", "--name", "demo-run"])

    assert result.exit_code == 0
    assert "Syncing code first (--watch implies --sync)." in result.output
    assert "Job created: job-123" in result.output
    assert "Check status with: inspire job status job-123" in result.output
