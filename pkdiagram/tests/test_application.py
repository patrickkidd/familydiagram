from pkdiagram import util
from pkdiagram.pyqt import QSettings
from pkdiagram.app import Application

# Captured at import, before the autouse prefs fixture patches it.
appPrefs = Application.prefs


def test_prefs_fixture_is_ini_file(prefs, tmp_path):
    assert (prefs.fileName(), prefs.format()) == (
        str(tmp_path / "settings.ini"),
        QSettings.IniFormat,
    )


def test_prefs_in_test_data_dir(qApp, tmp_path, monkeypatch):
    monkeypatch.setattr(util, "IS_DEV", True)
    monkeypatch.setenv("FD_TEST_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(qApp, "_prefs", None)
    settings = appPrefs(qApp)
    assert (settings.fileName(), settings.format()) == (
        str(tmp_path / "settings.ini"),
        QSettings.IniFormat,
    )
