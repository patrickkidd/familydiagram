import pickle
import logging

from btcopilot.schema import DiagramData
from pkdiagram.pyqt import QMessageBox


log = logging.getLogger(__name__)


class DiagramSaver:
    """Sole owner of the server save for an open diagram.

    Resolves the Diagram by id on every save so a cache-object swap cannot
    orphan it, and owns the merge baseline that swap used to discard.
    """

    S_SAVE_FAILED = "Could not save diagram after 3 attempts due to concurrent modifications. Please try again."

    def __init__(self, session, fileModel):
        self.session = session
        self.fileModel = fileModel
        self._baselines: dict[int, bytes] = {}

    def forget(self, diagramId):
        self._baselines.pop(diagramId, None)

    def save(self, diagramId: int, data: bytes) -> bool:
        diagram = self.fileModel.findDiagram(diagramId)

        # Baseline for the merge: Pro's Scene view at the last successful
        # save (or, on first save, what was loaded from server at open —
        # Pro's Scene loads from diagram.data so they're equivalent). NOT
        # the canonical server state, NOT the post-merge bytes — those may
        # contain other-client items that Pro's Scene never loaded, which
        # would get interpreted as deletes on the next save.
        # Plan: doc/plans/2026-05-01--mvp-merge-fix/README.md
        snapshotBytes = self._baselines.get(diagramId) or diagram.data
        openSnapshot = pickle.loads(snapshotBytes) if snapshotBytes else {}

        def applyChange(diagramData: DiagramData):
            # Only modify Scene-owned fields (FR-2 in DATA_SYNC_FLOW.md).
            localData = pickle.loads(data)
            # Scene collections — snapshot-diff merge. For each field,
            # take server's copy unless the user actually edited the
            # item (snapshot vs local differ), preventing a stale
            # snapshot from clobbering concurrent edits.
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
            # Metadata
            diagramData.uuid = localData.get("uuid")
            diagramData.name = localData.get("name")
            diagramData.tags = localData.get("tags", [])
            diagramData.loggedDateTime = localData.get("loggedDateTime", [])
            diagramData.masterKey = localData.get("masterKey")
            diagramData.alias = localData.get("alias")
            diagramData.version = localData.get("version")
            diagramData.versionCompat = localData.get("versionCompat")
            diagramData.lastItemId = max(
                diagramData.lastItemId, localData.get("lastItemId", 0)
            )
            # UI flags
            diagramData.readOnly = localData.get("readOnly", False)
            diagramData.contributeToResearch = localData.get(
                "contributeToResearch", False
            )
            diagramData.useRealNames = localData.get("useRealNames", False)
            diagramData.password = localData.get("password")
            diagramData.requirePasswordForRealNames = localData.get(
                "requirePasswordForRealNames", False
            )
            diagramData.showAliases = localData.get("showAliases", False)
            diagramData.hideNames = localData.get("hideNames", False)
            diagramData.hideToolBars = localData.get("hideToolBars", False)
            diagramData.hideEmotionalProcess = localData.get(
                "hideEmotionalProcess", False
            )
            diagramData.hideEmotionColors = localData.get("hideEmotionColors", False)
            diagramData.hideDateSlider = localData.get("hideDateSlider", False)
            diagramData.hideVariablesOnDiagram = localData.get(
                "hideVariablesOnDiagram", False
            )
            diagramData.hideVariableSteadyStates = localData.get(
                "hideVariableSteadyStates", False
            )
            diagramData.hideSARFGraphics = localData.get("hideSARFGraphics", True)
            diagramData.exclusiveLayerSelection = localData.get(
                "exclusiveLayerSelection", True
            )
            diagramData.storePositionsInLayers = localData.get(
                "storePositionsInLayers", False
            )
            diagramData.currentDateTime = localData.get("currentDateTime")
            diagramData.scaleFactor = localData.get("scaleFactor")
            diagramData.pencilColor = localData.get("pencilColor")
            diagramData.eventProperties = localData.get("eventProperties", [])
            diagramData.legendData = localData.get("legendData")
            return diagramData

        stillValid = lambda d: True

        success = diagram.save(
            self.session.server(), applyChange, stillValid, useJson=False
        )

        if success:
            self._baselines[diagramId] = data
            log.info(
                f"Pushed diagram {diagram.id} to server, bytes: {len(diagram.data)}, version: {diagram.version}"
            )
        else:
            QMessageBox.warning(None, "Save Failed After Retries", self.S_SAVE_FAILED)

        return success
