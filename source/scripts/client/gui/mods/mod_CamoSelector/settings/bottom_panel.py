import Keys
from PYmodsCore import overrideMethod, overrideStaticMethod, checkKeys
from gui import InputHandler
from gui.Scaleform.daapi.settings.views import VIEW_ALIAS
from gui.Scaleform.daapi.view.lobby.customization.customization_bottom_panel import CustomizationBottomPanel as CBP
from gui.Scaleform.daapi.view.lobby.customization.shared import C11nTabs, TABS_ITEM_MAPPING
from gui.Scaleform.locale.ITEM_TYPES import ITEM_TYPES
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from gui.Scaleform.locale.TOOLTIPS import TOOLTIPS
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION
from gui.shared.gui_items import GUI_ITEM_TYPE_NAMES
from gui.shared.utils.functions import makeTooltip
from helpers import i18n
from .shared import CSTabs, CSMode, tabToItem
from .. import g_config

CBP.ctx = property(lambda self: self._CustomizationBottomPanel__ctx)
CBP.handleKey = lambda self, event: self._CustomizationBottomPanel__setFooterInitData() if event.key in (
    Keys.KEY_LSHIFT, Keys.KEY_RSHIFT) else None


@overrideMethod(CBP, '_populate')
def _populate(base, self):
    base(self)
    InputHandler.g_instance.onKeyDown += self.handleKey
    InputHandler.g_instance.onKeyUp += self.handleKey


@overrideMethod(CBP, '_dispose')
def _dispose(base, self):
    InputHandler.g_instance.onKeyDown -= self.handleKey
    InputHandler.g_instance.onKeyUp -= self.handleKey
    base(self)


# @overrideMethod(CBP, '_CustomizationBottomPanel')
@overrideMethod(CBP, '_CustomizationBottomPanel__setFooterInitData')
def __setFooterInitData(_, self):
    self.as_setBottomPanelInitDataS({
        'tabsAvailableRegions': (C11nTabs if self.ctx.mode == CSMode.BUY else CSTabs).AVAILABLE_REGIONS,
        'defaultStyleLabel': VEHICLE_CUSTOMIZATION.DEFAULTSTYLE_LABEL,
        'carouselInitData': self._CustomizationBottomPanel__getCarouselInitData(),
        'switcherInitData': self._CustomizationBottomPanel__getSwitcherInitData(self.ctx.mode),
        'filtersVO': {'popoverAlias': VIEW_ALIAS.CUSTOMIZATION_FILTER_POPOVER,
                      'mainBtn': {'value': RES_ICONS.MAPS_ICONS_BUTTONS_FILTER,
                                  'tooltip': VEHICLE_CUSTOMIZATION.CAROUSEL_FILTER_MAINBTN},
                      'hotFilters': [{'value': RES_ICONS.MAPS_ICONS_CUSTOMIZATION_STORAGE_ICON,
                                      'tooltip': VEHICLE_CUSTOMIZATION.CAROUSEL_FILTER_STORAGEBTN,
                                      'selected': self._carouselDP.getOwnedFilter()},
                                     {'value': RES_ICONS.MAPS_ICONS_BUTTONS_EQUIPPED_ICON,
                                      'tooltip': VEHICLE_CUSTOMIZATION.CAROUSEL_FILTER_EQUIPPEDBTN,
                                      'selected': self._carouselDP.getAppliedFilter()}]}})


@overrideStaticMethod(CBP, '_CustomizationBottomPanel__getSwitcherInitData')
def __getSwitcherInitData(_, mode):
    isLeft = not checkKeys([[Keys.KEY_LSHIFT, Keys.KEY_RSHIFT]])
    otherMode = (mode + 1 if isLeft else mode - 1 + len(CSMode.NAMES)) % len(CSMode.NAMES)
    return {'leftLabel': g_config.i18n['UI_flash_switcher_' + CSMode.NAMES[mode if isLeft else otherMode]],
            'rightLabel': g_config.i18n['UI_flash_switcher_' + CSMode.NAMES[otherMode if isLeft else mode]],
            'leftEvent': 'installStyle',
            'rightEvent': 'installStyles',
            'isLeft': isLeft}


@overrideMethod(CBP, '_CustomizationBottomPanel')
def __getItemTabsData(_, self):
    data = []
    pluses = []
    for tabIdx in self.ctx.visibleTabs:
        itemTypeID = (TABS_ITEM_MAPPING[tabIdx] if self.ctx.mode == CSMode.BUY else tabToItem(tabIdx))
        typeName = GUI_ITEM_TYPE_NAMES[itemTypeID]
        showPlus = not self.ctx.checkSlotsFilling(itemTypeID, self.ctx.currentSeason)
        data.append({'label': i18n.makeString(ITEM_TYPES.customizationPlural(typeName)),
                     'tooltip': makeTooltip(ITEM_TYPES.customizationPlural(typeName),
                                            TOOLTIPS.customizationItemTab(typeName)),
                     'id': tabIdx})
        pluses.append(showPlus)

    return data, pluses


@overrideMethod(CBP, '_CustomizationBottomPanel__onModeChanged')
def __onModeChanged(_, self, mode):
    self._CustomizationBottomPanel__updateTabs(self.ctx.currentTab)
    self._carouselDP.selectItem(
        self.ctx.modifiedStyle if self.ctx.currentTab == (C11nTabs if mode == CSMode.BUY else CSTabs).STYLE else None)
    self._CustomizationBottomPanel__setBottomPanelBillData()
