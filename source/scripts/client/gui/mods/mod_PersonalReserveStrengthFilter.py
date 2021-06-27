import BigWorld
from PYmodsCore import overrideMethod
from account_helpers import AccountSettings
from frameworks.wulf import WindowLayer
from goodies.goodie_constants import GOODIE_RESOURCE_TYPE
from gui.Scaleform.daapi.settings.views import VIEW_ALIAS
from gui.Scaleform.daapi.view.lobby.storage.personalreserves import boosters_view
from gui.Scaleform.daapi.view.lobby.storage.storage_helpers import isStorageSessionTimeout
from gui.Scaleform.daapi.view.lobby.storage.storage_view import StorageView
from gui.Scaleform.framework import ComponentSettings, ScopeTemplates as ST, ViewSettings, g_entitiesFactories
from gui.Scaleform.framework.entities.View import View
from gui.Scaleform.framework.managers.loaders import SFViewLoadParams
from gui.Scaleform.genConsts.STORAGE_CONSTANTS import STORAGE_CONSTANTS
from gui.Scaleform.locale.TOOLTIPS import TOOLTIPS
from gui.shared import EVENT_BUS_SCOPE, g_eventBus
from gui.shared.events import ViewEventType
from gui.shared.personality import ServicesLocator as SL
from gui.shared.utils.requesters import REQ_CRITERIA

_STRENGTH_FILTER_ITEMS = [
    {'filterValue': 1 << _i, 'selected': False, 'tooltip': '', 'label': TOOLTIPS.level(_i + 1)} for _i in xrange(4)]


class StorageCategoryPersonalReservesView(boosters_view.StorageCategoryPersonalReservesView):
    alias = 'StorageCategoryPersonalReservesWithStrengthViewUI'
    _instance = None

    def as_initStrengthFilterS(self, strengthFiltersVO):
        return self.flashObject.as_initStrengthFilter(strengthFiltersVO) if self._isDAAPIInited() else None

    def __init__(self):
        super(StorageCategoryPersonalReservesView, self).__init__()
        self._strengthMask = 0

    def _populate(self):
        super(StorageCategoryPersonalReservesView, self)._populate()
        StorageCategoryPersonalReservesView._instance = self

    def _dispose(self):
        StorageCategoryPersonalReservesView._instance = None
        super(StorageCategoryPersonalReservesView, self)._dispose()

    def resetFilter(self):
        self._strengthMask = 0
        super(StorageCategoryPersonalReservesView, self).resetFilter()

    def _loadFilters(self):
        if isStorageSessionTimeout():
            return
        filterDict = AccountSettings.getSessionSettings(self._getClientSectionKey())
        self.__filterMask, self._strengthMask = filterDict['filterMask'], filterDict['strengthMask']

    def _saveFilters(self):
        filterDict = {'filterMask': self.__filterMask, 'strengthMask': self._strengthMask}
        AccountSettings.setSessionSettings(self._getClientSectionKey(), filterDict)

    def onStrengthChange(self, filterMask):
        self._strengthMask = filterMask
        self.__onUpdateBoosters()

    def _getBoosterTier(self, item):
        values = (25, 50, 100, 200, 300)
        if item.boosterType in (GOODIE_RESOURCE_TYPE.CREW_XP, GOODIE_RESOURCE_TYPE.FREE_XP):
            values = values[1:]
        else:
            values = values[:3]
        return 0 if item.effectValue not in values else values.index(item.effectValue)

    def __initFilter(self):
        # noinspection PyUnresolvedReferences
        WGReservesView._StorageCategoryPersonalReservesView__initFilter(self)
        self.as_initStrengthFilterS({'minSelectedItems': 0, 'items': [
            dict(i, selected=bool(self._strengthMask & i['filterValue'])) for i in reversed(_STRENGTH_FILTER_ITEMS)]})

    def as_updateCounterS(self, shouldShow, displayString, isZeroCount):
        super(StorageCategoryPersonalReservesView, self).as_updateCounterS(
            shouldShow and self._strengthMask, displayString, isZeroCount)


@overrideMethod(boosters_view, 'getCriteriaFromFilterMask')
def new_getCriteriaFromFilterMask(base, filterMask):
    criteria = base(filterMask)
    self = StorageCategoryPersonalReservesView._instance
    if not self:
        return criteria
    levels = {i for i in xrange(4) if self._strengthMask & i}
    if levels:
        criteria |= REQ_CRITERIA.CUSTOM(lambda i: self._getBoosterTier(i) in levels)
    return criteria


@overrideMethod(StorageView, '__createSections')
def new_createSections(base, self):
    sections = base(self)
    for section in sections:
        if section['linkage'] == STORAGE_CONSTANTS.PERSONAL_RESERVES_VIEW:
            print 'replaced linkage'
            section['linkage'] = StorageCategoryPersonalReservesView.alias
    return sections


@overrideMethod(StorageView, '__setActiveSectionIdx')
def new_setActiveSectionIdx(base, self, sectionAlias):
    base(self)
    for idx, section in enumerate(self._StorageView__sections):
        if sectionAlias == STORAGE_CONSTANTS.PERSONAL_RESERVES_VIEW:
            if section['linkage'] == StorageCategoryPersonalReservesView.alias:
                self._StorageView__activeSectionIdx = idx


class _Loader(View):
    alias = 'PersonalReserveStrengthFilterLoader'

    def _populate(self):
        print 'am loading'
        super(_Loader, self)._populate()
        BigWorld.callback(0, self.destroy)


g_eventBus.addListener(ViewEventType.LOAD_VIEW, lambda e: (
    SL.appLoader.getApp().loadView(SFViewLoadParams(_Loader.alias)),
    SL.appLoader.getApp().as_loadLibrariesS(['PersonalReserveStrengthFilter.swf'])
) if e.alias == VIEW_ALIAS.LOBBY_STORAGE else None, EVENT_BUS_SCOPE.LOBBY)
# noinspection PyArgumentList
g_entitiesFactories.initSettings((ComponentSettings(
    StorageCategoryPersonalReservesView.alias, StorageCategoryPersonalReservesView, ST.DEFAULT_SCOPE),
    ViewSettings(_Loader.alias, _Loader, 'PersonalReserveStrengthFilter.swf', WindowLayer.WINDOW, None, ST.GLOBAL_SCOPE)
))
