import time
import logging

import pytest

from pkdiagram.pyqt import QMessageBox
from conftest import TEST_TIMEOUT_MS


log = logging.getLogger(__name__)


def test_hangWatchdog(qApp, watchdog):
    start_time = time.time()
    QMessageBox.information(None, "Test", "Will hang test suite")
    assert watchdog.killed() == True
    watchdog.cancel()
    log.info(f"")
    # elapsed time should be approximately of TEST_TIMEOUT_MS
    elapsed_time = (time.time() - start_time) * 1000
    assert elapsed_time == pytest.approx(TEST_TIMEOUT_MS, rel=0.05)
