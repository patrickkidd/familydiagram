import os.path, datetime, pickle, logging
from contextlib import ExitStack

import pytest
import mock
from sqlalchemy import inspect

from conftest import _scene_data
import vedana
from pkdiagram import (
    util,
    mainwindow,
    Scene,
    Person,
    AppConfig,
    Session,
    AppController,
    MainWindow,
    FileManager,
)
from pkdiagram.pyqt import Qt, QFileInfo, QSettings, QMetaObject

from fdserver.extensions import db
from fdserver.models import Diagram


def test_close_after_adding_lots(
    test_activation, test_user_diagrams, test_user, server_down, qtbot, create_ac_mw
):
    raise NotImplementedError
