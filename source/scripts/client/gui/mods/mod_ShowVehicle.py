import BigWorld
import Keys
import bisect
from AvatarInputHandler.DynamicCameras.SniperCamera import SniperCamera
from AvatarInputHandler.control_modes import SniperControlMode
from OpenModsCore import Analytics, SimpleConfigInterface, checkKeys, find_attr, overrideMethod
from gui.Scaleform.daapi.view.battle.shared.crosshair import CrosshairPanelContainer
from gui.Scaleform.locale.INGAME_GUI import INGAME_GUI
from helpers import i18n
from vehicle_systems.tankStructure import TankPartNames


class ConfigInterface(SimpleConfigInterface):
    def __init__(self):
        self.vehicleVisible = True
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.1.0 (%(file_compile_date)s)'
        self.author = 'by Polyacov_Yury (formerly by l3VGV, supported by KL1SK)'
        self.modsGroup = 'PYmods'
        self.modSettingsID = 'PYmodsGUI'
        self.defaultKeys = {'hotkey': [Keys.KEY_F11]}
        self.data = {
            'enabled': True, 'enableBeforeBattle': True, 'hideTurret': False, 'changeZoom': True, 'zoomValue': 0.8,
            'blacklist': 'germany:Karl,ussr:R00_T_50_2,usa:A00_T110E5,france:F00_AMX_50Foch_155',
            'hotkey': self.defaultKeys['hotkey'],
        }
        self.i18n = {
            'name': 'Show vehicle in sniper mode',
            'UI_setting_enableBeforeBattle_text': 'Active at battle start',
            'UI_setting_enableBeforeBattle_tooltip': (
                'Vehicle hull is displayed in sniper mode on battle start.\n'
                'If this is off, the hotkey press result is preserved until game restart.'),
            'UI_setting_changeZoom_text': 'Add another zoom value',
            'UI_setting_changeZoom_tooltip':
                'The mod adds another zoom value in sniper mode so that you could see your vehicle hull better.',
            'UI_setting_hideTurret_text': 'Hide vehicle turret',
            'UI_setting_hideTurret_tooltip': 'If this is off - only vehicle gun is hidden.',
            'UI_setting_zoomValue_text': 'Additional zoom value',
            'UI_setting_zoomValue_tooltip': 'The value that gets added into the list of zoom values.',
            'UI_setting_blacklist_text': 'Vehicle blacklist',
            'UI_setting_blacklist_tooltip': (
                'The list of vehicles that do not get processed by the mod.\n\n'
                'I have no idea, why the users wanted this, since the mod has a toggle hotkey, but ok.'),
            'UI_setting_hotkey_text': 'Toggle hotkey',
            'UI_setting_hotkey_tooltip': 'This hotkey toggles vehicle hull displaying.\nWorks only in sniper mode.'}
        super(ConfigInterface, self).init()

    def createTemplate(self):
        return {
            'modDisplayName': self.i18n['name'],
            'enabled': self.data['enabled'],
            'column1': [
                self.tb.createControl('changeZoom'),
                self.tb.createStepper('zoomValue', 0.1, 1.0, 0.1, True),
                self.tb.createEmpty(),
                self.tb.createControl('blacklist', self.tb.types.TextInput, 800),
            ],
            'column2': [
                self.tb.createHotKey('hotkey'),
                self.tb.createControl('enableBeforeBattle'),
                self.tb.createControl('hideTurret'),
            ]}


config = ConfigInterface()
analytics = Analytics(config.ID, config.version, 'UA-76792179-20')


@overrideMethod(SniperCamera, '__showVehicle')
def new_SniperCamera__showVehicle(base, self, visible, changing=False, *args, **kwargs):
    if not config.data['enabled']:
        return base(self, visible, *args, **kwargs)

    zoom = self._SniperCamera__aimingSystem.overrideZoom(config.data['zoomValue'])
    zooms, exposures = self._cfg['zooms'], self._SniperCamera__dynamicCfg['zoomExposure']
    if config.vehicleVisible and config.data['changeZoom']:
        if zoom not in zooms:
            bisect.insort(zooms, zoom)
        if 0.7 not in exposures:
            exposures.insert(zooms.index(zoom), 0.7)
    else:
        if zoom in zooms:
            zooms.remove(zoom)
        if 0.7 in exposures:
            exposures.remove(0.7)

    if changing:  # config.vehicleVisible == visible
        setGunVisible(not visible)
        return base(self, visible, *args, **kwargs)
    elif visible:
        setGunVisible(visible)
        return base(self, visible, *args, **kwargs)
    visible = config.vehicleVisible
    setGunVisible(not visible)
    return base(self, visible, *args, **kwargs)


def setGunVisible(visible):
    player = BigWorld.player()
    vehicle = player.getVehicleAttached()
    if vehicle is None or player.vehicleTypeDescriptor.name in config.data['blacklist']:
        return
    model = vehicle.model
    vehicle.appearance.showStickers(visible)
    parts = (TankPartNames.GUN,)
    if config.data['hideTurret']:
        parts = (TankPartNames.TURRET,) + parts
    for part in parts:
        partHandleNotFoundErrorCode = 0xFFFFFFFFL
        partHandle = model.findPartHandleByNode(model.node(part))
        if partHandle == partHandleNotFoundErrorCode:
            continue
        model.setPartVisible(partHandle, visible)


@overrideMethod(SniperControlMode, 'handleKeyEvent')
def new_SniperControlMode_handleKeyEvent(base, self, isDown, key, mods, event=None, *args, **kwargs):
    if config.data['enabled'] and isDown and checkKeys(config.data['hotkey'], key):
        config.vehicleVisible = not config.vehicleVisible
        self._cam._SniperCamera__showVehicle(config.vehicleVisible, True)
    return base(self, isDown, key, mods, event, *args, **kwargs)


@overrideMethod(SniperCamera, '__getZooms')
def new_SniperCamera_getZooms(base, self, *args, **kwargs):
    zooms = base(self, *args, **kwargs)
    if not self._cfg['increasedZoom'] and config.data['zoomValue'] in zooms:
        zooms.append(self._cfg['zooms'][3])
    return zooms


@overrideMethod(CrosshairPanelContainer, 'as_setZoomS')
def new_CrosshairPanelContainer_as_setZoomS(base, self, zoomStr):
    if not zoomStr:
        zoomFactor = find_attr(self, '__zoomFactor')
        zoomStr = (i18n.makeString(INGAME_GUI.AIM_ZOOM).replace('%(zoom)d', '%(zoom)s')) % {'zoom': round(zoomFactor, 2)}
    return base(self, zoomStr)
