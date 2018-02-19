import struct

import items.vehicles
from AvatarInputHandler import cameras
from CurrentVehicle import g_currentVehicle
from PYmodsCore import loadJson
from account_helpers.settings_core.settings_constants import GRAPHICS, GAME
from adisp import async, process as adisp_process
from gui import DialogsInterface, SystemMessages, g_tankActiveCamouflage
from gui.Scaleform.daapi.settings.views import VIEW_ALIAS
from gui.Scaleform.daapi.view.dialogs import I18nConfirmDialogMeta
from gui.Scaleform.daapi.view.lobby.customization import CustomizationItemCMHandler
from gui.Scaleform.daapi.view.lobby.customization.customization_cm_handlers import CustomizationOptions
from gui.Scaleform.daapi.view.lobby.customization.customization_item_vo import buildCustomizationItemDataVO
from gui.Scaleform.daapi.view.lobby.customization.main_view import AnchorPositionData, CustomizationAnchorInitVO, \
    CustomizationAnchorPositionVO, CustomizationAnchorsSetVO, CustomizationCarouselDataVO, CustomizationSlotIdVO, \
    CustomizationSlotUpdateVO, _C11nWindowsLifecycleHandler, _VehicleCustomizationAnchorsUpdater
from gui.Scaleform.daapi.view.lobby.customization.shared import OutfitInfo, SEASONS_ORDER, SEASON_IDX_TO_TYPE, \
    SEASON_TYPE_TO_NAME, getCustomPurchaseItems, getItemInventoryCount, getTotalPurchaseInfo
from gui.Scaleform.daapi.view.lobby.customization.sound_constants import C11N_SOUND_SPACE, SOUNDS
from gui.Scaleform.daapi.view.meta.CustomizationMainViewMeta import CustomizationMainViewMeta
from gui.Scaleform.framework.managers.view_lifecycle_watcher import ViewLifecycleWatcher
from gui.Scaleform.genConsts.CUSTOMIZATION_ALIASES import CUSTOMIZATION_ALIASES
from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from gui.Scaleform.locale.MESSENGER import MESSENGER
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from gui.Scaleform.locale.SYSTEM_MESSAGES import SYSTEM_MESSAGES
from gui.Scaleform.locale.TOOLTIPS import TOOLTIPS
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION
from gui.SystemMessages import CURRENCY_TO_SM_TYPE, SM_TYPE
from gui.app_loader import g_appLoader
from gui.app_loader.settings import GUI_GLOBAL_SPACE_ID as _SPACE_ID
from gui.customization.shared import chooseMode
from gui.shared import EVENT_BUS_SCOPE, events, g_eventBus
from gui.shared.formatters import formatPrice, getItemPricesVO, icons, text_styles
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.gui_items.gui_item_economics import ITEM_PRICE_EMPTY, ItemPrice
from gui.shared.utils import toUpper
from gui.shared.utils.HangarSpace import g_hangarSpace
from gui.shared.utils.decorators import process
from gui.shared.utils.functions import makeTooltip
from hangar_camera_common import CameraRelatedEvents
from helpers import dependency, int2roman
from helpers.i18n import makeString as _ms
from items.components.c11n_constants import SeasonType
from skeletons.account_helpers.settings_core import ISettingsCore
from skeletons.gui.customization import ICustomizationService
from skeletons.gui.lobby_context import ILobbyContext
from skeletons.gui.shared import IItemsCache
from vehicle_systems.tankStructure import TankPartIndexes
from . import g_config
from .carousel import CustomizationCarouselDataProvider, comparisonKey
from .shared import C11nMode, C11nTabs, RandMode, TeamMode


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
        self._tabIndex = C11nTabs.SHOP
        self._lastTab = C11nTabs.SHOP
        self._originalOutfits = {}
        self._modifiedOutfits = {}
        self._currentOutfit = None
        self._setupOutfit = None
        self._mode = C11nMode.INSTALL
        self._currentSettings = {'custom': {}, 'remap': {}}
        self._randMode = RandMode.RANDOM
        self._ally = True
        self._enemy = True
        self._settingSeason = SeasonType.UNDEFINED
        self._isDeferredRenderer = True
        self.__anchorPositionCallbackID = None
        self._state = {}
        self._needFullRebuild = False
        self.__locatedOnEmblem = False
        self.itemIsPicked = False
        self._vehicleCustomizationAnchorsUpdater = None

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
        g_eventBus.addListener(CameraRelatedEvents.IDLE_CAMERA, self.__onNotifyHangarCameraIdleStateChanged)
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
        self._vehicleCustomizationAnchorsUpdater = _VehicleCustomizationAnchorsUpdater(self.service)
        self._vehicleCustomizationAnchorsUpdater.startUpdater()
        self.refreshOutfit()
        self.settingsCore.onSettingsChanged += self.__onSettingsChanged
        self.__updateCameraParallaxFlag()
        self.service.startHighlighter(chooseMode(GUI_ITEM_TYPE.CAMOUFLAGE, g_currentVehicle.item))

    def _dispose(self):
        if g_appLoader.getSpaceID() != _SPACE_ID.LOGIN:
            self.__releaseItemSound()
            self.soundManager.playInstantSound(SOUNDS.EXIT)
        self.settingsCore.onSettingsChanged -= self.__onSettingsChanged
        self._vehicleCustomizationAnchorsUpdater.stopUpdater()
        self._vehicleCustomizationAnchorsUpdater = None
        if self.__locatedOnEmblem and g_hangarSpace.spaceInited:
            space = g_hangarSpace.space
            space.clearSelectedEmblemInfo()
            space.locateCameraToPreview()
        self.__viewLifecycleWatcher.stop()
        self.service.stopHighlighter()
        self.lobbyContext.deleteHeaderNavigationConfirmator(self.__confirmHeaderNavigation)
        self.lobbyContext.getServerSettings().onServerSettingsChange -= self.__onServerSettingChanged
        self.service.onCarouselFilter -= self.__onCarouselFilter
        self.service.onRemoveItems -= self.removeItems
        self.service.onOutfitChanged -= self.__onOutfitChanged
        g_eventBus.removeListener(CameraRelatedEvents.IDLE_CAMERA, self.__onNotifyHangarCameraIdleStateChanged)
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
                'tabsAvailableRegions': C11nTabs.AVAILABLE_REGIONS,
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
        return {'leftLabel': g_config.i18n['UI_flash_switcher_%s' % C11nMode.NAMES[self._mode]],
                'rightLabel': g_config.i18n['UI_flash_switcher_%s' % C11nMode.NAMES[not self._mode]],
                'leftEvent': 'installStyle%s' % ('s' if self._mode else ''),
                'rightEvent': 'installStyle%s' % ('s' if not self._mode else ''),
                'isLeft': True}

    def __setBuyingPanelData(self, *_):
        purchaseItems = self.getPurchaseItems()
        cart = getTotalPurchaseInfo(purchaseItems)
        totalPriceVO = getItemPricesVO(cart.totalPrice)
        cleanSettings = self._cleanSettings(self._currentSettings, checkSeasons=False)
        keys = []
        if cart.numTotal:
            keys.append('install')
        if cart.totalPrice != ITEM_PRICE_EMPTY:
            self.as_showBuyingPanelS()
        else:
            self.as_hideBuyingPanelS()
        if any(cleanSettings.itervalues()) or not keys:
            keys.append('apply')
        label = g_config.i18n['UI_flash_commit_' + '_and_'.join(keys)]
        isApplyEnabled = bool(cart.numTotal) or any(cleanSettings.itervalues())
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
        self.__releaseItemSound()
        self.soundManager.playInstantSound(SOUNDS.SELECT)
        purchaseItems = self.getPurchaseItems()
        self.buyAndExit(purchaseItems)

    def onSelectItem(self, index):
        self._carouselDP.selectItemIdx(index)
        self.soundManager.playInstantSound(SOUNDS.SELECT)

    def onPickItem(self):
        if self._mode == C11nMode.SETUP:
            self.__onRegionHighlighted(GUI_ITEM_TYPE.CAMOUFLAGE, 1, 0, True, False)
        elif not self.itemIsPicked:
            self.soundManager.playInstantSound(SOUNDS.PICK)
            self.itemIsPicked = True

    def onReleaseItem(self):
        self.__releaseItemSound()

    def changeSeason(self, seasonIdx):
        self._currentSeason = SEASON_IDX_TO_TYPE[seasonIdx]
        seasonName = SEASON_TYPE_TO_NAME.get(self._currentSeason)
        self.soundManager.playInstantSound(SOUNDS.SEASON_SELECT.format(seasonName))
        self.refreshOutfit()
        self.refreshCarousel(rebuild=True)
        self.as_refreshAnchorPropertySheetS()
        self.__setAnchorsInitData(self._tabIndex, True, True)

    def changeCamoTeamMode(self, idx):
        self._ally = bool(idx & TeamMode.ALLY)
        self._enemy = bool(idx & TeamMode.ENEMY)
        self._updateCurrentSettings()
        self.__setBuyingPanelData()

    def changeCamoRandMode(self, idx):
        self._randMode = idx
        self._updateCurrentSettings()
        self.__setBuyingPanelData()

    def _updateCurrentSettings(self):
        item = self._currentOutfit.getContainer(1).slotFor(GUI_ITEM_TYPE.CAMOUFLAGE).getItem(0)
        itemName, itemKey = (item.descriptor.userKey, 'custom') if item.priceGroup == 'custom' else (item.id, 'remap')
        settings = self._currentSettings[itemKey].setdefault(itemName, {})
        settings['useForAlly'] = self._ally
        settings['useForEnemy'] = self._enemy
        settings['random_mode'] = self._randMode

    def _cleanSettings(self, allSettings, checkSeasons=True):
        camouflages = items.vehicles.g_cache.customization20().camouflages
        for itemsKey in allSettings:
            itemSettings = allSettings[itemsKey]
            for camoID in itemSettings.keys():
                origSetting = g_config.camouflages[itemsKey].get(camoID, {})
                camoSetting = itemSettings[camoID]
                if 'season' in camoSetting:
                    if checkSeasons and itemsKey == 'remap' and not self.itemsCache.items.getItemByCD(
                            camouflages[camoID].compactDescr).isHidden:
                        print '%s: in-shop camouflage season changing is disabled (id: %s, season setting was %s)' % (
                            g_config.ID, camoID, camoSetting['season'] or 'empty')
                        del camoSetting['season']
                        if 'season' in origSetting:
                            del origSetting['season']
                    elif 'season' not in origSetting:
                        itemSeasons = SeasonType.UNDEFINED
                        for season in SEASONS_CONSTANTS.SEASONS:
                            if season in camoSetting['season']:
                                itemSeasons |= getattr(SeasonType, season.upper())
                        camoSeason = camouflages[camoID].season
                        if itemSeasons == (camoSeason if camoSeason < 8 else camoSeason - 8):
                            del camoSetting['season']
                    elif origSetting['season'] == camoSetting['season']:
                        del camoSetting['season']
                for team in ('useForAlly', 'useForEnemy'):
                    if team in camoSetting:
                        if origSetting.get(team, True) == camoSetting[team]:
                            del camoSetting[team]
                if 'random_mode' in camoSetting:
                    if camoSetting['random_mode'] == origSetting.get('random_mode', RandMode.RANDOM):
                        del camoSetting['random_mode']
                if not camoSetting:
                    del itemSettings[camoID]
        return allSettings

    def refreshCarousel(self, rebuild=False):
        if rebuild:
            self._carouselDP.buildList(self._tabIndex, self._currentSeason, refresh=False)
            self.as_setCarouselDataS(self._buildCustomizationCarouselDataVO())
        self._carouselDP.refresh()

    def refreshHotFilters(self):
        self.as_setCarouselFiltersDataS(
            {'hotFilters': [self._carouselDP.getOwnedFilter(), self._carouselDP.getAppliedFilter()]})

    def refreshOutfit(self):
        if self._mode == C11nMode.INSTALL:
            self._currentOutfit = self._modifiedOutfits[self._currentSeason]
        else:
            self._currentOutfit = self._setupOutfit
        self.service.tryOnOutfit(self._currentOutfit)
        g_tankActiveCamouflage[g_currentVehicle.item.intCD] = self._currentSeason

    def showGroupFromTab(self, tabIndex):
        self.soundManager.playInstantSound(SOUNDS.TAB_SWITCH)
        self._tabIndex = tabIndex
        self.__setAnchorsInitData(self._tabIndex, True)
        self.__updateAnchorPositions()
        self.refreshCarousel(rebuild=True)
        if self._mode == C11nMode.SETUP:
            self.__onRegionHighlighted(GUI_ITEM_TYPE.CAMOUFLAGE, 1, 0, True, False)

    def installCustomizationElement(self, intCD, areaId, slotId, regionId, seasonIdx):
        if self.itemIsPicked:
            self.soundManager.playInstantSound(SOUNDS.APPLY)
        item = self.itemsCache.items.getItemByCD(intCD)
        if self._mode == C11nMode.INSTALL:
            season = SEASON_IDX_TO_TYPE.get(seasonIdx, self._currentSeason)
            outfit = self._modifiedOutfits[season]
            outfit.getContainer(areaId).slotFor(slotId).set(item, idx=regionId)
        else:
            outfit = self._setupOutfit
            for areaId in xrange(1, 4):
                outfit.getContainer(areaId).slotFor(slotId).set(item, idx=regionId)
            itemName, itemKey = (item.descriptor.userKey, 'custom') if item.priceGroup == 'custom' else (item.id, 'remap')
            itemSettings = self._currentSettings[itemKey].setdefault(itemName, {})
            itemOrigSettings = g_config.camouflages[itemKey].get(itemName, {})
            itemSeasonsStr = itemSettings.get('season', itemOrigSettings.get('season', None))
            if itemSeasonsStr is not None:
                itemSeasons = SeasonType.UNDEFINED
                for season in SEASONS_CONSTANTS.SEASONS:
                    if season in itemSeasonsStr:
                        itemSeasons |= getattr(SeasonType, season.upper())
            else:
                itemSeasons = item.season
                itemSeasonsStr = itemSettings['season'] = ','.join(
                    x for x in SEASONS_CONSTANTS.SEASONS if getattr(SeasonType, x.upper()) & itemSeasons)
            if seasonIdx not in SEASON_IDX_TO_TYPE:  # item is selected from carousel, not changed from property sheet
                self._settingSeason = itemSeasons
                self._randMode = itemSettings.get('random_mode', itemOrigSettings.get('random_mode', RandMode.RANDOM))
                self._ally = itemSettings.get('useForAlly', itemOrigSettings.get('useForAlly', True))
                self._enemy = itemSettings.get('useForEnemy', itemOrigSettings.get('useForEnemy', True))
            else:
                self._settingSeason |= SEASON_IDX_TO_TYPE[seasonIdx]
                newSeasons = set(x for x in SEASONS_CONSTANTS.SEASONS if x in itemSeasonsStr)
                newSeasons.add(SEASON_TYPE_TO_NAME[SEASON_IDX_TO_TYPE[seasonIdx]])
                itemSettings['season'] = ','.join(x for x in SEASONS_CONSTANTS.SEASONS if x in newSeasons)
        outfit.invalidate()
        self.refreshOutfit()
        self.__setBuyingPanelData()
        self.__setHeaderInitData()
        self.refreshCarousel(rebuild=self._carouselDP.getAppliedFilter() or self._carouselDP.getOwnedFilter())

    def clearCustomizationItem(self, areaId, slotId, regionId, seasonIdx):
        self.soundManager.playInstantSound(SOUNDS.REMOVE)
        if self._mode == C11nMode.INSTALL:
            season = SEASON_IDX_TO_TYPE.get(seasonIdx, self._currentSeason)
            outfit = self._modifiedOutfits[season]
            outfit.getContainer(areaId).slotFor(slotId).remove(idx=regionId)
        else:
            item = self._setupOutfit.getContainer(areaId).slotFor(slotId).getItem(regionId)
            itemName, itemKey = (item.descriptor.userKey, 'custom') if item.priceGroup == 'custom' else (item.id, 'remap')
            itemSettings = self._currentSettings[itemKey].setdefault(itemName, {})
            itemOrigSettings = g_config.camouflages[itemKey].get(itemName, {})
            itemSeasonsStr = itemSettings.get('season', itemOrigSettings.get('season', None))
            if seasonIdx not in SEASON_IDX_TO_TYPE:
                print 'WARNING', seasonIdx
            else:
                newSeasons = set()
                if itemSeasonsStr is not None:
                    [newSeasons.add(x) for x in SEASONS_CONSTANTS.SEASONS if x in itemSeasonsStr]
                newSeasons.discard(SEASON_TYPE_TO_NAME[SEASON_IDX_TO_TYPE[seasonIdx]])
                itemSettings['season'] = ','.join(x for x in SEASONS_CONSTANTS.SEASONS if x in newSeasons)
                self._settingSeason = SeasonType.UNDEFINED
                for season in newSeasons:
                    self._settingSeason |= getattr(SeasonType, season.upper())
        self.refreshOutfit()
        self.__setAnchorsInitData(self._tabIndex, True, True)
        self.__setBuyingPanelData()
        self.__setHeaderInitData()
        self.refreshCarousel(rebuild=self._carouselDP.getAppliedFilter() or self._carouselDP.getOwnedFilter())

    def switchToCustom(self, updateUI=True):
        self.service.startHighlighter(chooseMode(GUI_ITEM_TYPE.CAMOUFLAGE, g_currentVehicle.item))
        self.switchMode(C11nMode.INSTALL)

    def switchToStyle(self):
        self.switchMode(C11nMode.SETUP)
        self.service.stopHighlighter()
        self.__onRegionHighlighted(GUI_ITEM_TYPE.CAMOUFLAGE, 1, 0, True, False)

    def switchMode(self, mode):
        self.soundManager.playInstantSound(SOUNDS.TAB_SWITCH)
        self._mode = mode
        self.refreshOutfit()
        self.__setFooterInitData()
        self._carouselDP.selectItem()
        self.__setBuyingPanelData()
        self.__setHeaderInitData()

    def fadeOutAnchors(self, isFadeOut):
        self.fadeAnchorsOut = isFadeOut

    def closeWindow(self):
        purchaseItems = self.getPurchaseItems()
        cart = getTotalPurchaseInfo(purchaseItems)
        if cart.numTotal or any(self._cleanSettings(self._currentSettings).itervalues()):
            DialogsInterface.showDialog(I18nConfirmDialogMeta('customization/close'), self.__onConfirmCloseWindow)
        else:
            self.__onConfirmCloseWindow(proceed=True)

    def itemContextMenuDisplayed(self):
        cmHandler = self.app.contextMenuManager.getCurrentHandler()
        if isinstance(cmHandler, CustomizationItemCMHandler):
            cmHandler.onSelected += self._itemCtxMenuSelected

    def resetFilter(self):
        self.clearFilter()
        self.refreshFilterData()
        self.refreshHotFilters()
        self.refreshCarousel(rebuild=True)

    def clearFilter(self):
        self._carouselDP.clearFilter()

    def refreshFilterData(self):
        self.as_setFilterDataS(self._carouselDP.getFilterData())

    def getHistoricalPopoverData(self):
        self.soundManager.playInstantSound(SOUNDS.SELECT)
        nonHistoricItems = []
        for outfit in self._modifiedOutfits.itervalues():
            nonHistoricItems.extend((item for item in outfit.items() if not item.isHistorical()))

        return {'items': [item.intCD for item in sorted(nonHistoricItems, key=comparisonKey)]}

    def removeItems(self, *intCDs):
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
        self.__setAnchorsInitData(self._tabIndex, True, True)
        self.as_refreshAnchorPropertySheetS()
        self.refreshCarousel(rebuild=self._carouselDP.getAppliedFilter() or self._carouselDP.getOwnedFilter())

    def updatePropertySheetButtons(self, areaId, slotId, regionId):
        self.service.onPropertySheetShow(areaId, slotId, regionId)

    def onLobbyClick(self):
        pass

    # noinspection SpellCheckingInspection
    def setEnableMultiselectRegions(self, isEnabled):
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
        return self._currentOutfit

    def getModifiedOutfit(self, season):
        return self._modifiedOutfits.get(season)

    def getMode(self):
        return self._mode

    def getCurrentSeason(self):
        return self._currentSeason

    def getCurrentTab(self):
        return self._tabIndex

    def getRandMode(self):
        return self._randMode

    def getIsAlly(self):
        return self._ally

    def getIsEnemy(self):
        return self._enemy

    def getTeamMode(self):
        return 0 | (self._ally and TeamMode.ALLY) | (self._enemy and TeamMode.ENEMY)

    def getSettingSeason(self):
        return self._settingSeason

    def getAppliedItems(self, isOriginal=True):
        outfits = self._originalOutfits if isOriginal else self._modifiedOutfits
        seasons = SeasonType.COMMON_SEASONS if isOriginal else (self._currentSeason,)
        appliedItems = set()
        for seasonType in seasons:
            outfit = outfits[seasonType]
            appliedItems.update((i.intCD for i in outfit.items()))
        return appliedItems

    def isItemInOutfit(self, item):
        return any((outfit.has(item) for outfit in self._originalOutfits.itervalues())) or any(
            (outfit.has(item) for outfit in self._modifiedOutfits.itervalues()))

    def buyAndExit(self, purchaseItems):
        self._currentSettings = self._cleanSettings(self._currentSettings)
        for itemsKey in self._currentSettings:
            for camoName in self._currentSettings[itemsKey]:
                g_config.camouflages[itemsKey].setdefault(camoName, {}).update(self._currentSettings[itemsKey][camoName])
        if self._currentSettings['remap']:
            newSettings = {'disable': g_config.disable,
                           'remap': g_config.camouflages['remap']}
            loadJson(g_config.ID, 'settings', newSettings, g_config.configPath, True)
        if self._currentSettings['custom']:
            for confFolderName in g_config.configFolders:
                configFolder = g_config.configFolders[confFolderName]
                loadJson(g_config.ID, 'settings', {key: g_config.camouflages['custom'][key] for key in configFolder},
                         g_config.configPath + 'camouflages/' + confFolderName + '/', True, False)
        if any(self._currentSettings.itervalues()):
            from ..processors import collectCamouflageData
            collectCamouflageData()
        self.itemsCache.onSyncCompleted -= self.__onCacheReSync
        boughtOutfits = {season: self.service.getCustomOutfit(season) for season in SeasonType.COMMON_SEASONS}
        cart = getTotalPurchaseInfo(purchaseItems)
        nationName, vehicleName = g_currentVehicle.item.descriptor.name.split(':')
        vehConfig = g_config.camouflagesCache.get(nationName, {}).get(vehicleName, {})
        for pItem in purchaseItems:
            assert pItem.slot == GUI_ITEM_TYPE.CAMOUFLAGE
            if pItem.selected:
                boughtSlot = boughtOutfits[pItem.group].getContainer(pItem.areaID).slotFor(pItem.slot)
                component = self._modifiedOutfits[pItem.group].getContainer(pItem.areaID).slotFor(pItem.slot).getComponent(
                    pItem.regionID)
                bComponent = boughtSlot.getComponent(pItem.regionID)
                seasonName = SEASON_TYPE_TO_NAME[pItem.group]
                if pItem.item == boughtSlot.getItem(pItem.regionID) and \
                        component.palette == bComponent.palette and component.patternSize == bComponent.patternSize and \
                        not pItem.isDismantling:
                    vehConfig.get(seasonName, {}).pop(TankPartIndexes.getName(pItem.areaID), [])
                else:
                    g_config.camouflagesCache.setdefault(nationName, {}).setdefault(vehicleName, {}).setdefault(
                        seasonName, {})[TankPartIndexes.getName(pItem.areaID)] = (
                        [pItem.item.id, component.palette, component.patternSize] if not pItem.isDismantling else [])
                g_config.hangarCamoCache.get(nationName, {}).get(vehicleName, {}).get(seasonName, {}).pop(
                    TankPartIndexes.getName(pItem.areaID), {})
        for nationName in g_config.camouflagesCache.keys():
            for vehicleName in g_config.camouflagesCache[nationName].keys():
                for season in g_config.camouflagesCache[nationName][vehicleName].keys():
                    if not g_config.camouflagesCache[nationName][vehicleName][season]:
                        del g_config.camouflagesCache[nationName][vehicleName][season]
                if not g_config.camouflagesCache[nationName][vehicleName]:
                    del g_config.camouflagesCache[nationName][vehicleName]
            if not g_config.camouflagesCache[nationName]:
                del g_config.camouflagesCache[nationName]
        loadJson(g_config.ID, 'camouflagesCache', g_config.camouflagesCache, g_config.configPath, True)
        if cart.totalPrice != ITEM_PRICE_EMPTY:
            msgCtx = {'money': formatPrice(cart.totalPrice.price),
                      'count': cart.numSelected}
            SystemMessages.pushMessage(g_config.i18n['UI_flashCol_applied_money'] % msgCtx,
                                       type=CURRENCY_TO_SM_TYPE.get(cart.totalPrice.getCurrency(byWeight=True),
                                                                    SM_TYPE.PurchaseForGold))
        else:
            SystemMessages.pushI18nMessage(MESSENGER.SERVICECHANNELMESSAGES_SYSMSG_CONVERTER_CUSTOMIZATIONS,
                                           type=SM_TYPE.Information)
        self.__onCacheReSync()
        self.itemsCache.onSyncCompleted += self.__onCacheReSync

    # noinspection PyUnusedLocal
    @process('sellItem')
    def sellItem(self, intCD, shouldSell):
        assert False

    def onAnchorsShown(self, anchors):
        if self._vehicleCustomizationAnchorsUpdater is not None:
            self._vehicleCustomizationAnchorsUpdater.setAnchors(anchors, True)

    def _itemCtxMenuSelected(self, ctxMenuID, itemIntCD):
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
        for zIdx, posData in enumerate(anchorPosData):
            anchorVOs.append(CustomizationAnchorPositionVO(zIdx, posData.slotId._asdict())._asdict())
        return CustomizationAnchorsSetVO(anchorVOs)._asdict()

    def _buildCustomizationCarouselDataVO(self):
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
        from ..processors import applyCache
        self._setupOutfit = self.service.getEmptyOutfit()
        descriptor = g_currentVehicle.item.descriptor
        nationName, vehName = descriptor.name.split(':')
        for season in SeasonType.COMMON_SEASONS:
            outfit = self.service.getCustomOutfit(season).copy()
            seasonName = SEASON_TYPE_TO_NAME[season]
            applyCache(outfit, vehName, g_config.camouflagesCache.get(nationName, {}).get(vehName, {}).get(seasonName, {}))
            self._originalOutfits[season] = outfit.copy()
            applyCache(outfit, vehName, g_config.hangarCamoCache.get(nationName, {}).get(vehName, {}).get(seasonName, {}))
            self._modifiedOutfits[season] = outfit.copy()
        if self._mode == C11nMode.INSTALL:
            self._currentOutfit = self._modifiedOutfits[self._currentSeason]
        else:
            self._currentOutfit = self._setupOutfit

    def __updateAnchorPositions(self, _=None):
        self.as_setAnchorPositionsS(self._getUpdatedAnchorPositions())

    def __onRegionHighlighted(self, typeID, tankPartID, regionID, selected, hovered):
        slotId = None
        if hovered:
            self.soundManager.playInstantSound(SOUNDS.HOVER)
            return
        if tankPartID != -1 and regionID != -1:
            slotId = CustomizationSlotIdVO(tankPartID if self._mode == C11nMode.INSTALL else 1, typeID,
                                           regionID)._asdict()
            if selected:
                self.soundManager.playInstantSound(SOUNDS.CHOOSE)
        if self._mode == C11nMode.INSTALL or slotId is not None:
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
        self.refreshCarousel(rebuild=self._needFullRebuild)
        self.refreshOutfit()
        self.as_refreshAnchorPropertySheetS()
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

        def customizationSlotIdToUid(customizationSlotIdVO):
            s = struct.pack('bbh', customizationSlotIdVO.areaId, customizationSlotIdVO.slotId, customizationSlotIdVO.regionId)
            return struct.unpack('I', s)[0]

        anchorVOs = []
        cType = GUI_ITEM_TYPE.CAMOUFLAGE
        for container in self._currentOutfit.containers():
            for slot in (x for x in container.slots() if x.getType() == cType):
                for regionId, region in enumerate(slot.getRegions()):
                    slotId = CustomizationSlotIdVO(container.getAreaID(), slot.getType(), regionId)
                    popoverAlias = CUSTOMIZATION_ALIASES.CUSTOMIZATION_CAMO_POPOVER
                    item = slot.getItem(regionId)
                    itemIntCD = item.intCD if item is not None else 0
                    uid = customizationSlotIdToUid(slotId)
                    if self.__getAnchorPositionData(slotId, region) is not None:
                        anchorVOs.append(CustomizationSlotUpdateVO(slotId._asdict(), popoverAlias, itemIntCD, uid)._asdict())

        if update:
            self.as_updateAnchorDataS(CustomizationAnchorInitVO(anchorVOs, doRegions)._asdict())
        else:
            self.as_setAnchorInitS(CustomizationAnchorInitVO(anchorVOs, doRegions)._asdict())

    def onSelectHotFilter(self, index, value):
        (self._carouselDP.setOwnedFilter, self._carouselDP.setAppliedFilter)[index](value)
        self.refreshCarousel(rebuild=True)

    def __getHistoricIndicatorData(self):
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
        data = []
        for tabIdx in self.__getVisibleTabs():
            data.append({'label': g_config.i18n['UI_flash_tabs_%s_label' % tabIdx],
                         'tooltip': makeTooltip(g_config.i18n['UI_flashCol_tabs_%s_text' % tabIdx],
                                                g_config.i18n['UI_flashCol_tabs_%s_tooltip' % tabIdx]),
                         'id': tabIdx})

        return data

    def __getVisibleTabs(self):
        visibleTabs = []
        for tabIdx in C11nTabs.VISIBLE:
            data = self._carouselDP.getSeasonAndTabData(tabIdx, self._currentSeason)
            if not data.itemCount:
                continue
            visibleTabs.append(tabIdx)

        return visibleTabs

    def __onNotifyHangarCameraIdleStateChanged(self, event):
        isIdle = event.ctx.get('started', False)
        self.as_cameraAutoRotateChangedS(isIdle)

    @async
    @adisp_process
    def __confirmHeaderNavigation(self, callback):
        purchaseItems = self.getPurchaseItems()
        cart = getTotalPurchaseInfo(purchaseItems)
        if cart.numTotal:
            result = yield DialogsInterface.showI18nConfirmDialog('customization/close')
        else:
            result = True
        callback(result)
        self.__onConfirmCloseWindow(result)

    def __releaseItemSound(self):
        if self.itemIsPicked:
            self.soundManager.playInstantSound(SOUNDS.RELEASE)
            self.itemIsPicked = False

    def __onSettingsChanged(self, diff):
        if GAME.HANGAR_CAM_PARALLAX_ENABLED in diff:
            self.__updateCameraParallaxFlag()

    def __updateCameraParallaxFlag(self):
        parallaxEnabled = bool(self.settingsCore.getSetting(GAME.HANGAR_CAM_PARALLAX_ENABLED))
        self.as_setParallaxFlagS(parallaxEnabled)
