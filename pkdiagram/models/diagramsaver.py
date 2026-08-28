import logging
import pickle
from dataclasses import MISSING, Field, fields
from typing import Callable

from btcopilot.schema import DiagramData
from pkdiagram.pyqt import QMessageBox
from pkdiagram.server_types import Diagram


log = logging.getLogger(__name__)


# Owned by the server row, never by the Scene: the row id, the staged
# extraction, the cluster cache, and the id watermark (clamped below).
ROW_FIELDS = ("id", "pdp", "clusters", "clusterCacheKey", "lastItemId")

# Everything else on DiagramData comes from the Scene bytes handed to save().
# Derived, so a field added to DiagramData is written rather than silently
# dropped.
SCENE_FIELDS: tuple[Field, ...] = tuple(
    f
    for f in fields(DiagramData)
    if f.name not in ROW_FIELDS and f.name not in DiagramData.SCENE_COLLECTION_FIELDS
)


def _default(f: Field):
    return f.default_factory() if f.default is MISSING else f.default


class DiagramSaver:
    """Sole owner of the server write for an open diagram, in both apps.

    Resolves the Diagram by id on every save so a cache-object swap cannot
    orphan it, and owns the merge baseline that swap used to discard.

    Every save runs to completion and returns what the server did, including
    one requested while another is in flight. Diagram.save blocks on a nested
    event loop, so such a request is always on the stack above the save it
    would be waiting for — waiting could only deadlock. Interleaving is safe
    instead: each write carries the version it expects, and a write that loses
    the race replays its merge on the refreshed row.
    """

    S_SAVE_FAILED = "Could not save diagram after 3 attempts due to concurrent modifications. Please try again."

    def __init__(self, session, resolve: Callable[[int], Diagram]):
        self.session = session
        self.resolve = resolve
        self._baselines: dict[int, bytes] = {}
        self._saving = False

    def forget(self, diagramId: int):
        self._baselines.pop(diagramId, None)

    def save(
        self,
        diagramId: int,
        sceneData: bytes,
        mutate: Callable[[DiagramData], DiagramData] | None = None,
    ) -> bool:
        if self._saving:
            log.warning(
                f"Save of diagram {diagramId} requested from inside another save"
            )
        self._saving = True
        try:
            return self._save(diagramId, sceneData, mutate)
        finally:
            self._saving = False

    def _save(self, diagramId: int, sceneData: bytes, mutate) -> bool:
        diagram = self.resolve(diagramId)

        # Baseline for the merge: this client's Scene view at the last
        # successful save (or, on first save, what was loaded from the server
        # at open). NOT the canonical server state, NOT the post-merge bytes —
        # those may contain other-client items this Scene never loaded, which
        # would be read as deletes on the next save.
        # Plan: doc/plans/2026-05-01--mvp-merge-fix/README.md
        snapshotBytes = self._baselines.get(diagramId) or diagram.data
        openSnapshot = pickle.loads(snapshotBytes) if snapshotBytes else {}
        localData = pickle.loads(sceneData)

        def applyChange(diagramData: DiagramData) -> DiagramData:
            # Scene collections — snapshot-diff merge. For each field, take
            # the server's copy unless the user actually edited the item
            # (snapshot vs local differ), preventing a stale snapshot from
            # clobbering concurrent edits.
            for fname in DiagramData.SCENE_COLLECTION_FIELDS:
                setattr(
                    diagramData,
                    fname,
                    DiagramData.apply_local_changes(
                        getattr(diagramData, fname),
                        openSnapshot.get(fname, []),
                        localData.get(fname, []),
                    ),
                )
            for f in SCENE_FIELDS:
                setattr(diagramData, f.name, localData.get(f.name, _default(f)))
            # Never below a reserved id block, or the next Pro allocation
            # collides with ids another client already holds.
            diagramData.lastItemId = max(
                diagramData.lastItemId,
                localData.get("lastItemId", 0),
                diagram.blockEnd,
            )
            return mutate(diagramData) if mutate else diagramData

        success = diagram.save(self.session.server(), applyChange, lambda d: True)

        if success:
            self._baselines[diagramId] = sceneData
            log.info(
                f"Pushed diagram {diagram.id} to server, bytes: {len(diagram.data)}, version: {diagram.version}"
            )
        else:
            QMessageBox.warning(None, "Save Failed After Retries", self.S_SAVE_FAILED)

        return success
