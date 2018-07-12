import BigWorld
import Keys
import Math
import bisect
from AvatarInputHandler.DynamicCameras.SniperCamera import SniperCamera
from AvatarInputHandler.control_modes import SniperControlMode
from PYmodsCore import PYmodsConfigInterface, overrideMethod, Analytics, checkKeys
from vehicle_systems.tankStructure import TankPartNames


class ConfigInterface(PYmodsConfigInterface):
    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.0.0 (%(file_compile_date)s)'
        self.author += ' (formerly by l3VGV, supported by KL1SK)'
        self.defaultKeys = {'hotkey': [Keys.KEY_F11]}
        self.data = {'enabled': True, 'isEnabled': True, 'changeZoom': True, 'zoomValue': 0.8,
                     'blacklist': 'germany:Karl,ussr:R00_T_50_2,usa:A00_T110E5,france:F00_AMX_50Foch_155',
                     'hotkey': self.defaultKeys['hotkey']}
        self.i18n = {
            'name': 'Show vehicle in sniper mode',
            'UI_setting_isEnabled_text': 'Active at battle start',
            'UI_setting_isEnabled_tooltip': 'Vehicle hull is displayed in sniper mode on battle start.',
            'UI_setting_changeZoom_text': 'Add another zoom value',
            'UI_setting_changeZoom_tooltip':
                'The mod adds another zoom value in sniper mode so that you could see your vehicle hull better.',
            'UI_setting_zoomValue_text': 'Additional zoom value',
            'UI_setting_zoomValue_tooltip': 'The value that gets added into the list of zoom values.',
            'UI_setting_blacklist_text': 'Vehicle blacklist',
            'UI_setting_blacklist_tooltip': 'The list of vehicles that do not get processed by the mod.\n\nI have no idea, '
                                            'why the users wanted this, since the mod has a toggle hotkey, but ok.',
            'UI_setting_hotkey_text': 'Toggle hotkey',
            'UI_setting_hotkey_tooltip': 'This hotkey only works in sniper mode and toggles vehicle hull displaying.'}
        super(ConfigInterface, self).init()

    def createTemplate(self):
        return {'modDisplayName': self.i18n['name'],
                'settingsVersion': 1,
                'enabled': self.data['enabled'],
                'column1': [self.tb.createControl('changeZoom'),
                            self.tb.createStepper('zoomValue', 0.1, 1.0, 0.1, True),
                            self.tb.createControl('blacklist', 'TextInputField', 800)],
                'column2': [self.tb.createHotKey('hotkey'),
                            self.tb.createControl('isEnabled')]}


config = ConfigInterface()
analytics = Analytics(config.ID, config.version, 'UA-76792179-20')


def addValues(zooms, exposures):
    zoom = config.data['zoomValue']
    if config.data['isEnabled']:
        if zoom not in zooms:
            bisect.insort(zooms, zoom)
        if 0.7 not in exposures:
            exposures.insert(zooms.index(zoom), 0.7)
    else:
        if zoom in zooms:
            zooms.remove(zoom)
        if 0.7 in exposures:
            exposures.remove(0.7)


@overrideMethod(SniperCamera, 'enable')
def new_SniperCamera_enable(base, self, *a, **kw):
    if config.data['enabled']:
        addValues(self._SniperCamera__cfg['zooms'], self._SniperCamera__dynamicCfg['zoomExposure'])
    base(self, *a, **kw)
    if config.data['enabled'] and config.data['isEnabled']:
        hide_hull(True)


@overrideMethod(SniperCamera, 'disable')
def new_SniperCamera_disable(base, self):
    if config.data['enabled'] and config.data['isEnabled']:
        hide_hull(False)
    base(self)


def hide_hull(hide):
    player = BigWorld.player()
    vehicle = player.getVehicleAttached()
    if vehicle is not None and player.vehicleTypeDescriptor.name not in config.data['blacklist']:
        vehicle.show(hide)
        scaleMatrix = Math.Matrix()
        scaleMatrix.setScale((0.001,) * 3 if hide else (1.0,) * 3)
        vehicle.appearance.compoundModel.node(TankPartNames.GUN, scaleMatrix)


@overrideMethod(SniperControlMode, 'handleKeyEvent')
def new_SniperControlMode_handleKeyEvent(base, self, isDown, key, mods, event=None):
    if config.data['enabled'] and isDown and checkKeys(config.data['hotkey']):
        config.data['isEnabled'] = not config.data['isEnabled']
        hide_hull(config.data['isEnabled'])
        addValues(self._cam._SniperCamera__cfg['zooms'], self._cam._SniperCamera__dynamicCfg['zoomExposure'])
    base(self, isDown, key, mods, event)


@overrideMethod(SniperCamera, '_SniperCamera__getZooms')
def new_SniperCamera_getZooms(base, self):
    zooms = base(self)
    if not self._SniperCamera__cfg['increasedZoom'] and config.data['zoomValue'] in zooms:
        zooms.append(self._SniperCamera__cfg['zooms'][3])
    return zooms
