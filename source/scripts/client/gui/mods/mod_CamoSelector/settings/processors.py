from gui.shared.gui_items.processors import Processor, makeI18nError


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
