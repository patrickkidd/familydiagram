import logging

from pkdiagram.pyqt import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QApplication,
    QDesktopServices,
    QUrl,
    Qt,
)

log = logging.getLogger(__name__)


class AuthUrlDialog(QDialog):
    """Dialog to display and handle training web app authentication URL"""

    def __init__(self, authUrl, parent=None):
        super().__init__(parent)
        self.authUrl = authUrl

        self.setWindowTitle("Training App Authentication")
        self.setModal(True)
        self.setMinimumWidth(600)

        Layout = QVBoxLayout(self)

        InfoLabel = QLabel(
            "Use this link to authenticate to the Family Diagram training web app:"
        )
        InfoLabel.setWordWrap(True)

        self.urlEdit = QLineEdit(authUrl)
        self.urlEdit.setReadOnly(True)
        self.urlEdit.selectAll()

        ExpiryLabel = QLabel("This link expires in 5 minutes")
        ExpiryLabel.setStyleSheet("color: #666; font-size: 10px;")

        ButtonLayout = QHBoxLayout()

        CopyButton = QPushButton("Copy URL")
        CopyButton.clicked.connect(self.onCopyUrl)

        OpenButton = QPushButton("Open in Browser")
        OpenButton.clicked.connect(self.onOpenUrl)
        OpenButton.setDefault(True)

        CloseButton = QPushButton("Close")
        CloseButton.clicked.connect(self.close)

        ButtonLayout.addWidget(CopyButton)
        ButtonLayout.addWidget(OpenButton)
        ButtonLayout.addWidget(CloseButton)

        Layout.addWidget(InfoLabel)
        Layout.addWidget(self.urlEdit)
        Layout.addWidget(ExpiryLabel)
        Layout.addLayout(ButtonLayout)

    def onCopyUrl(self):
        """Copy URL to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.authUrl)
        log.info("Auth URL copied to clipboard")

    def onOpenUrl(self):
        """Open URL in default browser"""
        QDesktopServices.openUrl(QUrl(self.authUrl))
        log.info(f"Opened auth URL in browser: {self.authUrl}")
        self.close()
