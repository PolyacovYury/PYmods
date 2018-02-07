from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.view.lobby.customization.camo_anchor_properties import CustomizationCamoAnchorVO, \
    CustomizationCamoSwatchVO, _DEFAULT_COLORNUM, _PALETTE_BACKGROUND, _PALETTE_HEIGHT, _PALETTE_TEXTURE, \
    _PALETTE_WIDTH, CamoAnchorProperties
from gui.Scaleform.daapi.view.lobby.customization.customization_item_vo import buildCustomizationItemDataVO
from gui.Scaleform.daapi.view.lobby.customization.main_view import MainView
from gui.Scaleform.daapi.view.lobby.customization.sound_constants import SOUNDS
from gui.Scaleform.locale.ITEM_TYPES import ITEM_TYPES
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION
from gui.shared.formatters import text_styles
from gui.shared.gui_items import GUI_ITEM_TYPE, GUI_ITEM_TYPE_NAMES
from gui.shared.gui_items.customization.c11n_items import camoIconTemplate
from helpers.i18n import makeString as _ms
from .shared import C11N_MODE
from ..shared import RAND_MODE
from .. import g_config


@overrideMethod(CamoAnchorProperties, 'applyData')
def applyData(base, self, areaID, slotID, regionID):
    print self, self.__class__, areaID, slotID, regionID
    print 'applyData', isinstance(self._c11nView, MainView), self._c11nView.getMode() == C11N_MODE.INSTALL
    if isinstance(self._c11nView, MainView) or self._c11nView.getMode() == C11N_MODE.INSTALL:
        return base(self, areaID, slotID, regionID)
    slot = self._c11nView.getCurrentOutfit().getContainer(areaID).slotFor(slotID)
    self._item = slot.getItem(regionID)
    self._component = slot.getComponent(regionID)
    self._extractDataFromElement()
    self._sendData(self._getData())


@overrideMethod(CamoAnchorProperties, '_extractDataFromElement')
def _extractDataFromElement(base, self):
    print 'extractDataFromElement', isinstance(self._c11nView, MainView), self._c11nView.getMode() == C11N_MODE.INSTALL
    if isinstance(self._c11nView, MainView) or self._c11nView.getMode() == C11N_MODE.INSTALL:
        return base(self)
    self._isEmpty = not self._item
    if not self._isEmpty:
        self._name = text_styles.highTitle(self._item.userName)
        self._desc = self._AnchorProperties__generateDescription()
    else:
        itemTypeID = GUI_ITEM_TYPE.CAMOUFLAGE
        itemTypeName = GUI_ITEM_TYPE_NAMES[itemTypeID]
        self._name = text_styles.highTitle(_ms(VEHICLE_CUSTOMIZATION.CUSTOMIZATION_POPOVER_EMPTYTEXT,
                                               elementType=_ms(ITEM_TYPES.customization(itemTypeName))))
        self._desc = text_styles.neutral(VEHICLE_CUSTOMIZATION.CUSTOMIZATION_POPOVER_EMPTYSLOT_HINT)


@overrideMethod(CamoAnchorProperties, '_getItemData')
def _getItemData(base, self):
    """
    generates data for the carousel item renderer
    :return: carousel item renderer VO
    """
    print 'getItemData', isinstance(self._c11nView, MainView), self._c11nView.getMode() == C11N_MODE.INSTALL
    if isinstance(self._c11nView, MainView) or self._c11nView.getMode() == C11N_MODE.INSTALL:
        return base(self)
    rendererVO = None
    if self._item is not None:
        rendererVO = buildCustomizationItemDataVO(self._item, count=self._c11nView.getItemInventoryCount(
            self._item) if self._item.isRentable else None, plainView=True)
    return rendererVO


@overrideMethod(CamoAnchorProperties, '_AnchorProperties__generateDescription')
def _generateDescription(base, self):
    print 'generateDescription', isinstance(self._c11nView, MainView), self._c11nView.getMode() == C11N_MODE.INSTALL
    if isinstance(self._c11nView, MainView) or self._c11nView.getMode() == C11N_MODE.INSTALL:
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
        desc = text_styles.concatStylesToSingleLine(desc,
                                                    _ms(VEHICLE_CUSTOMIZATION.CUSTOMIZATION_INFOTYPE_DESCRIPTION_TYPE,
                                                        elementType=text_styles.stats(self._item.groupUserName)))
    return text_styles.main(desc)


@overrideMethod(CamoAnchorProperties, 'setCamoColor')
def setCamoColor(base, self, paletteIdx):
    """
    sets the current camo's palette to the palette at the provided index
    :param paletteIdx:
    """
    if isinstance(self._c11nView, MainView) or self._c11nView.getMode() == C11N_MODE.INSTALL:
        return base(self, paletteIdx)
    self._c11nView.soundManager.playInstantSound(SOUNDS.SELECT)
    self._c11nView.changeCamoTeamMode(paletteIdx)


@overrideMethod(CamoAnchorProperties, 'setCamoScale')
def setCamoScale(base, self, scale, scaleIndex):
    """
    Set the scale of the camo to the provided scale value
    :param scale: the new value for camo's patternSize. represents amount of tiling to do
    :param scaleIndex: the index of the camo scale slider that was selected
    """
    if isinstance(self._c11nView, MainView) or self._c11nView.getMode() == C11N_MODE.INSTALL:
        return base(self, scale, scaleIndex)
    self._c11nView.soundManager.playInstantSound(SOUNDS.SELECT)
    self._c11nView.changeCamoRandMode(scaleIndex)


@overrideMethod(CamoAnchorProperties, '_getData')
def _getData(base, self):
    print 'getData', isinstance(self._c11nView, MainView), self._c11nView.getMode() == C11N_MODE.INSTALL
    if isinstance(self._c11nView, MainView) or self._c11nView.getMode() == C11N_MODE.INSTALL:
        return base(self)
    swatchColors = []
    swatchScales = []
    if self._item:
        for idx in RAND_MODE.NAMES:
            swatchScales.append({'paletteIcon': '',
                                 'label': g_config.i18n['UI_flash_randMode_%s' % RAND_MODE.NAMES[idx]],
                                 'selected': self._c11nView.getRandMode() == idx,
                                 'value': idx})

        colorNum = 2
        red = 255 + (255 << 24)
        green = (255 << 8) + (255 << 24)
        palettes = [(green, green, 0, 0), (red, red, 0, 0), (red, green, 0, 0)]

        for idx, palette in enumerate(palettes):
            texture = _PALETTE_TEXTURE.format(colornum=colorNum)
            icon = camoIconTemplate(texture, _PALETTE_WIDTH, _PALETTE_HEIGHT, palette, background=_PALETTE_BACKGROUND)
            swatchColors.append(CustomizationCamoSwatchVO(icon, idx == self._c11nView.getTeamMode())._asdict())

    scaleText = VEHICLE_CUSTOMIZATION.CUSTOMIZATION_POPOVER_CAMO_SCALE
    itemData = self._getItemData()
    if itemData is None:
        itemData = {'intCD': 0,
                    'icon': RES_ICONS.MAPS_ICONS_LIBRARY_TANKITEM_BUY_TANK_POPOVER_SMALL}
    return CustomizationCamoAnchorVO(self._name, self._desc, self._isEmpty, itemData, swatchColors, scaleText,
                                     swatchScales).asDict()
