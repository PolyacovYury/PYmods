from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.view.lobby.customization import shared as sh
from gui.Scaleform.daapi.view.lobby.customization.main_view import MainView as WGMainView, _logger
from gui.Scaleform.daapi.view.lobby.customization.shared import CustomizationTabs, checkSlotsFilling
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION
from gui.customization.constants import CustomizationModes
from gui.customization.shared import SEASONS_ORDER, isVehicleCanBeCustomized
from gui.impl.backport import image, text
from gui.impl.gen import R
from gui.shared.formatters import icons, text_styles
from gui.shared.gui_items import GUI_ITEM_TYPE, GUI_ITEM_TYPE_NAMES
from gui.shared.utils.requesters import REQ_CRITERIA
from helpers import int2roman
from items.components.c11n_constants import EDITABLE_STYLE_STORAGE_DEPTH
from .. import g_config


class MainView(WGMainView):
    def __setNotificationCounters(self):
        itemTypes = sh.getItemTypesAvailableForVehicle() if self.__ctx.isPurchase else ()
        if not itemTypes:
            return self.as_setNotificationCountersS([0 for _ in SEASONS_ORDER])
        seasonCounters = {season: 0 for season in SEASONS_ORDER}
        itemsFilter = ~REQ_CRITERIA.CUSTOMIZATION.ALL_SEASON
        if self.__ctx.modeId == sh.CustomizationModes.EDITABLE_STYLE:
            itemsFilter |= REQ_CRITERIA.CUSTOM(lambda item: self.__ctx.mode.style.isItemInstallable(item))
        for season in SEASONS_ORDER:
            if season != self.__ctx.season:
                seasonCounters[season] = g_currentVehicle.item.getC11nItemsNoveltyCounter(
                    g_currentVehicle.itemsCache.items, itemTypes, season, itemsFilter)
        self.as_setNotificationCountersS([seasonCounters[season] for season in SEASONS_ORDER])

    def onPressClearBtn(self):
        WGMainView.onPressClearBtn(self)
        self.__ctx.cancelChanges()

    def __needsSpecialLabel(self):
        counter = 0
        for intCD in self.__bottomPanel._carouselDP.collection:
            item = self.service.getItemByCD(intCD)
            if item.itemTypeID != GUI_ITEM_TYPE.STYLE:
                break
            if item.canBeEditedForVehicle(g_currentVehicle.item.intCD):
                counter += 1
            if counter > EDITABLE_STYLE_STORAGE_DEPTH:
                return True

    def __getItemsCounterText(self):
        slotType = self.__ctx.mode.slotType
        if self.__ctx.modeId == CustomizationModes.STYLED and self.__needsSpecialLabel():
            return text_styles.vehicleStatusSimpleText(text(
                R.strings.vehicle_customization.savedStyles.label(),
                img=icons.makeImageTag(image(R.images.gui.maps.icons.customization.edited_big())),
                current=len(self.service.getStoredStyleDiffs()), max=EDITABLE_STYLE_STORAGE_DEPTH))
        if self.__ctx.mode.tabId == CustomizationTabs.STYLES:
            if self.__ctx.mode.modifiedStyle is not None:
                return text_styles.bonusPreviewText(text(
                    R.strings.vehicle_customization.customization.header.counter.editablestyle.installed(),
                    name=self.__ctx.mode.modifiedStyle.userName))
            else:
                return text_styles.stats(text(
                    R.strings.vehicle_customization.customization.header.counter.style.notInstalled()))
        if self.__ctx.modeId == CustomizationModes.EDITABLE_STYLE:
            return text_styles.bonusPreviewText(text(
                R.strings.vehicle_customization.customization.header.counter.editablestyle.installed(),
                name=self.__ctx.mode.style.userName))
        if not isVehicleCanBeCustomized(g_currentVehicle.item, slotType):
            return ''
        if slotType == GUI_ITEM_TYPE.INSIGNIA:
            insignia_text = text(R.strings.achievements.marksOnGun0()) + ': ' + text(
                R.strings.achievements.marksOnGun.descr.param.label.num(
                    self.hangarSpace.space.getVehicleEntity().appearance._getThisVehicleDossierInsigniaRank())())
            try:
                from helpers.i18n.hangarpainter import _config as _
                insignia_text = "<font color='#%s'>%s</font>" % (_.data['colour'], insignia_text)
            except ImportError:
                pass
            return text_styles.bonusPreviewText(insignia_text)
        typeName = GUI_ITEM_TYPE_NAMES[slotType]
        slotsCount, filledSlotsCount = checkSlotsFilling(self.__ctx.mode.currentOutfit, slotType)
        return (text_styles.bonusPreviewText if slotsCount == filledSlotsCount else text_styles.stats)(text(
            R.strings.vehicle_customization.customization.header.counter.dyn(typeName)(),
            filled=filledSlotsCount, available=slotsCount))

    def __setHeaderInitData(self):
        vehicle = g_currentVehicle.item
        self.as_setHeaderDataS({
            'tankTier': str(int2roman(vehicle.level)),
            'tankName': vehicle.shortUserName,
            'tankInfo': self.__getItemsCounterText(),
            'tankType': '{}_elite'.format(vehicle.type) if vehicle.isElite else vehicle.type,
            'isElite': vehicle.isElite,
            'closeBtnTooltip': VEHICLE_CUSTOMIZATION.CUSTOMIZATION_HEADERCLOSEBTN})

    def __selectFirstVisibleTab(self):
        visibleTabs = self.__bottomPanel.getVisibleTabs()
        if not visibleTabs:
            _logger.error('There is no visible customization tabs for current vehicle: %s', g_currentVehicle.item)
        elif self.__ctx.mode.tabId not in visibleTabs:
            self.__ctx.mode.changeTab(visibleTabs[0])


@overrideMethod(WGMainView, '__new__')
def new(base, cls, *a, **kw):
    if not g_config.data['enabled']:
        return base(cls, *a, **kw)
    return base(MainView, *a, **kw)
