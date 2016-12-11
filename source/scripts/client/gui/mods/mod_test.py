# -*- coding: utf-8 -*-
import codecs
import json
import os
import re
import traceback


class Test:
    def __init__(self):
        self.ID = 'TestConf'
        self.conf_changed = False

    def byte_ify(self, inputs):
        if inputs:
            if isinstance(inputs, dict):
                return {self.byte_ify(key): self.byte_ify(value) for key, value in inputs.iteritems()}
            elif isinstance(inputs, list):
                return [self.byte_ify(element) for element in inputs]
            elif isinstance(inputs, tuple):
                return tuple(self.byte_ify(element) for element in inputs)
            elif isinstance(inputs, unicode):
                # noinspection PyArgumentEqualDefault
                return inputs.encode('utf-8')
            else:
                return inputs
        return inputs

    @staticmethod
    def json_comments(text):
        regex = r'\s*(\/{2}).*$'
        regex_inline = r'(:?(?:\s)*([A-Za-zА-Яа-я\d\.{}]*)|((?<=\").*\"),?)(?:\s)*((((\/{2})).*)|)$'
        lines = text.split('\n')
        excluded = []
        for index, line in enumerate(lines):
            if re.search(regex, line):
                if re.search(r'^' + regex, line, re.IGNORECASE):
                    excluded.append(lines[index])
                elif re.search(regex_inline, line):
                    lines[index] = re.sub(regex_inline, r'\1', line)
        for line in excluded:
            lines.remove(line)
        return '\n'.join(lines), excluded

    @staticmethod
    def json_dumps(conf):
        return json.dumps(conf, sort_keys=True, indent=4, ensure_ascii=False, encoding='utf-8-sig', separators=(',', ': '))

    def loadJson(self, name, oldConfig, path, save=False, rewrite=True):
        config_new = oldConfig
        if not os.path.exists(path):
            os.makedirs(path)
        new_path = '%s%s.json' % (path, name)
        if save:
            if os.path.isfile(new_path):
                config_newS = ''
                config_oldS = self.json_dumps(oldConfig)
                try:
                    with codecs.open(new_path, 'r', encoding='utf-8-sig') as json_file:
                        config_newS = json_file.read()
                        config_newExcl = self.byte_ify(self.json_comments(config_newS)[1])
                except StandardError:
                    traceback.print_exc()
                    print config_newS.replace('\r', '')
                    config_newS = config_oldS
                    config_newExcl = []
                config_newD = self.byte_ify(config_newS)
                conf_newL = config_newD.split('\n')
                self.conf_changed = False
                if not rewrite:
                    def checkSubDict(oldDict, start_idx, end_idx):
                        decer = json.JSONDecoder(encoding='utf-8-sig')
                        encer = json.JSONEncoder(encoding='utf-8-sig')
                        new_end_idx = None
                        subLevels = 0
                        for idx in xrange(start_idx, end_idx):
                            newLine = conf_newL[idx]
                            if newLine in config_newExcl:
                                continue
                            if new_end_idx >= idx:
                                continue
                            if ':' in newLine:
                                new_key, new_value = newLine.split(':', 1)
                                new_key = new_key.strip().replace('"', '')
                                new_value = self.json_comments(new_value)[0].strip()
                                if new_value.endswith(','):
                                    new_value = ''.join(new_value.rsplit(',', 1)).strip()
                                if new_key in oldDict:
                                    if new_value == '{':
                                        subKey = new_key
                                        new_start_idx = idx
                                        new_end_idx = idx
                                        while new_end_idx < end_idx:
                                            curNewLine = self.byte_ify(self.json_comments(conf_newL[new_end_idx])[0])
                                            if '{' in curNewLine and new_end_idx > new_start_idx:
                                                subLevels += 1
                                            if '}' not in curNewLine:
                                                new_end_idx += 1
                                                continue
                                            if '}' in self.json_comments(curNewLine)[0].strip():
                                                if subLevels:
                                                    subLevels -= 1
                                                else:
                                                    break
                                        checkSubDict(oldDict[subKey], new_start_idx + 1, new_end_idx - 1)
                                    elif oldDict[new_key] != decer.decode(new_value):
                                        conf_newL[idx] = ':'.join(
                                            (newLine.split(':', 1)[0], newLine.split(':', 1)[1].replace(
                                                new_value, '%s' % encer.encode(oldDict[new_key]), 1)))
                                        self.conf_changed = True
                    try:
                        checkSubDict(oldConfig, 0, len(conf_newL))
                    except StandardError:
                        print new_path
                        traceback.print_exc()

                else:
                    self.conf_changed = not config_oldS == \
                        self.json_dumps(self.byte_ify(json.loads(self.json_comments(config_newD)[0])))
                    if self.conf_changed:
                        conf_newL = self.byte_ify(config_oldS).split('\n')
                if self.conf_changed:
                    print '%s: updating config: %s' % (self.ID, new_path)
                    with codecs.open(new_path, 'w', encoding='utf-8-sig') as json_file:
                        json_file.write(self.byte_ify('\n'.join(conf_newL)))
                        config_new = oldConfig
            else:
                with codecs.open(new_path, 'w', encoding='utf-8-sig') as json_file:
                    data = self.json_dumps(oldConfig)
                    json_file.write(self.byte_ify(data))
                    config_new = oldConfig
        elif os.path.isfile(new_path):
            data = ''
            excluded = []
            try:
                with codecs.open(new_path, 'r', encoding='utf-8-sig') as json_file:
                    data, excluded = self.json_comments(json_file.read())
                    config_new = self.byte_ify(json.loads(data))
            except StandardError:
                print new_path
                traceback.print_exc()
                if excluded:
                    print data
        else:
            with codecs.open(new_path, 'w', encoding='utf-8-sig') as json_file:
                data = self.json_dumps(oldConfig)
                json_file.write(self.byte_ify(data))
                config_new = oldConfig
                print '%s: ERROR: Config not found, creating default: %s' % (self.ID, new_path)
        return config_new

test = Test()
Conf = test.loadJson('mod_UT_announcer', {}, 'D:/Games/World_of_Tanks/res_mods/0.9.16/scripts/client/gui/mods/')
Conf['colorBlind'] = True
test.loadJson('mod_UT_announcer', Conf, 'D:/Games/World_of_Tanks/res_mods/0.9.16/scripts/client/gui/mods/', True, False)
