"""A private redis for one sandbox: own port, no persistence, own child process."""

import logging
import socket
import subprocess
import time

from mcpserver.ports import free_port

logger = logging.getLogger("sandbox.redis")

START_TIMEOUT = 15


class RedisServer:
    def __init__(self, port: int = None):
        self.port = port or free_port()
        self.process: subprocess.Popen = None

    @property
    def url(self) -> str:
        return f"redis://127.0.0.1:{self.port}/0"

    def start(self) -> str:
        self.process = subprocess.Popen(
            [
                "redis-server",
                "--port",
                str(self.port),
                "--bind",
                "127.0.0.1",
                "--save",
                "",
                "--appendonly",
                "no",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        deadline = time.time() + START_TIMEOUT
        while time.time() < deadline:
            if self.process.poll() is not None:
                stderr = self.process.stderr.read().decode(errors="replace")
                raise RuntimeError(f"redis-server exited: {stderr[-400:]}")
            if self._ping():
                logger.info(f"redis ready on {self.port}")
                return self.url
            time.sleep(0.2)
        self.stop()
        raise RuntimeError(
            f"redis-server not ready on {self.port} after {START_TIMEOUT}s"
        )

    def _ping(self) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", self.port), timeout=1) as s:
                s.sendall(b"PING\r\n")
                return s.recv(16).startswith(b"+PONG")
        except OSError:
            return False

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)
        self.process = None
