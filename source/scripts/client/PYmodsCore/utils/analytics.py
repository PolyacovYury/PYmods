import BigWorld
import threading
import urllib
import urllib2
from PlayerEvents import g_playerEvents
from constants import AUTH_REALM

__all__ = ('Analytics',)


class Analytics(object):
    def __init__(self, description, version, ID, confList=None):
        from ..events import game
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

    def start(self, *_, **__):
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
