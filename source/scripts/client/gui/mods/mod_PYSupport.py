import BigWorld
from PlayerEvents import g_playerEvents
from adisp import process
from functools import partial
from helpers import dependency
from skeletons.connection_mgr import IConnectionManager


@process
def openBrowser(_):
    from gui.app_loader import g_appLoader
    app = g_appLoader.getDefLobbyApp()
    if app:
        from helpers import dependency
        from skeletons.gui.game_control import IBrowserController
        browserCtrl = dependency.instance(IBrowserController)
        browsers = browserCtrl._BrowserController__browsers
        browserID = max(browsers.keys()) + 1 if browsers else browserCtrl._BrowserController__browserIDGenerator.next()
        yield browserCtrl.load(
            url='http://pymodsproject.ru/download/', browserID=browserID, useBrowserWindow=False,
            showBrowserCallback=lambda: (BigWorld.callback(3.5, partial(browserCtrl.delBrowser, browserID)),
                                         g_playerEvents.onAccountShowGUI.__isub__(openBrowser)))


dependency.instance(IConnectionManager).onConnected += lambda: g_playerEvents.onAccountShowGUI.__iadd__(openBrowser)
print "Support (v.1.0, %(file_compile_date)s) for Polyacov_Yury: provided."
