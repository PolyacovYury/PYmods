from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.view.lobby.customization.camo_anchor_properties import CamoAnchorProperties, \
    CustomizationCamoAnchorVO
from gui.Scaleform.daapi.view.lobby.customization.customization_item_vo import buildCustomizationItemDataVO
from gui.Scaleform.daapi.view.lobby.customization.main_view import MainView
from gui.Scaleform.daapi.view.lobby.customization.sound_constants import SOUNDS
from gui.Scaleform.framework import ViewTypes
from gui.Scaleform.locale.ITEM_TYPES import ITEM_TYPES
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION
from gui.app_loader import g_appLoader
from gui.shared.formatters import text_styles
from gui.shared.gui_items import GUI_ITEM_TYPE, GUI_ITEM_TYPE_NAMES
from helpers import i18n
from helpers.i18n import makeString as _ms
from .shared import C11nMode, RandMode, TeamMode


@overrideMethod(CamoAnchorProperties, '_extractDataFromElement')
def _extractDataFromElement(base, self):
    if isinstance(self._c11nView, MainView):
        return base(self)
    self._isEmpty = not self._item
    if not self._isEmpty:
        self._name = text_styles.highTitle(self._item.userName)
        self._desc = self._AnchorProperties__generateDescription()
    else:
        itemTypeName = GUI_ITEM_TYPE_NAMES[GUI_ITEM_TYPE.CAMOUFLAGE]
        self._name = text_styles.highTitle(_ms(VEHICLE_CUSTOMIZATION.CUSTOMIZATION_POPOVER_EMPTYTEXT,
                                               elementType=_ms(ITEM_TYPES.customization(itemTypeName))))
        self._desc = text_styles.neutral(VEHICLE_CUSTOMIZATION.CUSTOMIZATION_POPOVER_EMPTYSLOT_HINT)


@overrideMethod(CamoAnchorProperties, '_getItemData')
def _getItemData(base, self):
    if isinstance(self._c11nView, MainView):
        return base(self)
    rendererVO = None
    if self._item is not None:
        rendererVO = buildCustomizationItemDataVO(self._item, count=self._c11nView.getItemInventoryCount(
            self._item) if self._item.isRentable else None, plainView=True)  # no bonus shall be displayed
    return rendererVO


@overrideMethod(CamoAnchorProperties, '_AnchorProperties__generateDescription')
def _generateDescription(base, self):
    if isinstance(self._c11nView, MainView) or self._c11nView.getMode() == C11nMode.INSTALL:
        return base(self)
    mapValue = VEHICLE_CUSTOMIZATION.CUSTOMIZATION_POPOVER_EMPTYSLOT
    if self._item is not None:
        if self._item.isAllSeason():
            mapValue = VEHICLE_CUSTOMIZATION.CUSTOMIZATION_POPOVER_STYLE_ANY
        elif self._item.isSummer():
            mapValue = VEHICLE_CUSTOMIZATION.CUSTOMIZATION_POPOVER_STYLE_SUMMER
        elif self._item.isWinter():
            mapValue = VEHICLE_CUSTOMIZATION.CUSTOMIZATION_POPOVER_STYLE_WINTER
        elif self._item.isDesert():
            mapValue = VEHICLE_CUSTOMIZATION.CUSTOMIZATION_POPOVER_STYLE_DESERT
    desc = _ms(VEHICLE_CUSTOMIZATION.CUSTOMIZATION_INFOTYPE_DESCRIPTION_MAP, mapType=text_styles.stats(mapValue))
    if self._item.groupUserName:
        desc = text_styles.concatStylesToSingleLine(
            desc, _ms(VEHICLE_CUSTOMIZATION.CUSTOMIZATION_INFOTYPE_DESCRIPTION_TYPE, elementType=text_styles.stats(
                self._item.groupUserName)))
    return text_styles.main(desc)


@overrideMethod(CamoAnchorProperties, 'setCamoColor')
def setCamoColor(base, self, paletteIdx):
    if isinstance(self._c11nView, MainView) or self._c11nView.getMode() == C11nMode.INSTALL:
        return base(self, paletteIdx)
    self._c11nView.soundManager.playInstantSound(SOUNDS.SELECT)
    self._c11nView.changeCamoTeamMode(paletteIdx + 1)


@overrideMethod(CamoAnchorProperties, 'setCamoScale')
def setCamoScale(base, self, scale, scaleIndex):
    if isinstance(self._c11nView, MainView) or self._c11nView.getMode() == C11nMode.INSTALL:
        return base(self, scale, scaleIndex)
    self._c11nView.soundManager.playInstantSound(SOUNDS.SELECT)
    self._c11nView.changeCamoRandMode(scaleIndex)


@overrideMethod(CamoAnchorProperties, '_getData')
def _getData(base, self):
    if isinstance(self._c11nView, MainView) or self._c11nView.getMode() == C11nMode.INSTALL:
        result = base(self)
        for swatch in result['swatchColors']:
            swatch['label'] = ''
        return result
    from . import g_config
    swatchColors = []
    swatchScales = []
    if self._item:
        for idx in RandMode.NAMES:
            swatchScales.append({'paletteIcon': '', 'selected': self._c11nView.getRandMode() == idx,
                                 'label': g_config.i18n['UI_flash_randMode_%s' % RandMode.NAMES[idx]], 'value': idx})
        for idx in TeamMode.NAMES:
            swatchColors.append({'paletteIcon': '', 'selected': self._c11nView.getTeamMode() == idx,
                                 'label': g_config.i18n['UI_flash_teamMode_%s' % TeamMode.NAMES[idx]], 'value': idx})
    itemData = self._getItemData()
    if itemData is None:
        itemData = {'intCD': 0,
                    'icon': RES_ICONS.MAPS_ICONS_LIBRARY_TANKITEM_BUY_TANK_POPOVER_SMALL}
    return CustomizationCamoAnchorVO(self._name, self._desc, self._isEmpty, itemData, swatchColors,
                                     g_config.i18n['UI_flashCol_randMode_label'], swatchScales).asDict()


@overrideMethod(i18n, 'makeString')
def new_makeString(base, key, *args, **kwargs):
    if key == VEHICLE_CUSTOMIZATION.CUSTOMIZATION_POPOVER_CAMO_COLOR:
        print 'TEXT DETECTED'
        view = g_appLoader.getDefLobbyApp().containerManager.getContainer(ViewTypes.LOBBY_SUB).getView()
        if not isinstance(view, MainView) and view.getMode() == C11nMode.SETUP:
            from . import g_config
            return g_config.i18n['UI_flashCol_teamMode_label']
    return base(key, *args, **kwargs)
