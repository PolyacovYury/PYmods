# -*- coding: utf-8 -*-
import BigWorld
from Account import PlayerAccount
from OpenModsCore import SimpleConfigInterface, overrideMethod
from collections import OrderedDict
from gambiter import g_guiFlash
from gambiter.flash import COMPONENT_TYPE
from gui.Scaleform.daapi.view.lobby.hangar.Hangar import Hangar
from gui.Scaleform.daapi.view.meta.LobbyHeaderMeta import LobbyHeaderMeta
from gui.shared.personality import ServicesLocator as SL
from gui.shared.utils.requesters.ItemsRequester import REQ_CRITERIA
from shared_utils import safeCancelCallback

BOOSTER_ICON_EMPTY = 'img://gui/maps/icons/filters/empty.png'


class BoosterCache(object):
    def __init__(self, booster):
        self._booster = booster
        self.finishTime = booster.finishTime
        self.effectTime = booster._goodieDescription.lifetime

    def __getattr__(self, item):
        if item in ('finishTime', 'effectTime'):
            return self.__dict__[item]
        return getattr(self.__dict__['_booster'], item)


class ConfigInterface(SimpleConfigInterface):
    def __init__(self):
        self.__isBattle = True
        self.boosters = ([], [])
        self.updateCallback = None
        super(ConfigInterface, self).__init__()

    @property
    def isBattle(self):
        return self.__isBattle

    @isBattle.setter
    def isBattle(self, value):
        self.__isBattle = value
        if self.updateCallback:
            self.updateCallback = safeCancelCallback(self.updateCallback)
        if not value:
            self.updateCallback = BigWorld.callback(1, self.update)

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.0.0 (%(file_compile_date)s)'
        self.author = 'by ktulho, HEKPOMAHT, Polyacov_Yury'
        self.modsGroup = 'PYmods'
        self.modSettingsID = 'PYmodsGUI'
        self.data = {
            'enabled': True,
            'hideAvailableBooster': False,
        }
        self.i18n = {
            'name': 'Hangar Booster Viewer',
            'UI_setting_hideAvailableBooster_text': 'Hide available booster icon and quantity',
            'UI_setting_hideAvailableBooster_tooltip': 'Hides default plus icon and quantity of available boosters',
        }
        super(ConfigInterface, self).init()

    def createTemplate(self):
        return {
            'modDisplayName': self.i18n['name'], 'enabled': self.data['enabled'],
            'column1': [
                self.tb.createControl('hideAvailableBooster'),
            ],
            'column2': [
            ]}

    def load(self):
        super(ConfigInterface, self).load()
        g_guiFlash.createComponent(self.ID + '_1bg', COMPONENT_TYPE.IMAGE, {
            "x": 74, "y": 51, 'image': '../HangarBoosterViewer/bg/0.png'}, False, True)
        g_guiFlash.createComponent(self.ID + '_2icons', COMPONENT_TYPE.LABEL, {
            "x": 85, "y": 28, 'text': ''}, False, True)
        g_guiFlash.createComponent(self.ID + '_3timer', COMPONENT_TYPE.LABEL, {
            "x": 120, "y": 69, "shadow": {"alpha": 75, "blur": 3, "color": "0x0000CD", "strength": 1}, 'text': ''
        }, False, True)

    def update(self):
        if self.updateCallback:
            self.updateCallback = safeCancelCallback(self.updateCallback)
        if not self.isBattle:
            self.updateCallback = BigWorld.callback(1, self.update)
            self.boosters = (SL.goodiesCache.getClanReserves().values(), [
                BoosterCache(b) for b in SL.goodiesCache.getBoosters(criteria=REQ_CRITERIA.BOOSTER.ACTIVE).itervalues()])
        activeCRTypes = OrderedDict((i, j) for (i, j) in ((i, self.type(1, i)) for i in xrange(2)) if j)
        activeRTypes = OrderedDict((i, j) for (i, j) in ((i, self.type(0, i)) for i in xrange(3)) if j)
        g_guiFlash.updateComponent(self.ID + '_1bg', {
            'image': '../HangarBoosterViewer/bg/%s.png' % (len(activeCRTypes) + len(activeRTypes))
        })
        g_guiFlash.updateComponent(self.ID + '_2icons', {'text': (
                ''.join(("<img src='img://gui/HangarBoosterViewer/clan/%s.png'>" % t for t in activeCRTypes.values()))
                + ''.join(("<img src='img://gui/HangarBoosterViewer/active/%s.png'>" % t for t in activeRTypes.values())))
        })
        g_guiFlash.updateComponent(self.ID + '_3timer', {'text': (
            "<font color='#CCFFFF' size='12'><textformat tabstops='[65,130,195,260]'>" + '\t'.join(
                [self.leftTime(1, i) for i in activeCRTypes] + [self.leftTime(0, i) for i in activeRTypes]
            ) + "</textformat></font>")})

    def reserveFromIndex(self, index, reserves):
        return reserves[index] if index < len(reserves) else None

    def type(self, clan, index):
        b = self.reserveFromIndex(index, self.boosters[not clan])
        return b and b.boosterGuiType

    def leftTime(self, clan, index):
        b = self.reserveFromIndex(index, self.boosters[not clan])
        if b is None:
            return None
        left_time = b.getUsageLeftTime()
        h, m = divmod(left_time / 60, 60)
        s = left_time % 60
        if h > 0:
            return "{:d}:{:02d}:{:02d}".format(h, m, s)
        return "{:02d}:{:02d}".format(m, s)


g_config = ConfigInterface()


@overrideMethod(LobbyHeaderMeta, 'as_setBoosterDataS')
def as_setBoosterDataS(base, self, data):
    try:
        if not g_config.data['enabled']:
            return
        if data['hasActiveBooster']:
            data['boosterIcon'] = BOOSTER_ICON_EMPTY
            data['boosterBg'] = BOOSTER_ICON_EMPTY
            data['boosterText'] = ''
        elif data['hasAvailableBoosters'] and not data['hasActiveBooster'] and g_config.data['hideAvailableBooster']:
            data['boosterIcon'] = BOOSTER_ICON_EMPTY
            data['boosterBg'] = BOOSTER_ICON_EMPTY
            data['boosterText'] = ''
    finally:
        return base(self, data)


@overrideMethod(PlayerAccount, 'onArenaCreated')
def PlayerAccount_onArenaCreated(base, *a, **k):
    g_config.isBattle = True
    return base(*a, **k)


@overrideMethod(Hangar, '_populate')
def Hangar_populate(base, *a, **k):
    try:
        return base(*a, **k)
    finally:
        g_config.isBattle = False
