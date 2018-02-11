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


class OutfitApplier(Processor):
    """ Outfit buyer and applier.
    """

    def __init__(self, vehicle, outfit, season):
        super(OutfitApplier, self).__init__()
        self.vehicle = vehicle
        self.outfit = outfit
        self.season = season

    def _errorHandler(self, code, errStr='', ctx=None):
        if not errStr:
            msg = 'server_error'
        else:
            msg = errStr
        return makeI18nError('customization/{}'.format(msg))

    def _request(self, callback):
        print self.vehicle.invID, self.season, self.outfit.pack().makeCompDescr()
        self._response(0, callback)
