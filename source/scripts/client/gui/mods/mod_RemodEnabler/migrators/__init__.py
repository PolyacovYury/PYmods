import os

from . import json_update, remod_json_update, remod_json_to_xml


def migrateConfigs(g_config):
    json_update.migrateConfigs(g_config)


def migrateRemod(g_config, path, name, json_data):
    new_conf = remod_json_update.migrateRemod(g_config, json_data)
    remod_json_to_xml.save_as_xml(g_config, path, name, new_conf)
    os.remove(path + '/' + name + '.json')
