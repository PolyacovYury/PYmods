import glob
import os
from PYmodsCore import remDups, loadJson
from collections import namedtuple, OrderedDict
from PYmodsCore.config.json_reader import JSONLoader

Wheel = namedtuple('Wheel', ('isLeft', 'radius', 'nodeName', 'isLeading', 'leadingSyncAngle'))
WheelGroup = namedtuple('WheelGroup', ('isLeft', 'template', 'count', 'startIndex', 'radius'))
WheelsConfig = namedtuple('WheelsConfig', ('lodDist', 'groups', 'wheels'))
TrackNode = namedtuple('TrackNode', ('name', 'isLeft', 'initialOffset', 'leftNodeName', 'rightNodeName', 'damping',
                                     'elasticity', 'forwardElasticityCoeff', 'backwardElasticityCoeff'))
TrackMaterials = namedtuple('TrackNode', ('lodDist', 'leftMaterial', 'rightMaterial', 'textureScale'))
TrackParams = namedtuple('TrackNode', ('thickness', 'maxAmplitude', 'maxOffset', 'gravity'))
GroundNode = namedtuple('GroundNode', ('name', 'isLeft', 'minOffset', 'maxOffset'))
GroundNodeGroup = namedtuple('GroundNodeGroup', ('isLeft', 'minOffset', 'maxOffset', 'template', 'count', 'startIndex'))
Traces = namedtuple('Traces', ('lodDist', 'bufferPrefs', 'textureSet', 'centerOffset', 'size'))
SplineConfig = namedtuple('SplineConfig', (
    'segmentModelLeft', 'segmentModelRight', 'segmentLength', 'leftDesc', 'rightDesc', 'lodDist', 'segmentOffset',
    'segment2ModelLeft', 'segment2ModelRight', 'segment2Offset', 'atlasUTiles', 'atlasVTiles'))
NodesAndGroups = namedtuple('NodesAndGroups', ('nodes', 'groups'))
chassis_params = ('traces', 'tracks', 'wheels', 'groundNodes', 'trackNodes', 'splineDesc', 'trackParams')


def readOrdered(new_path):
    import json
    config_new = None
    if os.path.isfile(new_path):
        data, excluded, success = JSONLoader.json_file_read(new_path, False)
        if success:
            try:
                config_new = JSONLoader.byte_ify(json.loads(data, object_pairs_hook=OrderedDict))
            except StandardError as e:
                print new_path
                print e
    return config_new


def migrateSettings(g_config, old_data, new_data):
    whitelist = []
    for team in g_config.teams:
        had_WL = (team + 'Whitelist') in old_data
        old_WL = (x.strip() for x in old_data.pop(team + 'Whitelist', '').split(',') if x.strip())
        new_data[team] = new_data.get(team, old_data.pop('swap' + team.capitalize(), True) and (not had_WL or bool(old_WL)))
        whitelist.extend(old_WL)
    new_data['whitelist'] = sorted(remDups(whitelist + new_data.get('whitelist', [])))


def migrateConfigs(g_config):
    settings = loadJson(g_config.ID, 'settings', g_config.settings, g_config.configPath)
    if settings and 'remods' in settings:
        for sname, remodData in settings['remods'].items():
            if not remodData.pop('enabled', True):
                print g_config.ID + ': WARNING! Disabled remod detected:', sname + (
                    '. Remod disabling is not supported anymore, delete unneeded remods. '
                    'If game crashed - this is, probably, the reason.')
            migrateSettings(g_config, remodData, remodData)
        loadJson(g_config.ID, 'settings', settings['remods'], g_config.configPath, True)

    selectedData = loadJson(g_config.ID, 'remodsCache', g_config.modelsData['selected'], g_config.configPath)
    for key in selectedData.keys():
        if not key.islower():
            selectedData[key.lower()] = selectedData.pop(key)
        if key.lower() == 'remod':
            del selectedData[key.lower()]
    loadJson(g_config.ID, 'remodsCache', selectedData, g_config.configPath, True)

    configsPath = g_config.configPath + 'remods/*.json'
    for configPath in glob.iglob(configsPath):
        sname = os.path.basename(configPath).split('.')[0]
        old_conf = readOrdered(configPath)
        if not old_conf:
            print g_config.ID + ': error while reading', os.path.basename(configPath) + '.'
            continue
        new_conf = OrderedDict()
        new_conf['message'] = old_conf.get('authorMessage', old_conf.get('message', ''))
        migrateSettings(g_config, old_conf, new_conf)
        for key, val in old_conf.items():
            if key in ('authorMessage',) or 'Whitelist' in key or 'swap' in key:
                continue
            elif key == 'engine':
                val = OrderedDict((k, v) for k, v in val.iteritems() if 'wwsound' not in k)
            elif key == 'gun':
                val = OrderedDict((k, v) for k, v in val.iteritems() if 'ffect' not in k)
            elif key == 'hull':
                if 'exhaust' in val and 'nodes' in val['exhaust'] and isinstance(val['exhaust']['nodes'], basestring):
                    val['exhaust']['nodes'] = val['exhaust']['nodes'].split()
            elif key == 'chassis':
                val = migrate_chassis_config(val)
            new_conf[key] = val
        loadJson(g_config.ID, sname, new_conf, g_config.configPath + 'remods/', True, sort_keys=False)


def migrate_chassis_config(config):  # please send data['chassis'] here
    new_config = OrderedDict()
    for key in config:
        if key not in chassis_params:
            if 'wwsound' not in key:  # sounds are obsolete
                new_config[key] = config[key]
            if key == 'AODecals' and config[key] and isinstance(config[key][0], dict):
                new_config[key] = [[row for row in decal['transform'].values()] for decal in config[key]]
            continue  # config already converted
        if isinstance(config[key], basestring):
            obj = eval(config[key])
            if isinstance(obj, dict):  # ancient config
                if key == 'traces':
                    obj = Traces(**obj)
                elif key == 'tracks':
                    obj = TrackMaterials(**obj)
                elif key == 'wheels':
                    obj = WheelsConfig(
                        lodDist=obj['lodDist'],
                        groups=[d if hasattr(d, '_fields') else WheelGroup(*d) for d in obj['groups']],
                        wheels=[d if hasattr(d, '_fields') else Wheel(d[0], d[2], d[1], d[3], d[4]) for d in obj['wheels']])
                elif key == 'groundNodes':
                    obj = NodesAndGroups(
                        nodes=[d if hasattr(d, '_fields') else GroundNode(d[1], d[0], d[2], d[3]) for d in obj['nodes']],
                        groups=[d if hasattr(d, '_fields') else GroundNodeGroup(d[0], d[4], d[5], d[1], d[2], d[3])
                                for d in obj['groups']])
                elif key == 'trackNodes':
                    obj = NodesAndGroups(nodes=[
                        d if hasattr(d, '_fields') else TrackNode(d[0], d[1], d[2], d[5], d[6], d[4], d[3], d[7], d[8])
                        for d in obj['nodes']], groups=[])
                elif key == 'splineDesc':
                    obj = SplineConfig(**obj)
                elif key == 'trackParams':
                    obj = TrackParams(**obj)
            if not isinstance(obj, dict):  # we assume that we have a namedtuple, if we don't - something malicious, so crash
                if key == 'traces':
                    obj = obj._replace(size=list(obj.size))
                obj = OrderedDict(zip(obj._fields, obj))
                keys = ()
                if key == 'wheels':
                    keys = ('groups', 'wheels')
                elif key in ('groundNodes', 'trackNodes'):
                    keys = ('nodes', 'groups')
                for sub in keys:
                    obj[sub] = list(obj[sub])
                    for idx, value in enumerate(obj[sub]):
                        obj[sub][idx] = OrderedDict(zip(value._fields, value))
            new_config[key] = obj
        obj = new_config[key]
        newLodDist = new_config.get('chassisLodDistance')
        if key == 'wheels':
            lodDist = obj.pop('lodDist', None)
            if newLodDist is None and lodDist is not None:
                new_config['chassisLodDistance'] = lodDist
            for wheel in obj['wheels']:
                for s_key in ('index', 'hitTester', 'materials'):
                    wheel.setdefault(s_key, None)
                wheel.setdefault('position', (0, 0, 0))
        if key == 'groundNodes':
            for group in obj['groups']:
                if 'template' in group:
                    group['nodesTemplate'] = group.pop('template')
                group.setdefault('affectedWheelsTemplate', None)
                if 'count' in group:
                    group['nodesCount'] = group.pop('count')
                group.setdefault('collisionSamplesCount', 1)
                group.setdefault('hasLiftMode', False)
            for node in obj['nodes']:
                if 'name' in node:
                    node['nodeName'] = node.pop('name')
                node.setdefault('affectedWheelName', '')
                node.setdefault('collisionSamplesCount', 1)
                node.setdefault('hasLiftMode', False)
            obj.setdefault('activePostmortem', False)
            obj.setdefault('lodSettings', None)
        if key == 'trackNodes':
            obj.setdefault('activePostmortem', False)
            obj.setdefault('lodSettings', None)
        if key == 'traces':
            obj.setdefault('activePostmortem', False)
        if key == 'splineDesc' and 'segmentModelSets' not in obj:
            obj['segmentModelSets'] = OrderedDict([('default', OrderedDict([
                ('left', obj.pop('segmentModelLeft')),
                ('right', obj.pop('segmentModelRight')),
                ('secondLeft', obj.pop('segment2ModelLeft', '')),
                ('secondRight', obj.pop('segment2ModelRight', ''))]))])
    new_config.setdefault('leveredSuspension', None)
    return new_config
