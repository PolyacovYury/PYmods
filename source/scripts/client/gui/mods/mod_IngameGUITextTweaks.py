import BigWorld
from PYmodsCore import overrideMethod, PYmodsConfigInterface, Analytics, events
from constants import ARENA_GUI_TYPE
from functools import partial
from gui.Scaleform.daapi.view.battle.shared.crosshair.plugins import VehicleStatePlugin
from gui.Scaleform.daapi.view.battle.shared.messages import VehicleMessages
from gui.Scaleform.daapi.view.battle.shared.messages.fading_messages import FadingMessages
from gui.Scaleform.daapi.view.battle.shared.postmortem_panel import PostmortemPanel
from messenger import storage
from messenger.formatters.chat_message import _BattleMessageBuilder
from messenger.m_constants import USER_TAG
from messenger.proto.bw_chat2.battle_chat_cmd import _ReceivedCmdDecorator
from threading import Thread


class ConfigInterface(PYmodsConfigInterface):
    def __init__(self):
        self.friends = None
        events.LobbyView.populate.after(lambda: Thread(target=self.onHangarInit).start())
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.1.0 (%(file_compile_date)s)'
        # noinspection LongLine
        self.data = {
            'enabled': True, 'removeNicknames': 0,
            'iconFormat': "<img src='img://gui/maps/icons/vehicleTypes/%(colour)s/%(classTag)s.png' width='17' height='21' vspace='-5'/>"}
        self.i18n = {
            'name': 'Ingame GUI text tweaks',
            'UI_setting_removeNicknames_text': 'Remove nicknames',
            'UI_setting_removeNicknames_tooltip':
                'Nicknames in battle chat, fading messages and other places are cut off. Modes:\n'
                '<b>None</b>: nicknames are not cut off.\n'
                '<b>Smart</b>: nicknames for friends, squad mates and non-random allies are preserved.\n'
                '<b>All</b>: all nicknames are cut off.',
            'UI_setting_removeNicknames_none': 'None',
            'UI_setting_removeNicknames_smart': 'Smart',
            'UI_setting_removeNicknames_all': 'All',
            'UI_setting_iconFormat_text': 'Icon format',
            'UI_setting_iconFormat_tooltip':
                'Format of vehicle class icon that gets put before vehicle names.\n'
                '%(colour)s: "green" if vehicle is ally else "red".\n'
                '%(classTag)s: gets replaced by vehicle class tag. '
                'Variants: "lightTank", "mediumTank", "heavyTank", "SPG", "AT-SPG" (case insensitive).'}
        super(ConfigInterface, self).init()

    def createTemplate(self):
        return {'modDisplayName': self.i18n['name'],
                'enabled': self.data['enabled'],
                'column1': [self.tb.createControl('iconFormat', self.tb.types.TextInput, 400)],
                'column2': [self.tb.createOptions(
                    'removeNicknames', [self.i18n['UI_setting_removeNicknames_' + key] for key in ('none', 'smart', 'all')])]}

    def onHangarInit(self):
        if self.friends is None:
            self.friends = set()
            usersStorage = storage.storage_getter('users')
            for user in usersStorage().all():
                tags = user.getTags()
                if USER_TAG.FRIEND in tags:
                    self.friends.add(user.getName())

            while True:
                friends = set()
                usersStorage = storage.storage_getter('users')
                for user in usersStorage().all():
                    tags = user.getTags()
                    if USER_TAG.FRIEND in tags:
                        friends.add(user.getName())

                if friends == self.friends:
                    break
                self.friends = friends

    def reformat(self, battleCtx, vID, income, mask=' ('):
        if not self.data['enabled']:
            return income
        isAlly = battleCtx.isAlly
        getVehicleClass = lambda vehID: battleCtx.getVehicleInfo(vehID).vehicleType.classTag
        result = income.replace(mask, mask + self.data['iconFormat'] % {
            'colour': 'green' if isAlly(vID) else 'red', 'classTag': getVehicleClass(vID)}, 1)
        if mask in result and (
                config.data['removeNicknames'] == 2 or config.data['removeNicknames'] and not (
                isAlly(vID) and (BigWorld.player().arena.guiType not in (ARENA_GUI_TYPE.EPIC_RANDOM, ARENA_GUI_TYPE.RANDOM))
                or battleCtx.isSquadMan(vID) or (self.friends is not None and battleCtx.getPlayerName(vID) in self.friends))):
            result = result.split(mask, 1)[1]
            if '(' in mask:
                result = result.rsplit(')', 1)[0]
        return result


config = ConfigInterface()
analytics = Analytics(config.ID, config.version, 'UA-76792179-21')


@overrideMethod(FadingMessages, '_FadingMessages__formatEntitiesEx')
def new_formatEntities(base, self, args, extra=None, *a, **kw):
    base(self, args, extra, *a, **kw)
    for argName, vID in (extra if extra is not None else ()):
        if argName in args:
            args[argName] = config.reformat(self.sessionProvider.getCtx(), vID, args[argName])


@overrideMethod(VehicleMessages, '_VehicleMessages__formatEntity')
def new_formatEntity(base, self, entityID, *a, **kw):
    return config.reformat(self.sessionProvider.getCtx(), entityID, base(self, entityID, *a, **kw), '| ')


@overrideMethod(_BattleMessageBuilder, 'setName')
def new_setName(base, self, dbID, *a, **kw):
    self = base(self, dbID, *a, **kw)
    battleCtx = self.sessionProvider.getCtx()
    self._ctx['playerName'] = config.reformat(battleCtx, battleCtx.getVehIDByAccDBID(dbID), self._ctx['playerName'])
    return self


@overrideMethod(_ReceivedCmdDecorator, '_getTarget')
def new_getTarget(base, self, *a, **kw):
    return config.reformat(self.sessionProvider.getCtx(), self.getFirstTargetID(), base(self, *a, **kw))


def new_setPlayerInfo(attrClass, base, self, vehicleID, *a, **kw):
    base(self, vehicleID, *a, **kw)
    if config.data['enabled']:
        pInfo = getattr(self, '_%s__playerInfo' % attrClass)
        fullName = config.reformat(self.sessionProvider.getCtx(), vehicleID, pInfo.playerFullName)
        setattr(self, '_%s__playerInfo' % attrClass, pInfo._replace(playerFullName=fullName))


overrideMethod(PostmortemPanel, '_PostmortemPanel__setPlayerInfo', partial(new_setPlayerInfo, 'PostmortemPanel'))
overrideMethod(VehicleStatePlugin, '_VehicleStatePlugin__setPlayerInfo', partial(new_setPlayerInfo, 'VehicleStatePlugin'))
