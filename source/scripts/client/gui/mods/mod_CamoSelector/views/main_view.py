from gui.shared.utils.decorators import process
from gui.Scaleform.daapi.view.lobby.customization.main_view import MainView


class CamoSelectorMainView(MainView):
    def showBuyWindow(self):
        print 'showBuyWindow'
        result = super(CamoSelectorMainView, self).showBuyWindow()
        print result
        return result

    def onSelectItem(self, index):
        print 'onSelectItem', index
        result = super(CamoSelectorMainView, self).onSelectItem(index)
        print result
        return result

    def onPickItem(self):
        print 'onPickItem'
        result = super(CamoSelectorMainView, self).onPickItem()
        print result
        return result

    def onReleaseItem(self):
        print 'onReleaseItem'
        result = super(CamoSelectorMainView, self).onReleaseItem()
        print result
        return result

    def changeSeason(self, seasonIdx):
        print 'changeSeason', seasonIdx
        result = super(CamoSelectorMainView, self).changeSeason(seasonIdx)
        print result
        return result

    def refreshCarousel(self, rebuild=False):
        print 'refreshCarousel', rebuild
        result = super(CamoSelectorMainView, self).refreshCarousel(rebuild)
        print result
        return result

    def refreshOutfit(self):
        print 'refreshOutfit'
        result = super(CamoSelectorMainView, self).refreshOutfit()
        print result
        return result

    def showGroupFromTab(self, tabIndex):
        print 'showGroupFromTab', tabIndex
        result = super(CamoSelectorMainView, self).showGroupFromTab(tabIndex)
        print result
        return result

    def installCustomizationElement(self, intCD, areaId, slotId, regionId, seasonIdx):
        print 'installCustomizationElement', intCD, areaId, slotId, regionId, seasonIdx
        result = super(CamoSelectorMainView, self).installCustomizationElement(intCD, areaId, slotId, regionId, seasonIdx)
        print result
        return result

    def clearCustomizationItem(self, areaId, slotId, regionId, seasonIdx):
        print 'clearCustomizationItem', areaId, slotId, regionId, seasonIdx
        result = super(CamoSelectorMainView, self).clearCustomizationItem(areaId, slotId, regionId, seasonIdx)
        print result
        return result

    def switchToCustom(self, updateUI=True):
        print 'switchToCustom', updateUI
        result = super(CamoSelectorMainView, self).switchToCustom(updateUI)
        print result
        return result

    def switchToStyle(self):
        print 'switchToStyle'
        result = super(CamoSelectorMainView, self).switchToStyle()
        print result
        return result

    def fadeOutAnchors(self, isFadeOut):
        print 'fadeOutAnchors', isFadeOut
        result = super(CamoSelectorMainView, self).fadeOutAnchors(isFadeOut)
        print result
        return result

    def closeWindow(self):
        print 'closeWindow'
        result = super(CamoSelectorMainView, self).closeWindow()
        print result
        return result

    def itemContextMenuDisplayed(self):
        print 'itemContextMenuDisplayed'
        result = super(CamoSelectorMainView, self).itemContextMenuDisplayed()
        print result
        return result

    def resetFilter(self):
        print 'resetFilter'
        result = super(CamoSelectorMainView, self).resetFilter()
        print result
        return result

    def clearFilter(self):
        print 'clearFilter'
        result = super(CamoSelectorMainView, self).clearFilter()
        print result
        return result

    def refreshFilterData(self):
        print 'refreshFilterData'
        result = super(CamoSelectorMainView, self).refreshFilterData()
        print result
        return result

    def getHistoricalPopoverData(self):
        print 'getHistoricalPopoverData'
        result = super(CamoSelectorMainView, self).getHistoricalPopoverData()
        print result
        return result

    def removeItems(self, *intCDs):
        print 'removeItems', intCDs
        result = super(CamoSelectorMainView, self).removeItems(*intCDs)
        print result
        return result

    def updatePropertySheetButtons(self, areaId, slotId, regionId):
        print 'updatePropertySheetButtons', areaId, slotId, regionId
        result = super(CamoSelectorMainView, self).updatePropertySheetButtons(areaId, slotId, regionId)
        print result
        return result

    def onLobbyClick(self):
        print 'onLobbyClick'
        result = super(CamoSelectorMainView, self).onLobbyClick()
        print result
        return result

    def setEnableMultiselectRegions(self, isEnabled):
        print 'setEnableMultiselectRegions', isEnabled
        result = super(CamoSelectorMainView, self).setEnableMultiselectRegions(isEnabled)
        print result
        return result

    def onChangeSize(self):
        print 'onChangeSize'
        result = super(CamoSelectorMainView, self).onChangeSize()
        print result
        return result

    def onSelectAnchor(self, areaID, regionID):
        print 'onSelectAnchor', areaID, regionID
        result = super(CamoSelectorMainView, self).onSelectAnchor(areaID, regionID)
        print result
        return result

    def getOutfitsInfo(self):
        print 'getOutfitsInfo'
        result = super(CamoSelectorMainView, self).getOutfitsInfo()
        print result
        return result

    def getStyleInfo(self):
        print 'getStyleInfo'
        result = super(CamoSelectorMainView, self).getStyleInfo()
        print result
        return result

    def getPurchaseItems(self):
        print 'getPurchaseItems'
        result = super(CamoSelectorMainView, self).getPurchaseItems()
        print result
        return result

    def getItemInventoryCount(self, item):
        print 'getInventoryCount', item
        result = super(CamoSelectorMainView, self).getItemInventoryCount(item)
        print result
        return result

    def getCurrentOutfit(self):
        print 'getCurrentOutfit'
        result = super(CamoSelectorMainView, self).getCurrentOutfit()
        print result
        return result

    def getModifiedStyle(self):
        print 'getModifiedStyle'
        result = super(CamoSelectorMainView, self).getModifiedStyle()
        print result
        return result

    def getModifiedOutfit(self, season):
        print 'getModifiedOutfit', season
        result = super(CamoSelectorMainView, self).getModifiedOutfit(season)
        print result
        return result

    def getMode(self):
        print 'getMode'
        result = super(CamoSelectorMainView, self).getMode()
        print result
        return result

    def getCurrentSeason(self):
        print 'getCurrentSeason'
        result = super(CamoSelectorMainView, self).getCurrentSeason()
        print result
        return result

    def getCurrentTab(self):
        print 'getCurrentTab'
        result = super(CamoSelectorMainView, self).getCurrentTab()
        print result
        return result

    def getAppliedItems(self):
        print 'getAppliedItems'
        result = super(CamoSelectorMainView, self).getAppliedItems()
        print result
        return result

    def isItemInOutfit(self, item):
        print 'isItemInOutfit', item
        result = super(CamoSelectorMainView, self).isItemInOutfit(item)
        print result
        return result

    @process('buyAndInstall')
    def buyAndExit(self, purchaseItems):
        print 'buyAndExit', purchaseItems
        result = super(CamoSelectorMainView, self).buyAndExit(purchaseItems)
        print result
        return result

    @process('sellItem')
    def sellItem(self, intCD, shouldSell):
        print 'sellItem', intCD, shouldSell
        result = super(CamoSelectorMainView, self).sellItem(intCD, shouldSell)
        print result
        return result

    def _populate(self):
        print '_populate'
        result = super(CamoSelectorMainView, self)._populate()
        print result
        return result

    def _dispose(self):
        print '_dispose'
        result = super(CamoSelectorMainView, self)._dispose()
        print result
        return result

    def _itemCtxMenuSelected(self, ctxMenuID, itemIntCD):
        print '_itemCtxMenuSelected', ctxMenuID, itemIntCD
        result = super(CamoSelectorMainView, self)._itemCtxMenuSelected(ctxMenuID, itemIntCD)
        print result
        return result

    def _getUpdatedAnchorPositions(self):
        print '_getUpdatedAnchorPositions'
        result = super(CamoSelectorMainView, self)._getUpdatedAnchorPositions()
        print result
        return result

    def _buildCustomizationCarouselDataVO(self):
        print '_buildCustomizationCarouselDataVO'
        result = super(CamoSelectorMainView, self)._buildCustomizationCarouselDataVO()
        print result
        return result

    def _carouseItemWrapper(self, itemCD):
        print '_carouselItemWrapper', itemCD
        result = super(CamoSelectorMainView, self)._carouseItemWrapper(itemCD)
        print result
        return result
