import Math
import ResMgr

import BigWorld
import Keys
import bisect
from AvatarInputHandler.DynamicCameras.SniperCamera import SniperCamera
from AvatarInputHandler.control_modes import SniperControlMode
from vehicle_systems.tankStructure import TankPartNames

showHull = True
changeZoom = True
zoom = 0.8
keySV = Keys.KEY_F11
blacklist = ['germany:Karl', 'ussr:R00_T_50_2', 'usa:A00_T110E5', 'france:F00_AMX_50Foch_155']
conf = ResMgr.openSection('../mods/configs/ShowVehicle/ShowVehicle.xml')
if conf is not None:
    changeZoom = conf.readBool('changeZoom', True)
    zoom = conf.readFloat('zoom', 0.8)
    keyS = conf.readString('hotKey', 'KEY_F11')
    if not hasattr(Keys, keyS):
        print 'ShowVehicle: hotkey config not valid, returned to KEY_F11'
    else:
        keySV = getattr(Keys, keyS)
    blacklist = [name.strip() for name in conf.readString('blacklist', '').split(',')]
else:
    print 'ShowVehicle: config not found, creating default'
    newConf = ResMgr.openSection('../mods/configs/ShowVehicle/ShowVehicle.xml', True)
    newConf.writeString('hotKey', 'KEY_F11')
    newConf.writeString('blacklist', ','.join(blacklist))
    newConf.writeBool('changeZoom', True)
    newConf.writeFloat('zoom', 0.8)
    newConf.save()


def addValues(zooms, exposures):
    if showHull:
        if zoom not in zooms:
            bisect.insort(zooms, zoom)
        if 0.7 not in exposures:
            exposures.insert(zooms.index(zoom), 0.7)
    else:
        if zoom in zooms:
            zooms.remove(zoom)
        if 0.7 in exposures:
            exposures.remove(0.7)


def sV_SniperCamera_enable(self, targetPos, saveZoom):
    addValues(self._SniperCamera__cfg['zooms'], self._SniperCamera__dynamicCfg['zoomExposure'])
    OLD_SniperCamera_enable(self, targetPos, saveZoom)
    if showHull:
        show_Hull(True)


def sV_SniperCamera_disable(self):
    if showHull:
        show_Hull(False)
    OLD_SniperCamera_disable(self)


def show_Hull(show):
    player = BigWorld.player()
    vehicle = player.getVehicleAttached()
    if vehicle is not None and player.vehicleTypeDescriptor.name not in blacklist:
        vehicle.show(show)
        scaleMatrix = Math.Matrix()
        scaleMatrix.setScale((0.001,) * 3 if show else (1.0,) * 3)
        vehicle.appearance.compoundModel.node(TankPartNames.GUN, scaleMatrix)


def sV_SniperControlMode_handleKeyEvent(self, isDown, key, mods, event=None):
    global showHull
    if isDown and key == keySV and mods == 0:
        showHull = not showHull
        show_Hull(showHull)
        addValues(self._cam._SniperCamera__cfg['zooms'], self._cam._SniperCamera__dynamicCfg['zoomExposure'])
    OLD_SniperControlMode_handleKeyEvent(self, isDown, key, mods, event)


def sV_SniperCamera_getZooms(self):
    zooms = OLD_SniperCamera_getZooms(self)
    if not self._SniperCamera__cfg['increasedZoom'] and zoom in zooms:
        zooms.append(self._SniperCamera__cfg['zooms'][3])
    return zooms


OLD_SniperCamera_enable = SniperCamera.enable
SniperCamera.enable = sV_SniperCamera_enable
OLD_SniperCamera_disable = SniperCamera.disable
SniperCamera.disable = sV_SniperCamera_disable
OLD_SniperControlMode_handleKeyEvent = SniperControlMode.handleKeyEvent
SniperControlMode.handleKeyEvent = sV_SniperControlMode_handleKeyEvent
OLD_SniperCamera_getZooms = SniperCamera._SniperCamera__getZooms
SniperCamera._SniperCamera__getZooms = sV_SniperCamera_getZooms
