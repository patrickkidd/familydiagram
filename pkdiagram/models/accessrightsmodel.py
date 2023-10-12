import pickle
from typing import List
import vedana
from ..pyqt import Qt, pyqtSlot, pyqtProperty, pyqtSignal, QAbstractListModel, QModelIndex, QVariant, QMessageBox
from .. import util
from ..server_types import AccessRight



class AccessRightsModel(QAbstractListModel):
    """ Manage the access rights on a diagram. """

    UsernameRole = Qt.UserRole + 1
    RightRole = UsernameRole + 1

    S_CLIENT_ONLY_ALLOWED_ONE_RIGHT = (
        "You are using the Client license which only allows adding a single access right. This can be for any user with a professional license, for example your therapist or coach. If you want to grant a different person access to your diagram, you will need to remove the existing access right first."
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self._session = None
        self._diagram = None
        self._isAddingRight = False

    def setSession(self, session):
        self._session = session

    def setServerDiagram(self, diagram):
        self._diagram = diagram
        self.ownerChanged.emit()
        self.modelReset.emit()

    def diagram(self):
        return self._diagram

    ## Qt Virtuals

    def roleNames(self):
        return {
            self.UsernameRole: b'username',
            self.RightRole: b'rightCode'
        }

    def rowCount(self, parent=QModelIndex()):
        if self._diagram:
            return len(self._diagram.access_rights)
        else:
            return 0

    def columnCount(self, parent=QModelIndex()):
        return 2

    def data(self, index, role=Qt.DisplayRole):
        ret = None
        if self._diagram:
            access_right = self._diagram.access_rights[index.row()]
            if index.column() == 0 and role in (Qt.DisplayRole, self.UsernameRole):
                user = util.find(self._session.users, lambda x: x.id == access_right.user_id)
                if user:
                    ret = user.username
            elif index.column() == 1 or role in (Qt.DisplayRole, self.RightRole):
                ret = access_right.right
        return ret

    def setData(self, index, value, role=Qt.EditRole):
        if not self._diagram:
            return False
        if index.row() < 0 or index.row() >= len(self._diagram.access_rights):
            return False
        ret = False
        access_right = self._diagram.access_rights[index.row()]
        # if index.column() == 0 and role in (Qt.EditRole, self.UsernameRole):
        #     user = self.findUser(value)
        #     if user and user.id != access_role.user_id:
        #         self._session.server().blockingRequest('PATCH', f"/access_rights/{access_right.id}", data={
        #             'user_id': value,
        #             'session': self._session.token
        #         })
        #         access_right.user_id = value
        #         ret = True
        if index.column() == 1 or role == self.RightRole:
            if value and access_right.right != value:
                self._session.server().blockingRequest('PATCH', f"/access_rights/{access_right.id}", data={
                    'right': value,
                    'session': self._session.token
                })
                access_right.right = value
                ret = True
        return ret

    # Other Verbs

    @pyqtSlot(str, result=QVariant)
    def findUser(self, username):
        ret = None
        if self._session:
            ret = util.find(self._session.users, lambda x: x.username == username and x.username != self._session.user.username)
        else:
            ret = None
        return ret

    ownerChanged = pyqtSignal()

    @pyqtProperty(str, notify=ownerChanged)
    def owner(self):
        if self._diagram:
            return self._diagram.user.username
        else:
            return ''

    @pyqtSlot(str, result=bool)
    def addRight(self, username):
        if self._isAddingRight:
            return False
        with util.monkeypatch(self, '_isAddingRight', True):
            if not username:
                return False
            user = self.findUser(username)
            if not user:
                QMessageBox.warning(None, 'Could not add access right.', f"The user {username} does not exist")
                return False
            for access_right in self._diagram.access_rights:
                if access_right.user_id == user.id:
                    QMessageBox.warning(None, 'Could not add access right.', f"An access right for {username} already exists.")
                    return False
            if self._session.hasFeature(vedana.LICENSE_CLIENT) and len(self._diagram.access_rights) >= 1:
                QMessageBox.warning(None, 'Could not add access right.', self.S_CLIENT_ONLY_ALLOWED_ONE_RIGHT)
                return False
            response = self._session.server().blockingRequest('POST', "/access_rights", data={
                'diagram_id': self._diagram.id,
                'user_id': user.id,
                'right': vedana.ACCESS_READ_ONLY,
                'session': self._session.token
            })
            data = pickle.loads(response.body)
            newRow = len(self._diagram.access_rights)
            self.beginInsertRows(QModelIndex(), newRow, newRow)
            self._diagram.access_rights.append(
                AccessRight(
                    id=data['id'],
                    diagram_id=data['diagram_id'],
                    user_id=data['user_id'],
                    right=data['right']
                )
            )
            self.endInsertRows()
        return True

    @pyqtSlot(int)
    def deleteRight(self, row):
        access_right = self._diagram.access_rights[row]
        response = self._session.server().blockingRequest('DELETE', f"/access_rights/{access_right.id}", data={
            'session': self._session.token
        })
        self.beginRemoveRows(QModelIndex(), row, row)
        self._diagram.access_rights.remove(access_right)
        self.endRemoveRows()

