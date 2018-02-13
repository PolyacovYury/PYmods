from PYmodsCore import overrideMethod
from gui.ClientHangarSpace import _VehicleAppearance
from gui.Scaleform.framework import ViewTypes
from gui.app_loader import g_appLoader


@overrideMethod(_VehicleAppearance, '_VehicleAppearance__getActiveOutfit')
def new_getActiveOutfit(base, self):
    container = g_appLoader.getDefLobbyApp().containerManager.getContainer(ViewTypes.LOBBY_SUB)
    if container is not None:
        c11nView = container.getView()
        if c11nView is not None:
            return c11nView.getCurrentOutfit()  # fix for HangarFreeCam
    return base(self)
