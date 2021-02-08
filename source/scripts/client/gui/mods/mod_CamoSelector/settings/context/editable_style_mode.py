from gui.Scaleform.daapi.view.lobby.customization.context.editable_style_mode import EditableStyleMode as WGEditableMode
from gui.customization.shared import EDITABLE_STYLE_IRREMOVABLE_TYPES
from items.components.c11n_constants import SeasonType


class EditableStyleMode(WGEditableMode):
    def __init__(self, ctx, baseMode):
        super(EditableStyleMode, self).__init__(ctx)
        self._baseMode = baseMode

    # noinspection DuplicatedCode
    def isPossibleToInstallItemForAllSeasons(self, slotId, intCD):
        item = self._service.getItemByCD(intCD)
        if item.itemTypeID in EDITABLE_STYLE_IRREMOVABLE_TYPES:
            if self.isBaseItem(slotId):
                firstSeason, otherSeasons = SeasonType.COMMON_SEASONS[0], SeasonType.COMMON_SEASONS[1:]
                baseSlotData = self.getSlotDataFromBaseOutfit(slotId, firstSeason)
                for season in otherSeasons:
                    slotData = self.getSlotDataFromBaseOutfit(slotId, season)
                    if baseSlotData.intCD != slotData.intCD:
                        return False

                return True
        return self._service.getItemByCD(intCD).season == SeasonType.ALL

    def getItemInventoryCount(self, item, excludeBase=False):
        return 10  # should be enough to plaster any vehicle

