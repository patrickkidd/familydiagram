from pkdiagram.pyqt import QApplication
from pkdiagram import util
from pkdiagram.widgets import Dialog
from pkdiagram.mainwindow.welcome_form import Ui_Welcome


class Welcome(Dialog):
    def __init__(self, mw):
        super().__init__(mw)
        self.mw = mw
        self.ui = Ui_Welcome()
        self.ui.setupUi(self)

        self.ui.dontShowBox.toggled[bool].connect(self.onDontShow)
        QApplication.instance().paletteChanged.connect(self.onSystemPaletteChanged)
        self.onSystemPaletteChanged()

    def onSystemPaletteChanged(self):
        ss = """Welcome, *[class~="QCheckBox"] {
            background-color: %s;
            color: %s;
        }
        """ % (
            util.QML_WINDOW_BG,
            util.QML_ACTIVE_TEXT_COLOR,
        )
        if util.IS_UI_DARK_MODE:
            bb_ss = (
                """
            #bottomBar {
                background: %s;
            }"""
                % util.QML_CONTROL_BG
            )
            tl_ss = (
                """
            #titleLabel {
                padding: 20px;
                background-color: %s;
            }
            """
                % util.QML_CONTROL_BG
            )
        else:
            bb_ss = """
            #bottomBar {
                border-top: 1px solid #afafaf;
                background: qlineargradient(spread:pad, x1:1, y1:1, x2:1, y2:0, stop:0 rgba(216, 216, 216, 255), stop:1 rgba(228, 228, 228, 255));
            }"""
            tl_ss = """
            #titleLabel {
                padding: 20px;
                background-color: white;
            }
            """
        self.ui.bottomBar.setStyleSheet(bb_ss)
        self.ui.dontShowBox.setStyleSheet("background-color: transparent")
        self.setStyleSheet(ss)
        self.ui.titleLabel.setStyleSheet(tl_ss)
        # self.setPalette(QApplication.palette())

    @util.blocked
    def init(self):
        dontShowWelcome = self.prefs.value(
            "dontShowWelcome", type=bool, defaultValue=False
        )
        self.ui.dontShowBox.setChecked(dontShowWelcome)
        super().init()

    def deinit(self):
        pass

    @property
    def prefs(self):
        return self.mw.prefs

    def onDone(self):
        self.hide()

    @util.blocked
    def onDontShow(self, on):
        self.prefs.setValue("dontShowWelcome", on)
