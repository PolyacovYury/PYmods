from PYmodsCore import loadJson
from . import json_update, remod_json_update


def migrateConfigs(g_config):
    json_update.migrateConfigs(g_config)


def migrateRemod(g_config, path, name, json_data):
    new_conf = remod_json_update.migrateRemod(g_config, json_data)
    loadJson(g_config.ID, name, new_conf, path, True, sort_keys=False)
