import BigWorld
from . import ModEvent

__all__ = ('populate',)

populate = ModEvent()


def delayed_hooks():
    global populate
    from .. import overrideMethod
    from gui.Scaleform.daapi.view.login.LoginView import LoginView
    populate = overrideMethod(LoginView, '_populate', populate)


BigWorld.callback(0, delayed_hooks)
