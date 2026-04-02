"""Tests for debug report logging setup and error-path reporting."""

from __future__ import annotations

import json
import importlib
import logging
from pathlib import Path

import pytest
from click.testing import CliRunner
import click

from inspire.cli.context import EXIT_GENERAL_ERROR
from inspire.cli.logging_setup import clear_debug_logging, configure_debug_logging, redact_text
import inspire.cli.logging_setup as logging_setup
from inspire.cli.main import main as cli_main

cli_module = importlib.import_module("inspire.cli.main")


@pytest.fixture(autouse=True)
def _reset_logging_state() -> None:
    yield
    clear_debug_logging()


def test_redact_text_masks_common_sensitive_patterns() -> None:
    raw = (
        "Authorization: Bearer abc123\n"
        "token=abc123&x=1\n"
        '{"password":"s3cr3t","api_key":"xyz"}\n'
        "/jupyter/nb-1/mytoken/proxy/31337"
    )

    redacted = redact_text(raw)
    assert "abc123" not in redacted
    assert "s3cr3t" not in redacted
    assert "xyz" not in redacted
    assert "<redacted>" in redacted


def test_configure_debug_logging_creates_report_and_prunes(monkeypatch, tmp_path: Path) -> None:
    log_dir = tmp_path / "debug-logs"
    monkeypatch.setenv("INSPIRE_DEBUG_LOG_DIR", str(log_dir))

    log_dir.mkdir(parents=True, exist_ok=True)
    for idx in range(6):
        old_file = log_dir / f"inspire-debug-20250101-00000{idx}-1.log"
        old_file.write_text("old")

    report_path = configure_debug_logging(argv=["inspire", "--debug"], keep_logs=3)
    assert report_path is not None

    report = Path(report_path)
    assert report.exists()
    content = report.read_text(encoding="utf-8")
    assert "Debug session started" in content
    assert "argv=['inspire', '--debug']" in content

    remaining = sorted(log_dir.glob("inspire-debug-*.log"))
    assert len(remaining) <= 3


def test_configure_debug_logging_uses_unique_report_paths(monkeypatch, tmp_path: Path) -> None:
    log_dir = tmp_path / "debug-logs"
    monkeypatch.setenv("INSPIRE_DEBUG_LOG_DIR", str(log_dir))

    first = configure_debug_logging(argv=["inspire", "--debug"])
    clear_debug_logging()
    second = configure_debug_logging(argv=["inspire", "--debug"])
    clear_debug_logging()

    assert first is not None and second is not None
    assert first != second
    assert Path(first).exists()
    assert Path(second).exists()


def test_clear_debug_logging_restores_logger_state(monkeypatch, tmp_path: Path) -> None:
    log_dir = tmp_path / "debug-logs"
    monkeypatch.setenv("INSPIRE_DEBUG_LOG_DIR", str(log_dir))

    inspire_logger = logging.getLogger("inspire")
    original_level = inspire_logger.level
    original_propagate = inspire_logger.propagate

    clear_debug_logging()
    inspire_logger.setLevel(logging.WARNING)
    inspire_logger.propagate = True

    configure_debug_logging(argv=["inspire", "--debug"])
    assert inspire_logger.level == logging.DEBUG
    assert inspire_logger.propagate is False

    clear_debug_logging()
    assert inspire_logger.level == logging.WARNING
    assert inspire_logger.propagate is True

    inspire_logger.setLevel(original_level)
    inspire_logger.propagate = original_propagate


def test_debug_error_prints_report_path_in_human_mode(monkeypatch, tmp_path: Path) -> None:
    log_dir = tmp_path / "debug-logs"
    monkeypatch.setenv("INSPIRE_DEBUG_LOG_DIR", str(log_dir))

    missing = tmp_path / "missing-file.txt"
    runner = CliRunner()
    result = runner.invoke(cli_main, ["--debug", "bridge", "scp", str(missing), "/tmp/dst"])

    assert result.exit_code == EXIT_GENERAL_ERROR
    assert "Local path not found" in result.output
    assert "Debug report:" in result.output
    assert len(list(log_dir.glob("inspire-debug-*.log"))) == 1


def test_debug_error_keeps_json_output_clean(monkeypatch, tmp_path: Path) -> None:
    log_dir = tmp_path / "debug-logs"
    monkeypatch.setenv("INSPIRE_DEBUG_LOG_DIR", str(log_dir))

    missing = tmp_path / "missing-file.txt"
    runner = CliRunner()
    result = runner.invoke(
        cli_main,
        ["--debug", "--json", "bridge", "scp", str(missing), "/tmp/dst"],
    )

    assert result.exit_code == EXIT_GENERAL_ERROR
    payload = json.loads(result.output)
    assert payload["success"] is False
    assert "Debug report:" not in result.output
    assert len(list(log_dir.glob("inspire-debug-*.log"))) == 1


def test_configure_json_logging_suppresses_warning_output(capsys) -> None:
    inspire_logger = logging.getLogger("inspire")
    original_propagate = inspire_logger.propagate

    try:
        logging_setup._configure_json_logging()
        logging.getLogger("inspire.platform.web.session").warning("Any warning")
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""
    finally:
        for handler in list(inspire_logger.handlers):
            if getattr(handler, "_inspire_json_mode_handler", False):
                inspire_logger.removeHandler(handler)
                handler.close()
        inspire_logger.propagate = original_propagate


def test_configure_json_logging_disables_propagation_and_deduplicates_handler() -> None:
    inspire_logger = logging.getLogger("inspire")
    original_propagate = inspire_logger.propagate

    try:
        logging_setup._configure_json_logging()
        logging_setup._configure_json_logging()

        json_handlers = [
            handler
            for handler in inspire_logger.handlers
            if getattr(handler, "_inspire_json_mode_handler", False)
        ]
        assert inspire_logger.propagate is False
        assert len(json_handlers) == 1
        assert isinstance(json_handlers[0], logging.NullHandler)
    finally:
        for handler in list(inspire_logger.handlers):
            if getattr(handler, "_inspire_json_mode_handler", False):
                inspire_logger.removeHandler(handler)
                handler.close()
        inspire_logger.propagate = original_propagate


def test_cli_unhandled_exception_in_json_mode_emits_json(monkeypatch, capsys) -> None:
    def boom(*_args, **_kwargs) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(cli_module.main, "main", boom)

    with pytest.raises(SystemExit) as exc:
        cli_module.cli(["--json"])

    assert exc.value.code == EXIT_GENERAL_ERROR
    payload = json.loads(capsys.readouterr().err)
    assert payload["success"] is False
    assert payload["error"]["type"] == "UnhandledError"
    assert payload["error"]["message"] == "boom"


def test_cli_unhandled_exception_in_human_mode_emits_text(monkeypatch, capsys) -> None:
    def boom(*_args, **_kwargs) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(cli_module.main, "main", boom)

    with pytest.raises(SystemExit) as exc:
        cli_module.cli(["job", "list"])

    assert exc.value.code == EXIT_GENERAL_ERROR
    assert "Error: boom" in capsys.readouterr().err


def test_cli_abort_in_json_mode_emits_json(monkeypatch, capsys) -> None:
    def abort(*_args, **_kwargs) -> None:
        raise click.Abort()

    monkeypatch.setattr(cli_module.main, "main", abort)

    with pytest.raises(SystemExit) as exc:
        cli_module.cli(["--json", "job", "list"])

    assert exc.value.code == EXIT_GENERAL_ERROR
    payload = json.loads(capsys.readouterr().err)
    assert payload["success"] is False
    assert payload["error"]["type"] == "Abort"
    assert payload["error"]["message"] == "Aborted!"


def test_cli_usage_error_with_global_json_emits_json(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        cli_module.cli(["--json", "resources", "--badopt"])

    assert exc.value.code == 2
    payload = json.loads(capsys.readouterr().err)
    assert payload["success"] is False
    assert payload["error"]["type"] == "NoSuchOption"
    assert payload["error"]["message"] == "No such option: --badopt"


def test_cli_usage_error_with_subcommand_json_stays_human(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        cli_module.cli(["tunnel", "list", "--badopt", "--json"])

    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "Usage:" in err
    assert "No such option: --badopt" in err


def test_cli_no_such_command_with_json_emits_json(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        cli_module.cli(["--json", "does-not-exist"])

    assert exc.value.code == 2
    payload = json.loads(capsys.readouterr().err)
    assert payload["success"] is False
    assert payload["error"]["type"] == "UsageError"
    assert payload["error"]["message"] == "No such command 'does-not-exist'."


def test_cli_no_such_command_with_trailing_json_stays_human(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        cli_module.cli(["does-not-exist", "--json"])

    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "Usage:" in err
    assert "No such command 'does-not-exist'." in err


def test_cli_no_such_subcommand_with_trailing_json_stays_human(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        cli_module.cli(["notebook", "topp", "--json"])

    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "Usage:" in err
    assert "No such command 'topp'." in err


def test_cli_missing_parameter_with_subcommand_json_stays_human(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        cli_module.cli(["tunnel", "remove", "--json"])

    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "Usage:" in err
    assert "No such option: --json" in err


def test_cli_bad_parameter_with_subcommand_json_stays_human(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        cli_module.cli(["tunnel", "list", "--json", "--limit", "abc"])

    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "Usage:" in err
    assert "No such option: --json" in err


@pytest.mark.parametrize(
    "argv",
    [
        ["config", "check", "--json", "--badopt"],
        ["config", "show", "--json", "--badopt"],
        ["init", "--json", "--badopt"],
        ["project", "select", "--json", "--badopt"],
    ],
)
def test_cli_usage_error_with_local_json_alias_stays_human(argv, capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        cli_module.cli(argv)

    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "Usage:" in err
    assert "No such option: --json" in err


def test_click_command_invocation_restores_logger_state() -> None:
    inspire_logger = logging.getLogger("inspire")
    original_level = inspire_logger.level
    original_propagate = inspire_logger.propagate

    runner = CliRunner()
    result = runner.invoke(cli_main, ["--json", "config", "show"])

    assert result.exit_code == 0
    assert not any(
        getattr(handler, "_inspire_json_mode_handler", False) for handler in inspire_logger.handlers
    )
    assert inspire_logger.level == original_level
    assert inspire_logger.propagate == original_propagate


def test_cli_json_parse_error_restores_logger_state() -> None:
    inspire_logger = logging.getLogger("inspire")
    original_level = inspire_logger.level
    original_propagate = inspire_logger.propagate

    with pytest.raises(SystemExit) as exc:
        cli_module.cli(["--json", "config", "show", "--badopt"])

    assert exc.value.code == 2
    assert not any(
        getattr(handler, "_inspire_json_mode_handler", False) for handler in inspire_logger.handlers
    )
    assert inspire_logger.level == original_level
    assert inspire_logger.propagate == original_propagate


def test_cli_usage_error_without_json_stays_human(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        cli_module.cli(["resources", "--badopt"])

    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "No such option: --badopt" in err
    assert "Usage:" in err


def test_cli_invalid_json_position_stays_human(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        cli_module.cli(["resources", "--badopt", "--json"])

    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "No such option: --badopt" in err
    assert "Usage:" in err


@pytest.mark.parametrize(
    "argv,expected_error",
    [
        (["--debug", "resources", "--json"], "No such option: --json"),
        (
            ["--profile", "foo", "resources", "--badopt", "--json"],
            "No such option: --badopt",
        ),
    ],
)
def test_cli_invalid_json_position_with_prefixed_globals_stays_human(
    argv, expected_error, capsys
) -> None:
    with pytest.raises(SystemExit) as exc:
        cli_module.cli(argv)

    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "Usage:" in err
    assert expected_error in err
