"""Stack safety and command boundary tests without a Docker daemon."""

import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from scripts import stack


def bare_stack() -> stack.Stack:
    instance = object.__new__(stack.Stack)
    instance.docker = "/tools with spaces/docker"
    instance.env = dict(os.environ)
    instance.base = [
        instance.docker,
        "compose",
        "--file",
        "/checkout with spaces/compose.yml",
    ]
    instance.password = "must-not-print"
    instance.timeout = 30
    instance.project = "soly19-validation-test"
    return instance


def test_reset_requires_explicit_flag_before_docker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        shutil, "which", lambda _: pytest.fail("Docker must not be invoked")
    )
    with pytest.raises(SystemExit) as error:
        stack.main(["stack-reset"])
    assert error.value.code == 2


def test_down_retains_volumes_reset_removes_only_project(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instance = bare_stack()
    commands = []

    def record(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", record)
    instance.down()
    instance.down(reset=True)
    assert commands[0] == [*instance.base, "down", "--timeout", "30"]
    assert commands[1] == [*commands[0], "--volumes"]
    assert all(
        "prune" not in command and "--rmi" not in command for command in commands
    )


def test_argument_boundaries_runtime_environment_and_secret_redaction(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    instance = bare_stack()

    def fail(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert command[-1] == "argument with spaces"
        assert kwargs["env"]["LOCAL_ONLY"] == "runtime-value"
        assert kwargs["cwd"] == stack.ROOT
        return subprocess.CompletedProcess(
            command, 23, "", "must-not-print: connection failed"
        )

    instance.env["LOCAL_ONLY"] = "runtime-value"
    monkeypatch.setattr(subprocess, "run", fail)
    with pytest.raises(subprocess.CalledProcessError) as error:
        instance.compose("argument with spaces")
    assert error.value.returncode == 23
    assert "must-not-print" not in capsys.readouterr().err


def test_configuration_failure_never_prints_substituted_secrets(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    instance = bare_stack()
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **kw: subprocess.CompletedProcess(a[0], 1, "", "unknown-password"),
    )
    with pytest.raises(subprocess.CalledProcessError):
        instance.compose("config", "--format", "json")
    assert "unknown-password" not in capsys.readouterr().err


def test_registration_timeout_and_late_success(monkeypatch: pytest.MonkeyPatch) -> None:
    instance = bare_stack()
    monkeypatch.setattr(instance, "registered", lambda: {"taskmanagers": []})
    times = iter([0, 31])
    monkeypatch.setattr(time, "monotonic", lambda: next(times))
    with pytest.raises(stack.StackError, match="Timed out"):
        instance.wait_registered()
    results = iter([{"taskmanagers": []}, {"taskmanagers": [{"id": "worker"}]}])
    monkeypatch.setattr(instance, "registered", lambda: next(results))
    monkeypatch.setattr(time, "monotonic", lambda: 0)
    monkeypatch.setattr(time, "sleep", lambda _: None)
    instance.wait_registered()


def test_missing_docker_actionable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _: None)
    with pytest.raises(stack.StackError, match="WSL2"):
        stack.Stack(Path(".env.example"))


def test_main_preserves_external_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: Any) -> None:
        raise subprocess.CalledProcessError(23, ["docker"])

    monkeypatch.setattr(stack, "Stack", fail)
    assert stack.main(["stack-status"]) == 23


def test_validation_refuses_other_or_existing_projects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.validate_stack import validate

    instance = bare_stack()
    instance.project = "soly"
    with pytest.raises(stack.StackError, match="own soly19-validation"):
        validate(instance)
    instance.project = "soly19-validation-existing"
    monkeypatch.setattr(
        instance,
        "call",
        lambda *a, **kw: subprocess.CompletedProcess([], 0, "existing", ""),
    )
    with pytest.raises(stack.StackError, match="refuses an existing"):
        validate(instance)


def test_main_entry_dispatch_without_venv(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(stack.ROOT / "scripts/dev.py"), "stack-reset"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2
    assert "--yes" in result.stderr
    assert "ModuleNotFoundError" not in result.stderr


def test_compose_uses_resolved_env_and_root_without_echo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_file = tmp_path / "config with spaces.env"
    env_file.write_text("local example", encoding="utf-8")
    calls = []
    config = {
        "name": "soly19-validation-config",
        "x-soly-stack": {"timeout": 17},
        "services": {
            "postgres": {"environment": {"POSTGRES_PASSWORD": "runtime"}},
            "kafka-init": {
                "environment": {
                    "SOLY_KAFKA_TOPIC": "custom",
                    "SOLY_KAFKA_PARTITIONS": "3",
                }
            },
        },
    }

    def fake(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if "info" in command:
            output = json.dumps({"OSType": "linux", "Architecture": "x86_64"})
        elif "config" in command:
            output = json.dumps(config)
        else:
            output = "5.8.0"
        return subprocess.CompletedProcess(command, 0, output, "")

    monkeypatch.setattr(shutil, "which", lambda _: "docker")
    monkeypatch.setattr(subprocess, "run", fake)
    instance = stack.Stack(env_file, "soly19-validation-config")
    assert instance.topic == "custom" and instance.timeout == 17
    assert calls[-1][calls[-1].index("--env-file") + 1] == str(env_file.resolve())
    assert str(stack.ROOT / "compose.yml") in calls[-1]


@pytest.mark.parametrize(
    "host,port,valid",
    [("localhost", 19092, True), ("kafka", 19092, False), ("localhost", 9092, False)],
)
def test_host_metadata_rejects_wrong_advertised_address(
    host: str,
    port: int,
    valid: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = (
        struct.pack(">iiiih", 19, 0, 1, 1, len(host))
        + host.encode()
        + struct.pack(">ih", port, -1)
    )
    mock = MagicMock()
    mock.__enter__.return_value = mock
    # Exercise partial frame delivery, not just a single successful recv.
    mock.recv.side_effect = [
        struct.pack(">i", len(response)),
        response[:10],
        response[10:],
    ]
    monkeypatch.setattr(socket, "create_connection", lambda *a, **kw: mock)
    if valid:
        stack.check_external_kafka(19092)
    else:
        with pytest.raises(stack.StackError, match="advertises"):
            stack.check_external_kafka(19092)


@pytest.mark.parametrize("shell", ["sh", "pwsh", "powershell"])
def test_stack_wrappers_skip_broken_venv_and_preserve_arguments(
    shell: str,
    tmp_path: Path,
) -> None:
    if shell == "sh" and os.name == "nt":
        pytest.skip("Unix entry point is tested on Linux")
    executable = shutil.which(shell)
    if executable is None:
        pytest.skip(f"{shell} is not installed")
    repo = tmp_path / "checkout with spaces"
    (repo / "scripts").mkdir(parents=True)
    extension = "sh" if shell == "sh" else "ps1"
    wrapper = repo / f"dev.{extension}"
    shutil.copyfile(stack.ROOT / wrapper.name, wrapper)
    (repo / "scripts/dev.py").write_text(
        "import json, sys; print(json.dumps(sys.argv[1:])); sys.exit(23)",
        encoding="utf-8",
    )
    for relative in (".venv/bin/python", ".venv/Scripts/python.exe"):
        broken = repo / relative
        broken.parent.mkdir(parents=True, exist_ok=True)
        broken.write_text("#!/bin/sh\nexit 71\n", encoding="utf-8")
        broken.chmod(0o755)
    env = dict(os.environ)
    env.pop("SOLY_PYTHON", None)
    arguments = ["stack-status", "--env-file", "config with spaces.env"]
    command = [executable]
    if shell != "sh":
        command += ["-NoProfile", "-File"]
    result = subprocess.run(
        [*command, str(wrapper), *arguments],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 23, result.stdout + result.stderr
    assert json.loads(result.stdout) == arguments
