"""Exercise environment safeguards, command failures and both shell entry points."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import dev


def test_external_failure_is_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(dev, "ROOT", tmp_path)
    with pytest.raises(subprocess.CalledProcessError) as failure:
        dev.run([sys.executable, "-c", "raise SystemExit(37)"])
    assert failure.value.returncode == 37


def test_main_preserves_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise subprocess.CalledProcessError(23, ["check"])

    monkeypatch.setattr(sys, "argv", ["dev.py", "check", "--use-current-python"])
    monkeypatch.setattr(dev, "check", fail)
    monkeypatch.setattr(dev, "require_java", lambda: None)
    assert dev.main() == 23


def test_setup_never_uses_global_python(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "prefix", sys.base_prefix)
    monkeypatch.delenv("CI", raising=False)
    with pytest.raises(dev.DevError, match="virtual environment"):
        dev.interpreter(True, setup=True)


def test_wrong_version_is_actionable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "version_info", (3, 14, 0))
    with pytest.raises(dev.DevError, match="SOLY_PYTHON"):
        dev.require_version()


@pytest.mark.parametrize("version", [(3, 12, 0), (3, 12, 10), (3, 12, 15), (3, 12, 16)])
def test_local_python_3_12_patches_are_supported(
    version: tuple[int, int, int], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(sys, "version_info", version)
    dev.require_version()


@pytest.mark.parametrize("version", [(3, 12, 10), (3, 12, 16)])
def test_ci_requires_pinned_patch(
    version: tuple[int, int, int], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CI", "true")
    monkeypatch.setattr(sys, "version_info", version)
    with pytest.raises(dev.DevError, match="CI requires Python 3.12.15"):
        dev.require_version()


def test_ci_accepts_pinned_patch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CI", "true")
    monkeypatch.setattr(sys, "version_info", (3, 12, 15))
    dev.require_version()


def test_venv_accepts_any_python_3_12_patch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(dev, "ROOT", tmp_path)
    python = tmp_path / ".venv" / (
        "Scripts/python.exe" if os.name == "nt" else "bin/python"
    )
    python.parent.mkdir(parents=True)
    python.touch()
    (tmp_path / ".venv/pyvenv.cfg").write_text(
        "include-system-site-packages = false\n", encoding="utf-8"
    )
    commands: list[list[str]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(dev.subprocess, "run", fake_run)
    dev.validate_venv(python)
    assert "sys.version_info[:2] == (3, 12)" in commands[0][-1]


def test_setup_preserves_incomplete_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(dev, "ROOT", tmp_path)
    directory = tmp_path / ".venv"
    directory.mkdir()
    sentinel = directory / "keep.txt"
    sentinel.write_text("local data", encoding="utf-8")
    with pytest.raises(dev.DevError, match="incomplete"):
        dev.interpreter(False, setup=True)
    assert sentinel.read_text(encoding="utf-8") == "local data"


def test_setup_uses_hash_locks_and_processing_build_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []

    def record(command: list[str]) -> None:
        commands.append(command)

    monkeypatch.setattr(dev, "run", record)
    dev.setup("python with spaces")
    installs = [command for command in commands if "install" in command]
    locked = [command for command in installs if "-r" in command]
    assert all("--require-hashes" in command for command in locked)
    assert all(command[0] == "python with spaces" for command in commands)
    assert not any("--upgrade" in command for command in commands)
    if dev.PROCESSING:
        assert locked[0][-1] == "requirements/build.txt"
        assert "--only-binary=:all:" in locked[0]
        assert locked[1][-1] == "requirements/dev.txt"
        assert "--no-build-isolation" in locked[1]
        assert "--only-binary=:all:" not in locked[1]
    else:
        assert len(locked) == 1
        assert "--only-binary=:all:" in locked[0]
    editable = [command for command in installs if "-e" in command]
    assert len(editable) == int(dev.SERVICE)
    if editable:
        assert "--no-deps" in editable[0] and "--no-build-isolation" in editable[0]


def test_check_is_read_only_and_stops_at_first_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []
    monkeypatch.setattr(dev, "ROOT", tmp_path)

    def record(command: list[str], *, env: dict[str, str] | None = None) -> None:
        assert env is not None and env["PYTHONDONTWRITEBYTECODE"] == "1"
        commands.append(command)

    monkeypatch.setattr(dev, "run", record)
    dev.check(sys.executable)
    assert len(commands) == 5
    assert commands[0][2:] == ["pip", "check"]
    assert "no:cacheprovider" in commands[1]
    assert "--no-cache" in commands[2] and "--fix" not in commands[2]
    assert "--check" in commands[3]
    cache = Path(commands[4][commands[4].index("--cache-dir") + 1])
    assert not cache.is_relative_to(tmp_path) and not cache.exists()
    assert list(tmp_path.iterdir()) == []

    def fail(command: list[str], *, env: dict[str, str] | None = None) -> None:
        raise subprocess.CalledProcessError(9, command)

    monkeypatch.setattr(dev, "run", fail)
    with pytest.raises(subprocess.CalledProcessError):
        dev.check(sys.executable)


def test_processing_platform_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dev, "PROCESSING", True)
    monkeypatch.setattr(sys, "platform", "win32")
    with pytest.raises(dev.DevError, match="WSL2"):
        dev.require_platform()


def test_missing_java_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JAVA_HOME", raising=False)
    with pytest.raises(dev.DevError, match="JAVA_HOME"):
        dev.require_java()


def test_missing_docker_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _: None)
    with pytest.raises(dev.DevError, match="Docker is missing"):
        dev.docker_smoke()


@pytest.mark.parametrize("processing", [False, True])
def test_docker_keeps_smoke_isolation(
    processing: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []
    monkeypatch.setattr(dev, "PROCESSING", processing)
    monkeypatch.setattr(shutil, "which", lambda _: "/tool path/docker")
    monkeypatch.setattr(dev, "run", commands.append)
    dev.docker_smoke()
    assert "linux/amd64" in commands[0]
    assert commands[1][1:5] == ["run", "--rm", "--network", "none"]
    assert "--workdir" in commands[1] and "/tmp" in commands[1]
    assert "--read-only" in commands[1] if not processing else "-I" in commands[1]
    assert "--volume" not in commands[1] and "-v" not in commands[1]


@pytest.mark.parametrize("shell", ["sh", "pwsh"])
def test_wrappers_handle_spaces_arguments_and_exit_codes(
    shell: str,
    tmp_path: Path,
) -> None:
    if shell == "sh" and os.name == "nt":
        pytest.skip("Unix entry point is exercised on Unix")
    executable = shutil.which(shell)
    if executable is None:
        pytest.skip(f"{shell} is not installed")
    repo = tmp_path / "checkout with spaces"
    (repo / "scripts").mkdir(parents=True)
    extension = "sh" if shell == "sh" else "ps1"
    script = repo / f"dev.{extension}"
    shutil.copyfile(dev.ROOT / script.name, script)
    (repo / "scripts/dev.py").write_text(
        "import json, sys; print(json.dumps(sys.argv[1:])); sys.exit(23)",
        encoding="utf-8",
    )
    command = [executable]
    if shell == "pwsh":
        command += ["-NoProfile", "-File"]
    result = subprocess.run(
        [*command, str(script), "argument with spaces", "--use-current-python"],
        cwd=tmp_path,
        env={**os.environ, "SOLY_PYTHON": sys.executable},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 23, result.stdout + result.stderr
    assert json.loads(result.stdout) == ["argument with spaces", "--use-current-python"]


@pytest.mark.parametrize("shell", ["sh", "pwsh"])
@pytest.mark.parametrize(
    "arguments",
    [
        ["docker-smoke"],
        ["docker-smoke", "--use-current-python"],
        ["--use-current-python", "docker-smoke"],
    ],
)
def test_docker_wrapper_ignores_broken_venv(
    shell: str,
    arguments: list[str],
    tmp_path: Path,
) -> None:
    if os.name == "nt":
        pytest.skip("The executable test shim requires Unix")
    executable = shutil.which(shell)
    if executable is None:
        pytest.skip(f"{shell} is not installed")
    repo = tmp_path / "checkout with spaces"
    (repo / "scripts").mkdir(parents=True)
    extension = "sh" if shell == "sh" else "ps1"
    script = repo / f"dev.{extension}"
    shutil.copyfile(dev.ROOT / script.name, script)
    (repo / "scripts/dev.py").write_text(
        "import json, sys; print(json.dumps(sys.argv[1:])); sys.exit(23)",
        encoding="utf-8",
    )
    # Cover both venv locations selected by PowerShell on Unix.
    for relative in (".venv/bin/python", ".venv/Scripts/python.exe"):
        broken = repo / relative
        broken.parent.mkdir(parents=True, exist_ok=True)
        broken.write_text("#!/bin/sh\nexit 71\n", encoding="utf-8")
        broken.chmod(0o755)
    host = tmp_path / "host bin"
    host.mkdir()
    (host / "python3.12").symlink_to(sys.executable)
    env = {**os.environ, "PATH": str(host) + os.pathsep + os.environ["PATH"]}
    env.pop("SOLY_PYTHON", None)
    command = [executable]
    if shell == "pwsh":
        command += ["-NoProfile", "-File"]
    result = subprocess.run(
        [*command, str(script), *arguments],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 23, result.stdout + result.stderr
    assert json.loads(result.stdout) == arguments


@pytest.mark.parametrize("native_errors", [False, True])
@pytest.mark.parametrize("exit_code", [0, 23])
def test_powershell_preserves_exit_codes_and_caller_preference(
    native_errors: bool,
    exit_code: int,
    tmp_path: Path,
) -> None:
    executable = shutil.which("pwsh")
    if executable is None:
        pytest.skip("pwsh is not installed")
    repo = tmp_path / "checkout with spaces"
    (repo / "scripts").mkdir(parents=True)
    script = repo / "dev.ps1"
    shutil.copyfile(dev.ROOT / script.name, script)
    (repo / "scripts/dev.py").write_text(
        f"raise SystemExit({exit_code})",
        encoding="utf-8",
    )
    preference = "$true" if native_errors else "$false"
    command = (
        "$ErrorActionPreference = 'Stop'; "
        f"$PSNativeCommandUseErrorActionPreference = {preference}; "
        "& $env:SOLY_TEST_WRAPPER check; $code = $LASTEXITCODE; "
        f"if ($PSNativeCommandUseErrorActionPreference -ne {preference}) "
        "{ throw 'Wrapper changed caller preference' }; exit $code"
    )
    result = subprocess.run(
        [executable, "-NoProfile", "-Command", command],
        cwd=tmp_path,
        env={
            **os.environ,
            "SOLY_PYTHON": sys.executable,
            "SOLY_TEST_WRAPPER": str(script),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == exit_code, result.stdout + result.stderr
    assert "Cannot run Python" not in result.stderr
