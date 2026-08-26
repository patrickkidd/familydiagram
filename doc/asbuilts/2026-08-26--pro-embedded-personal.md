# Personal chat embedded in Pro (FD-336 WP-F)

Discuss / Learn / Plan render inside the Pro case drawer's **Chat** tab, driving
Pro's open Scene and Diagram. There is no second Session, no second Scene and no
diagram load on the Personal side.

## The seam

`personal/propersonal.py` — `ProPersonal` is the Pro-side composition root:
`DiscussionController`, `PDPController` (on Pro's `ServerFileManagerModel.saver`),
`SARFGraphModel`, `ClusterModel`, `TextToSpeech`, `VoiceRecorder`, plus the
`personalApp` API the Personal QML calls (`initEventForm`, `editEvent`,
`deleteEvent`, `eventFormDoneEditing`). No Analytics, AppConfig, DiagramLoader or
ShakeDetector. `contextProperties()` supplies only what Pro's engine lacks;
`diagramLoader` is registered null because Pro opens the case.

`MainWindow` builds it on the first server case opened (`_ensureProPersonal`), so
a local-file-only session never constructs speech, audio or the chat prefs.
`onServerFileClicked` binds scene + diagram; `setDocument` unbinds.
`QmlEngine` registers `proPersonal` as null up front and swaps in the real object
via `setProPersonal`, which re-evaluates the QML bindings.

## Embedded mode

`PersonalContainer.embedded` drops the hamburger, the account drawer, the
profile popup, the first-launch wizard, the account dialog and the Clear-Data
dropdown. Discussion switching, extract, rebuild, the PDP sheet and the paste/
attach import stay. The container is loaded by a `Loader` in `CaseProperties.qml`
that follows `proPersonal.enabled`; disabled shows `disabledReason` instead.
Unloading destroys the QML event form, so `ProPersonal` drops its wrapper
whenever it becomes disabled and rebuilds on the next `initEventForm`.

## Gates

**Ownership (D3):** enabled only when the Scene has a server Diagram, the Scene
is not read-only, and `diagram.user_id == session.user.id`.

**Save-before-chat (D6):** `personal/savegate.py` — `SaveGate` is consulted by
`DiscussionController.sendStatement` and `PDPController.extractFull`. A dirty Pro
stack prompts; Save emits `saveRequested` (MainWindow saves synchronously) and
the action proceeds only if the stack is then clean. Standalone Personal sets no
gate.

**MCP bridge (D16):** `_findPersonalAppController` finds the standalone root only,
so Pro's `save_diagram` / `open_server_diagram` route through MainWindow.
`_findPersonalComponents` / `_findPersonalRootItem` resolve either app for the
chat-state commands.

## Known limitation

Cluster detection is not run or persisted in Pro. Clusters stored on the row by
the Personal app are loaded and displayed; new ones are not written back,
because Pro's writer takes no `mutate` hook.
