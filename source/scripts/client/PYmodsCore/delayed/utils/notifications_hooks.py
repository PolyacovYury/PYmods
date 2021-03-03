import BigWorld
import re
from notification.NotificationsCollection import NotificationsCollection
from notification.actions_handlers import NotificationsActionsHandlers
from ... import overrideMethod

__all__ = ()


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
