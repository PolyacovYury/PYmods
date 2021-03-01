import BigWorld
from functools import partial

__all__ = ('sendPanelMessage', 'checkKeys', 'refreshCurrentVehicle', 'Sound',)


def checkKeys(keys, key=None):  # thx to P0LIR0ID
    keySets = [data if not isinstance(data, int) else (data,) for data in keys]
    return (bool(keys) and all(any(BigWorld.isKeyDown(x) for x in keySet) for keySet in keySets)
            and (key is None or any(key in keySet for keySet in keySets)))


def refreshCurrentVehicle():
    from CurrentVehicle import g_currentPreviewVehicle, g_currentVehicle
    if g_currentPreviewVehicle.item:
        g_currentPreviewVehicle.hangarSpace.updatePreviewVehicle(g_currentPreviewVehicle.item)
    else:
        g_currentVehicle.refreshModel()
    from HeroTank import HeroTank
    for entity in HeroTank.allCameraObjects:
        if isinstance(entity, HeroTank):
            entity.recreateVehicle()


def sendPanelMessage(text='', colour='Green', panel='Player'):
    from gui.Scaleform.framework import WindowLayer
    from gui.shared.personality import ServicesLocator
    """
    panel = 'Player', 'Vehicle', 'VehicleError'
    colour = 'Red', 'Purple', 'Green', 'Gold', 'Yellow', 'Self'
    """
    battle_page = ServicesLocator.appLoader.getDefBattleApp().containerManager.getContainer(WindowLayer.VIEW).getView()
    if battle_page is not None:
        getattr(battle_page.components['battle%sMessages' % panel], 'as_show%sMessageS' % colour, None)(None, text)
    else:
        BigWorld.callback(0.5, partial(sendPanelMessage, text, colour, panel))


class Sound(object):
    def __init__(self, soundPath):
        import SoundGroups
        self.__sndPath = soundPath
        self.__sndTick = SoundGroups.g_instance.getSound2D(self.__sndPath)
        self.__isPlaying = True
        self.stop()

    @property
    def isPlaying(self):
        return self.__isPlaying

    @property
    def sound(self):
        return self.__sndTick

    def play(self):
        self.stop()
        if self.__sndTick:
            self.__sndTick.play()
        self.__isPlaying = True

    def stop(self):
        if self.__sndTick:
            self.__sndTick.stop()
        self.__isPlaying = False
