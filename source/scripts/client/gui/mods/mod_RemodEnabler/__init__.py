import PYmodsCore
from config import g_config
import skinLoader
import processor
import collision

g_config.load()
statistic_mod = PYmodsCore.Analytics(g_config.ID, g_config.version.split(' ', 1)[0], 'UA-76792179-4')
