class SaveGuard:
    """Serializes writes to one Diagram: a save requested while another is
    running is queued and run after it, so two save paths can't interleave.

    Deliberately holds no reference back to its owner — the components that
    share a guard are all children of the controller that owns it, and a
    cycle through them would defer their teardown to the garbage collector."""

    def __init__(self):
        self._saving = False
        self._queue = []

    def __call__(self, fn):
        if self._saving:
            self._queue.append(fn)
            return None
        self._saving = True
        try:
            return fn()
        finally:
            self._saving = False
            if self._queue:
                self(self._queue.pop(0))
