"""Local infrastructure commands; only Docker and Python's standard library."""

import argparse
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ("kafka", "postgres", "jobmanager", "taskmanager")
COMMANDS = tuple(
    f"stack-{name}" for name in ("build", "up", "status", "smoke", "down", "reset")
)


class StackError(Exception):
    """An actionable local-stack failure."""


def check_external_kafka(port: int) -> None:
    """Read-only Metadata v4 request: verify the host's advertised broker address.

    Wire fields: Apache Kafka 4.2.2 MetadataRequest/MetadataResponse.json.
    Empty topics + AllowAutoTopicCreation=false cannot create application data.
    """
    request = struct.pack(">hhih", 3, 4, 19, 4) + b"soly" + struct.pack(">i?", 0, False)

    def receive(connection: socket.socket, size: int) -> bytes:
        result = bytearray()
        while len(result) < size:
            part = connection.recv(size - len(result))
            if not part:
                raise StackError("Kafka closed the host metadata connection.")
            result.extend(part)
        return bytes(result)

    with socket.create_connection(("127.0.0.1", port), timeout=5) as connection:
        connection.sendall(struct.pack(">i", len(request)) + request)
        size = struct.unpack(">i", receive(connection, 4))[0]
        if not 12 <= size <= 1024 * 1024:
            raise StackError("Unexpected Kafka metadata response size.")
        response = receive(connection, size)
    try:
        correlation, _, brokers = struct.unpack_from(">iii", response)
        if correlation != 19 or brokers != 1:
            raise StackError("Expected one broker in host Kafka metadata.")
        host_size = struct.unpack_from(">h", response, 16)[0]
        if host_size < 1:
            raise StackError("Invalid Kafka advertised hostname.")
        host = response[18 : 18 + host_size].decode("utf-8")
        advertised_port = struct.unpack_from(">i", response, 18 + host_size)[0]
    except (struct.error, UnicodeError) as error:
        raise StackError("Invalid Kafka metadata response.") from error
    if (host, advertised_port) != ("localhost", port):
        raise StackError(
            f"Kafka advertises {host}:{advertised_port}, expected localhost:{port}."
        )
    print(f"Host Kafka metadata OK: localhost:{port}", flush=True)


class Stack:
    def __init__(self, env_file: Path, project: str | None = None) -> None:
        docker = shutil.which("docker")
        if docker is None:
            raise StackError(
                "Docker is missing. Use Docker Desktop with Linux containers, or "
                "run ./dev.sh inside WSL2 with Docker Engine and the Compose plugin."
            )
        self.docker = docker
        self.env = dict(os.environ)
        self.timeout = 180
        self.password = ""
        self.env_file = env_file.resolve()
        if not self.env_file.is_file():
            raise StackError("Copy .env.example to .env, or pass --env-file PATH.")
        self.base = [
            self.docker,
            "compose",
            "--profile",
            "tools",
            "--project-directory",
            str(ROOT),
            "--file",
            str(ROOT / "compose.yml"),
            "--env-file",
            str(self.env_file),
        ]
        if project is not None:
            if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", project):
                raise StackError(
                    "Project names must use lowercase letters/digits, - or _."
                )
            self.base += ["--project-name", project]
        try:
            compose_version = self.call(
                [self.docker, "compose", "version", "--short"]
            ).stdout.strip()
        except subprocess.CalledProcessError as error:
            raise StackError(
                "Install a current Docker Compose plugin (docker compose)."
            ) from error
        version_match = re.match(r"v?(\d+)\.(\d+)", compose_version)
        if not version_match or tuple(map(int, version_match.groups())) < (2, 24):
            raise StackError("Docker Compose 2.24 or newer is required.")
        info = json.loads(
            self.call([self.docker, "info", "--format", "{{json .}}"]).stdout
        )
        if info.get("OSType") != "linux" or info.get("Architecture") not in {
            "x86_64",
            "amd64",
        }:
            raise StackError("This stack requires a Linux amd64 Docker Engine.")
        # Never print rendered configuration: it contains the runtime DB password.
        self.config: dict[str, Any] = json.loads(
            self.compose("config", "--format", "json").stdout
        )
        self.project: str = self.config["name"]
        self.password = str(
            self.config["services"]["postgres"]["environment"]["POSTGRES_PASSWORD"]
        )
        self.timeout = int(self.config["x-soly-stack"]["timeout"])
        if self.timeout < 1:
            raise StackError("SOLY_STACK_TIMEOUT must be a positive number of seconds.")
        topic_env = self.config["services"]["kafka-init"]["environment"]
        self.topic = str(topic_env["SOLY_KAFKA_TOPIC"])
        partitions = str(topic_env["SOLY_KAFKA_PARTITIONS"])
        if not re.fullmatch(r"[a-zA-Z0-9._-]{1,249}", self.topic) or self.topic in {
            ".",
            "..",
        }:
            raise StackError("Invalid SOLY_KAFKA_TOPIC.")
        if not re.fullmatch(r"[1-9][0-9]*", partitions):
            raise StackError("SOLY_KAFKA_PARTITIONS must be a positive integer.")

    def call(
        self,
        command: list[str],
        *,
        input_text: str | None = None,
        stream: bool = False,
        timeout: int | None = None,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=self.env,
            input=input_text,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=not stream,
            timeout=timeout or self.timeout,
            check=False,
        )
        if result.returncode:
            if result.stderr:
                # config errors can contain substituted values; never echo its output.
                if "config" not in command:
                    message = result.stderr
                    if self.password:
                        message = message.replace(self.password, "<redacted>")
                    print(message[-6000:], file=sys.stderr)
            raise subprocess.CalledProcessError(result.returncode, command)
        return result

    def compose(
        self,
        *arguments: str,
        input_text: str | None = None,
        stream: bool = False,
        timeout: int | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return self.call(
            [*self.base, *arguments],
            input_text=input_text,
            stream=stream,
            timeout=timeout,
        )

    def container(self, service: str) -> str:
        ids = self.compose("ps", "--all", "--quiet", service).stdout.split()
        if len(ids) != 1:
            raise StackError(f"Expected one {service} container; run stack-up.")
        return ids[0]

    def inspect(self, service: str) -> dict[str, Any]:
        value: dict[str, Any] = json.loads(
            self.call(
                [
                    self.docker,
                    "inspect",
                    self.container(service),
                ]
            ).stdout
        )[0]
        return value

    def build(self) -> str:
        if not (ROOT / "processing/Dockerfile").is_file():
            raise StackError(
                "Initialize the pinned submodules: git submodule update --init --recursive."
            )
        commit = self.call(
            ["git", "-C", str(ROOT / "processing"), "rev-parse", "HEAD"]
        ).stdout.strip()
        # Compare content, including staged edits; Windows and WSL share no stat cache.
        dirty = (
            self.call(
                [
                    "git",
                    "-C",
                    str(ROOT / "processing"),
                    "diff",
                    "--name-only",
                    "HEAD",
                    "--",
                ]
            ).stdout
            + self.call(
                [
                    "git",
                    "-C",
                    str(ROOT / "processing"),
                    "ls-files",
                    "--others",
                    "--exclude-standard",
                ]
            ).stdout
        )
        if dirty:
            raise StackError(
                "Processing has local changes. Build from a clean, pinned service checkout."
            )
        pinned = self.call(["git", "ls-tree", "HEAD", "processing"]).stdout.split()
        if len(pinned) < 3 or pinned[2] != commit:
            raise StackError(
                "Processing differs from the main repository's pinned commit."
            )
        with tempfile.TemporaryDirectory(prefix="soly-stack-build-") as directory:
            iid = Path(directory) / "image-id"
            self.call(
                [
                    self.docker,
                    "build",
                    "--platform",
                    "linux/amd64",
                    "--iidfile",
                    str(iid),
                    "--tag",
                    f"{self.project}-processing:local-stack",
                    str(ROOT / "processing"),
                ],
                stream=True,
                timeout=3600,
            )
            image = iid.read_text(encoding="utf-8").strip()
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", image):
            raise StackError(
                "Docker did not return a content-addressed Processing image ID."
            )
        self.env["SOLY_PROCESSING_IMAGE"] = image
        print(f"Processing commit {commit}; image {image}", flush=True)
        return image

    def initialize_topic(self) -> None:
        result = self.compose("run", "--rm", "--no-deps", "kafka-init")
        print(result.stdout.strip(), flush=True)

    def registered(self) -> dict[str, Any]:
        result = self.compose(
            "exec",
            "-T",
            "jobmanager",
            "/opt/python/bin/python3",
            "-c",
            "import urllib.request; print(urllib.request.urlopen("
            "'http://127.0.0.1:8081/taskmanagers', timeout=3).read().decode())",
            timeout=10,
        )
        value: dict[str, Any] = json.loads(result.stdout)
        return value

    def wait_registered(self) -> None:
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                managers = self.registered().get("taskmanagers", [])
                if len(managers) == 1:
                    print(
                        f"One TaskManager registered: {managers[0]['id']}", flush=True
                    )
                    return
            except (
                subprocess.CalledProcessError,
                subprocess.TimeoutExpired,
                ValueError,
            ):
                pass
            if time.monotonic() >= deadline:
                raise StackError(
                    "Timed out waiting for exactly one registered TaskManager. Run stack-status and docker compose logs."
                )
            time.sleep(2)

    def up(self) -> None:
        self.build()
        try:
            self.compose(
                "up",
                "--detach",
                "--wait",
                "--wait-timeout",
                str(self.timeout),
                *SERVICES,
                stream=True,
                timeout=self.timeout + 60,
            )
        except subprocess.CalledProcessError as error:
            print(
                "Stack start failed: check free host ports and container logs. Data volumes were preserved.",
                file=sys.stderr,
            )
            raise error
        self.initialize_topic()
        self.wait_registered()

    def status(self) -> None:
        print(self.compose("ps", "--all").stdout, end="")
        self.assert_ready()
        self.initialize_topic_description()
        print(json.dumps(self.registered(), sort_keys=True))

    def assert_ready(self) -> None:
        for service in SERVICES:
            state = self.inspect(service)["State"]
            if (
                not state.get("Running")
                or state.get("Health", {}).get("Status", "healthy") != "healthy"
            ):
                raise StackError(
                    f"{service} is not ready; run stack-up and inspect logs."
                )
        if len(self.registered().get("taskmanagers", [])) != 1:
            raise StackError("Expected exactly one registered TaskManager.")

    def kafka(self, tool: str, *arguments: str, input_text: str | None = None) -> str:
        return self.compose(
            "exec",
            "-T",
            "kafka",
            f"/opt/kafka/bin/{tool}.sh",
            "--bootstrap-server",
            "kafka:19092",
            *arguments,
            input_text=input_text,
            timeout=60,
        ).stdout

    def initialize_topic_description(self) -> None:
        print(self.kafka("kafka-topics", "--describe", "--topic", self.topic).strip())

    def sql(self, statement: str) -> str:
        return self.compose(
            "exec",
            "-T",
            "postgres",
            "sh",
            "-c",
            'PGPASSWORD="$POSTGRES_PASSWORD" psql -X -h 127.0.0.1 '
            '-U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -At',
            input_text=statement,
            timeout=30,
        ).stdout.strip()

    def smoke(self) -> None:
        self.assert_ready()
        for service in ("kafka", "postgres"):
            info = self.inspect(service)
            expected_digest = self.config["services"][service]["image"].rsplit("@", 1)[
                -1
            ]
            if info["Config"]["Image"].rsplit("@", 1)[-1] != expected_digest:
                raise StackError(
                    f"{service} is not running the pinned manifest digest."
                )
            print(
                f"{service}: manifest {expected_digest}; image {info['Image']}",
                flush=True,
            )
        self.initialize_topic_description()
        if self.sql("SELECT 1;\n") != "1":
            raise StackError("PostgreSQL did not return SELECT 1 = 1.")
        ids = [self.inspect(role)["Image"] for role in ("jobmanager", "taskmanager")]
        if ids[0] != ids[1]:
            raise StackError("Flink roles use different image IDs.")
        lock = json.loads(
            (ROOT / "processing/connectors/jars.lock.json").read_text(encoding="utf-8")
        )
        probe = (ROOT / "scripts/stack_probe.py").read_text(encoding="utf-8")
        reports = []
        for role in ("jobmanager", "taskmanager"):
            report = json.loads(
                self.compose(
                    "exec",
                    "-T",
                    role,
                    "/opt/python/bin/python3",
                    "-",
                    json.dumps(lock),
                    input_text=probe,
                    timeout=30,
                ).stdout
            )
            reports.append(report)
            print(f"{role}: image {ids[0]}; {json.dumps(report, sort_keys=True)}")
        if reports[0] != reports[1]:
            raise StackError("Flink role runtime/connector configuration differs.")
        self.call(
            [
                self.docker,
                "run",
                "--rm",
                "--network",
                "none",
                "--hostname",
                "localhost",
                "--workdir",
                "/tmp",
                "--entrypoint",
                "/opt/python/bin/python3",
                ids[0],
                "-I",
                "/opt/soly/smoke_test.py",
            ],
            stream=True,
            timeout=180,
        )
        for service in ("kafka", "postgres", "jobmanager"):
            for port in self.config["services"][service]["ports"]:
                with socket.create_connection(
                    ("127.0.0.1", int(port["published"])), timeout=5
                ):
                    pass
        check_external_kafka(
            int(self.config["services"]["kafka"]["ports"][0]["published"])
        )
        kafka_env = self.inspect("kafka")["Config"]["Env"]
        expected = self.config["services"]["kafka"]["environment"][
            "KAFKA_ADVERTISED_LISTENERS"
        ]
        if f"KAFKA_ADVERTISED_LISTENERS={expected}" not in kafka_env:
            raise StackError("Unexpected Kafka advertised listeners.")
        # Each run owns a separate transport-only topic; never pollute the configured topic.
        topic = f"soly-infra-probe-{uuid.uuid4().hex}"
        token = uuid.uuid4().hex
        self.kafka(
            "kafka-topics",
            "--create",
            "--topic",
            topic,
            "--partitions",
            "1",
            "--replication-factor",
            "1",
        )
        try:
            self.kafka(
                "kafka-console-producer", "--topic", topic, input_text=token + "\n"
            )
            actual = self.kafka(
                "kafka-console-consumer",
                "--topic",
                topic,
                "--from-beginning",
                "--max-messages",
                "1",
                "--timeout-ms",
                "30000",
            ).strip()
            if actual != token:
                raise StackError(
                    "Kafka transport round-trip returned an unexpected value."
                )
        finally:
            self.kafka("kafka-topics", "--delete", "--topic", topic)
        print(
            "Infrastructure smoke OK: Kafka, PostgreSQL, Flink registration and identical runtimes.",
            flush=True,
        )

    def down(self, *, reset: bool = False) -> None:
        arguments = ["down", "--timeout", "30"]
        if reset:
            arguments.append("--volumes")
        self.compose(*arguments, stream=True, timeout=120)


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=COMMANDS)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument(
        "--project-name", help="separate Compose project, network and volumes"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="explicitly confirm stack-reset data deletion",
    )
    args = parser.parse_args(arguments)
    if args.command == "stack-reset" and not args.yes:
        parser.error(
            "stack-reset deletes this project's data volumes; pass --yes explicitly"
        )
    if args.yes and args.command != "stack-reset":
        parser.error("--yes is only valid for stack-reset")
    try:
        instance = Stack(args.env_file, args.project_name)
        if args.command == "stack-reset":
            instance.down(reset=True)
        else:
            getattr(instance, args.command.removeprefix("stack-").replace("-", "_"))()
    except subprocess.CalledProcessError as error:
        print(
            f"Stack command failed (exit {error.returncode}). Check Docker/Compose configuration and logs.",
            file=sys.stderr,
        )
        return error.returncode if 0 < error.returncode < 256 else 1
    except (
        StackError,
        OSError,
        ValueError,
        KeyError,
        subprocess.TimeoutExpired,
    ) as error:
        print(f"Stack command failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
