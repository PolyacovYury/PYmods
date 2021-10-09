from OpenModsCore import loadJson, remDups


def migrateSettings(g_config, old_data, new_data):
    whitelist = []
    for team in g_config.teams:
        had_WL = (team + 'Whitelist') in old_data
        old_WL = (x.strip() for x in old_data.pop(team + 'Whitelist', '').split(',') if x.strip())
        new_data[team] = new_data.get(team, old_data.pop('swap' + team.capitalize(), True) and (not had_WL or bool(old_WL)))
        whitelist.extend(old_WL)
    new_data['whitelist'] = sorted(remDups(whitelist + new_data.get('whitelist', [])))


# noinspection PyUnresolvedReferences
def migrateConfigs(g_config):
    settings = loadJson(g_config.ID, 'settings', g_config.settings, g_config.configPath)
    if settings and 'remods' in settings:
        for name, remodData in settings['remods'].items():
            if not remodData.pop('enabled', True):
                print g_config.LOG, 'WARNING! Disabled remod detected:', name + (
                    '. Remod disabling is not supported anymore, delete unneeded remods. '
                    'If game crashed - this is, probably, the reason.')
            migrateSettings(g_config, remodData, remodData)
        loadJson(g_config.ID, 'settings', settings['remods'], g_config.configPath, True)

    selectedData = loadJson(g_config.ID, 'remodsCache', g_config.selectedData, g_config.configPath)
    for key in selectedData.keys():
        if not key.islower():
            selectedData[key.lower()] = selectedData.pop(key)
        if key.lower() == 'remod':
            del selectedData[key.lower()]
    loadJson(g_config.ID, 'remodsCache', selectedData, g_config.configPath, True)
