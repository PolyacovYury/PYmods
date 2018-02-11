from PYmodsCore import overrideMethod
from gui.Scaleform.framework import ViewTypes
from gui.app_loader import g_appLoader
from gui.shared.gui_items.processors import Processor, makeI18nError
from gui.ClientHangarSpace import _VehicleAppearance


@overrideMethod(_VehicleAppearance, '_VehicleAppearance__getActiveOutfit')
def new_getActiveOutfit(base, self):
    c11nView = g_appLoader.getDefLobbyApp().containerManager.getContainer(ViewTypes.LOBBY_SUB).getView()
    if c11nView is not None:
        return c11nView.getCurrentOutfit()  # fix for HangarFreeCam
    return base(self)
