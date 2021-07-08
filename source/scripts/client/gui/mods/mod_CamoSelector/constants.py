from VehicleStickers import SlotTypes
from gui import hangar_vehicle_appearance
from gui.Scaleform.daapi.view.lobby.customization import (
    customization_carousel, customization_properties_sheet, popovers, shared as lobby_shared,
)
from gui.Scaleform.daapi.view.lobby.customization.context import custom_mode, editable_style_mode
from gui.Scaleform.daapi.view.lobby.customization.shared import (
    CustomizationTabs, ITEM_TYPE_TO_SLOT_TYPE, ITEM_TYPE_TO_TAB, TYPES_ORDER,
)
from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from gui.customization import shared as gui_shared
from gui.customization.constants import CustomizationModes
from gui.impl.backport import text
from gui.impl.gen import R
from gui.shared.gui_items import GUI_ITEM_TYPE
from items.components.c11n_constants import CustomizationType, EMPTY_ITEM_ID, SeasonType
from vehicle_outfit.outfit import ANCHOR_TYPE_TO_SLOT_TYPE_MAP, Area


class VIEW_ALIAS(object):
    CAMO_SELECTOR_KIT_POPOVER = 'CustomizationCamoSelectorKitPopover'


STARTER_ITEM_ID = EMPTY_ITEM_ID + 1
CUSTOM_GROUP_NAME = intern('custom')
SEASON_NAME_TO_TYPE = {
    SEASONS_CONSTANTS.SUMMER: SeasonType.SUMMER, SEASONS_CONSTANTS.WINTER: SeasonType.WINTER,
    SEASONS_CONSTANTS.DESERT: SeasonType.DESERT}

CustomizationTabs.INSIGNIA = 8
CustomizationTabs.ALL += (CustomizationTabs.INSIGNIA,)
CustomizationTabs.MODES[CustomizationModes.CUSTOM] += (CustomizationTabs.INSIGNIA,)
CustomizationTabs.SLOT_TYPES[CustomizationTabs.INSIGNIA] = GUI_ITEM_TYPE.INSIGNIA
CustomizationTabs.ITEM_TYPES[CustomizationTabs.INSIGNIA] = (GUI_ITEM_TYPE.INSIGNIA,)
ITEM_TYPE_TO_TAB[GUI_ITEM_TYPE.INSIGNIA] = CustomizationTabs.INSIGNIA
ITEM_TYPE_TO_SLOT_TYPE[GUI_ITEM_TYPE.INSIGNIA] = GUI_ITEM_TYPE.INSIGNIA
gui_shared.C11N_ITEM_TYPE_MAP[GUI_ITEM_TYPE.INSIGNIA] = CustomizationType.INSIGNIA
TYPES_ORDER = (GUI_ITEM_TYPE.INSIGNIA,) + TYPES_ORDER
customization_carousel.TYPES_ORDER = popovers.TYPES_ORDER = TYPES_ORDER
ANCHOR_TYPE_TO_SLOT_TYPE_MAP[SlotTypes.INSIGNIA_ON_GUN] = GUI_ITEM_TYPE.INSIGNIA
hangar_vehicle_appearance.SLOT_TYPES += (GUI_ITEM_TYPE.INSIGNIA,)
CustomizationModes.CAMO_SELECTOR = 8
CustomizationModes.ALL += (CustomizationModes.CAMO_SELECTOR,)


def getAvailableRegions(areaId, slotType, vehicleDescr=None):
    if slotType == GUI_ITEM_TYPE.INSIGNIA:
        if areaId != Area.GUN:
            return ()
        return old_getAvailableRegions(areaId, GUI_ITEM_TYPE.PAINT, vehicleDescr)[:1]
    return old_getAvailableRegions(areaId, slotType, vehicleDescr)


old_getAvailableRegions = gui_shared.getAvailableRegions
for obj in (gui_shared, lobby_shared, custom_mode, customization_properties_sheet, editable_style_mode):
    setattr(obj, 'getAvailableRegions', getAvailableRegions)

insignia_names = {
    'wh': text(R.strings.vehicle_customization.special_style.kv2_w()),
    'chuck': text(R.strings.vehicle_customization.special_style.ny_2021_chuck()),
}
