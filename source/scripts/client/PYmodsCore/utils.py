# -*- coding: utf-8 -*-
import BigWorld
import inspect
import random
import sys
import threading
import urllib
import urllib2
from PlayerEvents import g_playerEvents
from constants import AUTH_REALM
from functools import partial, update_wrapper

MAX_CHAT_MESSAGE_LENGTH = 220
__all__ = ['pickRandomPart', 'sendMessage', 'sendChatMessage', 'remDups', 'checkKeys', 'refreshCurrentVehicle', 'Analytics',
           'Sound', 'objToDict', 'overrideMethod']


def checkKeys(keys, key=None):  # thx to P0LIR0ID
    keySets = [data if not isinstance(data, int) else (data,) for data in keys]
    return (bool(keys) and all(any(BigWorld.isKeyDown(x) for x in keySet) for keySet in keySets)
            and (key is None or any(key in keySet for keySet in keySets)))


def remDups(seq):  # Dave Kirby, order preserving
    seen = set()
    return [x for x in seq if x not in seen and not seen.add(x)]


def overrideMethod(obj, prop, getter=None, setter=None, deleter=None):
    """
    :param obj: object, which attribute needs overriding
    :param prop: attribute name (can be not mangled), attribute must be callable
    :param getter: fget function or None
    :param setter: fset function or None
    :param deleter: fdel function or None
    :return function: unmodified getter or, if getter is None and src is not property, decorator"""

    if inspect.isclass(obj) and prop.startswith('__') and prop not in dir(obj) + dir(type(obj)):
        prop = obj.__name__ + prop
        if not prop.startswith('_'):
            prop = '_' + prop
    src = getattr(obj, prop)
    if type(src) is property and (getter or setter or deleter):
        props = []
        for func, fType in ((getter, 'fget'), (setter, 'fset'), (deleter, 'fdel')):
            assert func is None or callable(func), fType + ' is not callable!'
            props.append(partial(func, getattr(src, fType)) if func else getattr(src, fType))
        setattr(obj, prop, property(*props))
        return getter
    elif getter:
        getter_orig = getter
        assert callable(src), 'Source property is not callable!'
        assert callable(getter_orig), 'Handler is not callable!'
        while isinstance(getter, partial):
            getter = getter.func

        def getter_new(*a, **k):  # noinspection PyUnusedLocal
            info = None
            try:
                return getter_orig(src, *a, **k)
            except Exception:  # Code to remove this wrapper from traceback
                info = sys.exc_info()
                new_tb = info[2].tb_next  # https://stackoverflow.com/q/44813333
                if new_tb is None:  # exception occurs inside this wrapper, not inside of getter_orig
                    new_tb = _generate_new_tb(getter.func_code)
                raise info[0], info[1], new_tb
            finally:
                del info

        try:
            update_wrapper(getter_new, getter)
        except AttributeError:
            pass
        if inspect.isclass(obj):
            if inspect.isfunction(src):
                getter_new = staticmethod(getter_new)
            elif getattr(src, '__self__', None) is not None:
                getter_new = classmethod(getter_new)
        setattr(obj, prop, getter_new)
        return getter_orig
    else:
        return partial(overrideMethod, obj, prop)


def _generate_new_tb(co):  # https://unterwaditzer.net/2018/python-custom-tracebacks.html
    ns = {}
    exec (compile(''.join(('\n' * (co.co_firstlineno - 1), 'def ', co.co_name, '(): 1/0')), co.co_filename, 'exec'), ns)
    tb_obj = None
    try:
        ns[co.co_name]()
    except ZeroDivisionError:
        tb_obj = sys.exc_info()[2].tb_next
    return tb_obj


def objToDict(obj):
    if isinstance(obj, list):
        return [objToDict(o) for o in obj]
    elif hasattr(obj, 'toDict'):
        return {k: objToDict(v) for k, v in obj.toDict().iteritems()}
    elif isinstance(obj, dict):  # just in case
        return {k: objToDict(v) for k, v in obj.iteritems()}
    return obj


def pickRandomPart(variantList, lastID, isRandom=True):
    if not variantList:
        return ['', -1]
    elif len(variantList) == 1:
        return variantList[0], 0
    newID = lastID
    while isRandom and newID == lastID:
        newID = random.randrange(len(variantList))
    if not isRandom:
        newID = (newID + 1) % len(variantList)
    return variantList[newID], newID


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


def sendMessage(text='', colour='Green', panel='Player'):
    from gui.Scaleform.framework import ViewTypes
    from gui.shared.personality import ServicesLocator
    """
    panel = 'Player', 'Vehicle', 'VehicleError'
    colour = 'Red', 'Purple', 'Green', 'Gold', 'Yellow', 'Self'
    """
    battle_page = ServicesLocator.appLoader.getDefBattleApp().containerManager.getContainer(ViewTypes.VIEW).getView()
    if battle_page is not None:
        getattr(battle_page.components['battle%sMessages' % panel], 'as_show%sMessageS' % colour, None)(None, text)
    else:
        BigWorld.callback(0.5, partial(sendMessage, text, colour, panel))


def sendChatMessage(fullMsg, chanId, delay):
    currPart, remains = __splitChatMessage(fullMsg)
    __sendChatMessagePart(currPart, chanId)
    if remains:
        BigWorld.callback(delay / 1000.0, partial(sendChatMessage, remains, chanId, delay))


def __splitChatMessage(msg):
    if len(msg) <= MAX_CHAT_MESSAGE_LENGTH:
        return msg, ''
    strPart = msg[:MAX_CHAT_MESSAGE_LENGTH]
    splitPos = strPart.rfind(' ')
    if splitPos == -1:
        splitPos = MAX_CHAT_MESSAGE_LENGTH
    return msg[:splitPos], msg[splitPos:]


def __sendChatMessagePart(msg, chanId):
    import BattleReplay
    from messenger import MessengerEntry
    from messenger.m_constants import PROTO_TYPE
    from messenger.proto import proto_getter
    msg = msg.encode('utf-8')
    proto = proto_getter(PROTO_TYPE.BW_CHAT2).get()
    if proto is None or BattleReplay.isPlaying():
        MessengerEntry.g_instance.gui.addClientMessage('OFFLINE: %s' % msg, True)
    elif chanId in (0, 1):  # 0 == 'All', 1 == 'Team'
        proto.arenaChat.broadcast(msg, int(not chanId))
    elif chanId == 2:
        proto.unitChat.broadcast(msg, 1)


class Analytics(object):
    def __init__(self, description, version, ID, confList=None):
        from .events import game
        self.mod_description = description
        self.mod_id_analytics = ID
        self.mod_version = version
        self.confList = confList if confList else []
        self.analytics_started = False
        self._thread_analytics = None
        self.user = None
        self.playerName = ''
        self.old_user = None
        self.old_playerName = ''
        self.lang = ''
        self.lastTime = BigWorld.time()
        g_playerEvents.onAccountShowGUI += self.start
        game.fini.before.event += self.end

    def template(self, old=False):
        return {
            'v': 1,  # Protocol version
            'tid': '%s' % self.mod_id_analytics,  # Mod Analytics ID ('UA-XXX-Y')
            'cid': '%s' % self.old_user if old else self.user,  # User ID
            'an': '%s' % self.mod_description,  # Mod name
            'av': '%s %s' % (self.mod_description, self.mod_version),  # App version.
            'cd': '%s (Cluster: [%s], lang: [%s])' % (
                self.old_playerName if old else self.playerName, AUTH_REALM, self.lang),  # Readable user name
            'ul': '%s' % self.lang,  # client language
            't': 'event'  # Hit type
        }

    def analytics_start(self):
        from helpers import getClientLanguage
        self.lang = str(getClientLanguage()).upper()
        template = self.template()
        requestsPool = []
        if not self.analytics_started:
            requestsPool.append(dict(template, sc='start', t='screenview'))
            requestsPool.extend(dict(template, ec='config', ea='collect', el=conf.split('.')[0]) for conf in self.confList)
            self.analytics_started = True
            self.old_user = BigWorld.player().databaseID
            self.old_playerName = BigWorld.player().name
        elif BigWorld.time() - self.lastTime >= 1200:
            requestsPool.append(dict(template, ec='session', ea='keep'))
        for params in requestsPool:
            self.lastTime = BigWorld.time()
            urllib2.urlopen(url='https://www.google-analytics.com/collect?', data=urllib.urlencode(params)).read()

    # noinspection PyUnusedLocal
    def start(self, ctx):
        player = BigWorld.player()
        if self.user is not None and self.user != player.databaseID:
            self.old_user = player.databaseID
            self.old_playerName = player.name
            self._thread_analytics = threading.Thread(target=self.end, name=threading._newname('Analytics-%d'))
            self._thread_analytics.start()
        self.user = player.databaseID
        self.playerName = player.name
        self._thread_analytics = threading.Thread(target=self.analytics_start, name=threading._newname('Analytics-%d'))
        self._thread_analytics.start()

    def end(self, *_, **__):
        if self.analytics_started:
            from helpers import getClientLanguage
            self.lang = str(getClientLanguage()).upper()
            urllib2.urlopen(url='https://www.google-analytics.com/collect?',
                            data=urllib.urlencode(dict(self.template(True), sc='end', ec='session', ea='end'))).read()
            self.analytics_started = False


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
