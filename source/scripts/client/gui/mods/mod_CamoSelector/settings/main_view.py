import math

import BigWorld
from AvatarInputHandler import cameras, mathUtils
from CurrentVehicle import g_currentVehicle
from account_helpers.settings_core.settings_constants import GRAPHICS
from adisp import async
from functools import partial
from gui import DialogsInterface, SystemMessages, g_tankActiveCamouflage
from gui.Scaleform.daapi.settings.views import VIEW_ALIAS
from gui.Scaleform.daapi.view.dialogs import I18nConfirmDialogMeta
from gui.Scaleform.daapi.view.lobby.customization import CustomizationItemCMHandler
from gui.Scaleform.daapi.view.lobby.customization.customization_cm_handlers import CustomizationOptions
from gui.Scaleform.daapi.view.lobby.customization.customization_item_vo import buildCustomizationItemDataVO
from gui.Scaleform.daapi.view.lobby.customization.main_view import ANCHOR_ALPHA_MIN, ANCHOR_FADE_EXPO, \
    ANCHOR_UPDATE_FREQUENCY, ANCHOR_UPDATE_TIMER_DELAY, AnchorPositionData, CustomizationAnchorInitVO, \
    CustomizationAnchorPositionVO, CustomizationAnchorsSetVO, CustomizationCarouselDataVO, CustomizationSlotIdVO, \
    CustomizationSlotUpdateVO, _C11nWindowsLifecycleHandler
from gui.Scaleform.daapi.view.lobby.customization.shared import OutfitInfo, SEASONS_ORDER, SEASON_IDX_TO_TYPE, \
    SEASON_TYPE_TO_NAME
from gui.Scaleform.daapi.view.lobby.customization.sound_constants import C11N_SOUND_SPACE, SOUNDS
from gui.Scaleform.daapi.view.meta.CustomizationMainViewMeta import CustomizationMainViewMeta
from gui.Scaleform.framework.managers.view_lifecycle_watcher import ViewLifecycleWatcher
from gui.Scaleform.genConsts.CUSTOMIZATION_ALIASES import CUSTOMIZATION_ALIASES
from gui.Scaleform.locale.MESSENGER import MESSENGER
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from gui.Scaleform.locale.SYSTEM_MESSAGES import SYSTEM_MESSAGES
from gui.Scaleform.locale.TOOLTIPS import TOOLTIPS
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION
from gui.SystemMessages import CURRENCY_TO_SM_TYPE, SM_TYPE
from gui.app_loader import g_appLoader
from gui.app_loader.settings import GUI_GLOBAL_SPACE_ID as _SPACE_ID
from gui.shared import EVENT_BUS_SCOPE, events, g_eventBus
from gui.shared.formatters import formatPrice, getItemPricesVO, icons, text_styles
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.gui_items.gui_item_economics import ITEM_PRICE_EMPTY, ItemPrice
from gui.shared.utils import toUpper
from gui.shared.utils.HangarSpace import g_hangarSpace
from gui.shared.utils.decorators import process
from gui.shared.utils.functions import makeTooltip
from helpers import dependency, int2roman
from helpers.i18n import makeString as _ms
from items.components.c11n_constants import SeasonType
from skeletons.account_helpers.settings_core import ISettingsCore
from skeletons.gui.customization import ICustomizationService
from skeletons.gui.lobby_context import ILobbyContext
from skeletons.gui.shared import IItemsCache
from .carousel import CustomizationCarouselDataProvider, comparisonKey
from .processors import OutfitApplier
from .shared import C11N_MODE, CUSTOMIZATION_TABS, POPOVER_ALIAS, chooseMode, getCustomPurchaseItems, getItemInventoryCount, \
    getTotalPurchaseInfo
from .. import g_config


class CamoSelectorMainView(CustomizationMainViewMeta):
    _COMMON_SOUND_SPACE = C11N_SOUND_SPACE
    lobbyContext = dependency.descriptor(ILobbyContext)
    itemsCache = dependency.descriptor(IItemsCache)
    service = dependency.descriptor(ICustomizationService)
    settingsCore = dependency.descriptor(ISettingsCore)

    def __init__(self, _=None):
        super(CamoSelectorMainView, self).__init__()
        self.__viewLifecycleWatcher = ViewLifecycleWatcher()
        self.fadeAnchorsOut = False
        self.anchorMinScale = 0.75
        self._currentSeason = SeasonType.SUMMER
        self._tabIndex = CUSTOMIZATION_TABS.SHOP
        self._lastTab = CUSTOMIZATION_TABS.SHOP
        self._originalOutfits = {}
        self._modifiedOutfits = {}
        self._currentOutfit = None
        self._mode = C11N_MODE.INSTALL
        self._isDeferredRenderer = True
        self.__anchorPositionCallbackID = None
        self._state = {}
        self._needFullRebuild = False
        self.__hangarSpace = g_hangarSpace.space
        self.__locatedOnEmblem = False
        self.itemIsPicked = False

    def _populate(self):
        super(CamoSelectorMainView, self)._populate()
        self.soundManager.playInstantSound(SOUNDS.ENTER)
        self.__viewLifecycleWatcher.start(self.app.containerManager, [_C11nWindowsLifecycleHandler()])
        self._isDeferredRenderer = self.settingsCore.getSetting(GRAPHICS.RENDER_PIPELINE) == 0
        self.lobbyContext.addHeaderNavigationConfirmator(self.__confirmHeaderNavigation)
        self.lobbyContext.getServerSettings().onServerSettingsChange += self.__onServerSettingChanged
        self.service.onCarouselFilter += self.__onCarouselFilter
        self.service.onRemoveItems += self.removeItems
        self.service.onOutfitChanged += self.__onOutfitChanged
        g_eventBus.addListener(events.LobbySimpleEvent.NOTIFY_SPACE_MOVED, self.__onNotifySpaceMoved)
        g_eventBus.addListener(events.LobbySimpleEvent.NOTIFY_CURSOR_DRAGGING, self.__onNotifyCursorDragging)
        g_hangarSpace.onSpaceCreate += self.__onSpaceCreateHandler
        self.service.onRegionHighlighted += self.__onRegionHighlighted
        self.itemsCache.onSyncCompleted += self.__onCacheReSync
        self.__carveUpOutfits()
        self._carouselDP = CustomizationCarouselDataProvider(g_currentVehicle, self._carouseItemWrapper, self)
        self._carouselDP.setFlashObject(self.as_getDataProviderS())
        self._carouselDP.setEnvironment(self.app)
        self.__setHeaderInitData()
        self.__setFooterInitData()
        self.__setBuyingPanelData()
        self.__setSeasonData()
        self.refreshOutfit()

    def _dispose(self):
        if g_appLoader.getSpaceID() != _SPACE_ID.LOGIN:
            self.__releaseItemSound()
            self.soundManager.playInstantSound(SOUNDS.EXIT)
        if self.__locatedOnEmblem:
            self.__hangarSpace.clearSelectedEmblemInfo()
            self.__hangarSpace.locateCameraToPreview()
        self.__viewLifecycleWatcher.stop()
        self.__stopTimer()
        self.service.stopHighlighter()
        self.lobbyContext.deleteHeaderNavigationConfirmator(self.__confirmHeaderNavigation)
        self.lobbyContext.getServerSettings().onServerSettingsChange -= self.__onServerSettingChanged
        self.service.onCarouselFilter -= self.__onCarouselFilter
        self.service.onRemoveItems -= self.removeItems
        self.service.onOutfitChanged -= self.__onOutfitChanged
        g_eventBus.removeListener(events.LobbySimpleEvent.NOTIFY_SPACE_MOVED, self.__onNotifySpaceMoved)
        g_eventBus.removeListener(events.LobbySimpleEvent.NOTIFY_CURSOR_DRAGGING, self.__onNotifyCursorDragging)
        g_hangarSpace.onSpaceCreate -= self.__onSpaceCreateHandler
        self.service.onRegionHighlighted -= self.__onRegionHighlighted
        self.itemsCache.onSyncCompleted -= self.__onCacheReSync
        if g_currentVehicle.item:
            g_tankActiveCamouflage[g_currentVehicle.item.intCD] = self._currentSeason
            g_currentVehicle.refreshModel()
        super(CamoSelectorMainView, self)._dispose()

    def __setHeaderInitData(self):
        vehicle = g_currentVehicle.item
        self.as_setHeaderDataS({'tankTier': str(int2roman(vehicle.level)),
                                'tankName': vehicle.shortUserName,
                                'tankType': '{}_elite'.format(vehicle.type) if vehicle.isElite else vehicle.type,
                                'isElite': vehicle.isElite,
                                'closeBtnTooltip': VEHICLE_CUSTOMIZATION.CUSTOMIZATION_HEADERCLOSEBTN,
                                'historicVO': self.__getHistoricIndicatorData()})

    def __setFooterInitData(self):
        self.as_setBottomPanelInitDataS(
            {'tabData': {
                'tabData': self.__getItemTabsData(),
                'selectedTab': self._tabIndex},
             'tabsAvailableRegions': CUSTOMIZATION_TABS.AVAILABLE_REGIONS,
             'defaultStyleLabel': VEHICLE_CUSTOMIZATION.DEFAULTSTYLE_LABEL,
             'carouselInitData': self.__getCarouselInitData(),
             'switcherInitData': self.__getSwitcherInitData()})
        self.as_setCarouselFiltersInitDataS(
            {'popoverAlias': VIEW_ALIAS.CUSTOMIZATION_FILTER_POPOVER,
             'mainBtn': {'value': RES_ICONS.MAPS_ICONS_BUTTONS_FILTER,
                         'tooltip': VEHICLE_CUSTOMIZATION.CAROUSEL_FILTER_MAINBTN},
             'hotFilters': [{'value': RES_ICONS.MAPS_ICONS_CUSTOMIZATION_STORAGE_ICON,
                             'tooltip': VEHICLE_CUSTOMIZATION.CAROUSEL_FILTER_STORAGEBTN,
                             'selected': self._carouselDP.getOwnedFilter()},
                            {'value': RES_ICONS.MAPS_ICONS_BUTTONS_EQUIPPED_ICON,
                             'tooltip': VEHICLE_CUSTOMIZATION.CAROUSEL_FILTER_EQUIPPEDBTN,
                             'selected': self._carouselDP.getAppliedFilter()}]})

    def __getSwitcherInitData(self):
        """ Switcher is a style/custom selector.
        """
        return {'leftLabel': g_config.i18n['UI_flash_switcher_%s' % C11N_MODE.NAMES[self._mode]],
                'rightLabel': g_config.i18n['UI_flash_switcher_%s' % C11N_MODE.NAMES[not self._mode]],
                'leftEvent': 'installStyle%s' % ('s' if self._mode else ''),
                'rightEvent': 'installStyle%s' % ('s' if not self._mode else ''),
                'isLeft': True}

    def __setBuyingPanelData(self, *_):
        """ Update the buying panel according to the current state of cart.
        """
        purchaseItems = self.getPurchaseItems()
        cart = getTotalPurchaseInfo(purchaseItems)
        totalPriceVO = getItemPricesVO(cart.totalPrice)
        if cart.totalPrice != ITEM_PRICE_EMPTY:
            label = g_config.i18n['UI_flash_commit_install']
            self.as_showBuyingPanelS()
        else:
            label = g_config.i18n['UI_flash_commit_apply']
            self.as_hideBuyingPanelS()
        isApplyEnabled = bool(cart.numTotal)
        shortage = self.itemsCache.items.stats.money.getShortage(cart.totalPrice.price)
        self.as_setBottomPanelHeaderS({'buyBtnEnabled': isApplyEnabled,
                                       'buyBtnLabel': label,
                                       'enoughMoney': getItemPricesVO(ItemPrice(shortage, shortage))[0],
                                       'pricePanel': totalPriceVO[0]})

    def __setSeasonData(self):
        seasonRenderersList = []
        for season in SEASONS_ORDER:
            seasonName = SEASON_TYPE_TO_NAME.get(season)
            seasonRenderersList.append({'seasonName': VEHICLE_CUSTOMIZATION.getSeasonName(seasonName),
                                        'seasonIconSmall': RES_ICONS.getSeasonIcon(seasonName)})

        self.as_setSeasonPanelDataS({'seasonRenderersList': seasonRenderersList})

    def getPurchaseItems(self):
        return getCustomPurchaseItems(self.getOutfitsInfo())

    def showBuyWindow(self):
        """  Displays the purchase / buy window or apply immediately.
        """
        self.__releaseItemSound()
        self.soundManager.playInstantSound(SOUNDS.SELECT)
        purchaseItems = self.getPurchaseItems()
        cart = getTotalPurchaseInfo(purchaseItems)
        if cart.totalPrice == ITEM_PRICE_EMPTY:
            self.buyAndExit(purchaseItems)
        else:
            self.as_hideAnchorPropertySheetS()
            self.fireEvent(events.LoadViewEvent(VIEW_ALIAS.CUSTOMIZATION_PURCHASE_WINDOW), EVENT_BUS_SCOPE.LOBBY)

    def onSelectItem(self, index):
        """ Select item in the carousel
        """
        self._carouselDP.selectItemIdx(index)
        self.soundManager.playInstantSound(SOUNDS.SELECT)

    def onPickItem(self):
        """ Pick item in the carousel
        """
        if not self.itemIsPicked:
            self.soundManager.playInstantSound(SOUNDS.PICK)
            self.itemIsPicked = True

    def onReleaseItem(self):
        """ Release selected item
        """
        self.__releaseItemSound()

    def changeSeason(self, seasonIdx):
        """ Change the current season.
        """
        self._currentSeason = SEASON_IDX_TO_TYPE[seasonIdx]
        seasonName = SEASON_TYPE_TO_NAME.get(self._currentSeason)
        self.soundManager.playInstantSound(SOUNDS.SEASON_SELECT.format(seasonName))
        self.refreshOutfit()
        self.refreshCarousel(rebuild=True)
        self.as_refreshAnchorPropertySheetS()
        self.__setAnchorsInitData(self._tabIndex, True, True)

    def refreshCarousel(self, rebuild=False):
        if rebuild:
            self._carouselDP.buildList(self._tabIndex, self._currentSeason, refresh=False)
            self.as_setCarouselDataS(self._buildCustomizationCarouselDataVO())
        self._carouselDP.refresh()

    def refreshHotFilters(self):
        self.as_setCarouselFiltersDataS(
            {'hotFilters': [self._carouselDP.getOwnedFilter(), self._carouselDP.getAppliedFilter()]})

    def refreshOutfit(self):
        """ Apply any changes to the vehicle's 3d model.
        """
        self._currentOutfit = self._modifiedOutfits[self._currentSeason]
        self.service.tryOnOutfit(self._currentOutfit)
        g_tankActiveCamouflage[g_currentVehicle.item.intCD] = self._currentSeason

    def showGroupFromTab(self, tabIndex):
        """ This is called when a tab change occurs in the front end.

        Initialize the new anchor or region set for the new tab group.
        Rebuild the carousel's DAAPIDataProvider
        Build bookmark data and send to ActionScript

        :param tabIndex: index of the newly selected tab
        """
        self.soundManager.playInstantSound(SOUNDS.TAB_SWITCH)
        self._tabIndex = tabIndex
        self.service.stopHighlighter()
        self.service.startHighlighter(chooseMode(self._mode, g_currentVehicle.item))
        self.__stopTimer()
        self.__setAnchorsInitData(self._tabIndex, True)
        self.__updateAnchorPositions()
        # slotIdVO = None
        # self.as_updateSelectedRegionsS(slotIdVO)
        self.refreshCarousel(rebuild=True)

    def installCustomizationElement(self, intCD, areaId, slotId, regionId, seasonIdx):
        """ Install the given item on a vehicle.
        """
        if self.itemIsPicked:
            self.soundManager.playInstantSound(SOUNDS.APPLY)
        item = self.itemsCache.items.getItemByCD(intCD)
        season = SEASON_IDX_TO_TYPE.get(seasonIdx, self._currentSeason)
        outfit = self._modifiedOutfits[season]
        outfit.getContainer(areaId).slotFor(slotId).set(item, idx=regionId)
        outfit.invalidate()
        self.refreshOutfit()
        self.__setBuyingPanelData()
        self.__setHeaderInitData()
        self.refreshCarousel(rebuild=self._carouselDP.getAppliedFilter() or self._carouselDP.getOwnedFilter())

    def clearCustomizationItem(self, areaId, slotId, regionId, seasonIdx):
        """ Removes the item from the given region.
        (called from property sheet).
        """
        self.soundManager.playInstantSound(SOUNDS.REMOVE)
        season = SEASON_IDX_TO_TYPE.get(seasonIdx, self._currentSeason)
        outfit = self._modifiedOutfits[season]
        outfit.getContainer(areaId).slotFor(slotId).remove(idx=regionId)
        self.refreshOutfit()
        self.__setAnchorsInitData(self._tabIndex, True, True)
        self.__setBuyingPanelData()
        self.__setHeaderInitData()
        self.refreshCarousel(rebuild=self._carouselDP.getAppliedFilter() or self._carouselDP.getOwnedFilter())

    def switchToCustom(self, updateUI=True):
        """ Turn on the Custom customization mode
        (where you create vehicle's look by yourself).
        """
        self.switchMode(C11N_MODE.INSTALL)

    def switchToStyle(self):
        """ Turn on the Style customization mode
        (where you use predefined vehicle looks).
        """
        self.switchMode(C11N_MODE.SETUP)

    def switchMode(self, mode):
        self.soundManager.playInstantSound(SOUNDS.TAB_SWITCH)
        self._mode = mode
        if self._mode == C11N_MODE.SETUP:
            self.__onRegionHighlighted(GUI_ITEM_TYPE.CAMOUFLAGE, 1, 0, True, False)
        self.refreshOutfit()
        self.__setFooterInitData()
        self._carouselDP.selectItem()
        self.__setBuyingPanelData()
        self.__setHeaderInitData()

    def fadeOutAnchors(self, isFadeOut):
        """ Set whether or not to fade anchors out
        """
        self.fadeAnchorsOut = isFadeOut

    def closeWindow(self):
        purchaseItems = self.getPurchaseItems()
        cart = getTotalPurchaseInfo(purchaseItems)
        if cart.numTotal:
            DialogsInterface.showDialog(I18nConfirmDialogMeta('customization/close'), self.__onConfirmCloseWindow)
        else:
            self.__onConfirmCloseWindow(proceed=True)

    def itemContextMenuDisplayed(self):
        """
        ActionScript initiated call that happens after the item context menu is displayed.
        Sets up an event for menu item presses
        """
        cmHandler = self.app.contextMenuManager.getCurrentHandler()
        if isinstance(cmHandler, CustomizationItemCMHandler):
            cmHandler.onSelected += self._itemCtxMenuSelected

    def resetFilter(self):
        """ Reset filter and rebuild carousel
        """
        self.clearFilter()
        self.refreshFilterData()
        self.refreshHotFilters()
        self.refreshCarousel(rebuild=True)

    def clearFilter(self):
        """ Reset filter and rebuild carousel
        """
        self._carouselDP.clearFilter()

    def refreshFilterData(self):
        """ Send new filter data to AS3.
        """
        self.as_setFilterDataS(self._carouselDP.getFilterData())

    def getHistoricalPopoverData(self):
        """ Get the unhistorical items for the Unhistorical popover (in the header)
        """
        self.soundManager.playInstantSound(SOUNDS.SELECT)
        items = []
        for outfit in self._modifiedOutfits.itervalues():
            items.extend((item for item in outfit.items() if not item.isHistorical()))

        return {'items': [item.intCD for item in sorted(items, key=comparisonKey)]}

    def removeItems(self, *intCDs):
        """ Remove the given item from every outfit.
        Don't care about mode there.
        """
        self.soundManager.playInstantSound(SOUNDS.REMOVE)
        for outfit in self._modifiedOutfits.itervalues():
            for slot in outfit.slots():
                for idx in range(slot.capacity()):
                    item = slot.getItem(idx)
                    if item and item.intCD in intCDs:
                        slot.remove(idx)

        self.refreshOutfit()
        self.__setHeaderInitData()
        self.__setBuyingPanelData()
        self.as_refreshAnchorPropertySheetS()
        self.refreshCarousel(rebuild=self._carouselDP.getAppliedFilter() or self._carouselDP.getOwnedFilter())

    def updatePropertySheetButtons(self, areaId, slotId, regionId):
        self.service.onPropertySheetShow(areaId, slotId, regionId)

    def onLobbyClick(self):
        pass

    # noinspection SpellCheckingInspection
    def setEnableMultiselectRegions(self, isEnabled):
        """ Turn off highlighting when doing pick'n'click.
        """
        self.service.setSelectHighlighting(isEnabled)

    def onChangeSize(self):
        self.__updateAnchorPositions()

    def onSelectAnchor(self, areaID, regionID):
        assert False

    def getOutfitsInfo(self):
        outfitsInfo = {}
        for season in SEASONS_ORDER:
            outfitsInfo[season] = OutfitInfo(self._originalOutfits[season], self._modifiedOutfits[season])

        return outfitsInfo

    def getItemInventoryCount(self, item):
        return getItemInventoryCount(item, self.getOutfitsInfo())

    def getCurrentOutfit(self):
        """ Returns current outfit applied on the vehicle.
        """
        return self._currentOutfit

    def getModifiedOutfit(self, season):
        """ Returns modified outfit for the given season.
        """
        return self._modifiedOutfits.get(season)

    def getMode(self):
        return C11N_MODE.INSTALL

    def getCurrentSeason(self):
        return self._currentSeason

    def getCurrentTab(self):
        return self._tabIndex

    def getAppliedItems(self, isOriginal=True):
        outfits = self._originalOutfits if isOriginal else self._modifiedOutfits
        seasons = SeasonType.COMMON_SEASONS if isOriginal else (self._currentSeason,)
        appliedItems = set()
        for seasonType in seasons:
            outfit = outfits[seasonType]
            appliedItems.update((i.intCD for i in outfit.items()))
        return appliedItems

    def isItemInOutfit(self, item):
        """ Check if item is in any outfit.
        """
        return any((outfit.has(item) for outfit in self._originalOutfits.itervalues())) or any(
            (outfit.has(item) for outfit in self._modifiedOutfits.itervalues()))

    @process('buyAndInstall')
    def buyAndExit(self, purchaseItems):
        self.itemsCache.onSyncCompleted -= self.__onCacheReSync
        cart = getTotalPurchaseInfo(purchaseItems)
        groupHasItems = {SeasonType.WINTER: False,
                         SeasonType.SUMMER: False,
                         SeasonType.DESERT: False}
        modifiedOutfits = {season: outfit.copy() for season, outfit in self._modifiedOutfits.iteritems()}
        results = []
        for pItem in purchaseItems:
            if not pItem.selected:
                if pItem.slot:
                    slot = modifiedOutfits[pItem.group].getContainer(pItem.areaID).slotFor(pItem.slot)
                    slot.remove(pItem.regionID)
            groupHasItems[pItem.group] = True

        groupHasItems[self._currentSeason] = True
        empty = self.service.getEmptyOutfit()
        for season in SeasonType.COMMON_SEASONS:
            if groupHasItems[season]:
                yield OutfitApplier(g_currentVehicle.item, empty, season).request()

        for season in SeasonType.COMMON_SEASONS:
            if groupHasItems[season]:
                outfit = modifiedOutfits[season]
                result = yield OutfitApplier(g_currentVehicle.item, outfit, season).request()
                results.append(result)

        errorCount = 0
        for result in results:
            if not result.success:
                errorCount += 1
            if result.userMsg:
                SystemMessages.pushI18nMessage(result.userMsg, type=result.sysMsgType)

        if not errorCount:
            if cart.totalPrice != ITEM_PRICE_EMPTY:
                msgCtx = {'money': formatPrice(cart.totalPrice.price),
                          'count': cart.numSelected}
                SystemMessages.pushI18nMessage(MESSENGER.SERVICECHANNELMESSAGES_SYSMSG_CONVERTER_CUSTOMIZATIONSBUY,
                                               type=CURRENCY_TO_SM_TYPE.get(cart.totalPrice.getCurrency(byWeight=True),
                                                                            SM_TYPE.PurchaseForGold), **msgCtx)
            else:
                SystemMessages.pushI18nMessage(MESSENGER.SERVICECHANNELMESSAGES_SYSMSG_CONVERTER_CUSTOMIZATIONS,
                                               type=SM_TYPE.Information)
            self.__onCacheReSync()
        self.itemsCache.onSyncCompleted += self.__onCacheReSync

    # noinspection PyUnusedLocal
    @process('sellItem')
    def sellItem(self, intCD, shouldSell):
        assert False

    def _itemCtxMenuSelected(self, ctxMenuID, itemIntCD):
        """ Event notification for when a item context menu is pressed

        :param ctxMenuID: ID of the menu item pressed
        :param itemIntCD: item CD for fetching the correct item
        """
        item = self.itemsCache.items.getItemByCD(itemIntCD)
        if ctxMenuID == CustomizationOptions.REMOVE_FROM_TANK:
            self.removeItems(item.intCD)

    def _getUpdatedAnchorPositions(self):
        anchorVOs = []
        anchorPosData = []
        outfit = self.service.getEmptyOutfit()
        for container in outfit.containers():
            for slot in (x for x in container.slots() if x.getType() == GUI_ITEM_TYPE.CAMOUFLAGE):
                for regionId, region in enumerate(slot.getRegions()):
                    slotId = CustomizationSlotIdVO(container.getAreaID(), slot.getType(), regionId)
                    anchorData = self.__getAnchorPositionData(slotId, region)
                    if anchorData is not None:
                        anchorPosData.append(anchorData)

        anchorPosData.sort(key=lambda pos: pos.angleToCamera)
        for zIdx, posData in enumerate(anchorPosData):
            alpha = (posData.angleToCamera / math.pi) ** ANCHOR_FADE_EXPO
            alpha = mathUtils.clamp(ANCHOR_ALPHA_MIN, 1, alpha)
            if posData.angleToCamera > math.pi / 2:
                scale = (1 - self.anchorMinScale) * 2 * posData.angleToCamera / math.pi + 2 * self.anchorMinScale - 1
            else:
                scale = self.anchorMinScale
            anchorVOs.append(CustomizationAnchorPositionVO(posData.clipSpacePos.x, posData.clipSpacePos.y, alpha, scale, zIdx,
                                                           posData.slotId._asdict())._asdict())

        return CustomizationAnchorsSetVO(anchorVOs)._asdict()

    def _buildCustomizationCarouselDataVO(self):
        """ Builds and returns a CustomizationCarouselDataVO, which handles bookmarks.

        :return: CustomizationCarouselDataVO with information on bookmarks.
        """
        isZeroCount = self._carouselDP.itemCount == 0
        countStyle = text_styles.error if isZeroCount else text_styles.main
        displayString = text_styles.main(
            '{} / {}'.format(countStyle(str(self._carouselDP.itemCount)), str(self._carouselDP.totalItemCount)))
        shouldShow = self._carouselDP.itemCount < self._carouselDP.totalItemCount
        return CustomizationCarouselDataVO(displayString, isZeroCount, shouldShow,
                                           itemLayoutSize=self._carouselDP.getItemSizeData(),
                                           bookmarks=self._carouselDP.getBookmarkData())._asdict()

    def _carouseItemWrapper(self, itemCD):
        item = self.itemsCache.items.getItemByCD(itemCD)
        itemInventoryCount = self.getItemInventoryCount(item)
        isCurrentlyApplied = itemCD in self._carouselDP.getCurrentlyApplied()
        return buildCustomizationItemDataVO(item, itemInventoryCount, isCurrentlyApplied=isCurrentlyApplied, plainView=True)

    def __carveUpOutfits(self):
        """ Fill up the internal structures with vehicle's outfits.
        """
        for season in SeasonType.COMMON_SEASONS:
            outfit = self.service.getEmptyOutfit()
            # TODO: fill it up with installed camouflages
            self._originalOutfits[season] = outfit.copy()
            self._modifiedOutfits[season] = outfit.copy()

        self._currentOutfit = self._modifiedOutfits[self._currentSeason]

    def __updateAnchorPositions(self, _=None):
        self.as_setAnchorPositionsS(self._getUpdatedAnchorPositions())

    def __onRegionHighlighted(self, typeID, tankPartID, regionID, selected, hovered):
        slotId = None
        if hovered:
            self.soundManager.playInstantSound(SOUNDS.HOVER)
            return
        if tankPartID != -1 and regionID != -1:
            slotId = CustomizationSlotIdVO(tankPartID if self._mode == C11N_MODE.INSTALL else 1, typeID,
                                           regionID)._asdict()
            if selected:
                self.soundManager.playInstantSound(SOUNDS.CHOOSE)
        self.as_onRegionHighlightedS(slotId)

    def __onSpaceCreateHandler(self):
        self.refreshOutfit()
        self.__updateAnchorPositions()

    def __onConfirmCloseWindow(self, proceed):
        if proceed:
            self.fireEvent(events.LoadViewEvent(VIEW_ALIAS.LOBBY_HANGAR), scope=EVENT_BUS_SCOPE.LOBBY)

    def __onCarouselFilter(self, **kwargs):
        if 'group' in kwargs:
            self._carouselDP.setActiveGroupIndex(kwargs['group'])
        if 'historic' in kwargs:
            self._carouselDP.setHistoricalFilter(kwargs['historic'])
        if 'inventory' in kwargs:
            self._carouselDP.setOwnedFilter(kwargs['inventory'])
        if 'applied' in kwargs:
            self._carouselDP.setAppliedFilter(kwargs['applied'])
        self.refreshCarousel(rebuild=True)
        self.refreshHotFilters()

    def __onOutfitChanged(self):
        self.refreshOutfit()
        self.__setBuyingPanelData()

    def __onCacheReSync(self, *_):
        if not g_currentVehicle.isPresent():
            self.__onConfirmCloseWindow(proceed=True)
            return
        self.__preserveState()
        self.__carveUpOutfits()
        self.__restoreState()
        self.__setHeaderInitData()
        self.__setBuyingPanelData()
        self.as_refreshAnchorPropertySheetS()
        self.refreshCarousel(rebuild=self._needFullRebuild)
        self.refreshOutfit()
        self._needFullRebuild = False

    def __preserveState(self):
        self._state.update(modifiedOutfits={season: outfit.copy() for season, outfit in self._modifiedOutfits.iteritems()})

    def __restoreState(self):
        self._modifiedOutfits = self._state.get('modifiedOutfits')
        self._state.clear()

    def __onServerSettingChanged(self, diff):
        if 'isCustomizationEnabled' in diff and not diff.get('isCustomizationEnabled', True):
            SystemMessages.pushI18nMessage(SYSTEM_MESSAGES.CUSTOMIZATION_UNAVAILABLE, type=SystemMessages.SM_TYPE.Warning)
            self.__onConfirmCloseWindow(proceed=True)

    # noinspection PyUnusedLocal
    def __setAnchorsInitData(self, tabIndex, doRegions, update=False):
        anchorVOs = []
        cType = GUI_ITEM_TYPE.CAMOUFLAGE
        for container in self._currentOutfit.containers():
            for slot in (x for x in container.slots() if x.getType() == cType):
                for regionId, region in enumerate(slot.getRegions()):
                    slotId = CustomizationSlotIdVO(container.getAreaID(), slot.getType(), regionId)
                    popoverAlias = POPOVER_ALIAS
                    item = slot.getItem(regionId)
                    itemIntCD = item.intCD if item is not None else 0
                    if self.__getAnchorPositionData(slotId, region) is not None:
                        anchorVOs.append(CustomizationSlotUpdateVO(slotId._asdict(), popoverAlias, itemIntCD)._asdict())

        if update:
            self.as_updateAnchorDataS(CustomizationAnchorInitVO(anchorVOs, doRegions)._asdict())
        else:
            self.as_setAnchorInitS(CustomizationAnchorInitVO(anchorVOs, doRegions)._asdict())

    def onSelectHotFilter(self, index, value):
        (self._carouselDP.setOwnedFilter, self._carouselDP.setAppliedFilter)[index](value)
        self.refreshCarousel(rebuild=True)

    def __getHistoricIndicatorData(self):
        """ Historicity indicator and name of the current style or custom outfit.
        """
        isDefault = all((outfit.isEmpty() for outfit in self._modifiedOutfits.itervalues()))
        isHistorical = all((outfit.isHistorical() for outfit in self._modifiedOutfits.itervalues()))
        name = _ms(VEHICLE_CUSTOMIZATION.HISTORICINDICATOR_STYLENAME_CUSTSOMSTYLE) if not isDefault else ''
        txtStyle = text_styles.stats if isHistorical else text_styles.tutorial
        return {'historicText': txtStyle(toUpper(name)),
                'isDefaultAppearance': isDefault,
                'isHistoric': isHistorical,
                'tooltip': TOOLTIPS.CUSTOMIZATION_NONHISTORICINDICATOR if not isHistorical else ''}

    @staticmethod
    def __getCarouselInitData():
        return {'message': '{}{}\n{}'.format(icons.makeImageTag(RES_ICONS.MAPS_ICONS_LIBRARY_ATTENTIONICONFILLED, vSpace=-3),
                                             text_styles.neutral(VEHICLE_CUSTOMIZATION.CAROUSEL_MESSAGE_HEADER),
                                             text_styles.main(VEHICLE_CUSTOMIZATION.CAROUSEL_MESSAGE_DESCRIPTION))}

    def __getAnchorPositionData(self, slotId, region):
        anchorPos = self.service.getPointForRegionLeaderLine(region)
        anchorNorm = anchorPos
        return None if anchorPos is None or anchorNorm is None else AnchorPositionData(
            cameras.get2DAngleFromCamera(anchorNorm), cameras.projectPoint(anchorPos), slotId)

    def __getItemTabsData(self):
        """ Tabs with customization items.
        """
        data = []
        for tabIdx in self.__getVisibleTabs():
            data.append({'label': g_config.i18n['UI_flash_tabs_%s_text' % tabIdx],
                         'tooltip': makeTooltip(g_config.i18n['UI_flash_tabs_%s_text' % tabIdx],
                                                g_config.i18n['UI_flash_tabs_%s_tooltip' % tabIdx]),
                         'id': tabIdx})

        return data

    def __getVisibleTabs(self):
        """ Get tabs that are actually visible.
        """
        visibleTabs = []
        for tabIdx in CUSTOMIZATION_TABS.VISIBLE:
            data = self._carouselDP.getSeasonAndTabData(tabIdx, self._currentSeason)
            if not data.itemCount:
                continue
            visibleTabs.append(tabIdx)

        return visibleTabs

    def __onNotifySpaceMoved(self, _):
        if self.__anchorPositionCallbackID is None:
            self.__startTimer(ANCHOR_UPDATE_TIMER_DELAY, self.__updateAnchorPositions)

    def __onNotifyCursorDragging(self, event):
        isDragging = event.ctx.get('isDragging', False)
        if not isDragging and self.__anchorPositionCallbackID is None:
            self.__startTimer(ANCHOR_UPDATE_TIMER_DELAY, self.__updateAnchorPositions)

    def __startTimer(self, delay, handler):
        self.__finishTime = BigWorld.time() + delay
        self.__updateTimer(handler)

    def __updateTimer(self, handler):
        if BigWorld.time() < self.__finishTime:
            self.__anchorPositionCallbackID = BigWorld.callback(ANCHOR_UPDATE_FREQUENCY, partial(self.__updateTimer, handler))
            handler()
        else:
            self.__stopTimer()

    def __stopTimer(self):
        if self.__anchorPositionCallbackID is not None:
            BigWorld.cancelCallback(self.__anchorPositionCallbackID)
            self.__anchorPositionCallbackID = None
            self.__finishTime = 0

    @async
    def __confirmHeaderNavigation(self, callback):
        purchaseItems = self.getPurchaseItems()
        cart = getTotalPurchaseInfo(purchaseItems)
        if cart.numTotal:
            DialogsInterface.showI18nConfirmDialog('customization/close', callback)
        else:
            callback(True)

    def __releaseItemSound(self):
        if self.itemIsPicked:
            self.soundManager.playInstantSound(SOUNDS.RELEASE)
            self.itemIsPicked = False
