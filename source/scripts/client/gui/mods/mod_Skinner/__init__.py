__modID__ = '%(mod_ID)s'
__date__ = '%(file_compile_date)s'
import PYmodsCore
from config import g_config
import loader
import processor


statistic_mod = PYmodsCore.Analytics(g_config.ID, g_config.version, 'UA-76792179-4')
