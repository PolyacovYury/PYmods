from PYmodsCore import overrideMethod, overrideStaticMethod
from gui.Scaleform.daapi.settings.views import VIEW_ALIAS
from gui.Scaleform.daapi.view.lobby.customization.customization_bottom_panel import CustomizationBottomPanel as CBP
from gui.Scaleform.locale.ITEM_TYPES import ITEM_TYPES
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from gui.Scaleform.locale.TOOLTIPS import TOOLTIPS
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION
from gui.shared.gui_items import GUI_ITEM_TYPE_NAMES, GUI_ITEM_TYPE
from gui.shared.utils.functions import makeTooltip
from helpers import i18n
from .shared import CSMode, tabToItem
from .. import g_config

CBP.ctx = property(lambda self: self._CustomizationBottomPanel__ctx)


@overrideMethod(CBP, '_CustomizationBottomPanel__setFooterInitData')
def __setFooterInitData(_, self):
    self.as_setBottomPanelInitDataS({
        'tabsAvailableRegions': self.ctx.tabsData.AVAILABLE_REGIONS,
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
    return {'leftLabel': g_config.i18n['UI_flash_switcher_' + CSMode.NAMES[mode]],
            'rightLabel': g_config.i18n['UI_flash_switcher_' + CSMode.NAMES[(mode + 1) % len(CSMode.NAMES)]],
            'leftEvent': 'installStyle',
            'rightEvent': 'installStyles',
            'isLeft': True}


@overrideMethod(CBP, '_CustomizationBottomPanel__getItemTabsData')
def __getItemTabsData(_, self):
    data = []
    pluses = []
    for tabIdx in self.ctx.visibleTabs:
        itemTypeID = tabToItem(tabIdx, self.ctx.mode)
        typeName = GUI_ITEM_TYPE_NAMES[itemTypeID]
        showPlus = not self.ctx.checkSlotsFilling(itemTypeID, self.ctx.currentSeason)
        data.append({'label': i18n.makeString(ITEM_TYPES.customizationPlural(typeName)),
                     'tooltip': makeTooltip(ITEM_TYPES.customizationPlural(typeName), TOOLTIPS.customizationItemTab(
                         typeName) if itemTypeID != GUI_ITEM_TYPE.STYLE else ''),
                     'id': tabIdx} if self.ctx.mode == CSMode.BUY else
                    {'label': g_config.i18n['UI_flash_tabs_%s_label' % tabIdx],
                     'tooltip': makeTooltip(g_config.i18n['UI_flashCol_tabs_%s_text' % tabIdx],
                                            g_config.i18n['UI_flashCol_tabs_%s_tooltip' % tabIdx]),
                     'id': tabIdx})
        pluses.append(showPlus)

    return data, pluses


# noinspection PyUnusedLocal
@overrideMethod(CBP, '_CustomizationBottomPanel__onModeChanged')
def __onModeChanged(_, self, mode):
    self._CustomizationBottomPanel__setFooterInitData()
    self._CustomizationBottomPanel__updateTabs(self.ctx.currentTab)
    self._carouselDP.selectItem(
        self.ctx.modifiedStyle if self.ctx.currentTab == self.ctx.tabsData.STYLE else None)
    self._CustomizationBottomPanel__setBottomPanelBillData()
