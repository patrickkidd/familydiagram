"""
Server-side id-block allocator for the Pro app's Scene.

When bound via `Scene.setIdAllocator(allocator)`, the Scene pulls new ids
from a server-reserved range instead of locally incrementing lastItemId.
This prevents id collisions when multiple clients (Pro × Personal, or
Pro × Pro) edit the same diagram concurrently.

Personal app does NOT use this — Personal allocates ids server-side via
commit_pdp_items, which is already serialized through the server.

Local .fd files do NOT use this — there's no concurrent writer to
collide with.

See plan: doc/plans/2026-05-01--mvp-merge-fix/README.md
"""

import os
import pickle
import logging

log = logging.getLogger(__name__)


class ServerBlockAllocator:
    DEFAULT_BLOCK_SIZE = 100

    def __init__(self, diagram, server, blockSize=None):
        self._diagram = diagram
        self._server = server
        if blockSize is None:
            blockSize = int(
                os.environ.get(
                    "FAMILYDIAGRAM_BLOCK_SIZE", self.DEFAULT_BLOCK_SIZE
                )
            )
        self._blockSize = blockSize
        self._next = None
        self._end = None

    def __call__(self) -> int:
        if self._next is None or self._next > self._end:
            self._refill()
        v = self._next
        self._next += 1
        return v

    def _refill(self):
        bdata = pickle.dumps({"count": self._blockSize})
        # Match Diagram.save's request style: explicit /v1 prefix +
        # from_root=True. (`from_root=False` would also work and produces
        # the same URL since util.serverUrl prepends /v1, but consistency
        # with Diagram.save makes the pattern obvious.)
        response = self._server.blockingRequest(
            "POST",
            f"/v1/diagrams/{self._diagram.id}/reserve_ids",
            bdata=bdata,
            from_root=True,
        )
        body = pickle.loads(response.body)
        self._next = body["start"]
        self._end = body["end"]
        # Server's lastItemId advanced and version bumped by the reservation.
        # Pull the new version into the Diagram so the next save expects it
        # and avoids a needless 409 on its first attempt.
        self._diagram.version = body["version"]
        log.info(
            f"ServerBlockAllocator: diagram {self._diagram.id} reserved "
            f"ids [{self._next}, {self._end}], new version {body['version']}"
        )
