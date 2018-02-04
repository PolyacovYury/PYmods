# coding=utf-8
import binascii
import zlib

import codecs
import json
import os
import re
import traceback

__all__ = ['loadJson']


class JSONObjectEncoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        super(JSONObjectEncoder, self).__init__(*args, **kwargs)
        self.current_indent = 0
        self.current_indent_str = ""

    def encode(self, o):
        try:
            # Special Processing for lists
            if isinstance(o, (list, tuple)):
                primitives_only = True
                for item in o:
                    if isinstance(item, dict):
                        primitives_only = False
                        break
                output = []
                if primitives_only:
                    for item in o:
                        output.append(self.encode(item))
                    return "[" + ", ".join(output) + "]"
                else:
                    self.current_indent += self.indent
                    self.current_indent_str = " " * self.current_indent
                    for item in o:
                        output.append(self.current_indent_str + self.encode(item))
                    self.current_indent -= self.indent
                    self.current_indent_str = " " * self.current_indent
                    return "[\n" + ",\n".join(output) + "\n" + self.current_indent_str + "]"
            elif isinstance(o, dict):
                output = []
                self.current_indent += self.indent
                self.current_indent_str = " " * self.current_indent
                keys = o.keys()
                if self.sort_keys:
                    keys = sorted(keys)
                for key in keys:
                    output.append(self.current_indent_str + json.dumps(key) + ": " + self.encode(o[key]))
                self.current_indent -= self.indent
                self.current_indent_str = " " * self.current_indent
                return "{\n" + ",\n".join(output) + "\n" + self.current_indent_str + "}"
            else:
                return super(self.__class__, self).encode(o)
        except StandardError:
            return str(o)


class JSONLoader:
    @classmethod
    def byte_ify(cls, inputs):
        if inputs:
            if isinstance(inputs, dict):
                return {cls.byte_ify(key): cls.byte_ify(value) for key, value in inputs.iteritems()}
            elif isinstance(inputs, list):
                return [cls.byte_ify(element) for element in inputs]
            elif isinstance(inputs, tuple):
                return tuple(cls.byte_ify(element) for element in inputs)
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
    def encrypt(line):
        return line.encode('zlib').encode('base64')

    @staticmethod
    def decrypt(line, encrypted):
        if not line:
            return encrypted, line
        try:
            return True, line.decode('base64').decode('zlib')
        except (binascii.Error, zlib.error):
            return False, line

    @staticmethod
    def json_dumps(conf, sort_keys):
        # noinspection PyArgumentEqualDefault
        return json.dumps(conf, sort_keys=sort_keys, indent=4, cls=JSONObjectEncoder,
                          ensure_ascii=False, encoding='utf-8', separators=(',', ': '))

    @classmethod
    def json_file_write(cls, new_path, data, encrypted):
        kwargs = {'mode': 'w', 'encoding': 'utf-8-sig'} if not encrypted else {'mode': 'wb'}
        with codecs.open(new_path, **kwargs) as json_file:
            writeToConf = cls.byte_ify(data)
            if encrypted:
                writeToConf = cls.encrypt(writeToConf)
            json_file.write(writeToConf)

    @classmethod
    def checkSubDict(cls, oldDict, conf_newL, config_newExcl, start_idx, end_idx):
        conf_changed = False
        decer = json.JSONDecoder(encoding='utf-8')
        # noinspection PyArgumentEqualDefault
        encer = json.JSONEncoder(encoding='utf-8')
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
                new_value = cls.json_comments(new_value)[0].strip()
                if new_value.endswith(','):
                    new_value = ''.join(new_value.rsplit(',', 1)).strip()
                if new_key in oldDict:
                    if new_value == '{':
                        subKey = new_key
                        new_start_idx = idx
                        new_end_idx = idx
                        while new_end_idx < end_idx:
                            curNewLine = cls.byte_ify(cls.json_comments(conf_newL[new_end_idx])[0])
                            if '{' in curNewLine and new_end_idx >= new_start_idx:
                                subLevels += 1
                            if '}' not in curNewLine:
                                new_end_idx += 1
                                continue
                            else:
                                subLevels -= 1
                            if '}' in cls.json_comments(curNewLine)[0].strip():
                                if subLevels > 0:
                                    subLevels -= 1
                                else:
                                    break
                        conf_changed |= cls.checkSubDict(
                            oldDict[subKey], conf_newL, config_newExcl, new_start_idx + 1, new_end_idx)
                    elif oldDict[new_key] != decer.decode(new_value):
                        conf_newL[idx] = ':'.join(
                            (newLine.split(':', 1)[0], newLine.split(':', 1)[1].replace(
                                new_value, '%s' % encer.encode(oldDict[new_key]), 1)))
                        conf_changed = True
        return conf_changed

    @classmethod
    def loadJson(cls, ID, name, oldConfig, path, save=False, rewrite=True, quiet=False, encrypted=False, sort_keys=True):
        config_new = oldConfig
        if not os.path.exists(path):
            os.makedirs(path)
        new_path = '%s%s.json' % (path, name)
        if save:
            if os.path.isfile(new_path):
                config_newS = ''
                config_oldS = cls.json_dumps(oldConfig, sort_keys)
                try:
                    kwargs = {'mode': 'r', 'encoding': 'utf-8-sig'} if not encrypted else {'mode': 'rb'}
                    with codecs.open(new_path, **kwargs) as json_file:
                        isEncrypted, config_newS = cls.decrypt(json_file.read(), encrypted)
                        if not isEncrypted and encrypted:
                            config_newS = config_newS.decode('utf-8-sig')
                        config_newExcl = cls.byte_ify(cls.json_comments(config_newS)[1])
                except StandardError as e:
                    print new_path
                    print e
                    if not encrypted:
                        print config_newS.replace('\r', '')
                    config_newS = config_oldS
                    config_newExcl = []
                config_newD = cls.byte_ify(config_newS)
                conf_newL = config_newD.split('\n')
                conf_changed = False
                if not rewrite:
                    try:
                        conf_changed = cls.checkSubDict(oldConfig, conf_newL, config_newExcl, 0, len(conf_newL))
                    except StandardError as e:
                        print new_path
                        print e

                else:
                    conf_changed = not config_oldS == cls.json_dumps(
                        cls.byte_ify(json.loads(cls.json_comments(config_newD)[0])), sort_keys)
                    if conf_changed:
                        conf_newL = cls.byte_ify(config_oldS).split('\n')
                if conf_changed:
                    if not quiet:
                        print '%s: updating config: %s' % (ID, new_path)
                    cls.json_file_write(new_path, '\n'.join(conf_newL), encrypted)
            else:
                cls.json_file_write(new_path, cls.json_dumps(oldConfig, sort_keys), encrypted)
        elif os.path.isfile(new_path):
            data = ''
            excluded = []
            try:
                kwargs = {'mode': 'r', 'encoding': 'utf-8-sig'} if not encrypted else {'mode': 'rb'}
                with codecs.open(new_path, **kwargs) as json_file:
                    isEncrypted, confData = cls.decrypt(json_file.read(), encrypted)
                    if not isEncrypted and encrypted:
                        confData = confData.decode('utf-8-sig')
                    data, excluded = cls.json_comments(confData)
                    config_new = cls.byte_ify(json.loads(data))
            except StandardError:
                print new_path
                traceback.print_exc()
                if excluded and not encrypted:
                    print data
        else:
            cls.json_file_write(new_path, cls.json_dumps(oldConfig, sort_keys), encrypted)
            print '%s: ERROR: Config not found, creating default: %s' % (ID, new_path)
        return config_new


loadJson = JSONLoader.loadJson
