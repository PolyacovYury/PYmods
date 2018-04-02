from PYmodsCore import overrideMethod, PYmodsConfigInterface, Analytics, doOverrideMethod
from functools import partial
from gui.Scaleform.daapi.view.battle.shared.crosshair.plugins import VehicleStatePlugin
from gui.Scaleform.daapi.view.battle.shared.messages import VehicleMessages
from gui.Scaleform.daapi.view.battle.shared.messages.fading_messages import FadingMessages
from gui.Scaleform.daapi.view.battle.shared.postmortem_panel import PostmortemPanel
from messenger.formatters.chat_message import _BattleMessageBuilder
from messenger.proto.bw_chat2.battle_chat_cmd import _ReceivedCmdDecorator


class ConfigInterface(PYmodsConfigInterface):
    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.1.0 (%(file_compile_date)s)'
        self.data = {
            'enabled': True, 'removeNicknames': False,
            'iconFormat': "<img src='img://gui/maps/icons/vehicleTypes/%(colour)s/%(classTag)s.png' width='17' height='21' vspace='-5'/>"}
        self.i18n = {
            'name': 'Ingame GUI text tweaks',
            'UI_setting_removeNicknames_text': 'Remove nicknames',
            'UI_setting_removeNicknames_tooltip': 'Nicknames in battle chat, fading messages and other places are cut off.',
            'UI_setting_iconFormat_text': 'Icon format',
            'UI_setting_iconFormat_tooltip':
                'Format of vehicle class icon that gets put before vehicle names.\n'
                '%(colour)s: "green" if vehicle is ally else "red".\n'
                '%(classTag)s: gets replaced by vehicle class tag. '
                'Variants: "lightTank", "mediumTank", "heavyTank", "SPG", "AT-SPG" (case insensitive).'}
        super(ConfigInterface, self).init()

    def createTemplate(self):
        return {'modDisplayName': self.i18n['name'],
                'settingsVersion': 1,
                'enabled': self.data['enabled'],
                'column1': [self.tb.createControl('iconFormat', 'TextInputField', 800)],
                'column2': [self.tb.createControl('removeNicknames')]}

    def reformat(self, battleCtx, vID, income, mask=' ('):
        if not self.data['enabled']:
            return income
        isAlly = battleCtx.isAlly
        getVehicleClass = lambda vehID: battleCtx.getVehicleInfo(vehID).vehicleType.classTag
        result = income.replace(mask, mask + self.data['iconFormat'] % {
            'colour': 'green' if isAlly(vID) else 'red', 'classTag': getVehicleClass(vID)}, 1)
        if config.data['removeNicknames'] and mask in result:
            result = result.split(mask, 1)[1]
            if '(' in mask:
                result = result.rsplit(')', 1)[0]
        return result


config = ConfigInterface()
analytics = Analytics(config.ID, config.version, 'UA-76792179-21')


@overrideMethod(FadingMessages, '_FadingMessages__formatEntitiesEx')
def new_formatEntities(base, self, args, extra=None):
    base(self, args, extra)
    for argName, vID in (extra if extra is not None else ()):
        if argName in args:
            args[argName] = config.reformat(self.sessionProvider.getCtx(), vID, args[argName])


@overrideMethod(VehicleMessages, '_VehicleMessages__formatEntity')
def new_formatEntity(base, self, entityID):
    return config.reformat(self.sessionProvider.getCtx(), entityID, base(self, entityID), '| ')


@overrideMethod(_BattleMessageBuilder, 'setName')
def new_setName(base, self, dbID, pName=None):
    self = base(self, dbID, pName)
    battleCtx = self.sessionProvider.getCtx()
    self._ctx['playerName'] = config.reformat(battleCtx, battleCtx.getVehIDByAccDBID(dbID), self._ctx['playerName'])
    return self


@overrideMethod(_ReceivedCmdDecorator, '_getTarget')
def new_getTarget(base, self):
    return config.reformat(self.sessionProvider.getCtx(), self.getFirstTargetID(), base(self))


def new_setPlayerInfo(attrClass, base, self, vehicleID):
    base(self)
    if config.data['enabled']:
        pInfo = getattr(self, '_%s__playerInfo' % attrClass)
        fullName = config.reformat(self.sessionProvider.getCtx(), vehicleID, pInfo.playerFullName)
        setattr(self, '_%s__playerInfo' % attrClass, pInfo._replace(playerFullName=fullName))


doOverrideMethod(PostmortemPanel, '_PostmortemPanel__setPlayerInfo', partial(new_setPlayerInfo, 'PostmortemPanel'))
doOverrideMethod(VehicleStatePlugin, '_VehicleStatePlugin__setPlayerInfo', partial(new_setPlayerInfo, 'VehicleStatePlugin'))
