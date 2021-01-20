import BigWorld
import re
from gui.Scaleform.daapi.view.dialogs import ConfirmDialogButtons, DIALOG_BUTTON_ID
from gui.Scaleform.daapi.view.dialogs.SimpleDialog import SimpleDialog
from notification.NotificationsCollection import NotificationsCollection
from notification.actions_handlers import NotificationsActionsHandlers
from .. import overrideMethod


__all__ = ['showConfirmDialog', 'showI18nDialog', 'showInfoDialog']


@overrideMethod(NotificationsCollection, 'addItem')
def new_addItem(base, self, item):
    if 'temp_SM' not in item._vo['message']['message']:
        return base(self, item)
    item._vo['message']['message'] = item._vo['message']['message'].replace('temp_SM', '')
    item._vo['notify'] = False
    if item._settings:
        item._settings.isNotify = False
    return True


@overrideMethod(NotificationsActionsHandlers, 'handleAction')
def new_handleAction(base, self, model, typeID, entityID, actionName):
    from notification.settings import NOTIFICATION_TYPE
    if typeID == NOTIFICATION_TYPE.MESSAGE and re.match('https?://', actionName, re.I):
        BigWorld.wg_openWebBrowser(actionName)
    else:
        base(self, model, typeID, entityID, actionName)


@overrideMethod(SimpleDialog, '__callHandler')
def new_callHandler(base, self, buttonID):
    if len(self._SimpleDialog__buttons) != 3:
        return base(self, buttonID)
    self._SimpleDialog__handler(buttonID)
    self._SimpleDialog__isProcessed = True


@overrideMethod(SimpleDialog, '_dispose')
def new_Dialog_dispose(base, self):
    if len(self._SimpleDialog__buttons) == 3:
        self._SimpleDialog__isProcessed = True  # don't call the handler upon window destruction, onWindowClose is fine
    return base(self)


def showSimpleDialog(header, text, buttons, callback):
    from gui import DialogsInterface
    from gui.Scaleform.daapi.view.dialogs import SimpleDialogMeta
    DialogsInterface.showDialog(SimpleDialogMeta(header, text, buttons, None), callback)


def showConfirmDialog(header, text, buttons, callback):
    showSimpleDialog(header, text, (ConfirmButtons if len(buttons) == 2 else RestartButtons)(*buttons), callback)


def showI18nDialog(header, text, key, callback):
    from gui.Scaleform.daapi.view.dialogs import I18nConfirmDialogButtons
    showSimpleDialog(header, text, I18nConfirmDialogButtons(key), callback)


def showInfoDialog(header, text, button, callback):
    from gui.Scaleform.daapi.view.dialogs import InfoDialogButtons
    showSimpleDialog(header, text, InfoDialogButtons(button), callback)


class ConfirmButtons(ConfirmDialogButtons):
    def getLabels(self):
        return ({'id': DIALOG_BUTTON_ID.SUBMIT, 'label': self._submit, 'focused': True},
                {'id': DIALOG_BUTTON_ID.CLOSE, 'label': self._close, 'focused': False})


class RestartButtons(ConfirmButtons):
    def __init__(self, submit, shutdown, close):
        self._shutdown = shutdown
        super(RestartButtons, self).__init__(submit, close)

    def getLabels(self):
        return ({'id': DIALOG_BUTTON_ID.SUBMIT, 'label': self._submit, 'focused': True},
                {'id': 'shutdown', 'label': self._shutdown, 'focused': False},
                {'id': DIALOG_BUTTON_ID.CLOSE, 'label': self._close, 'focused': False})
