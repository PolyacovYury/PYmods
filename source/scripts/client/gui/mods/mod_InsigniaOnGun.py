import BigWorld
from OpenModsCore import Analytics, SimpleConfigInterface, overrideMethod
from VehicleStickers import VehicleStickers
from gui.hangar_vehicle_appearance import HangarVehicleAppearance
from vehicle_systems.CompoundAppearance import CompoundAppearance


class ConfigInterface(SimpleConfigInterface):
    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.0.0 (%(file_compile_date)s)'
        self.author = 'by Polyacov_Yury'
        self.modsGroup = 'PYmods'
        self.modSettingsID = 'PYmodsGUI'
        self.data = {
            'enabled': True,
            'enableHangar': True, 'replaceHangar': False, 'hangar': 3,
            'enablePlayer': True, 'replacePlayer': False, 'player': 3,
            'enableAlly': False, 'replaceAlly': False, 'ally': 3,
            'enableEnemy': False, 'replaceEnemy': False, 'enemy': 3}
        self.i18n = {
            'name': 'Insignia on gun',
            'UI_setting_enableHangar_text': 'Enable in hangar',
            'UI_setting_enableHangar_tooltip': 'Activate hangar module.',
            'UI_setting_replaceHangar_text': 'Replace hangar marks',
            'UI_setting_replaceHangar_tooltip': 'If a vehicle has any marks you actually earned - it will be replaced.',
            'UI_setting_hangar_text': 'Number of marks in hangar',
            'UI_setting_hangar_tooltip': 'This number of marks on gun will be displayed in hangar.',
            'UI_setting_enablePlayer_text': 'Enable for player vehicle',
            'UI_setting_enablePlayer_tooltip': 'Activate processing of player vehicles.',
            'UI_setting_replacePlayer_text': 'Replace marks on player vehicle',
            'UI_setting_replacePlayer_tooltip': 'If your vehicle has any marks you actually earned - it will be replaced.',
            'UI_setting_player_text': 'Number of marks on player vehicle',
            'UI_setting_player_tooltip': 'This number of marks on gun will be displayed on player vehicle.',
            'UI_setting_enableAlly_text': 'Enable for ally vehicles',
            'UI_setting_enableAlly_tooltip': 'Activate processing of ally vehicles.',
            'UI_setting_replaceAlly_text': 'Replace marks on ally vehicles',
            'UI_setting_replaceAlly_tooltip': 'If an ally vehicle has any earned marks - it will be replaced.',
            'UI_setting_ally_text': 'Number of marks on ally vehicles',
            'UI_setting_ally_tooltip': 'This number of marks on gun will be displayed on ally vehicles.',
            'UI_setting_enableEnemy_text': 'Enable for enemy vehicles',
            'UI_setting_enableEnemy_tooltip': 'Activate processing of enemy vehicles.',
            'UI_setting_replaceEnemy_text': 'Replace marks on enemy vehicles',
            'UI_setting_replaceEnemy_tooltip': 'If an enemy vehicle has any earned marks - it will be replaced.',
            'UI_setting_enemy_text': 'Number of marks on enemy vehicles',
            'UI_setting_enemy_tooltip': 'This number of marks on gun will be displayed on enemy vehicles.'}
        super(ConfigInterface, self).init()

    def createTemplate(self):
        return {'modDisplayName': self.i18n['name'],
                'enabled': self.data['enabled'],
                'column1': [self.tb.createControl('enableHangar'),
                            self.tb.createControl('replaceHangar'),
                            self.tb.createStepper('hangar', 0, 3, 1, True),
                            self.tb.createControl('enablePlayer'),
                            self.tb.createControl('replacePlayer'),
                            self.tb.createStepper('player', 0, 3, 1, True)],
                'column2': [self.tb.createControl('enableAlly'),
                            self.tb.createControl('replaceAlly'),
                            self.tb.createStepper('ally', 0, 3, 1, True),
                            self.tb.createControl('enableEnemy'),
                            self.tb.createControl('replaceEnemy'),
                            self.tb.createStepper('enemy', 0, 3, 1, True)]}


@overrideMethod(HangarVehicleAppearance, '__getThisVehicleDossierInsigniaRank')
def new_getRank(base, *a, **kw):
    result = base(*a, **kw)
    if config.data['enabled'] and config.data['enableHangar'] and (config.data['replaceHangar'] or not result):
        return config.data['hangar']
    return result


@overrideMethod(CompoundAppearance, '_createStickers')
def new_createStickers(base, self, *a, **kw):
    vehicle = self._vehicle
    if not vehicle or not config.data['enabled']:
        return base(self, *a, **kw)
    insigniaRank = origRank = vehicle.publicInfo['marksOnGun']
    if vehicle.isPlayerVehicle:
        if config.data['enablePlayer'] and (config.data['replacePlayer'] or not origRank):
            insigniaRank = config.data['player']
    elif BigWorld.player().guiSessionProvider.getCtx().isAlly(vehicle.id):
        if config.data['enableAlly'] and (config.data['replaceAlly'] or not origRank):
            insigniaRank = config.data['ally']
    elif config.data['enableEnemy'] and (config.data['replaceEnemy'] or not origRank):
        insigniaRank = config.data['enemy']
    vehicleStickers = VehicleStickers(self.typeDescriptor, insigniaRank, self.outfit)
    clanID = BigWorld.player().arena.vehicles[self.id]['clanDBID']
    vehicleStickers.setClanID(clanID)
    return vehicleStickers


config = ConfigInterface()
analytics = Analytics(config.ID, config.version, 'UA-76792179-18')
