from gui.Scaleform.daapi.view.dialogs import ConfirmDialogButtons, DIALOG_BUTTON_ID
from gui.Scaleform.daapi.view.dialogs.SimpleDialog import SimpleDialog
from ... import overrideMethod

__all__ = ('showConfirmDialog', 'showI18nDialog', 'showInfoDialog')


def _showSimpleDialog(header, text, buttons, callback):
    from gui import DialogsInterface
    from gui.Scaleform.daapi.view.dialogs import SimpleDialogMeta
    DialogsInterface.showDialog(SimpleDialogMeta(header, text, buttons, None), callback)


def showConfirmDialog(header, text, buttons, callback):
    _showSimpleDialog(header, text, (_ConfirmButtons if len(buttons) == 2 else _RestartButtons)(*buttons), callback)


def showI18nDialog(header, text, key, callback):
    from gui.Scaleform.daapi.view.dialogs import I18nConfirmDialogButtons
    _showSimpleDialog(header, text, I18nConfirmDialogButtons(key), callback)


def showInfoDialog(header, text, button, callback):
    from gui.Scaleform.daapi.view.dialogs import InfoDialogButtons
    _showSimpleDialog(header, text, InfoDialogButtons(button), callback)


class _ConfirmButtons(ConfirmDialogButtons):
    def getLabels(self):
        return ({'id': DIALOG_BUTTON_ID.SUBMIT, 'label': self._submit, 'focused': True},
                {'id': DIALOG_BUTTON_ID.CLOSE, 'label': self._close, 'focused': False})


class _RestartButtons(_ConfirmButtons):
    def __init__(self, submit, shutdown, close):
        self._shutdown = shutdown
        super(_RestartButtons, self).__init__(submit, close)

    def getLabels(self):
        return ({'id': DIALOG_BUTTON_ID.SUBMIT, 'label': self._submit, 'focused': True},
                {'id': 'shutdown', 'label': self._shutdown, 'focused': False},
                {'id': DIALOG_BUTTON_ID.CLOSE, 'label': self._close, 'focused': False})


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
