"""A throwaway copy of the production dump in the local fdserver Postgres.

The dump is `fdserver/prod.dump`, refreshed by `fdserver/bin/pull_prod_to_dev.sh`.
It is never committed and never leaves this machine. Each sandbox restores it
into its own database and drops that database on shutdown; the shared
`familydiagram` dev database is never touched.
"""

import logging
import re
import subprocess
import time
import urllib.parse
from pathlib import Path

logger = logging.getLogger("sandbox.proddb")

CONTAINER = "fd-postgres"
SERVICE = "fd-postgres"
DUMP = "prod.dump"
COMPOSE = "docker-compose.yml"
RESTORE_TIMEOUT = 600


class ProdDB:
    def __init__(self, fdserver: Path, name: str):
        self.fdserver = Path(fdserver)
        self.name = name
        self.uri: str = None

    @property
    def dump(self) -> Path:
        return self.fdserver / DUMP

    def create(self) -> str:
        if not self.dump.is_file():
            raise RuntimeError(
                f"No production dump at {self.dump}. "
                f"Refresh it with {self.fdserver}/bin/pull_prod_to_dev.sh"
            )
        self._require_docker()
        self._require_container()

        user = self._exec("printenv", "POSTGRES_USER").strip()
        password = self._exec("printenv", "POSTGRES_PASSWORD").strip()
        port = self._host_port()

        self._psql(user, f'DROP DATABASE IF EXISTS "{self.name}" WITH (FORCE)')
        self._psql(user, f'CREATE DATABASE "{self.name}"')
        logger.info(f"restoring {self.dump} into {self.name}")
        with open(self.dump, "rb") as f:
            self._run(
                [
                    "docker",
                    "exec",
                    "-i",
                    CONTAINER,
                    "pg_restore",
                    "--no-acl",
                    "--no-owner",
                    "-U",
                    user,
                    "-d",
                    self.name,
                ],
                stdin=f,
                timeout=RESTORE_TIMEOUT,
            )
        self.uri = (
            f"postgresql://{urllib.parse.quote(user)}:"
            f"{urllib.parse.quote(password)}@127.0.0.1:{port}/{self.name}"
        )
        return self.uri

    def drop(self) -> None:
        if not self.uri:
            return
        user = self._exec("printenv", "POSTGRES_USER").strip()
        self._psql(user, f'DROP DATABASE IF EXISTS "{self.name}" WITH (FORCE)')
        logger.info(f"dropped {self.name}")
        self.uri = None

    def _require_docker(self) -> None:
        result = subprocess.run(
            ["docker", "info"], capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            raise RuntimeError(
                "Docker is not running — production data needs the fdserver Postgres. "
                "Start Docker Desktop (`open -a Docker`), then re-run."
            )

    def _require_container(self) -> None:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={CONTAINER}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if CONTAINER in result.stdout:
            return
        compose = self.fdserver / COMPOSE
        if not compose.is_file():
            raise RuntimeError(f"No {COMPOSE} at {compose}")
        logger.info(f"starting {SERVICE} from {compose}")
        self._run(
            ["docker", "compose", "-f", str(compose), "up", "-d", SERVICE], timeout=180
        )
        for _ in range(60):
            ready = subprocess.run(
                ["docker", "exec", CONTAINER, "pg_isready"],
                capture_output=True,
                timeout=30,
            )
            if ready.returncode == 0:
                return
            time.sleep(1)
        raise RuntimeError(f"{CONTAINER} did not become ready")

    def _host_port(self) -> int:
        out = self._run(["docker", "port", CONTAINER, "5432/tcp"], timeout=30)
        match = re.search(r":(\d+)\s*$", out.strip().splitlines()[0])
        if not match:
            raise RuntimeError(f"No host port published for {CONTAINER}:5432 ({out!r})")
        return int(match.group(1))

    def _psql(self, user: str, sql: str) -> str:
        return self._exec("psql", "-U", user, "-d", "postgres", "-c", sql)

    def _exec(self, *args: str) -> str:
        return self._run(["docker", "exec", CONTAINER, *args], timeout=120)

    def _run(self, cmd, stdin=None, timeout=60) -> str:
        result = subprocess.run(
            cmd, stdin=stdin, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"{' '.join(cmd)} failed ({result.returncode}): {result.stderr[-500:]}"
            )
        return result.stdout
