from abc import ABCMeta, abstractmethod
from gui.Scaleform.daapi.view.lobby.customization.anchor_properties import ANCHOR_TYPE
from gui.Scaleform.daapi.view.lobby.customization.camo_anchor_properties import CustomizationCamoAnchorVO, \
    CustomizationCamoSwatchVO, _DEFAULT_COLORNUM, _MAX_PALETTES, _PALETTE_BACKGROUND, _PALETTE_HEIGHT, _PALETTE_TEXTURE, \
    _PALETTE_WIDTH
from gui.Scaleform.daapi.view.lobby.customization.shared import CAMO_SCALE_SIZE
from gui.Scaleform.daapi.view.lobby.customization.sound_constants import SOUNDS
from gui.Scaleform.daapi.view.meta.CustomizationAnchorPropertiesMeta import CustomizationAnchorPropertiesMeta
from gui.Scaleform.framework import ViewTypes
from gui.Scaleform.locale.ITEM_TYPES import ITEM_TYPES
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION
from gui.shared.formatters import text_styles
from gui.shared.gui_items import GUI_ITEM_TYPE, GUI_ITEM_TYPE_NAMES
from gui.shared.gui_items.customization.c11n_items import camoIconTemplate
from helpers import dependency
from helpers.i18n import makeString as _ms
from skeletons.gui.customization import ICustomizationService
from skeletons.gui.shared import IItemsCache
from .item_vo import buildCustomizationItemDataVO


class AnchorProperties(CustomizationAnchorPropertiesMeta):
    __metaclass__ = ABCMeta
    itemsCache = dependency.descriptor(IItemsCache)

    def __init__(self):
        super(AnchorProperties, self).__init__()
        self._c11nView = None
        self._item = None
        self._component = None

    def applyData(self, areaID, slotID, regionID):
        slot = self._c11nView.getCurrentOutfit().getContainer(areaID).slotFor(slotID)
        self._item = slot.getItem(regionID)
        self._component = slot.getComponent(regionID)
        self._extractDataFromElement()
        self._sendData(self._getData())

    def refreshData(self):
        """
        Collects property data and sends to UI
        """
        self._extractDataFromElement()
        self._sendData(self._getData())

    def _getAnchorType(self):
        return ANCHOR_TYPE.NONE

    @abstractmethod
    def _getData(self):
        return None

    def _populate(self):
        super(AnchorProperties, self)._populate()
        self._c11nView = self.app.containerManager.getContainer(ViewTypes.LOBBY_SUB).getView()

    def _dispose(self):
        self._c11nView = None
        self._item = None
        self._component = None
        super(AnchorProperties, self)._dispose()

    def _extractDataFromElement(self):
        self._isEmpty = not self._item
        if not self._isEmpty:
            self._name = text_styles.highTitle(self._item.userName)
            self._desc = self.__generateDescription()
        else:
            itemTypeID = GUI_ITEM_TYPE.CAMOUFLAGE
            itemTypeName = GUI_ITEM_TYPE_NAMES[itemTypeID]
            self._name = text_styles.highTitle(_ms(VEHICLE_CUSTOMIZATION.CUSTOMIZATION_POPOVER_EMPTYTEXT,
                                                   elementType=_ms(ITEM_TYPES.customization(itemTypeName))))
            self._desc = text_styles.neutral(VEHICLE_CUSTOMIZATION.CUSTOMIZATION_POPOVER_EMPTYSLOT_HINT)

    def _sendData(self, data):
        # noinspection PyUnresolvedReferences
        self.as_setPopoverDataS(data)

    def _getItemData(self):
        """
        generates data for the carousel item renderer
        :return: carousel item renderer VO
        """
        rendererVO = None
        if self._item is not None:
            rendererVO = buildCustomizationItemDataVO(self._item, count=self._c11nView.getItemInventoryCount(
                self._item) if self._item.isRentable else None, plainView=True)
        return rendererVO

    def __generateDescription(self):
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


# noinspection PyAbstractClass
class CustomizationCamoAnchorPropertiesMeta(AnchorProperties):
    def setCamoColor(self, swatchID):
        self._printOverrideError('setCamoColor')

    def setCamoScale(self, scale, index):
        self._printOverrideError('setCamoScale')

    def as_setPopoverDataS(self, data):
        """
        :param data: Represented by CustomizationCamoAnchorVO (AS)
        """
        return self.flashObject.as_setPopoverData(data) if self._isDAAPIInited() else None


class CamoAnchorProperties(CustomizationCamoAnchorPropertiesMeta):
    service = dependency.descriptor(ICustomizationService)

    def setCamoColor(self, paletteIdx):
        """
        sets the current camo's palette to the palette at the provided index
        :param paletteIdx:
        """
        self._c11nView.soundManager.playInstantSound(SOUNDS.SELECT)
        self._component.palette = paletteIdx
        self.service.onOutfitChanged()

    def setCamoScale(self, scale, scaleIndex):
        """
        Set the scale of the camo to the provided scale value
        :param scale: the new value for camo's patternSize. represents amount of tiling to do
        :param scaleIndex: the index of the camo scale slider that was selected
        """
        self._c11nView.soundManager.playInstantSound(SOUNDS.SELECT)
        self._component.patternSize = scale
        self.service.onOutfitChanged()

    def _getAnchorType(self):
        return ANCHOR_TYPE.CAMO

    def _getData(self):
        swatchColors = []
        swatchScales = []
        if self._item:
            for idx in xrange(len(CAMO_SCALE_SIZE)):
                swatchScales.append({'paletteIcon': '',
                                     'label': CAMO_SCALE_SIZE[idx],
                                     'selected': self._component.patternSize == idx,
                                     'value': idx})

            colorNum = _DEFAULT_COLORNUM
            for palette in self._item.palettes:
                colorNum = max(colorNum, sum(((color >> 24) / 255.0 > 0 for color in palette)))

            for idx, palette in enumerate(self._item.palettes[:_MAX_PALETTES]):
                texture = _PALETTE_TEXTURE.format(colornum=colorNum)
                icon = camoIconTemplate(texture, _PALETTE_WIDTH, _PALETTE_HEIGHT, palette, background=_PALETTE_BACKGROUND)
                swatchColors.append(CustomizationCamoSwatchVO(icon, idx == self._component.palette)._asdict())

        scaleText = VEHICLE_CUSTOMIZATION.CUSTOMIZATION_POPOVER_CAMO_SCALE
        itemData = self._getItemData()
        if itemData is None:
            itemData = {'intCD': 0,
                        'icon': RES_ICONS.MAPS_ICONS_LIBRARY_TANKITEM_BUY_TANK_POPOVER_SMALL}
        return CustomizationCamoAnchorVO(self._name, self._desc, self._isEmpty, itemData, swatchColors, scaleText,
                                         swatchScales).asDict()
