import Event
import copy
from PYmodsCore.config import smart_update
from gui.Scaleform.framework import g_entitiesFactories, ViewSettings, WindowLayer, ScopeTemplates
from gui.Scaleform.framework.entities.View import View
from gui.Scaleform.framework.managers.loaders import SFViewLoadParams
from gui.shared.personality import ServicesLocator
from skeletons.gui.app_loader import GuiGlobalSpaceID


class Cache(object):
    def __init__(self):
        self.items = {}
        g_events.create += self.__create
        g_events.update += self.__update
        g_events.delete += self.__delete

    def __create(self, linkage, config):
        if linkage not in self.items:
            self.items[linkage] = {'config': config, 'data': {}}

    def __update(self, linkage, data):
        if linkage in self.items:
            self.items[linkage]['data'] = data

    def __delete(self, linkage):
        if linkage in self.items:
            del self.items[linkage]


class Events(object):
    def __init__(self):
        self.create = Event.Event()
        self.update = Event.Event()
        self.delete = Event.Event()
        self.onUIReady = Event.Event()
        self.onBattleLoaded = Event.Event()
        ServicesLocator.appLoader.onGUISpaceEntered += self.__onGUISpaceEntered

    def __onGUISpaceEntered(self, spaceID):
        if spaceID != GuiGlobalSpaceID.BATTLE:
            return
        app = ServicesLocator.appLoader.getDefBattleApp()
        if app is not None:
            app.loadView(SFViewLoadParams('PY_PlayersPanelAPI_UI'))


class PlayersPanelUI(View):
    def _populate(self):
        super(PlayersPanelUI, self)._populate()

        for linkage, data in g_cache.items.iteritems():
            self.as_createS(linkage, data['config'])

        g_events.create += self.as_createS
        g_events.update += self.as_updateS
        g_events.delete += self.as_deleteS

        g_events.onUIReady()

    def _dispose(self):
        g_events.create -= self.as_createS
        g_events.update -= self.as_updateS
        g_events.delete -= self.as_deleteS
        super(PlayersPanelUI, self)._dispose()

    def as_createS(self, linkage, config):
        if self._isDAAPIInited():
            self.flashObject.as_create(linkage, config)

    def as_updateS(self, linkage, data):
        if self._isDAAPIInited():
            self.flashObject.as_update(linkage, data)

    def as_deleteS(self, linkage):
        if self._isDAAPIInited():
            self.flashObject.as_delete(linkage)


# noinspection PyArgumentList
g_entitiesFactories.addSettings(ViewSettings(
    'PY_PlayersPanelAPI_UI', PlayersPanelUI, 'PlayersPanelAPI.swf', WindowLayer.WINDOW, None, ScopeTemplates.GLOBAL_SCOPE))

g_events = Events()
g_cache = Cache()

LABEL_CONFIG = {
    'isHtml': True,
    'left': {
        'x': 0,
        'y': 0,
        'height': 24,
        'width': 100,
        'align': 'left'},
    'right': {
        'x': 0,
        'y': 0,
        'height': 24,
        'width': 100,
        'align': 'right'},
    'shadow': {
        'distance': 0,
        'angle': 0,
        'color': 0x000000,
        'alpha': 90,
        'blurX': 2,
        'blurY': 2,
        'strength': 2,
        'quality': 2}
}


class PlayersPanelAPI(object):
    events = g_events

    def create(self, linkage, config):
        conf = copy.deepcopy(LABEL_CONFIG)
        smart_update(conf, config)
        g_events.create(linkage, conf)

    def update(self, linkage, data):
        g_events.update(linkage, data)

    def delete(self, linkage):
        g_events.delete(linkage)


g_PlayersPanelAPI = PlayersPanelAPI()
