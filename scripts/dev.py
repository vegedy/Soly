"""Development commands; keep each repository's copy independently usable."""

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

if sys.version_info < (3, 10):  # noqa: UP036 - bootstrap must explain old interpreters
    print(
        "Python 3.12.15 is required; set SOLY_PYTHON to its executable path.",
        file=sys.stderr,
    )
    sys.exit(1)

PROJECT = "soly"
ROOT = Path(__file__).resolve().parents[1]
VERSION = (3, 12, 15)
PROCESSING = PROJECT == "soly-processing"
SERVICE = PROJECT != "soly"


class DevError(Exception):
    """An actionable development-environment error."""


def run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    print("+ " + subprocess.list2cmdline(command), flush=True)
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def require_version() -> None:
    if sys.version_info[:3] != VERSION:
        raise DevError(
            f"Python 3.12.15 is required; got {platform.python_version()}. "
            "Install that version and set SOLY_PYTHON to its executable path."
        )


def require_platform() -> None:
    if PROCESSING and (
        sys.platform != "linux" or platform.machine().lower() not in {"x86_64", "amd64"}
    ):
        raise DevError(
            "Processing development requires Linux x86_64. On Windows use WSL2 "
            "and ./dev.sh inside Linux, or docker-smoke with Linux containers. "
            "Native Windows/macOS Processing is not supported."
        )


def require_java() -> None:
    java_home = os.environ.get("JAVA_HOME")
    if not java_home:
        raise DevError("Processing needs Java 17; set JAVA_HOME to its JDK directory.")
    java = Path(java_home) / "bin" / "java"
    if not java.is_file():
        raise DevError(f"JAVA_HOME has no bin/java: {java_home}")
    result = subprocess.run(
        [str(java), "-version"], check=True, capture_output=True, text=True
    )
    if not re.search(r'version "17(?:\.|\")', result.stdout + result.stderr):
        raise DevError(f"JAVA_HOME must select Java 17: {java_home}")


def venv_python() -> Path:
    directory = ROOT / ".venv"
    if directory.is_symlink():
        raise DevError(".venv must be a local directory, not a symbolic link.")
    return directory / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def validate_venv(python: Path) -> None:
    if not (ROOT / ".venv/pyvenv.cfg").is_file() or not python.is_file():
        raise DevError(
            ".venv is incomplete. Inspect it before moving it aside; run setup."
        )
    result = subprocess.run(
        [
            str(python),
            "-I",
            "-c",
            "import sys; sys.exit(0 if sys.version_info[:3] == (3, 12, 15) "
            "and sys.prefix != sys.base_prefix else 1)",
        ],
        cwd=ROOT,
        check=False,
    )
    if result.returncode:
        raise DevError(
            ".venv must use Python 3.12.15 without global site packages. "
            "Inspect it before moving it aside; run setup with SOLY_PYTHON set."
        )
    config = (ROOT / ".venv/pyvenv.cfg").read_text(encoding="utf-8").lower()
    if re.search(r"include-system-site-packages\s*=\s*true", config):
        raise DevError(".venv must not include global site packages.")


def interpreter(use_current: bool, *, setup: bool = False) -> str:
    if use_current:
        if setup and sys.prefix == sys.base_prefix and os.environ.get("CI") != "true":
            raise DevError(
                "setup --use-current-python requires a virtual environment or CI=true. "
                "Use setup without this option for a local .venv."
            )
        return sys.executable
    python = venv_python()
    if setup and not (ROOT / ".venv").exists():
        venv.EnvBuilder(with_pip=True).create(ROOT / ".venv")
    validate_venv(python)
    return str(python)


def setup(python: str) -> None:
    pip = [python, "-m", "pip", "install", "--require-hashes"]
    if PROCESSING:
        run([*pip, "--only-binary=:all:", "-r", "requirements/build.txt"])
        run([*pip, "--no-build-isolation", "-r", "requirements/dev.txt"])
    else:
        run([*pip, "--only-binary=:all:", "-r", "requirements/dev.txt"])
    if SERVICE:
        run(
            [
                python,
                "-m",
                "pip",
                "install",
                "--no-deps",
                "--no-build-isolation",
                "-e",
                ".[dev]",
            ]
        )
    run([python, "-m", "pip", "check"])


def check(python: str, *, integration: bool = False) -> None:
    # Put bytecode/tool caches outside the checkout; checks never format files.
    with tempfile.TemporaryDirectory(prefix="soly-check-") as cache:
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        if integration:
            run(
                [
                    python,
                    "-m",
                    "pytest",
                    "-p",
                    "no:cacheprovider",
                    "-m",
                    "service_copies",
                ],
                env=env,
            )
            return
        commands = [
            ["pip", "check"],
            ["pytest", "-p", "no:cacheprovider"],
            ["ruff", "check", "--no-cache", "."],
            ["ruff", "format", "--check", "--no-cache", "."],
            [
                "mypy",
                "--cache-dir",
                cache,
                *(["src"] if SERVICE else []),
                "tests",
                "scripts",
            ],
        ]
        for command in commands:
            run([python, "-m", *command], env=env)


def docker_smoke() -> None:
    docker = shutil.which("docker")
    if docker is None:
        raise DevError("Docker is missing. Install/start Docker with Linux containers.")
    image = f"{PROJECT}:dev-smoke"
    run([docker, "build", "--platform", "linux/amd64", "--tag", image, "."])
    command = [docker, "run", "--rm", "--network", "none"]
    if PROCESSING:
        command += [
            "--hostname",
            "localhost",
            "--workdir",
            "/tmp",
            "--entrypoint",
            "/opt/python/bin/python3",
            image,
            "-I",
            "/opt/soly/smoke_test.py",
        ]
    else:
        command += ["--read-only", "--workdir", "/tmp", image]
    run(command)


def main() -> int:
    commands = ["setup", "check", "format"]
    commands.append("docker-smoke" if SERVICE else "check-integration")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=commands)
    parser.add_argument(
        "--use-current-python",
        action="store_true",
        help="use the invoking interpreter (setup requires a venv or CI=true)",
    )
    args = parser.parse_args()
    try:
        # Docker uses the pinned image runtime, not the host Python/Java or .venv.
        if args.command == "docker-smoke":
            docker_smoke()
            return 0
        require_version()
        require_platform()
        if PROCESSING:
            require_java()
        python = interpreter(args.use_current_python, setup=args.command == "setup")
        if args.command == "setup":
            setup(python)
        elif args.command == "format":
            run([python, "-m", "ruff", "format", "--no-cache", "."])
        else:
            check(python, integration=args.command == "check-integration")
    except subprocess.CalledProcessError as error:
        print(f"Command failed (exit {error.returncode}).", file=sys.stderr)
        return error.returncode if 0 < error.returncode < 256 else 1
    except (DevError, OSError) as error:
        print(f"Development command failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
