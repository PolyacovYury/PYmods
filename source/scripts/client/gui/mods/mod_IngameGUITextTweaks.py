from PYmodsCore import overrideMethod, PYmodsConfigInterface, Analytics
from gui.battle_control.battle_ctx import BattleContext


class ConfigInterface(PYmodsConfigInterface):
    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.0.0 (%(file_compile_date)s)'
        self.data = {'enabled': True, 'removeNicknames': False,
                     'iconFormat': "<img src='img://gui/maps/icons/vehicleTypes/%(colour)s/%(classTag)s.png' width='17' "
                                   "height='21' vspace='-5'/>"}
        self.i18n = {
            'name': 'Ingame GUI tweaks',
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


config = ConfigInterface()
analytics = Analytics(config.ID, config.version, 'UA-76792179-21')


@overrideMethod(BattleContext, 'getPlayerFullName')
def new_getPlayerFullName(base, self, vID=None, accID=None, *a, **kw):
    result = base(self, vID, accID, *a, **kw)
    if config.data['enabled']:
        if vID is None:
            vID = self.getVehIDByAccDBID(accID)
        getVehicleClass = lambda vehID: self.getVehicleInfo(vehID).vehicleType.classTag
        result = result.replace(' (', ' (%s' % config.data['iconFormat'] % {
            'colour': 'green' if self.isAlly(vID) else 'red', 'classTag': getVehicleClass(vID)}, 1)
        if config.data['removeNicknames'] and ' (' in result:
            result = result.split(' (', 1)[1].rsplit(')', 1)[0]
    return result
