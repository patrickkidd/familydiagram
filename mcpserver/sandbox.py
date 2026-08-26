"""One sandbox backend: a btcopilot server plus the children it needs.

Owns a free port, a database (throwaway sqlite, a given postgres uri, or a
restore of the production dump), an optional private redis + celery worker, the
LLM stub, and the fdserver prompts. Every child process is this process's own
child and is torn down with it — nothing is ever matched by name or pattern.

The app, its config, its test routes and its seed profiles all come from
`btcopilot.testing`; this module only stands them up.
"""

import json
import logging
import os
import shutil
import sys
import tempfile
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Optional

import requests

from mcpserver.celeryworker import CeleryWorker
from mcpserver.checkouts import Checkouts
from mcpserver.ports import free_port
from mcpserver.proddb import ProdDB
from mcpserver.redisserver import RedisServer

logger = logging.getLogger("sandbox")

HEALTH_TIMEOUT = 30
CELERY_TARGET = "btcopilot.testing.celeryapp:celery"
NO_SEED = "none"

# Launcher → caller protocol, one line each on stdout once the backend is up.
READY_PREFIX = "READY:"
MANIFEST_PREFIX = "MANIFEST:"

# A seed file is either an explicit seed spec (plural lists) or a production
# export of one case (singular user + diagram, ids preserved). Both carry
# "discussions", so only the singular keys tell them apart.
EXPORT_KEYS = ("user", "diagram")


class Broker(str, Enum):
    Memory = "memory"
    Redis = "redis"


class Llm(str, Enum):
    Stub = "stub"
    Real = "real"


class Prompts(str, Enum):
    Auto = "auto"
    Off = "none"


class Db(str, Enum):
    Sqlite = "sqlite"
    Prod = "prod"


class Sandbox:
    def __init__(
        self,
        ticket: Optional[str] = None,
        port: Optional[int] = None,
        db: str = Db.Sqlite.value,
        seed: Optional[str] = None,
        broker: str = Broker.Memory.value,
        llm: str = Llm.Stub.value,
        prompts: str = Prompts.Auto.value,
        auto_auth_user: Optional[str] = None,
        hardware_uuid: Optional[str] = None,
        checkouts: Optional[Checkouts] = None,
    ):
        self.checkouts = checkouts or Checkouts.resolve(ticket)
        self.port = port or free_port()
        self.db = db
        self.seed = None if seed in (None, NO_SEED) else seed
        self.broker = Broker(broker)
        self.llm = Llm(llm)
        self.prompts = prompts
        self.auto_auth_user = auto_auth_user
        self.hardware_uuid = hardware_uuid
        self.dir = Path(tempfile.mkdtemp(prefix="fd_sandbox_"))
        self.redis: Optional[RedisServer] = None
        self.worker: Optional[CeleryWorker] = None
        self.proddb: Optional[ProdDB] = None
        self.manifest: dict = {}
        self._db_uri: Optional[str] = None
        self._broker: Optional[str] = None
        self._licensed = False
        self._app = None
        self._stopped = threading.Event()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    # -- configuration --

    def db_uri(self) -> str:
        """Restores the production dump when asked for it."""
        if self.db == Db.Prod.value:
            self.proddb = ProdDB(self.checkouts.fdserver.path, self._proddb_name())
            return self.proddb.create()
        if self.db == Db.Sqlite.value:
            return f"sqlite:///{self.dir / 'sandbox.db'}"
        if self.db.startswith(f"{Db.Sqlite.value}:"):
            directory = Path(self.db.split(":", 1)[1]).expanduser()
            directory.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{directory / 'sandbox.db'}"
        if "://" not in self.db:
            raise ValueError(
                f"--db {self.db}: expected 'sqlite', 'sqlite:<dir>', 'prod', or a database uri"
            )
        return self.db

    def _proddb_name(self) -> str:
        suffix = (self.checkouts.ticket or str(os.getpid())).lower().replace("-", "_")
        return f"fd_sandbox_{suffix}"

    def prompts_path(self) -> Optional[Path]:
        if self.prompts == Prompts.Off.value:
            return None
        if self.prompts == Prompts.Auto.value:
            return self.checkouts.prompts_path
        path = Path(self.prompts).expanduser()
        if not path.is_file():
            raise ValueError(f"--prompts {self.prompts}: no such file")
        return path

    def broker_url(self) -> Optional[str]:
        """Starts the private redis when one was asked for."""
        if self.broker is Broker.Memory:
            return None
        self.redis = RedisServer()
        return self.redis.start()

    def env(self) -> dict:
        """The environment btcopilot must see before it is imported at all.

        Starts the database and the broker it names, and keeps their urls for
        the app and the worker — nothing here can import btcopilot, because
        btcopilot binds the prompts path at import time.
        """
        self._db_uri = self.db_uri()
        self._broker = self.broker_url()

        result = os.environ.copy()
        result.pop("VIRTUAL_ENV", None)
        result.update(
            {
                "PYTHONUNBUFFERED": "1",
                "PYTHONPATH": self.pythonpath(),
                "BTCOPILOT_TEST_ROUTES": "1",
                "BTCOPILOT_LLM": self.llm.value,
            }
        )

        prompts = self.prompts_path()
        if prompts:
            result["FDSERVER_PROMPTS_PATH"] = str(prompts)
        else:
            result.pop("FDSERVER_PROMPTS_PATH", None)

        if self.auto_auth_user:
            result["FLASK_AUTO_AUTH_USER"] = self.auto_auth_user
        return result

    def pythonpath(self) -> str:
        return os.pathsep.join(
            [str(self.checkouts.btcopilot.path), os.environ.get("PYTHONPATH", "")]
        ).rstrip(os.pathsep)

    # -- lifecycle --

    def start(self) -> dict:
        """Serve in a background thread; return once health passes and seeding is done."""
        sys.path.insert(0, str(self.checkouts.btcopilot.path))
        os.environ.update(self.env())

        # btcopilot.personal.prompts binds FDSERVER_PROMPTS_PATH at import time and
        # the LLM stand-in reads BTCOPILOT_LLM, so btcopilot is imported only once
        # the environment above is complete and the checkout is on the path.
        from btcopilot.testing.sandbox import (
            BROKER_ENV,
            DB_URI_ENV,
            FD_DIR_ENV,
            create_sandbox_app,
        )

        self._app = create_sandbox_app(
            db_uri=self._db_uri, fd_dir=str(self.dir), broker=self._broker
        )
        self._blank_credentials()

        if self.redis:
            worker_env = os.environ.copy()
            worker_env.update(
                {
                    DB_URI_ENV: self._db_uri,
                    FD_DIR_ENV: str(self.dir),
                    BROKER_ENV: self._broker,
                }
            )
            self.worker = CeleryWorker(CELERY_TARGET, worker_env)
            self.worker.start()

        threading.Thread(target=self._serve, daemon=True).start()
        self._wait_for_health()

        seed = self._seed_login_user() or self._apply_seed()
        self.manifest = {
            "url": self.url,
            "port": self.port,
            "db": self._db_uri,
            "broker": self._broker or Broker.Memory.value,
            "llm": self.llm.value,
            "prompts": os.environ.get("FDSERVER_PROMPTS_PATH"),
            "dir": str(self.dir),
            "user": self._auto_auth(seed),
            "checkouts": self.checkouts.asdict(),
            "seed": seed,
        }
        return self.manifest

    def _blank_credentials(self) -> None:
        """Keep Patrick's real keys — and his bill — out of a stubbed sandbox.

        Flask loads ~/theapp/.env when app.run() starts, and every name it finds
        unset lands in the serving process. Naming them empty is what stops that,
        and btcopilot owns the list so the two repos cannot disagree about which
        providers a sandbox could otherwise reach. Imported here rather than in
        env() because importing btcopilot binds the prompts path.
        """
        if self.llm is not Llm.Stub:
            return
        from btcopilot.testing.credentials import BLANKED

        os.environ.update({name: "" for name in BLANKED})

    def _auto_auth(self, seed: Optional[dict]) -> Optional[str]:
        """Log in as the account the seed made, unless the caller named one.

        btcopilot's auth reads this per request, so setting it after the seed
        still reaches every later request.
        """
        if not self.auto_auth_user and seed:
            self.auto_auth_user = seed.get("primary_user")
        if self.auto_auth_user:
            os.environ["FLASK_AUTO_AUTH_USER"] = self.auto_auth_user
        return self.auto_auth_user

    def _serve(self) -> None:
        self._app.run(
            host="127.0.0.1",
            port=self.port,
            debug=False,
            use_reloader=False,
            threaded=True,
        )

    def _wait_for_health(self) -> None:
        deadline = time.time() + HEALTH_TIMEOUT
        while time.time() < deadline:
            try:
                response = requests.get(f"{self.url}/test/health", timeout=2)
            except requests.RequestException:
                time.sleep(0.2)
                continue
            if response.status_code == 200:
                logger.info(f"backend healthy on {self.url}")
                return
            raise RuntimeError(
                f"/test/health returned {response.status_code}: {response.text[:300]}"
            )
        raise RuntimeError(
            f"backend not healthy on {self.url} after {HEALTH_TIMEOUT}s "
            "(is BTCOPILOT_TEST_ROUTES honoured by this btcopilot checkout?)"
        )

    def _seed_login_user(self) -> Optional[dict]:
        """Seed the named login account before anything else, so it is the one
        holding this machine's licence. Returns None when no account was named,
        which leaves the profile's own first user as the account to sign in as.
        """
        if not self.auto_auth_user:
            return None
        first = self._seed("/test/seed", {"users": [{"username": self.auto_auth_user}]})
        self._apply_seed()
        return first

    def _apply_seed(self) -> Optional[dict]:
        """A profile expression, an explicit seed spec, or a production export."""
        if not self.seed:
            return None
        path = Path(self.seed).expanduser()
        if not path.is_file():
            return self._seed("/test/seed", {"profile": self.seed})
        body = json.loads(path.read_text())
        route = "/test/import" if any(k in body for k in EXPORT_KEYS) else "/test/seed"
        return self._seed(route, body)

    def _seed(self, route: str, body: dict) -> dict:
        """Licences land on THIS machine, or the apps open to a licence prompt.

        The app counts a licence as active only when one of its activations names
        a machine whose code is the app's own hardware uuid, so a seed that does
        not carry the caller's uuid produces rows that look licensed and behave
        unlicensed. Machine codes are globally unique, so only the first account
        seeded can hold it — which is why the login account goes first, and why
        only that first call is checked against the code the backend echoes back.
        """
        if self.hardware_uuid:
            body = {**body, "hardware_uuid": self.hardware_uuid}
        result = self.post(route, json=body)
        if self._licensed or not self.hardware_uuid:
            return result
        self._licensed = True
        used = result.get("hardware_uuid")
        if used != self.hardware_uuid:
            raise RuntimeError(
                f"{route} licensed the primary user to {used!r}, not this machine's "
                f"{self.hardware_uuid!r} — the apps would open unlicensed"
            )
        return result

    def post(self, route: str, **kwargs) -> dict:
        response = requests.post(f"{self.url}{route}", timeout=300, **kwargs)
        if response.status_code != 200:
            raise RuntimeError(
                f"POST {route} returned {response.status_code}: {response.text[:500]}"
            )
        return response.json()

    def wait(self) -> None:
        while not self._stopped.wait(1):
            pass

    def shutdown(self) -> None:
        self._stopped.set()
        if self.worker:
            self.worker.stop()
            self.worker = None
        if self.redis:
            self.redis.stop()
            self.redis = None
        if self.proddb:
            self.proddb.drop()
            self.proddb = None
        shutil.rmtree(self.dir, ignore_errors=True)
