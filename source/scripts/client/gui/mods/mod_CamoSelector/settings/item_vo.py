from gui.shared.formatters import getItemPricesVO
from gui.shared.gui_items.gui_item_economics import ITEM_PRICE_EMPTY


def buildCustomizationItemDataVO(item, count, plainView=False, showDetailItems=True, forceLocked=False,
                                 showUnsupportedAlert=False, isCurrentlyApplied=False):
    """ Build a CustomizationCarouselRendererVO out of the given item.
    """
    hasBonus = item.bonus is not None and not plainView
    locked = (not item.isUnlocked or forceLocked) and not plainView
    if plainView or item.isHidden:
        buyPrice = ITEM_PRICE_EMPTY
    else:
        buyPrice = item.getBuyPrice()
    isNonHistoric = not item.isHistorical()
    extraTitle = extraName = ''
    extraIcon = ''
    isEquipped = isCurrentlyApplied
    return CustomizationCarouselRendererVO(item.intCD, item.itemTypeID, item.isWide(), item.icon, hasBonus, locked, buyPrice,
                                           count, item.isRentable, showDetailItems, isNonHistoric, showUnsupportedAlert,
                                           extraTitle=extraTitle, extraName=extraName, extraIcon=extraIcon,
                                           showRareIcon=item.isRare(), isEquipped=isEquipped).asDict()


class CustomizationCarouselRendererVO(object):
    __slots__ = (
        'intCD', 'typeId', 'isWide', 'icon', 'hasBonus', 'locked', 'buyPrice', 'quantity', 'isRental', 'showDetailItems',
        'isNonHistoric', 'showAlert', 'buyOperationAllowed', 'extraTitle', 'extraName', 'extraIcon', 'showRareIcon',
        'isEquipped')

    def __init__(self, intCD, typeId, isWide, icon, hasBonus, locked, buyPrice, quantity=None, isRental=False,
                 showDetailItems=True, isNonHistoric=False, showAlert=False, buyOperationAllowed=True, extraTitle='',
                 extraName='', extraIcon='', showRareIcon=False, isEquipped=False):
        self.intCD = intCD
        self.typeId = typeId
        self.isWide = isWide
        self.icon = icon
        self.hasBonus = hasBonus
        self.locked = locked
        self.buyPrice = getItemPricesVO(buyPrice)[0]
        self.quantity = quantity
        self.isRental = isRental
        self.showDetailItems = showDetailItems
        self.isNonHistoric = isNonHistoric
        self.showAlert = showAlert
        self.buyOperationAllowed = buyOperationAllowed
        self.extraTitle = extraTitle
        self.extraName = extraName
        self.extraIcon = extraIcon
        self.showRareIcon = showRareIcon
        self.isEquipped = isEquipped

    def asDict(self):
        """
        Creates a dictionary with the class' relevant data.
        :return: data object
        """
        ret = {'intCD': self.intCD,
               'typeId': self.typeId,
               'isWide': self.isWide,
               'icon': self.icon,
               'locked': self.locked,
               'buyPrice': self.buyPrice,
               'isRental': self.isRental,
               'showDetailItems': self.showDetailItems,
               'isNonHistoric': self.isNonHistoric,
               'showAlert': self.showAlert,
               'buyOperationAllowed': self.buyOperationAllowed,
               'showRareIcon': self.showRareIcon,
               'isEquipped': self.isEquipped}
        if self.extraIcon:
            ret.update(styleIcon=self.extraIcon)
        if self.extraTitle and self.extraName:
            ret.update(styleTitle=self.extraTitle)
            ret.update(styleName=self.extraName)
        if self.quantity:
            ret.update(quantity=str(self.quantity))
        return ret
