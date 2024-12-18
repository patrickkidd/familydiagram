import os, sys, shutil

from pyqtdeploy import Component, ComponentOption, ExtensionModule

SOURCES = ["unsafearea.cpp", "_pkdiagram.cpp"]

BUILD_SOURCES = [
    "build/_pkdiagram/sip_pkdiagramAppFilter.cpp",
    "build/_pkdiagram/sip_pkdiagramcmodule.cpp",
    "build/_pkdiagram/sip_pkdiagramCUtil.cpp",
    "build/_pkdiagram/sip_pkdiagramFDDocument.cpp",
    "build/_pkdiagram/sip_pkdiagramPathItemBase.cpp",
    "build/_pkdiagram/sip_pkdiagramPathItemDelegate.cpp",
    "build/_pkdiagram/sip_pkdiagramPersonDelegate.cpp",
    "build/_pkdiagram/sip_pkdiagramQMap0100QString0100QString.cpp",
]

if sys.platform == "win32":
    SOURCES += ["_pkdiagram_win32.cpp"]
    BUILD_SOURCES += [
        "build/_pkdiagram/release/moc_unsafearea.cpp",
        "build/_pkdiagram/release/moc__pkdiagram.cpp",
    ]
else:
    SOURCES += ["_pkdiagram_mac.mm"]
    BUILD_SOURCES += [
        "build/_pkdiagram/moc_unsafearea.cpp",
        "build/_pkdiagram/moc__pkdiagram.cpp",
    ]

INCLUDES = [".", "build"]

MODULE_DIR = os.path.realpath(
    os.path.join(os.path.dirname(__file__), "..", "_pkdiagram")
)


class PKDiagramComponent(Component):
    """The vedana module component."""

    must_install_from_source = False
    preinstalls = ["Python", "PyQt", "Qt", "SIP"]
    provides = {
        "_pkdiagram": ExtensionModule(
            deps="PyQt:PyQt5.QtWidgets",
            source=[os.path.join(MODULE_DIR, x) for x in SOURCES + BUILD_SOURCES],
            includepath=[os.path.join(MODULE_DIR, x) for x in INCLUDES],
            qmake_qt=["gui", "widgets"],
        )
    }

    # def verify(self):
    #     for fpath in :
    #         if not os.path.isfile(fpath):
    #             self.error(f"The file {fpath} does not exist.")

    def get_archive_name(self):
        return ""

    def verify(self):
        for fpath in PKDiagramComponent.provides["_pkdiagram"].source:
            # fpath = os.path.realpath(os.path.join(this_dir, relative_fpath))
            if not os.path.isfile(fpath):
                self.error(f"The source file doesn't exist: {fpath}")

    def install(self):
        orig_cwd = os.getcwd()
        try:
            _path = os.path.realpath(
                os.path.join(self._sysroot.sysroot_dir, "..", "..", "_pkdiagram")
            )
            os.chdir(_path)
            self.run("sip-build")
        except Exception as e:
            self.verbose(str(e))
        finally:
            os.chdir(orig_cwd)
