"""A celery worker for one sandbox, sharing the sandbox's app config via FLASK_* env."""

import logging
import subprocess
import sys
import threading
from typing import Dict, List

logger = logging.getLogger("sandbox.celery")

START_TIMEOUT = 60
READY = "ready."


class CeleryWorker:
    def __init__(self, target: str, env: Dict[str, str]):
        self.target = target
        self.env = env
        self.process: subprocess.Popen = None
        self.lines: List[str] = []
        self._ready = threading.Event()

    def start(self) -> None:
        self.process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "celery",
                "-A",
                self.target,
                "worker",
                "--pool=solo",
                "--loglevel=info",
                "--without-gossip",
                "--without-mingle",
                "--without-heartbeat",
            ],
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        threading.Thread(target=self._read, daemon=True).start()
        if not self._ready.wait(START_TIMEOUT) or self.process.poll() is not None:
            tail = "\n".join(self.lines[-20:])
            self.stop()
            raise RuntimeError(
                f"celery worker ({self.target}) not ready after {START_TIMEOUT}s:\n{tail}"
            )
        logger.info(f"celery worker ready ({self.target})")

    def _read(self) -> None:
        for raw in self.process.stdout:
            line = raw.decode(errors="replace").rstrip("\n")
            self.lines.append(line)
            if READY in line:
                self._ready.set()
        self._ready.set()

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)
        self.process = None
