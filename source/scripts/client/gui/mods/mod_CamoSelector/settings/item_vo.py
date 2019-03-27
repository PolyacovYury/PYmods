from gui.Scaleform.daapi.view.lobby.customization.customization_item_vo import CustomizationCarouselRendererVO
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION
from gui.shared.formatters import text_styles
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.gui_items.gui_item_economics import ITEM_PRICE_EMPTY
from helpers.i18n import makeString as _ms


def buildCustomizationItemDataVO(
        isBuy, item, count, plainView=False, showDetailItems=True, forceLocked=False, showUnsupportedAlert=False,
        isCurrentlyApplied=False, addExtraName=True, isAlreadyUsed=False, isDarked=False, noPrice=False,
        autoRentEnabled=False, customIcon=None, vehicle=None):
    isSpecial = item.isVehicleBound and (item.buyCount > 0 or item.inventoryCount > 0) or item.isLimited and item.buyCount > 0
    hasBonus = item.bonus is not None and not plainView
    locked = (not item.isUnlocked or forceLocked) and not plainView
    buyPrice = ITEM_PRICE_EMPTY if isBuy and (plainView or item.isHidden or noPrice) else item.getBuyPrice()
    if buyPrice == ITEM_PRICE_EMPTY and count <= 0:
        count = 1
    isNonHistoric = not item.isHistorical()
    if addExtraName and item.itemTypeID in (GUI_ITEM_TYPE.MODIFICATION, GUI_ITEM_TYPE.STYLE):
        extraNames = (text_styles.bonusLocalText(item.userName), text_styles.highTitle(item.userName))
    else:
        extraNames = None
    imageCached = item.itemTypeID is not GUI_ITEM_TYPE.PROJECTION_DECAL
    rentalInfoText = ''
    if item.isRentable and count <= 0:
        rentalInfoText = text_styles.main(_ms(VEHICLE_CUSTOMIZATION.CAROUSEL_RENTALBATTLES, battlesNum=item.rentCount))
    icon = customIcon if customIcon else item.icon
    noveltyCounter = 0 if not vehicle else item.getNoveltyCounter(vehicle)
    return CustomizationCarouselRendererVO(
        item.intCD, item.itemTypeID, item.isWide(), icon, hasBonus, locked, buyPrice, count, item.isRentable,
        showDetailItems, isNonHistoric, isSpecial, isDarked, isAlreadyUsed, showUnsupportedAlert, extraNames=extraNames,
        showRareIcon=item.isRare(), isEquipped=isCurrentlyApplied, rentalInfoText=rentalInfoText, imageCached=imageCached,
        autoRentEnabled=autoRentEnabled, isAllSeasons=item.isAllSeason(), noveltyCounter=noveltyCounter).asDict()
