import PYmodsCore
from config import g_config
import skinLoader
import processor
import collision

g_config.load()
statistic_mod = PYmodsCore.Analytics(g_config.ID, g_config.version, 'UA-76792179-4')
